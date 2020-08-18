#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
#
import math
import random

import numpy as np

from mlos.Spaces import Dimension, Hypergrid, SimpleHypergrid, ContinuousDimension, DiscreteDimension, CategoricalDimension, Point
from mlos.Spaces.HypergridAdapters import CategoricalToDiscreteHypergridAdapter, CompositeToSimpleHypergridAdapter
from mlos.Tracer import trace
from mlos.Logger import create_logger
from .DecisionTreeRegressionModel import DecisionTreeRegressionModel, DecisionTreeRegressionModelConfig
from .RegressionModel import RegressionModel, RegressionModelConfig
from .Prediction import Prediction




class HomogeneousRandomForestRegressionModelConfig(RegressionModelConfig):

    CONFIG_SPACE = SimpleHypergrid(
        name="homogeneous_random_forest_regression_model_config",
        dimensions=[
            DiscreteDimension(name="n_estimators", min=1, max=100),
            ContinuousDimension(name="features_fraction_per_estimator", min=0, max=1, include_min=False, include_max=True),
            ContinuousDimension(name="samples_fraction_per_estimator", min=0, max=1, include_min=False, include_max=True),
            CategoricalDimension(name="regressor_implementation", values=[DecisionTreeRegressionModel.__name__]),
        ]
    ).join(
        subgrid=DecisionTreeRegressionModelConfig.CONFIG_SPACE,
        on_external_dimension=CategoricalDimension(name="regressor_implementation", values=[DecisionTreeRegressionModel.__name__])
    )

    DEFAULT = Point(
        n_estimators=5,
        features_fraction_per_estimator=1,
        samples_fraction_per_estimator=1,
        regressor_implementation=DecisionTreeRegressionModel.__name__,
        decision_tree_regression_model_config=DecisionTreeRegressionModelConfig.DEFAULT
    )

    def __init__(
            self,
            n_estimators=DEFAULT.n_estimators,
            features_fraction_per_estimator=DEFAULT.features_fraction_per_estimator,
            samples_fraction_per_estimator=DEFAULT.samples_fraction_per_estimator,
            regressor_implementation=DEFAULT.regressor_implementation,
            decision_tree_regression_model_config: Point()=DEFAULT.decision_tree_regression_model_config
    ):
        self.n_estimators = n_estimators
        self.features_fraction_per_estimator = features_fraction_per_estimator
        self.samples_fraction_per_estimator = samples_fraction_per_estimator
        self.regressor_implementation = regressor_implementation

        assert regressor_implementation == DecisionTreeRegressionModel.__name__
        self.decision_tree_regression_model_config = DecisionTreeRegressionModelConfig.create_from_config_point(decision_tree_regression_model_config)

    @classmethod
    def contains(cls, config):
        return True  # TODO: see if you can remove this class entirely.


class HomogeneousRandomForestRegressionModel(RegressionModel):
    """ A RandomForest with homogeneously configured trees.

    This is the first implementation of a random forest regressor (and more generally of an ensemble model)
    that returns variance in addition to prediction. This should allow us to build a more robust bayesian
    optimizer.

    1. In this random forest, all decision trees are uniformly configured.
    2. Each decision tree receives a subset of features and a subset of rows.

    """

    @trace()
    def __init__(
            self,
            model_config: HomogeneousRandomForestRegressionModelConfig,
            input_space: Hypergrid,
            output_space: Hypergrid,
            logger=None
    ):
        if logger is None:
            logger = create_logger("HomogeneousRandomForestRegressionModel")
        self.logger = logger

        assert HomogeneousRandomForestRegressionModelConfig.contains(model_config)
        super(HomogeneousRandomForestRegressionModel, self).__init__(
            model_type=type(self),
            model_config=model_config
        )

        self.input_space = input_space
        self.output_space = output_space

        self._input_space_adapter = CategoricalToDiscreteHypergridAdapter(
            adaptee=CompositeToSimpleHypergridAdapter(
                adaptee=self.input_space
            )
        )

        self._output_space_adapter = CategoricalToDiscreteHypergridAdapter(
            adaptee=CompositeToSimpleHypergridAdapter(
                adaptee=self.output_space
            )
        )

        self.target_dimension_names = [dimension.name for dimension in self._output_space_adapter.dimensions]
        assert len(self.target_dimension_names) == 1, "Single target predictions for now."

        self._decision_trees = []
        self._create_estimators()

    @trace()
    def _create_estimators(self):
        """ Create individual estimators.

        Each estimator is meant to have a different subset of features and a different subset of samples.

        In the long run, we can solve it by creating an ObservationSet or ObservationStream class, then each
        estimator would have its own ObservationStream object that would know which data points to fetch and
        how to do it.

        For now however, I'll do it here in-line to get it working.

        1. Selecting features - to select a subset of features for each estimator we will:
            1. Create a random valid point in the search space. Any such valid config will not contain mutually exclusive
                parameters (for example if we chose an LRU eviction strategy, we won't get any parameters for a Random eviction strategy)
            2. Select a subset of dimensions from such a valid point so that we comply with the 'features_fraction_per_estimator' value.
            3. Build an input hypergrid for each estimator. However dimensions from above could be deeply nested.
                For example: smart_cache_config.lru_cache_config.lru_cache_size. We don't need the individual hypergrids
                to be nested at all so we will 'flatten' the dimension name by replacing the '.' with another delimiter.
                Then for each observation we will flatten the names again to see if the observation belongs to our observation
                space. If it does, then we can use our observation selection filter to decide if we want to feed that observation
                to the model. I'll leave the observation selection filter implementation for some other day.

        :return:
        """
        # Now we get to create all the estimators, each with a different feature subset and a different
        # observation filter

        self.logger.debug(f"Creating {self.model_config.n_estimators} estimators. Request id: {random.random()}")

        all_dimension_names = [dimension.name for dimension in self.input_space.dimensions]
        total_num_dimensions = len(all_dimension_names)
        features_per_estimator = max(1, math.ceil(total_num_dimensions * self.model_config.features_fraction_per_estimator))

        for i in range(self.model_config.n_estimators):
            estimator_input_space = self._create_random_flat_subspace(
                original_space=self.input_space,
                subspace_name=f"estimator_{i}_input_space",
                max_num_dimensions=features_per_estimator
            )

            estimator_output_space = self._create_random_flat_subspace(
                original_space=self.output_space,
                subspace_name=f"estimator_{i}_output_space",
                max_num_dimensions=1
            )

            estimator = DecisionTreeRegressionModel(
                model_config=self.model_config.decision_tree_regression_model_config,
                input_space=estimator_input_space,
                output_space=estimator_output_space,
                logger=self.logger
            )

            # TODO: each one of them also needs a sample filter.
            self._decision_trees.append(estimator)

    @staticmethod
    def _create_random_flat_subspace(original_space, subspace_name, max_num_dimensions):
        """ Creates a random simple hypergrid from the hypergrid with up to max_num_dimensions dimensions.

        TODO: move this to the *Hypergrid classes.

        :param original_space:
        :return:
        """
        random_point = original_space.random()
        original_dimension_names = [dimension_name for dimension_name, _ in random_point]
        selected_dimension_names = random.sample(original_dimension_names, min(len(original_dimension_names), max_num_dimensions))
        flat_dimensions = []
        for original_dimension_name in selected_dimension_names:
            original_dimension = original_space[original_dimension_name]
            flat_dimension = original_dimension.copy()
            flat_dimension.name = Dimension.flatten_dimension_name(original_dimension_name)
            flat_dimensions.append(flat_dimension)
        flat_hypergrid = SimpleHypergrid(
            name=subspace_name,
            dimensions=flat_dimensions
        )
        return flat_hypergrid

    @trace()
    def fit(self, feature_values_pandas_frame, target_values_pandas_frame):
        """ Fits the random forest.

            The issue here is that the feature_values will come in as a numpy array where each column corresponds to one
            of the dimensions in our input space. The target_values will come in a similar numpy array with each column
            corresponding to a single dimension in our output space.

            Our goal is to slice them up and feed the observations to individual decision trees.

        :param feature_values:
        :param target_values:
        :return:
        """
        self.logger.debug(f"Fitting a {self.__class__.__name__} with {len(feature_values_pandas_frame.index)} observations.")

        feature_values_pandas_frame = self._input_space_adapter.translate_dataframe(feature_values_pandas_frame, in_place=False)
        target_values_pandas_frame = self._output_space_adapter.translate_dataframe(target_values_pandas_frame)

        # Let's select samples for each tree
        total_num_observations = len(feature_values_pandas_frame.index)
        num_observations_per_estimator = math.ceil(self.model_config.samples_fraction_per_estimator * total_num_observations)

        # TODO: for now feed each _estimator all of the data - they will pick their own.
        # Later give them a dataset/datastream which would be a wrapper around either SQL or arrow endpoints.

        for i, tree in enumerate(self._decision_trees):
            # Let's filter out the useless samples (samples with missing values)
            # TODO: DRY - this code is repeated for predict()
            estimators_df = feature_values_pandas_frame[[dimension.name for dimension in tree.input_space.dimensions]]
            filtered_observations = estimators_df[estimators_df.notnull().all(axis=1)]
            num_filtered_observations = len(filtered_observations.index)
            # We seed so that each time they are fitted on the same subset
            np.random.seed(i)
            # TODO: GOOD COMMENT HERE
            selected_observation_ids = np.random.randint(0, num_filtered_observations, min(num_filtered_observations, num_observations_per_estimator))
            num_selected_observations = len(selected_observation_ids)
            if tree.should_fit(num_selected_observations):
                tree.fit(filtered_observations.iloc[selected_observation_ids], target_values_pandas_frame.iloc[selected_observation_ids])

    @trace()
    def predict(self, feature_values_pandas_frame):
        """ Aggregate predictions from all estimators

        see: https://arxiv.org/pdf/1211.0906.pdf
        section: 4.3.2 for details

        :param feature_values_pandas_frame:
        :return: TODO: https://msdata.visualstudio.com/Database%20Systems/_backlogs/backlog/MLOS/Epics/?showParents=true&workitem=743670
        """
        self.logger.debug(f"Creating predictions for {len(feature_values_pandas_frame.index)} samples.")

        feature_values_pandas_frame = self._input_space_adapter.translate_dataframe(feature_values_pandas_frame)

        # Since each estimator actually spits out an array - this is an array of arrays where each "row" is a sequence
        # of predictions. This is in case feature_values_pandas_frame had multiple rows... - one prediciton per row per estimator
        #
        aggregate_predictions = []
        predictions = [estimator.predict(feature_values_pandas_frame) for estimator in self._decision_trees]
        for observation_id in range(len(feature_values_pandas_frame.index)):
            observation_predictions = [
                predictions[estimator_idx][observation_id]
                for estimator_idx, estimator
                in enumerate(self._decision_trees)
            ]
            observation_predictions = [prediction for prediction in observation_predictions if prediction.valid]
            if not observation_predictions or not any(prediction.valid for prediction in observation_predictions):
                # ALl of them were None - we can't really do a prediction
                aggregate_predictions.append(Prediction(target_name=self.target_dimension_names[0], valid=False))
            else:
                prediction_mean = np.mean([
                    prediction.mean
                    for prediction in observation_predictions
                    if prediction.valid
                ])
                prediction_variance = np.mean([
                    prediction.variance + prediction.mean ** 2
                    for prediction in observation_predictions
                    if prediction is not None
                ]) - prediction_mean ** 2
                aggregate_predictions.append(Prediction(
                    target_name=observation_predictions[0].target_name,
                    mean=prediction_mean,
                    variance=prediction_variance,
                    count=len(observation_predictions)
                ))
        return aggregate_predictions
