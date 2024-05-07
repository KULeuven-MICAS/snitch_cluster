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
# not correct, TODO: needs to be checked
def gemm_golden_model(m, k, n, row, size, col, a, b,
                            subtraction_a, subtraction_b):
    c = np.zeros(m * row * n * col, dtype=(np.int32))
    for mm in range(m * row):
        for nn in range(n * col):
            for kk in range(k * size):
                a_index = (
                   mm * k * size + kk
                )
                b_index = (
                   nn * k * size + kk
                )
                c_index = (
                    mm * col * n + nn
                )
                c[c_index] = c[c_index] + \
                    (a[a_index] - subtraction_a) * \
                    (b[b_index] - subtraction_b)
    return c

# Golden model for block GEMM in python
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

# Golden model for postprocessing in python
def postprocessing_simd_golden_model(
        data_in,
        input_zp_i,
        output_zp_i,
        shift_i,
        max_int_i,
        min_int_i,
        double_round_i,
        multiplier_i):
    c = np.zeros(data_in.shape)
    for i in range(len(data_in)):
        var = data_in[i] - input_zp_i
        # avoid overflow
        var = np.int64(var) * np.int64(multiplier_i)
        var = np.int32(var >> (shift_i - 1))
        if double_round_i:
            if var >= 0:
                var = var + 1
            else:
                var = var - 1
        var = var >> 1
        var = var + output_zp_i
        if var > max_int_i:
            var = max_int_i
        if var < min_int_i:
            var = min_int_i
        c[i] = var
    return c


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

    # common settings, a workaround for the current c library
    # TODO: remove this workaround
    data_str += [format_scalar_definition("int8_t", "Batch", kwargs["Batch"])]
    data_str += [
        format_scalar_definition("int32_t", "strideC", kwargs["strideC"])
    ]

    '''
    C = A * B
    with size of A: M x K
    B: K x N
    C: M x N
    1. A is reshuffled to tiled row major layout
    2. B is reshuffled to tiled column major layout
    3. C is generated with tiled row major layout, base address: delta_local_C_in
    '''

    # Generating matrix size settings for A 
    data_str += [format_scalar_definition("int8_t", "tempLoop0_A", kwargs["tempLoop0_A"])]
    data_str += [format_scalar_definition("int8_t", "tempLoop1_A", kwargs["tempLoop1_A"])]

    # Generating strides settings for A
    # DMA 
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
    # input
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

    data_str += [format_scalar_definition("int8_t", "tempLoop0_B", kwargs["tempLoop0_B"])]
    data_str += [format_scalar_definition("int8_t", "tempLoop1_B", kwargs["tempLoop1_B"])]
    # DMA
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
    # input
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

    # Generating the stirdes for GEMM output C
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_GEMM_C_out", kwargs["tempStride0_GEMM_C_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_GEMM_C_out", kwargs["tempStride1_GEMM_C_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_GEMM_C_out", kwargs["spatialStride1_GEMM_C_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "delta_local_GEMM_C_out", kwargs["delta_local_GEMM_C_out"]
        )
    ]

    data_str += [format_scalar_definition("int32_t", "delta_local_C_in", kwargs["delta_local_C_in"])]

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

    # Generating golden data for A and B after layout reshuffling
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
    # Generating golden C data using block GEMM
    c_golden_mm = block_gemm_golden_model(
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

    data_str += [format_vector_definition("int32_t", "C_golden_GEMM", c_golden_mm)]


    data_str += [format_scalar_definition("bool", "transpose_A", kwargs["transpose_A"])]
    data_str += [format_scalar_definition("bool", "transpose_B", kwargs["transpose_B"])]

    data_str += [format_vector_definition("int8_t", "A_data_layout_golden", A_data_layout_golden)]
    data_str += [format_vector_definition("int8_t", "B_data_layout_golden", B_data_layout_golden)]

    # Writing testing data and golden data into data.h
    data_str += [format_vector_definition("int8_t", "A", a)]
    data_str += [format_vector_definition("int8_t", "B", b)]

    '''
    C = Postprocessing(C).
    input data layout: tiled row major, as the output of GEMM, annonated as tempStride0_GEMM_C_out and tempStride1_GEMM_C_out
    base address: delta_local_C_in
    output data layout: tiled row major, as the out of Postprocessing SIMD, annonated as DMAtempStride0_C_in and DMAtempStride1_C_in
    base address: delta_local_C_out
    '''

    # Postprocessing SIMD output data layout settings
    data_str += [format_scalar_definition("int32_t", "DMAtempStride0_C_in", kwargs["DMAtempStride0_C_in"])]
    data_str += [format_scalar_definition("int32_t", "DMAtempStride1_C_in", kwargs["DMAtempStride1_C_in"])]

    # Generating random constant values
    input_zp_i = np.random.randint(MIN, MAX)
    output_zp_i = np.random.randint(MIN, MAX)
    shift_i = np.random.randint(0, 63) # values between 0-63
    max_int_i = MAX
    min_int_i = MIN
    double_round_i = np.random.randint(0, 1)
    multiplier_i = np.random.randint(-2**31, 2**31 - 1)

    # Writing the constant values to data.h
    data_str += [
        format_scalar_definition(
            "int8_t", "input_zp_i", input_zp_i
        )
    ]
    data_str += [
        format_scalar_definition(
            "int8_t", "output_zp_i", output_zp_i
        )
    ]
    data_str += [
        format_scalar_definition(
            "int8_t", "shift_i", shift_i
        )
    ]
    data_str += [
        format_scalar_definition(
            "int8_t", "max_int_i", max_int_i
        )
    ]
    data_str += [
    format_scalar_definition(
            "int8_t", "min_int_i", min_int_i
        )
    ]
    data_str += [
        format_scalar_definition(
            "int8_t", "double_round_i", double_round_i
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "multiplier_i", multiplier_i
        )
    ]

    c_golden_simd = postprocessing_simd_golden_model(
        c_golden_mm,
        input_zp_i,
        output_zp_i,
        shift_i,
        max_int_i,
        min_int_i,
        double_round_i,
        multiplier_i,
    )
    data_str += [format_vector_definition("int8_t", "C_golden_SIMD", c_golden_simd)]

    '''
    layout reshuffler for C
    input data layout: tiled row major, as the output of Postprocessing SIMD, annonated as tempStride0_C_in, tempStride1_C_in and spatialStride1_C_in
    base address: delta_local_C_out
    output data layout: tiled col major, as the input of GEMM, annonated as tempStride0_C_out, tempStride1_C_out and spatialStride1_C_out
    base address: delta_local_C_in
    '''

    data_str += [format_scalar_definition("int32_t", "delta_local_C_out", kwargs["delta_local_C_out"])]

    data_str += [format_scalar_definition("int8_t", "tempLoop0_C", kwargs["tempLoop0_C"])]
    data_str += [format_scalar_definition("int8_t", "tempLoop1_C", kwargs["tempLoop1_C"])]

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
    # output
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
    data_str += [format_scalar_definition("bool", "transpose_C", kwargs["transpose_C"])]

    C_data_layout_golden = data_reshuffler_golden_model(
        kwargs["tempLoop1_C"],
        kwargs["tempLoop0_C"],
        kwargs["spatial_len_0"],
        kwargs["spatial_len_1"],
        kwargs["tempStride0_C_in"],
        kwargs["tempStride1_C_in"],
        8,
        1,
        c_golden_simd
    )

    data_str += [format_vector_definition("int8_t", "C_data_layout_golden", C_data_layout_golden)]

    '''
    load in D and layout reshuffler for D
    from row major to tiled row major
    '''
    # load in D
    data_str += [format_scalar_definition("int8_t", "tempLoop0_D", kwargs["tempLoop0_D"])]
    data_str += [format_scalar_definition("int8_t", "tempLoop1_D", kwargs["tempLoop1_D"])]

    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride0_D_in", kwargs["DMAtempStride0_D_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAtempStride1_D_in", kwargs["DMAtempStride1_D_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "DMAspatialStride1_D_in", kwargs["DMAspatialStride1_D_in"]
        )
    ]

    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_D_in", kwargs["tempStride0_D_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_D_in", kwargs["tempStride1_D_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_D_in", kwargs["spatialStride1_D_in"]
        )
    ]    
    # output
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_D_out", kwargs["tempStride0_D_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_D_out", kwargs["tempStride1_D_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "spatialStride1_D_out", kwargs["spatialStride1_D_out"]
        )
    ] 

    data_str += [format_scalar_definition("int32_t", "delta_local_D_in", kwargs["delta_local_D_in"])]
    data_str += [format_scalar_definition("int32_t", "delta_local_D_out", kwargs["delta_local_D_out"])]

    length_d = (
        kwargs["tempLoop0_D"] * kwargs["tempLoop1_D"] * kwargs["meshRow"] * kwargs["tileSize"]
    )
    d = np.random.randint(MIN, MAX, length_d)

    # Generating golden data for D after layout reshuffling
    D_data_layout_golden = data_reshuffler_golden_model(
        kwargs["tempLoop0_D"],
        kwargs["tempLoop1_D"],
        kwargs["spatial_len_0"],
        kwargs["spatial_len_1"],
        kwargs["tempStride0_D_in"],
        kwargs["tempStride1_D_in"],
        1,
        kwargs["spatialStride1_D_in"],
        d
    )

    data_str += [format_vector_definition("int8_t", "D", d)]
    data_str += [format_scalar_definition("bool", "transpose_D", kwargs["transpose_D"])]

    # strides setting for E, two temp strides and one base address
    data_str += [format_scalar_definition("int32_t", "tempStride0_GEMM_E_out", kwargs["tempStride0_GEMM_E_out"])]
    data_str += [format_scalar_definition("int32_t", "tempStride1_GEMM_E_out", kwargs["tempStride1_GEMM_E_out"])]
    data_str += [format_scalar_definition("int32_t", "spatialStride1_GEMM_E_out", kwargs["spatialStride1_GEMM_E_out"])]
    data_str += [format_scalar_definition("int32_t", "delta_local_E_in", kwargs["delta_local_E_in"])]

    subtraction_d = np.random.randint(MIN, MAX)
    subtraction_c = np.random.randint(MIN, MAX)

    # Writing the subtraction value to data.h
    data_str += [
        format_scalar_definition(
            "int8_t", "subtraction_d", subtraction_d
        )
    ]
    data_str += [
        format_scalar_definition(
            "int8_t", "subtraction_c", subtraction_c
        )
    ]

    data_str += [format_vector_definition("int8_t", "D_data_layout_golden", D_data_layout_golden)]

    '''
    E = D * C!
    '''

    assert kwargs["tempLoop0_D"] == kwargs["tempLoop1_C"]
    assert kwargs["tempLoop0_A"] == kwargs["tempLoop0_B"]

    e_golden = block_gemm_golden_model(
        kwargs["tempLoop1_D"],
        kwargs["tempLoop0_D"],
        kwargs["tempLoop0_C"],
        kwargs["meshRow"],
        kwargs["tileSize"],
        kwargs["meshCol"],
        D_data_layout_golden,
        C_data_layout_golden,
        subtraction_d,
        subtraction_c
    )

    data_str += [format_vector_definition("int32_t", "E_golden", e_golden)]

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
