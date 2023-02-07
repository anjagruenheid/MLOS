"""
Contains the BaseOptimizer abstract class.
"""

from abc import ABCMeta, abstractmethod
from typing import Optional

import ConfigSpace
import pandas as pd
from mlos_core.spaces.adapters.adapter import BaseSpaceAdapter

# pylint: disable=consider-alternative-union-syntax


class BaseOptimizer(metaclass=ABCMeta):
    """Optimizer abstract base class defining the basic interface.

    Parameters
    ----------
    parameter_space : ConfigSpace.ConfigurationSpace
        The parameter space to optimize.

    space_adapter : BaseSpaceAdapter
        The space adapter class to employ for parameter space transformations.
    """
    def __init__(self, parameter_space: ConfigSpace.ConfigurationSpace, space_adapter: Optional[BaseSpaceAdapter] = None):
        self.parameter_space: ConfigSpace.ConfigurationSpace = parameter_space
        self.optimizer_parameter_space: ConfigSpace.ConfigurationSpace = \
            parameter_space if space_adapter is None else space_adapter.target_parameter_space

        if space_adapter is not None and space_adapter.orig_parameter_space != parameter_space:
            raise ValueError("Given parameter space differs from the one given to space adapter")

        self._space_adapter: Optional[BaseSpaceAdapter] = space_adapter
        self._observations = []
        self._pending_observations = []

    def __repr__(self):
        return f"{self.__class__.__name__}(parameter_space={self.parameter_space})"

    @property
    def space_adapter(self) -> Optional[BaseSpaceAdapter]:
        """Get the space adapter instance (if any)."""
        return self._space_adapter

    def register(self, configurations: pd.DataFrame, scores: pd.Series, context: pd.DataFrame = None):
        """Wrapper method, which employs the space adapter (if any), before registering the configurations and scores.

        Parameters
        ----------
        configurations : pd.DataFrame
            Dataframe of configurations / parameters. The columns are parameter names and the rows are the configurations.

        scores : pd.Series
            Scores from running the configurations. The index is the same as the index of the configurations.

        context : pd.DataFrame
            Not Yet Implemented.
        """
        self._observations.append((configurations, scores, context))

        if self._space_adapter:
            configurations = self._space_adapter.inverse_transform(configurations)
        return self._register(configurations, scores, context)

    @abstractmethod
    def _register(self, configurations: pd.DataFrame, scores: pd.Series, context: pd.DataFrame = None):
        """Registers the given configurations and scores.

        Parameters
        ----------
        configurations : pd.DataFrame
            Dataframe of configurations / parameters. The columns are parameter names and the rows are the configurations.

        scores : pd.Series
            Scores from running the configurations. The index is the same as the index of the configurations.

        context : pd.DataFrame
            Not Yet Implemented.
        """
        pass    # pylint: disable=unnecessary-pass # pragma: no cover

    def suggest(self, context: pd.DataFrame = None):
        """Wrapper method, which employs the space adapter (if any), after suggesting a new configuration.

        Parameters
        ----------
        context : pd.DataFrame
            Not Yet Implemented.

        Returns
        -------
        configuration : pd.DataFrame
            Pandas dataframe with a single row. Column names are the parameter names.
        """
        configuration = self._suggest(context)
        if self._space_adapter:
            configuration = self._space_adapter.transform(configuration)
        return configuration

    @abstractmethod
    def _suggest(self, context: pd.DataFrame = None):
        """Suggests a new configuration.

        Parameters
        ----------
        context : pd.DataFrame
            Not Yet Implemented.

        Returns
        -------
        configuration : pd.DataFrame
            Pandas dataframe with a single row. Column names are the parameter names.
        """
        pass    # pylint: disable=unnecessary-pass # pragma: no cover

    @abstractmethod
    def register_pending(self, configurations: pd.DataFrame, context: pd.DataFrame = None):
        """Registers the given configurations as "pending".
        That is it say, it has been suggested by the optimizer, and an experiment trial has been started.
        This can be useful for executing multiple trials in parallel, retry logic, etc.

        Parameters
        ----------
        configurations : pd.DataFrame
            Dataframe of configurations / parameters. The columns are parameter names and the rows are the configurations.

        context : pd.DataFrame
            Not Yet Implemented.
        """
        pass    # pylint: disable=unnecessary-pass # pragma: no cover

    def get_observations(self):
        """Returns the observations as a dataframe.

        Returns
        -------
        observations : pd.DataFrame
            Dataframe of observations. The columns are parameter names and "score" for the score, each row is an observation.
        """
        if len(self._observations) == 0:
            raise ValueError("No observations registered yet.")
        configs = pd.concat([config for config, _, _ in self._observations])
        scores = pd.concat([score for _, score, _ in self._observations])
        try:
            contexts = pd.concat([context for _, _, context in self._observations])
        except ValueError:
            contexts = None
        configs["score"] = scores
        if contexts is not None:
            # configs = pd.concat([configs, contexts], axis=1)
            # Not reachable for now
            raise NotImplementedError()  # pragma: no cover
        return configs

    def get_best_observation(self):
        """Returns the best observation so far as a dataframe.

        Returns
        -------
        best_observation : pd.DataFrame
            Dataframe with a single row containing the best observation. The columns are parameter names and "score" for the score.
        """
        if len(self._observations) == 0:
            raise ValueError("No observations registered yet.")
        observations = self.get_observations()
        return observations.nsmallest(1, columns='score')
