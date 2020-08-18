// -----------------------------------------------------------------------
// <copyright file="SharedMemoryRegionView.cs" company="Microsoft Corporation">
// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License. See LICENSE in the project root
// for license information.
// </copyright>
// -----------------------------------------------------------------------

using System;
using System.IO;
using System.Runtime.CompilerServices;

using MlosProxy = Proxy.Mlos.Core;
using MlosProxyInternal = Proxy.Mlos.Core.Internal;

namespace Mlos.Core
{
    public static class SharedMemoryRegionView
    {
        /// <summary>
        /// Creates a shared memory region view.
        /// </summary>
        /// <param name="sharedMemoryMapName"></param>
        /// <param name="sharedMemorySize"></param>
        /// <returns></returns>
        /// <typeparam name="T">Memory region type.</typeparam>
        public static SharedMemoryRegionView<T> Create<T>(string sharedMemoryMapName, ulong sharedMemorySize)
            where T : ICodegenProxy, new()
        {
            var memoryRegionView = new SharedMemoryRegionView<T>(SharedMemoryMapView.Create(sharedMemoryMapName, sharedMemorySize));

            MlosProxyInternal.MemoryRegionInitializer<T> memoryRegionInitializer = default;
            memoryRegionInitializer.Initalize(memoryRegionView);
            return memoryRegionView;
        }

        /// <summary>
        /// Creates or opens a shared memory region view.
        /// </summary>
        /// <param name="sharedMemoryMapName"></param>
        /// <param name="sharedMemorySize"></param>
        /// <returns></returns>
        /// <typeparam name="T">Memory region type.</typeparam>
        public static SharedMemoryRegionView<T> CreateOrOpen<T>(string sharedMemoryMapName, ulong sharedMemorySize)
            where T : ICodegenProxy, new()
        {
            try
            {
                return new SharedMemoryRegionView<T>(SharedMemoryMapView.Open(sharedMemoryMapName, sharedMemorySize));
            }
            catch (FileNotFoundException)
            {
                var memoryRegionView = new SharedMemoryRegionView<T>(SharedMemoryMapView.Create(sharedMemoryMapName, sharedMemorySize));

                MlosProxyInternal.MemoryRegionInitializer<T> memoryRegionInitializer = default;
                memoryRegionInitializer.Initalize(memoryRegionView);
                return memoryRegionView;
            }
        }

        /// <summary>
        /// Opens an existing shared memory region view.
        /// </summary>
        /// <param name="sharedMemoryMapName"></param>
        /// <param name="sharedMemorySize"></param>
        /// <returns></returns>
        /// <typeparam name="T">Memory region type.</typeparam>
        public static SharedMemoryRegionView<T> Open<T>(string sharedMemoryMapName, ulong sharedMemorySize)
            where T : ICodegenProxy, new()
        {
            return new SharedMemoryRegionView<T>(SharedMemoryMapView.Open(sharedMemoryMapName, sharedMemorySize));
        }
    }

    /// <summary>
    /// Class represents shared memory map view for given type of memory region.
    /// </summary>
    /// <typeparam name="T">Memory region type.</typeparam>
    public sealed class SharedMemoryRegionView<T> : IDisposable
         where T : ICodegenProxy, new()
    {
        public SharedMemoryRegionView(SharedMemoryMapView sharedMemoryMap)
        {
            this.sharedMemoryMap = sharedMemoryMap;

            var memoryRegion = new MlosProxyInternal.MemoryRegion
            {
                Buffer = sharedMemoryMap.Buffer,
                Signature = 0x67676767,
                MemoryRegionSize = sharedMemoryMap.MemSize,
                MemoryRegionCodeTypeIndex = default(T).CodegenTypeIndex(),
            };
        }

        public ulong MemSize => sharedMemoryMap.MemSize;

        /// <summary>
        /// Returns an instance of MemoryRegionProxy.
        /// </summary>
        /// <returns></returns>
        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public T MemoryRegion()
        {
            return new T { Buffer = sharedMemoryMap.Buffer };
        }

        #region IDisposable Support

        private void Dispose(bool disposing)
        {
            if (disposed)
            {
                return;
            }

            if (disposing)
            {
                sharedMemoryMap?.Dispose();
                sharedMemoryMap = null;
            }

            disposed = true;
        }

        /// <inheritdoc/>
        public void Dispose()
        {
            Dispose(true);
        }
        #endregion

        private SharedMemoryMapView sharedMemoryMap;

        private bool disposed = false;
    }
}
