#pragma once

namespace Mlos
{
namespace Core
{

//----------------------------------------------------------------------------
// NAME: MlosContext::CreateMemoryRegion
//
// PURPOSE:
//  Creates a shared memory view and registers it with Mlos.Agent.
//
// RETURNS:
//  HRESULT.
//
// NOTES:
//  Function opens or creates a shared memory view.
//
template<typename T>
HRESULT MlosContext::CreateMemoryRegion(const char* const sharedMemoryName, size_t memoryRegionSize, _Out_ SharedMemoryRegionView<T>& sharedMemoryRegionView)
{
    // Create region view, initialize it on create.
    //
    HRESULT hr = sharedMemoryRegionView.CreateOrOpen(sharedMemoryName, memoryRegionSize);
    if (FAILED(hr))
    {
        return hr;
    }

    // Initialize memory region if we created a new mapping, Otherwise assume Mlos.Agent has initialized it.
    //
    auto& memoryRegion = sharedMemoryRegionView.MemoryRegion();

    // Update region id if created a new one.
    //
    const bool createdNewRegion = (hr == S_OK);
    if (createdNewRegion)
    {
        memoryRegion.MemoryHeader.MemoryRegionId = ++m_globalMemoryRegion.TotalMemoryRegionCount;
    }

    // Send registration message.
    //
    Internal::RegisterMemoryRegionRequestMessage msg = { 0 };
    msg.Name = sharedMemoryName;
    msg.MemoryRegionSize = memoryRegion.MemoryHeader.MemoryRegionSize;
    msg.MemoryRegionId = memoryRegion.MemoryHeader.MemoryRegionId;
    m_controlChannel.SendMessage(msg);

    return S_OK;
}

//----------------------------------------------------------------------------
// NAME: MlosContext::RegisterComponentConfig
//
// PURPOSE:
//  Registers the component config. If the shared config already exists update the local config instance.
//
// RETURNS:
//  HRESULT.
//
// NOTES:
//
template <typename T>
HRESULT MlosContext::RegisterComponentConfig(ComponentConfig<T>& componentConfig)
{
    // Create or find existing shared configuration.
    //
    HRESULT hr = m_sharedConfigManager.CreateOrUpdateFrom(componentConfig);
    if (FAILED(hr))
    {
        return hr;
    }

    return S_OK;
}

//----------------------------------------------------------------------------
// NAME: MlosContext::SendControlMessage
//
// PURPOSE:
//  Sends the message using control channel.
//
// RETURNS:
//
// NOTES:
//
template<typename TMessage>
void MlosContext::SendControlMessage(TMessage& message)
{
    m_controlChannel.SendMessage(message);
}

//----------------------------------------------------------------------------
// NAME: MlosContext::SendFeedbackMessage
//
// PURPOSE:
//  Sends the message using feedback channel.
//
// RETURNS:
//
// NOTES:
//
template<typename TMessage>
void MlosContext::SendFeedbackMessage(TMessage& message)
{
    m_feedbackChannel.SendMessage(message);
}

//----------------------------------------------------------------------------
// NAME: MlosContext::SendTelemetryMessage
//
// PURPOSE:
//  Sends the message using telemetry channel.
//
// RETURNS:
//
// NOTES:
//
template<typename TMessage>
void MlosContext::SendTelemetryMessage(const TMessage& message) const
{
    m_telemetryChannel.SendMessage(message);
}

}
}