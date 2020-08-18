// -----------------------------------------------------------------------
// <copyright file="CSharpObjectDispatchHandlerCodeWriter.cs" company="Microsoft Corporation">
// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License. See LICENSE in the project root
// for license information.
// </copyright>
// -----------------------------------------------------------------------

using System;
using System.Reflection;

using Mlos.SettingsSystem.Attributes;

namespace Mlos.SettingsSystem.CodeGen.CodeWriters.CSharpObjectExchangeCodeWriters
{
    /// <summary>
    /// Code writer class which generates a dispatch table with object deserialize handlers.
    /// </summary>
    /// <remarks>
    /// // Generates a static table containing type information.
    /// </remarks>
    internal class CSharpObjectDispatchHandlerCodeWriter : CSharpTypeTableCodeWriter
    {
        /// <summary>
        /// Constructor.
        /// </summary>
        /// <param name="sourceTypesAssembly"></param>
        public CSharpObjectDispatchHandlerCodeWriter(Assembly sourceTypesAssembly)
            : base(sourceTypesAssembly)
        {
        }

        /// <inheritdoc />
        public override bool Accept(Type sourceType) => sourceType.IsCodegenType();

        /// <summary>
        /// Write beginning of the file.
        /// </summary>
        /// <remarks>
        /// Proxy structures are defined in namespace Proxy.
        /// </remarks>
        public override void WriteBeginFile()
        {
            // Tell stylecop to ignore this file.
            //
            WriteLine("// <auto-generated />");

            WriteGlobalBeginNamespace();

            // Define a global dispatch table.
            //
            WriteBlock(@"
                /// <summary>
                /// Static callback class.
                /// </summary>
                public static partial class ObjectDeserializeHandler
                {
                    /// <summary>
                    /// Callback array.
                    /// </summary>
                    public static readonly DispatchEntry[] DispatchTable = new DispatchEntry[]
                    {");

            IndentationLevel += 2;
        }

        /// <inheritdoc />
        public override void WriteEndFile()
        {
            // Close DispatchTable.
            //
            IndentationLevel--;
            WriteLine("};");
            WriteLine();

            // Define a dispatch table base index.
            //
            WriteBlock(@"
                // <summary>
                // Base assembly type index.
                // </summary>
                // <remarks>
                // Mlos.Agent updates this value when assembly is registered.
                // </remarks>
                public static uint DispatchTableBaseIndex = 0;");

            IndentationLevel--;
            WriteLine("}");

            WriteGlobalEndNamespace();
        }

        /// <summary>
        /// For each serializable structure, create an entry with deserialization handler in the dispatch callback table.
        /// </summary>
        /// <param name="sourceType"></param>
        public override void EndVisitType(Type sourceType)
        {
            string proxyTypeFullName = $"{Constants.ProxyNamespace}.{sourceType.GetTypeFullName()}";

            ulong typeHashValue = TypeMetadataMapper.GetTypeHashValue(sourceType);

            WriteBlock($@"
                new DispatchEntry
                {{
                    CodegenTypeHash = 0x{typeHashValue:x},
                    Callback = (bufferPtr, frameLength) =>
                    {{
                        var recvObjectProxy = new {proxyTypeFullName}() {{ Buffer = bufferPtr }};

                        bool isValid = recvObjectProxy.VerifyVariableData(frameLength);
                        if (isValid && {proxyTypeFullName}.Callback != null)
                        {{
                            {proxyTypeFullName}.Callback(recvObjectProxy);
                        }}

                        return isValid;
                    }},
                }},");

            ++ClassCount;
        }

        /// <inheritdoc />
        public override string FilePostfix => "_dispatch.cs";
    }
}
