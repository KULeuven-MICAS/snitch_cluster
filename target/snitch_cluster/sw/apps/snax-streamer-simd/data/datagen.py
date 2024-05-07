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
    emit_str += emit_gemm_data(**kwargs)
    return emit_str


MIN = -128
MAX = 127


def emit_gemm_data(**kwargs):
    data_str = []

    # Generating matrix size settings
    data_str += [format_scalar_definition("int8_t", "tempLoop0", kwargs["tempLoop0"])]
    data_str += [format_scalar_definition("int8_t", "tempLoop1", kwargs["tempLoop1"])]

    # Generating temporal strides settings

    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_in", kwargs["tempStride0_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_in", kwargs["tempStride1_in"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride0_out", kwargs["tempStride0_out"]
        )
    ]
    data_str += [
        format_scalar_definition(
            "int32_t", "tempStride1_out", kwargs["tempStride1_out"]
        )
    ]

    # Generating base address pointers
    data_str += [format_scalar_definition("int32_t", "delta_local_in", kwargs["delta_local_in"])]
    data_str += [format_scalar_definition("int32_t", "delta_local_out", kwargs["delta_local_out"])]

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

    # Generating random input data vector
    length_in = (
        kwargs["tempLoop0"] * kwargs["tempLoop1"] * kwargs["vec_len"]
    )
    length_out = (
        kwargs["tempLoop0"] * kwargs["tempLoop1"] * kwargs["vec_len"]
    )
    data_in = np.random.randint(-2**31, 2**31 - 1, length_in)

    # Generating golden data
    c_golden = postprocessing_simd_golden_model(
        data_in,
        input_zp_i,
        output_zp_i,
        shift_i,
        max_int_i,
        min_int_i,
        double_round_i,
        multiplier_i,
    )

    c_init = np.zeros(c_golden.shape)
    c_cpu = np.zeros(c_golden.shape)

    # Writing testing data and golden data into data.h
    data_str += [format_vector_definition("int32_t", "DataIn", data_in)]
    data_str += [format_vector_definition("int8_t", "C_golden", c_golden)]
    data_str += [format_vector_definition("int8_t", "C_golden_c_spec", c_golden)]
    data_str += [format_vector_definition("int8_t", "C", c_init)]
    data_str += [format_vector_definition("int8_t", "C_cpu", c_cpu)]

    data_str = "\n\n".join(data_str)

    return data_str


def main():
    # Parsing cmd args
    parser = argparse.ArgumentParser(description="Generating data for kernels")
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
