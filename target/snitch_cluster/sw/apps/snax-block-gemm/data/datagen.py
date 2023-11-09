#!/usr/bin/env python3

import numpy as np
import argparse
import pathlib
import hjson
import sys
import os

np.random.seed(42)

# Add data utility path
sys.path.append(os.path.join(os.path.dirname(__file__),
                "../../../../../../util/sim/"))
from data_utils import format_scalar_definition, \
                       format_vector_definition

# Golden model in python
def block_gemm_golden_model(m,k,n,row,size,col,a,b):
    c = np.zeros(m*row*n*col, dtype = (np.int32))
    for mm in range(m):
        for nn in range(n):
            for kk in range(k):
                for rr in range(row):
                    for cc in range(col):
                        for ss in range(size):
                            c[mm * n * row * col + nn * row * col + rr * size + cc] = \
                            c[mm * n * row * col + nn * row * col + rr * size + cc] + \
                                a[mm * k * row * col + kk * row * col + rr * size + ss] * \
                                b[nn * k * row * col + kk * row * col + cc * size + ss]
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
    data_str += [format_scalar_definition('int8_t', 'Batch', kwargs['Batch'])]
    data_str += [format_scalar_definition('int8_t', 'M', kwargs['M'])]
    data_str += [format_scalar_definition('int8_t', 'K', kwargs['K'])]
    data_str += [format_scalar_definition('int8_t', 'N', kwargs['N'])]

    # Generating strides settings
    data_str += [format_scalar_definition('int32_t', 'ldA', kwargs['ldA'])]
    data_str += [format_scalar_definition('int32_t', 'ldB', kwargs['ldB'])]
    data_str += [format_scalar_definition('int32_t', 'ldC', kwargs['ldC'])]
    data_str += [format_scalar_definition('int32_t', 'strideA', kwargs['strideA'])]
    data_str += [format_scalar_definition('int32_t', 'strideB', kwargs['strideB'])]
    data_str += [format_scalar_definition('int32_t', 'strideC', kwargs['strideC'])]

    # Generate random input matrices
    length_a = kwargs['M'] * kwargs['K'] * kwargs['meshRow'] * kwargs['tileSize']
    length_b = kwargs['N'] * kwargs['K'] * kwargs['meshCol'] * kwargs['tileSize']
    a = np.random.randint(MIN, MAX, length_a)
    b = np.random.randint(MIN, MAX, length_b)

    # Generating golden data
    c_golden = block_gemm_golden_model(kwargs['M'], kwargs['K'], kwargs['N'], kwargs['meshRow'], kwargs['tileSize'], kwargs['meshCol'], a, b)
    c_init = np.zeros(c_golden.shape)
    c_cpu = np.zeros(c_golden.shape)

    # Writing testing data and golden data into data.h
    data_str += [format_vector_definition('int8_t', 'A', a)]
    data_str += [format_vector_definition('int8_t', 'B', b)]
    data_str += [format_vector_definition('int32_t', 'C_golden', c_golden)]
    data_str += [format_vector_definition('int32_t', 'C', c_init)]
    data_str += [format_vector_definition('int32_t', 'C_cpu', c_cpu)]

    data_str = '\n\n'.join(data_str)

    return data_str

def main():

    # Parsing cmd args
    parser = argparse.ArgumentParser(description='Generate data for kernels')
    parser.add_argument(
        "-c", "--cfg",
        type=pathlib.Path,
        required=True,
        help='Select param config file kernel'
    )
    args = parser.parse_args()

    # Load param config file
    with args.cfg.open() as f:
        param = hjson.loads(f.read())

    # Emit header file
    print(emit_header_file(**param))

if __name__ == '__main__':
    main()