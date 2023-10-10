// Copyright 2020 ETH Zurich and University of Bologna.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

#include "snrt.h"

#include "data.h"

static inline uint32_t lw_reg (
    uint32_t base_address,
    uint16_t immediate_offset
){
    uint32_t loaded_reg;

    asm volatile(
        "lw %[result], %[offset](%[base])"
        : [result ]"=r" (loaded_reg)
        : [offset] "i" (immediate_offset), [base] "r" (base_address)
    );

    return loaded_reg;
};

int main() {
    // Set err value for checking
    int err = 0;

    uint32_t final_output;

    uint32_t *local_a, *local_b, *local_c, *local_o;

    // Allocate space in TCDM
    local_a = (uint32_t *)snrt_l1_next();
    local_b = local_a + VEC_LEN;
    local_c = local_b + VEC_LEN;
    local_o = local_c + 1;

    uint32_t dma_pre_load = snrt_mcycle();

    // Use data mover core to bring data from L3 to TCDM
    if (snrt_is_dm_core()) {
        size_t vector_size = VEC_LEN * sizeof(uint32_t);
        size_t scale_size = 1 * sizeof(uint32_t);
        snrt_dma_start_1d(local_a, A, vector_size);
        snrt_dma_start_1d(local_b, B, vector_size);
        snrt_dma_start_1d(local_c, &C, scale_size);
    }

    // Wait until DMA transfer is done
    snrt_cluster_hw_barrier();

    // Read the mcycle CSR (this is our way to mark/delimit a specific
    // code region for benchmarking)
    uint32_t pre_is_compute_core = snrt_mcycle();

    if (snrt_is_compute_core()) {
        // This marks the start of the accelerator style of MAC operation
        uint32_t csr_set = snrt_mcycle();

        // Set addresses
        write_csr(0x3d0, (uint32_t)local_a);
        write_csr(0x3d1, (uint32_t)local_b);
        write_csr(0x3d2, (uint32_t)local_c);
        write_csr(0x3d3, (uint32_t)local_o);

        // Set configs
        write_csr(0x3d4, 1);   // Number of iterations
        write_csr(0x3d5, 19);  // Vector length

        // Write start CSR to launch accelerator
        write_csr(0x3c0, 0);

        // Start of CSR start and poll until accelerator finishes
        uint32_t mac_start = snrt_mcycle();

        uint32_t break_poll;

        while (1) {
            // 0x3c3 is the CSR address for accelerator status
            break_poll = read_csr(0x3c3);
            if (break_poll == 0) {
                break;
            };
        };

        lw_reg(local_a, 0);
        lw_reg(local_a, 4);
        lw_reg(local_a, 8);
        lw_reg(local_a, 12);
        lw_reg(local_a, 16);
        lw_reg(local_a, 20);
        lw_reg(local_a, 24);
        lw_reg(local_a, 28);
        lw_reg(local_a, 32);
        lw_reg(local_a, 36);
        lw_reg(local_a, 40);
        lw_reg(local_a, 44);
        lw_reg(local_a, 48);
        lw_reg(local_a, 52);
        lw_reg(local_a, 56);
        lw_reg(local_a, 60);
        lw_reg(local_a, 64);
        lw_reg(local_a, 68);
        lw_reg(local_a, 72);
        lw_reg(local_a, 76);
        lw_reg(local_a, 80);
        lw_reg(local_a, 84);
        lw_reg(local_a, 88);
        lw_reg(local_a, 92);
        lw_reg(local_a, 96);
        lw_reg(local_a, 100);
        lw_reg(local_a, 104);
        lw_reg(local_a, 108);
        lw_reg(local_a, 112);
        lw_reg(local_a, 116);
        lw_reg(local_a, 120);
        lw_reg(local_a, 124);
        lw_reg(local_a, 128);
        lw_reg(local_a, 132);
        lw_reg(local_a, 136);
        lw_reg(local_a, 140);
        lw_reg(local_a, 144);
        lw_reg(local_a, 148);
        lw_reg(local_a, 152);
        lw_reg(local_a, 156);
        lw_reg(local_a, 160);
        lw_reg(local_a, 164);
        lw_reg(local_a, 168);
        lw_reg(local_a, 172);

        uint32_t mac_end = snrt_mcycle();

        final_output = *local_o;

        if (final_output != 54763) {
            err = 1;
        }

        uint32_t end_of_check = snrt_mcycle();
    };

    return err;
}
