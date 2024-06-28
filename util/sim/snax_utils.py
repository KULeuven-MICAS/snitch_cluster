#!/usr/bin/env python3

# Copyright 2024 KU Leuven.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

import numpy as np


# Function to perform 2D convolution on the input data using the specified kernel,
# stride, and padding. It returns the output feature map.
def conv2d(input_data, kernel, stride=(1, 1), padding=(0, 0)):
    batch_size, in_height, in_width, in_channels = input_data.shape
    out_channels, kernel_height, kernel_width, _ = kernel.shape
    stride_h, stride_w = stride
    pad_h, pad_w = padding

    # Calculate the output feature map dimensions
    out_height = (in_height - kernel_height + 2 * pad_h) // stride_h + 1
    out_width = (in_width - kernel_width + 2 * pad_w) // stride_w + 1

    # Add padding
    input_data_padded = np.pad(
        input_data, ((0, 0), (pad_h, pad_h), (pad_w, pad_w), (0, 0)), mode="constant"
    )

    # Initialize the output feature map
    output_data = np.zeros((batch_size, out_height, out_width, out_channels), np.int32)

    # Perform the convolution operation
    for b in range(batch_size):
        for oc in range(out_channels):
            for oh in range(out_height):
                for ow in range(out_width):
                    # Calculate the input region
                    ih_start = oh * stride_h
                    ih_end = ih_start + kernel_height
                    iw_start = ow * stride_w
                    iw_end = iw_start + kernel_width

                    # Slice to extract the input region
                    input_region = input_data_padded[
                        b, ih_start:ih_end, iw_start:iw_end, :
                    ]

                    # Slice to extract the corresponding convolution kernel
                    conv_kernel = kernel[oc, :, :, :]

                    # Perform the convolution calculation
                    output_data[b, oh, ow, oc] = np.sum(input_region * conv_kernel)

    return output_data


# Function to transform input data into columns for efficient convolution operations.
# It returns the transformed input data and reshaped kernel.
def im2col(input_data, kernel, stride=(1, 1), padding=(0, 0)):
    batch_size, in_height, in_width, in_channels = input_data.shape
    out_channels, kernel_height, kernel_width, _ = kernel.shape
    stride_h, stride_w = stride
    pad_h, pad_w = padding

    # Calculate the size of the output feature map
    out_height = (in_height + 2 * pad_h - kernel_height) // stride_h + 1
    out_width = (in_width + 2 * pad_w - kernel_width) // stride_w + 1

    # Apply zero padding to the input data
    input_data_padded = np.pad(
        input_data, ((0, 0), (pad_h, pad_h), (pad_w, pad_w), (0, 0)), mode="constant"
    )

    # Initialize the im2col matrix
    im2col_matrix = np.zeros(
        (batch_size, out_height * out_width, in_channels * kernel_height * kernel_width)
    )

    # Perform the im2col transformation on the input data
    for b in range(batch_size):
        for oh in range(out_height):
            for ow in range(out_width):
                # Calculate the input region
                ih_start = oh * stride_h
                ih_end = ih_start + kernel_height
                iw_start = ow * stride_w
                iw_end = iw_start + kernel_width

                # Slice and extract the input region
                input_region = input_data_padded[b, ih_start:ih_end, iw_start:iw_end, :]

                # Flatten the input region into a 1D vector and add it to the
                # corresponding position in the im2col matrix
                im2col_matrix[b, oh * out_width + ow, :] = input_region.reshape(-1)

    im2col_matrix = im2col_matrix.reshape(batch_size * out_height * out_width, -1)
    im2col_kernel = kernel.reshape(out_channels, -1).T

    return im2col_matrix, im2col_kernel


# Golden model function to perform block matrix multiplication with specific parameters.
# It returns the resulting matrix after the computation.
def block_gemm_golden_model(
    m, k, n, row, size, col, a, b, subtraction_a, subtraction_b, c
):
    d = np.zeros(m * row * n * col, dtype=(np.int32))
    for mm in range(m):
        for nn in range(n):
            for kk in range(k):
                for rr in range(row):
                    for cc in range(col):
                        for ss in range(size):
                            c_index = (
                                mm * n * row * col + nn * row * col + rr * col + cc
                            )
                            a_index = (
                                mm * k * row * size + kk * row * size + rr * size + ss
                            )
                            b_index = (
                                nn * k * size * col + kk * size * col + cc * size + ss
                            )
                            d[c_index] = d[c_index] + (a[a_index] - subtraction_a) * (
                                b[b_index] - subtraction_b
                            )
    d = np.add(c, d)
    return d


# Golden model function for reshuffling data with specified parameters. It applies
# strided layout mapping to the input data and returns the reshuffled data array.
def data_reshuffler_golden_model(
    tempLoop0,
    tempLoop1,
    spatial_len_0,
    spatial_len_1,
    tempStride0,
    tempStride1,
    spatialStride0,
    spatialStride1,
    data,
    int32=False,
):
    # abstract illusion: k innermost loop, m second innermost loop,
    # K third innermost loop, M outermost loop

    # total loop bounds = spatial loop bounds * temporal loop bounds
    K = tempLoop0 * spatial_len_0
    M = tempLoop1 * spatial_len_1

    # loop bounds settings
    matrix_size = {"K": K, "M": M, "k": spatial_len_0, "m": spatial_len_1}

    # stride settings
    strides = {
        "M": tempStride1,
        "K": tempStride0,
        "m": spatialStride1,
        "k": spatialStride0,
    }

    if int32:
        result_array = np.zeros((matrix_size["M"] * matrix_size["K"]), np.int32)
    else:
        result_array = np.zeros((matrix_size["M"] * matrix_size["K"]), np.int8)

    # apply strided layout mapping for the golden model of data reshuffler
    for M in range(matrix_size["M"] // matrix_size["m"]):
        for K in range(matrix_size["K"] // matrix_size["k"]):
            for m in range(matrix_size["m"]):
                for k in range(matrix_size["k"]):
                    result_array[
                        # output address calculation with coutinued increment
                        matrix_size["K"]
                        // matrix_size["k"]
                        * matrix_size["k"]
                        * matrix_size["m"]
                        * M
                        + matrix_size["k"] * matrix_size["m"] * K
                        + m * matrix_size["k"]
                        + k
                    ] = data[
                        # input address calculation with
                        # strided layout mapping eqaution
                        strides["M"] * M
                        + strides["K"] * K
                        + strides["m"] * m
                        + strides["k"] * k
                    ]

    return result_array.ravel()


# Golden model function for SIMD postprocessing of data. It performs operations such as
# zero point subtraction, multiplication, right shift, double rounding, and clipping.
def postprocessing_simd_golden_model(
    data_in,
    input_zp_i,
    output_zp_i,
    shift_i,
    max_int_i,
    min_int_i,
    double_round_i,
    multiplier_i,
):

    # Step 1: Subtract input zero point
    var = data_in - input_zp_i

    # Step 2: Multiply with the multiplier avoiding overflow
    var = np.int64(var) * np.int64(multiplier_i)

    # Step 3: Right shift
    var = np.int32(var >> (shift_i - 1))

    # Step 4: Apply double rounding if necessary
    if double_round_i:
        var = np.where(var >= 0, var + 1, var - 1)

    # Step 5: Final right shift
    var = var >> 1

    # Step 6: Add output zero point
    var = var + output_zp_i

    # Step 7: Clip the values to be within min and max integer range
    var = np.clip(var, min_int_i, max_int_i)

    return var


def max_pooling_3d(
    input_tensor, pool_size_w, pool_size_h, stride_w, stride_h, padding_w, padding_h
):

    H, W, C = input_tensor.shape

    out_width = (W + 2 * padding_w - pool_size_w) // stride_w + 1
    out_height = (H + 2 * padding_h - pool_size_h) // stride_h + 1

    input_padded = np.pad(
        input_tensor,
        ((padding_h, padding_h), (padding_w, padding_w), (0, 0)),
        mode="constant",
        constant_values=0,
    )

    pooled_tensor = np.zeros((out_height, out_width, C), dtype=np.int8)

    for i in range(out_height):
        for j in range(out_width):
            for k in range(C):
                h_start = i * stride_h
                h_end = h_start + pool_size_h
                w_start = j * stride_w
                w_end = w_start + pool_size_w
                pooled_tensor[i, j, k] = np.max(
                    input_padded[h_start:h_end, w_start:w_end, k]
                )

    return pooled_tensor


def max_pooling_4d(
    input_tensor, pool_size_w, pool_size_h, stride_w, stride_h, padding_w, padding_h
):

    C8, H, W, _ = input_tensor.shape
    assert input_tensor.shape[3] == 8

    out_width = (W + 2 * padding_w - pool_size_w) // stride_w + 1
    out_height = (H + 2 * padding_h - pool_size_h) // stride_h + 1

    input_padded = np.pad(
        input_tensor,
        ((0, 0), (padding_h, padding_h), (padding_w, padding_w), (0, 0)),
        mode="constant",
        constant_values=0,
    )

    pooled_tensor = np.zeros((C8, out_height, out_width, 8), dtype=np.int8)

    for c in range(C8):
        for i in range(out_height):
            for j in range(out_width):
                for k in range(8):
                    h_start = i * stride_h
                    h_end = h_start + pool_size_h
                    w_start = j * stride_w
                    w_end = w_start + pool_size_w
                    pooled_tensor[c, i, j, k] = np.max(
                        input_padded[c, h_start:h_end, w_start:w_end, k]
                    )

    return pooled_tensor
