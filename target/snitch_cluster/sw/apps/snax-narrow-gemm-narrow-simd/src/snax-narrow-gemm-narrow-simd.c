// Copyright 2023 KU Leuven.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

#include "data.h"

#include "snax-gemm-lib.h"

#include "snax-streamer-gemm-lib.h"
#include "snax-streamer-simd-lib.h"

int main() {
    printf("Start SNAX GEMM-SIMD\n");
    // Set err value for checking
    int err = 0;

    // Prepare addresses in TCDM
    int8_t *local_a, *local_b;
    int32_t* local_c;

    // Allocate space in TCDM
    local_a = (int8_t*)(snrt_l1_next() + delta_local_a);
    local_b = (int8_t*)(snrt_l1_next() + delta_local_b);
    local_c = (int32_t*)(snrt_l1_next() + delta_local_c);

    uint32_t dma_pre_load = snrt_mcycle();

    // Transfer data from L3 to L1
    // Using DMA only
    if (snrt_is_dm_core()) {
        load_input_data(Batch, M, K, N, local_a, local_b, A, B,
                        strideInnermostA, strideInnermostB, ldA, ldB, strideA,
                        strideB);
        printf("DMA load data done\n");
    }

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    // GeMM core
    if (snrt_global_core_idx() == 0) {
        printf("Start GEMM\n");
        uint32_t gemm_start = snrt_mcycle();

        // Set Streamer configuration CSR
        set_streamer_csr(K, N, M, strideInnermostA, ldA, spatialA, strideInnermostB, ldB, spatialB,
                         strideInnermostC, ldC, spatialC, delta_local_a, delta_local_b,
                         delta_local_c);

        // Set CSR to start Streamer
        set_streamer_start();

        // Set GEMM configuration CSR
        uint32_t subtraction_setting =
            gen_subtraction_config(subtraction_a, subtraction_b);

        set_block_gemm_csr(K, N, M, subtraction_setting);

        // Set CSR to start GEMM
        set_block_gemm_start();

        // Wait until Streamer and GEMM accelerator finish
        wait_streamer_gemm();

        uint32_t gemm_end = snrt_mcycle();

        uint32_t gemm_streamer_cycle = read_gemm_streamer_perf_counter();
        printf("GEMM Streamer cycles: %d \n", gemm_streamer_cycle);
        uint32_t gemm_cycle = read_gemm_perf_counter();
        printf("GEMM cycles: %d \n", gemm_cycle);

        // Compare SNAX GEMM result with golden model
        err += check_result(local_c, C_golden_MM, Batch, M, N, strideInnermostC,
                            ldC, strideC);
    };

    // Wait for all cores to finish
    snrt_cluster_hw_barrier();

    // Prepare addresses in TCDM for D (simd output)
    int8_t *local_d;
    local_d = (int8_t*)(snrt_l1_next() + delta_local_d);

    // Using simd core
    if (snrt_global_core_idx() == 1) {
        uint32_t simd_start = snrt_mcycle();

        // Set Streamer configuration CSR
        set_streamer_simd_csr(N, M, strideInnermostC,
                        ldC, strideInnermostD, ldD, (int32_t)delta_local_c, (int32_t)delta_local_d);

        // Set CSR to start Streamer
        start_streamer_simd();

        // Set simd configuration CSR
        uint32_t csr0 =
            gen_csr0_config(input_zp_i, output_zp_i, shift_i, max_int_i);
        uint32_t csr1 = gen_csr1_config(min_int_i, double_round_i);
        uint32_t csr2 = gen_csr2_config(multiplier_i);

        set_simd_csr(csr0, csr1, csr2, N * M);

        // Set CSR to start simd
        start_simd();

        // Wait until Streamer and simd accelerator finish
        wait_streamer_simd();

        uint32_t simd_end = snrt_mcycle();

        uint32_t simd_streamer_cycle = read_simd_streamer_perf_counter();
        printf("SIMD Streamer cycles: %d \n", simd_streamer_cycle);
        uint32_t simd_cycle = read_simd_perf_counter();
        printf("SIMD cycles: %d \n", simd_cycle);

        // Compare SNAX streamer-simd result with golden python model
        err += check_simd_result(N, M, strideInnermostD,
                            ldD, local_d, C_golden_SIMD);
    };

    return err;
}
