# Copyright 2023 KULeuven.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Josse Van Delm <jvandelm@esat.kuleuven.be>

######################
# Invocation options #
######################

DEBUG ?= OFF # ON to turn on debugging symbols

###################
# Build variables #
###################

# Compiler toolchain
LLVM_VERSION    = 17
LLVM_BINROOT    ?= /usr/bin 
RISCV_CC        ?= $(LLVM_BINROOT)/clang-$(LLVM_VERSION)
RISCV_LD        ?= $(LLVM_BINROOT)/ld.lld-$(LLVM_VERSION)
RISCV_AR        ?= $(LLVM_BINROOT)/llvm-ar-$(LLVM_VERSION)
RISCV_OBJCOPY   ?= $(LLVM_BINROOT)/llvm-objcopy-$(LLVM_VERSION)
RISCV_OBJDUMP   ?= $(LLVM_BINROOT)/llvm-objdump-$(LLVM_VERSION)
RISCV_DWARFDUMP ?= $(LLVM_BINROOT)/llvm-dwarfdump-$(LLVM_VERSION)

# Compiler flags
RISCV_CFLAGS += $(addprefix -I,$(INCDIRS))
RISCV_CFLAGS += --target=riscv32-unknown-elf
RISCV_CFLAGS += -mcpu=generic-rv32
RISCV_CFLAGS += -march=rv32imafdzfh
RISCV_CFLAGS += -menable-experimental-extensions
RISCV_CFLAGS += -mabi=ilp32d
RISCV_CFLAGS += -mcmodel=medany
# RISCV_CFLAGS += -mno-fdiv # Not supported by Clang
RISCV_CFLAGS += -ffast-math
RISCV_CFLAGS += -fno-builtin-printf
RISCV_CFLAGS += -fno-builtin-sqrtf
RISCV_CFLAGS += -fno-common
RISCV_CFLAGS += -ftls-model=local-exec
RISCV_CFLAGS += -O3
ifeq ($(DEBUG), ON)
RISCV_CFLAGS += -g
endif
# Required by math library to avoid conflict with stdint definition
RISCV_CFLAGS += -D__DEFINED_uint64_t

# Linker flags
RISCV_LDFLAGS += -fuse-ld=$(RISCV_LD)
# Not necessary, because implied with -nostdlib
#RISCV_LDFLAGS += -nostartfiles
RISCV_LDFLAGS += -nostdlib
RISCV_LDFLAGS += -lclang_rt.builtins-riscv32
RISCV_LDFLAGS += -L/tools/riscv-llvm/lib/clang/12.0.1/lib/
# Is this necessary?
RISCV_LDFLAGS += -lc
RISCV_LDFLAGS += -L/tools/riscv-llvm/riscv32-unknown-elf/lib/
 
# Archiver flags
RISCV_ARFLAGS = rcs
