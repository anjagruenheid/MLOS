//*********************************************************************
// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License. See License.txt in the project root
// for license information.
//
// @File: ObjectSerializationStringView.h
//
// Purpose:
//      <description>
//
// Notes:
//      <special-instructions>
//
//*********************************************************************

#pragma once

#include <string_view>
#include "BytePtr.h"
#include "ObjectSerializationStringView.h"

// Serialization methods for std::string_view, std::wstring_view.
//
namespace ObjectSerialization
{
template<>
constexpr inline size_t GetVariableDataSize(const std::string_view& object)
{
    return object.length();
}

template<>
constexpr inline size_t GetVariableDataSize(const std::wstring_view& object)
{
    return object.length() * sizeof(wchar_t);
}

template<size_t N>
constexpr inline size_t GetVariableDataSize(const std::array<std::string_view, N>& object)
{
    size_t length = 0;

    for (const auto& element : object)
    {
        length += GetVariableDataSize(element);
    }

    return length;
}

template<size_t N>
constexpr inline size_t GetVariableDataSize(const std::array<std::wstring_view, N>& object)
{
    size_t length = 0;

    for (const auto& element : object)
    {
        length += GetVariableDataSize(element);
    }

    return length;
}

template<>
inline size_t SerializeVariableData(
    Mlos::Core::BytePtr buffer,
    uint64_t objectOffset,
    uint64_t dataOffset,
    const std::string_view& object)
{
    size_t length = object.length();
    memcpy(buffer.Pointer + dataOffset, object.data(), length);
    *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset)) = (dataOffset - objectOffset);
    *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset + sizeof(uint64_t))) = length;

    return length;
}

template<>
inline size_t SerializeVariableData(
    Mlos::Core::BytePtr buffer,
    uint64_t objectOffset,
    uint64_t dataOffset,
    const std::wstring_view& object)
{
    size_t length = object.length() * sizeof(wchar_t);
    memcpy(buffer.Pointer + dataOffset, object.data(), length);
    *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset)) = (dataOffset - objectOffset);
    *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset + sizeof(uint64_t))) = length;

    return length;
}

template<size_t N>
inline size_t SerializeVariableData(
    Mlos::Core::BytePtr buffer,
    uint64_t objectOffset,
    uint64_t dataOffset,
    const std::array<std::string_view, N>& object)
{
    size_t length = 0;

    for (const auto& element : object)
    {
        size_t elementLength = element.length();
        memcpy(buffer.Pointer + dataOffset, element.data(), elementLength);
        *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset)) = (dataOffset - objectOffset);
        *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset + sizeof(uint64_t))) = elementLength;

        objectOffset += sizeof(std::string_view);
        dataOffset += elementLength;

        length += elementLength;
    }

    return length;
}

template<size_t N>
inline size_t SerializeVariableData(
    Mlos::Core::BytePtr buffer,
    uint64_t objectOffset,
    uint64_t dataOffset,
    const std::array<std::wstring_view, N>& object)
{
    size_t length = 0;

    for (const auto& element : object)
    {
        size_t elementLength = element.length() * sizeof(wchar_t);
        memcpy(buffer.Pointer + dataOffset, element.data(), elementLength);
        *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset)) = (dataOffset - objectOffset);
        *(reinterpret_cast<uint64_t*>(buffer.Pointer + objectOffset + sizeof(uint64_t))) = elementLength;

        objectOffset += sizeof(std::wstring_view);
        dataOffset += elementLength;

        length += elementLength;
    }

    return length;
}
}
