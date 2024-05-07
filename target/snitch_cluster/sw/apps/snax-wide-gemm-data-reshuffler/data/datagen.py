#!/usr/bin/env python3

# Copyright 2023 KU Leuven.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

import numpy as np
import argparse
import pathlib
import hjson
import sys
import os
# Add data utility path
sys.path.append(
    os.path.join(os.path.dirname(__file__), "../../../../../../util/sim/")
)
from data_utils import (format_scalar_definition, format_vector_definition)  # noqa E402

np.random.seed(42)


# Golden model in python
def gemm_golden_model(m, k, n, row, size, col, a, b,
                            subtraction_a, subtraction_b):
    a_matrix = np.reshape(a, (m * row, k * size))
    b_matrix = np.reshape(b, (k * size, n * col))
    # print("a\n", a_matrix)
    # print("b\n", b_matrix)
    # print("b\n", b_matrix.T)

    c = np.zeros((m * row, n * col), dtype=np.int32)
    for mm in range(m * row):
        for nn in range(n * col):
            for kk in range(k * size):
                c[mm, nn] += (a_matrix[mm, kk] - subtraction_a) * (b_matrix[kk, nn] - subtraction_b)
    return c.flatten()

def block_gemm_golden_model(m, k, n, row, size, col, a, b,
                            subtraction_a, subtraction_b):
    c = np.zeros(m * row * n * col, dtype=(np.int32))
    for mm in range(m):
        for nn in range(n):
            for kk in range(k):
                for rr in range(row):
                    for cc in range(col):
                        for ss in range(size):
                            c_index = (
                                mm * n * row * col
                                + nn * row * col
                                + rr * col
                                + cc
                            )
                            a_index = (
                                mm * k * row * size
                                + kk * row * size
                                + rr * size
                                + ss
                            )
                            b_index = (
                                nn * k * size * col
                                + kk * size * col
                                + cc * size
                                + ss
                            )
                            c[c_index] = c[c_index] + \
                                (a[a_index] - subtraction_a) * \
                                (b[b_index] - subtraction_b)
    return c

def data_reshuffler_golden_model(tempLoop0, tempLoop1, spatial_len_0, spatial_len_1, tempStride0, tempStride1, spatialStride0, spatialStride1, data):
    # abstract illusion: k innermost loop, m second innermost loop, K third innermost loop, M outermost loop

    # total loop bounds = spatial loop bounds * temporal loop bounds
    K = tempLoop0 * spatial_len_0
    M = tempLoop1 * spatial_len_1

    # loop bounds settings
    matrix_size = {
        'K': K,
        'M': M,
        'k': spatial_len_0,
        'm': spatial_len_1
    }

    # stride settings
    strides = {
        'M': tempStride1,
        'K': tempStride0,
        'm': spatialStride1,
        'k': spatialStride0
    }

    result_array = np.zeros((matrix_size["M"] * matrix_size["K"]), dtype=data.dtype)

    # apply strided layout mapping for the golden model of data reshuffler
    for M in range(matrix_size["M"] // matrix_size["m"]):
        for K in range(matrix_size["K"] // matrix_size["k"]):
            for m in range(matrix_size["m"]):
                for k in range(matrix_size["k"]):
                    result_array[
                        # output address calculation with coutinued increment
                        matrix_size["K"] // matrix_size["k"] * matrix_size["k"] * matrix_size['m'] * M 
                        + matrix_size["k"] * matrix_size['m'] * K 
                        + m * matrix_size['k'] 
                        + k
                        ] = data[
                        # input address calculation with strided layout mapping eqaution
                        strides["M"] * M
                        + strides["K"] * K
                        + strides["m"] * m
                        + strides["k"] * k
                    ]

    # print(result_array)
    return result_array.ravel()

# Add stdint.h header
def emit_header_file(**kwargs):
    emit_str = "#include <stdint.h>\n\n"
    emit_str += "#include <stdbool.h> \n\n"
    emit_str += emit_gemm_data(**kwargs)
    return emit_str


MIN = -128
MAX = 127


def emit_gemm_data(**kwargs):
    data_str = []

    # Generating matrix size settings
    data_str += [format_scalar_definition("int8_t", "Batch", kwargs["Batch"])]
    data_str += [
        format_scalar_definition("int32_t", "strideC", kwargs["strideC"])
    ]
    
    data_str += [format_scalar_definition("int8_t", "tempLoop0_A", kwargs["tempLoop0_A"])]
    data_str += [format_scalar_definition("int8_t", "tempLoop1_A", kwargs["tempLoop1_A"])]

    data_str += [format_scalar_definition("int8_t", "tempLoop0_B", kwargs["tempLoop0_B"])]
    data_str += [format_scalar_definition("int8_t", "tempLoop1_B", kwargs["tempLoop1_B"])]

    # Generating strides settings for A

    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride0_A_in", kwargs["DMAtempStride0_A_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride1_A_in", kwargs["DMAtempStride1_A_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAspatialStride1_A_in", kwargs["DMAspatialStride1_A_in"]
        )
    ]

    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_A_in", kwargs["tempStride0_A_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_A_in", kwargs["tempStride1_A_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_A_in", kwargs["spatialStride1_A_in"]
        )
    ]    
    # output
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_A_out", kwargs["tempStride0_A_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_A_out", kwargs["tempStride1_A_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_A_out", kwargs["spatialStride1_A_out"]
        )
    ] 

    data_str += [format_scalar_definition("int32_t", "delta_local_A_in", kwargs["delta_local_A_in"])]
    data_str += [format_scalar_definition("int32_t", "delta_local_A_out", kwargs["delta_local_A_out"])]

    # Generating the strides for B
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride0_B_in", kwargs["DMAtempStride0_B_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride1_B_in", kwargs["DMAtempStride1_B_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAspatialStride1_B_in", kwargs["DMAspatialStride1_B_in"]
        )
    ]

    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_B_in", kwargs["tempStride0_B_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_B_in", kwargs["tempStride1_B_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_B_in", kwargs["spatialStride1_B_in"]
        )
    ]    
    # output
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_B_out", kwargs["tempStride0_B_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_B_out", kwargs["tempStride1_B_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_B_out", kwargs["spatialStride1_B_out"]
        )
    ] 
    data_str += [format_scalar_definition("int32_t", "delta_local_B_in", kwargs["delta_local_B_in"])]
    data_str += [format_scalar_definition("int32_t", "delta_local_B_out", kwargs["delta_local_B_out"])]

    # Generating the stirdes for C
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride0_C_in", kwargs["DMAtempStride0_C_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride1_C_in", kwargs["DMAtempStride1_C_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAspatialStride1_C_in", kwargs["DMAspatialStride1_C_in"]
        )
    ]

    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_C_in", kwargs["tempStride0_C_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_C_in", kwargs["tempStride1_C_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_C_in", kwargs["spatialStride1_C_in"]
        )
    ]  
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_C_out", kwargs["tempStride0_C_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_C_out", kwargs["tempStride1_C_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_C_out", kwargs["spatialStride1_C_out"]
        )
    ] 
    data_str += [format_scalar_definition("int32_t", "delta_local_C_in", kwargs["delta_local_C_in"])]
    data_str += [format_scalar_definition("int32_t", "delta_local_C_out", kwargs["delta_local_C_out"])]

    # Generating random 8 integer a and b for subtraction
    subtraction_a = np.random.randint(MIN, MAX)
    subtraction_b = np.random.randint(MIN, MAX)

    # Writing the subtraction value to data.h
    data_str += [
        format_scalar_definition(
            "int8_t", "subtraction_a", subtraction_a
        )
    ]
    data_str += [
        format_scalar_definition(
            "int8_t", "subtraction_b", subtraction_b
        )
    ]

    # Generate random input matrices
    length_a = (
        kwargs["tempLoop0_A"] * kwargs["tempLoop1_A"] * kwargs["meshRow"] * kwargs["tileSize"]
    )
    length_b = (
        kwargs["tempLoop0_B"] * kwargs["tempLoop1_B"] * kwargs["meshCol"] * kwargs["tileSize"]
    )
    a = np.random.randint(MIN, MAX, length_a)
    b = np.random.randint(MIN, MAX, length_b)

    A_data_layout_golden = data_reshuffler_golden_model(
        kwargs["tempLoop0_A"],
        kwargs["tempLoop1_A"],
        kwargs["spatial_len_0"],
        kwargs["spatial_len_1"],
        kwargs["tempStride0_A_in"],
        kwargs["tempStride1_A_in"],
        1,
        kwargs["spatialStride1_A_in"],
        a
    )
    B_data_layout_golden = data_reshuffler_golden_model(
        kwargs["tempLoop0_B"],
        kwargs["tempLoop1_B"],
        kwargs["spatial_len_0"],
        kwargs["spatial_len_1"],
        kwargs["tempStride0_B_in"],
        kwargs["tempStride1_B_in"],
        1,
        kwargs["spatialStride1_B_in"],
        b
    )

    # Generating golden data
    c_golden = block_gemm_golden_model(
        kwargs["tempLoop1_A"],
        kwargs["tempLoop0_A"],
        kwargs["tempLoop1_B"],
        kwargs["meshRow"],
        kwargs["tileSize"],
        kwargs["meshCol"],
        A_data_layout_golden,
        B_data_layout_golden,
        subtraction_a,
        subtraction_b
    )

    data_str += [format_scalar_definition("bool", "transpose_A", kwargs["transpose_A"])]
    data_str += [format_scalar_definition("bool", "transpose_B", kwargs["transpose_B"])]
    data_str += [format_scalar_definition("bool", "transpose_C", kwargs["transpose_C"])]

    # Writing testing data and golden data into data.h
    data_str += [format_vector_definition("int8_t", "A", a)]
    data_str += [format_vector_definition("int8_t", "B", b)]
    data_str += [format_vector_definition("int32_t", "C_golden", c_golden)]
    data_str += [format_vector_definition("int8_t", "A_data_layout_golden", A_data_layout_golden)]
    data_str += [format_vector_definition("int8_t", "B_data_layout_golden", B_data_layout_golden)]


    data_str = "\n\n".join(data_str)

    return data_str


def main():
    # Parsing cmd args
    parser = argparse.ArgumentParser(description="Generate data for kernels")
    parser.add_argument(
        "-c",
        "--cfg",
        type=pathlib.Path,
        required=True,
        help="Select param config file kernel",
    )
    args = parser.parse_args()

    # Load param config file
    with args.cfg.open() as f:
        param = hjson.loads(f.read())

    # Emit header file
    print(emit_header_file(**param))


if __name__ == "__main__":
    main()
