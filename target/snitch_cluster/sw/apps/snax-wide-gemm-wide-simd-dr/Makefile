# Copyright 2023 KU Leuven.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

APP     = snax-wide-gemm-wide-simd-dr

INCDIRS = data

INCDIRS += ../../snax/streamer-gemm/include
INCDIRS += ../../snax/streamer-simd/include
INCDIRS += ../../snax/gemm/include
INCDIRS += ../../snax/data-reshuffler/include

# Include this binary in the final build
RISCV_LDFLAGS += ../../snax/streamer-gemm/build/snax-streamer-gemm-lib.o
RISCV_LDFLAGS += ../../snax/gemm/build/snax-gemm-lib.o
RISCV_LDFLAGS += ../../snax/streamer-simd/build/snax-streamer-simd-lib.o
RISCV_LDFLAGS += ../../snax/data-reshuffler/build/snax-data-reshuffler-lib.o

SRCS    = src/snax-wide-gemm-wide-simd-dr.c

include ../common.mk
include ./data/Makefile

$(DEP): $(DATA_H)
