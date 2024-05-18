// Copyright 2024 KU Leuven.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

#include "snrt.h"

#include "data.h"

int main() {
    // Set err value for checking
    int err = 0;

    uint64_t final_output;

    uint64_t *local_a, *local_b, *local_o;

    //---------------------------
    // Allocates space in TCDM
    //---------------------------
    local_a = (uint64_t *)snrt_l1_next();
    local_b = local_a + VEC_LEN;
    local_o = local_b + VEC_LEN;

    //---------------------------
    // Start of pre-loading data from L2 memory
    // towards the L1 TCDM memory
    //---------------------------

    // Use the Snitch core with a DMA
    // to move the data from L2 to L1
    if (snrt_is_dm_core()) {
        // This measures the start of cycle count
        // for preloading the data to the L1 memory
        uint32_t start_dma_load = snrt_mcycle();

        // The VEC_LEN is found in data.h
        size_t vector_size = VEC_LEN * sizeof(uint64_t);
        snrt_dma_start_1d(local_a, A, vector_size);
        snrt_dma_start_1d(local_b, B, vector_size);

        // Measure the end of the transfer process
        uint32_t end_dma_load = snrt_mcycle();
    }

    // Synchronize cores by setting up a
    // fence barrier for the DMA and accelerator core
    snrt_cluster_hw_barrier();

    // This is assigns the functions inside to
    // run the core with the accelerator
    if (snrt_is_compute_core()) {
        // This marks the start of the
        // setting of CSRs for the accelerator
        uint32_t start_csr_setup = snrt_mcycle();

        //------------------------------
        // 1st set the streamer CSRs
        // The list of CSRs are:
        // 0x3c0 - loop bound for all components (RW)
        // 0x3c1 - temporal stride for input A (RW)
        // 0x3c2 - temporal stride for input B (RW)
        // 0x3c3 - temporal stride for output O (RW)
        // 0x3c4 - spatial stride for input A (RW)
        // 0x3c5 - spatial stride for input B (RW)
        // 0x3c6 - spatial stride for input O (RW)
        // 0x3c7 - base pointer for input A (RW)
        // 0x3c8 - base pointer for input B (RW)
        // 0x3c9 - base pointer for input O (RW)
        // 0x3ca - send configurations to streamer (RW)
        // 0x3cb - performance counter of streamer (RO)
        //------------------------------
        write_csr(0x3c0, VEC_LEN);
        write_csr(0x3c1, 32);
        write_csr(0x3c2, 32);
        write_csr(0x3c3, 32);
        write_csr(0x3c4, 8);
        write_csr(0x3c5, 8);
        write_csr(0x3c6, 8);
        write_csr(0x3c7, (uint64_t)local_a);
        write_csr(0x3c8, (uint64_t)local_b);
        write_csr(0x3c9, (uint64_t)local_o);
        write_csr(0x3ca, 1);

        //------------------------------
        // 2nd set the CSRs of the accelerator
        // 0x3cc - mode of the ALU (RW)
        //       - 0 for add, 1 for sub, 2 for mul, 3 for XOR
        // 0x3cd - length of data (RW)
        // 0x3ce - send configurations to accelerator (RW)
        // 0x3cf - busy status (RO)
        // 0x3d0 - performance counter (RO)
        //------------------------------
        write_csr(0x3cc, 2);
        write_csr(0x3cd, VEC_LEN);
        write_csr(0x3ce, 1);

        uint32_t end_csr_setup = snrt_mcycle();

        // Do this to poll the accelerator
        while(read_csr(0x3cf));

        uint32_t perf_count = read_csr(0x3d0);
        printf("Accelerator Done! \n");
        printf("Accelerator Cycles: %d \n", perf_count);
        
    };

    return err;
}
