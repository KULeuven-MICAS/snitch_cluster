// Copyright 2023 KU Leuven.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

#include "data.h"

#include "snax-gemm-lib.h"

#include "snax-streamer-gemm-lib.h"
#include "snax-streamer-simd-lib.h"

#include "snax-data-reshuffler-lib.h"

int main() {

    // Set err value for checking
    int err = 0;

    /****************************************************************************
    * Move A and B data from L3 to L1
    * Perform data reshuffling on A and B for GEMM
    ****************************************************************************/

    // Prepare addresses in TCDM
    int8_t *local_A_in, *local_A_out, *local_B_in, *local_B_out;

    // Allocate space in TCDM
    local_A_in = (int8_t*)(snrt_l1_next() + delta_local_A_in);
    local_A_out = (int8_t*)(snrt_l1_next() + delta_local_A_out);
    local_B_in = (int8_t*)(snrt_l1_next() + delta_local_B_in);
    local_B_out = (int8_t*)(snrt_l1_next() + delta_local_B_out);

    // Transfer data from L3 to L1
    // Using DMA only
    if (snrt_is_dm_core()) {
        load_data_reshuffler_test_data(tempLoop0_A, tempLoop1_A, DMAtempStride0_A_in,
                        DMAtempStride1_A_in, DMAspatialStride1_A_in, local_A_in, A);
        load_data_reshuffler_test_data(tempLoop0_B, tempLoop1_B, DMAtempStride0_B_in,
                        DMAtempStride1_B_in, DMAspatialStride1_B_in, local_B_in, B);
    }

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    /****************************************************************************
    * Perform GEMM on A and B using GEMM core, C = A * B, int8 -> int32
    ****************************************************************************/
    int32_t* local_C_in, *local_C_out, *local_GEMM_C_out;
    local_C_in = (int32_t*)(snrt_l1_next() + delta_local_C_in);
    local_C_out = (int32_t*)(snrt_l1_next() + delta_local_C_out);
    local_GEMM_C_out = (int32_t*)(snrt_l1_next() + delta_local_GEMM_C_out);

    // Perform GEMM on A and B using GEMM core
    if (snrt_global_core_idx() == 0) {

        // Set Streamer configuration CSR
        set_streamer_csr(tempLoop0_A, tempLoop1_B, tempLoop1_A, tempStride0_A_in, tempStride1_A_in, spatialStride1_A_in, tempStride0_B_in, tempStride1_B_in, spatialStride1_B_in,
                         tempStride0_GEMM_C_out, tempStride1_GEMM_C_out, spatialStride1_GEMM_C_out, delta_local_A_in, delta_local_B_in,
                         delta_local_GEMM_C_out);

        // Set GEMM configuration CSR
        uint32_t subtraction_setting =
            gen_subtraction_config(subtraction_a, subtraction_b);

        // Set GEMM configuration CSR 
        set_block_gemm_csr(tempLoop0_A, tempLoop1_B, tempLoop1_A, subtraction_setting);

        uint32_t gemm_start = snrt_mcycle();

        // Set CSR to start Streamer
        set_streamer_start();

        // Set CSR to start GEMM
        set_block_gemm_start();

        // Wait until Streamer and GEMM accelerator finish
        wait_streamer_gemm();

        uint32_t gemm_end = snrt_mcycle();

        uint32_t gemm_cycle = read_gemm_perf_counter();
        // Compare SNAX GEMM result with golden model
        err += check_result(local_GEMM_C_out, C_golden_GEMM, Batch, tempLoop1_B, tempLoop1_A, tempStride0_GEMM_C_out,
                            tempStride1_GEMM_C_out, strideC);
        
        printf("GEMM on A and B finished. error: %d\n", err);
        printf("GEMM cycles: %d \n", gemm_cycle);
    };

    snrt_cluster_hw_barrier();

    /****************************************************************************
    * Perform post-processing for GEMM'S output data C, int32 -> int8 
    ****************************************************************************/

    // Perform post-processing for C using post-processing core
    // Data width reduced from int32 to int8 for C

    if (snrt_global_core_idx() == 1) {

        // Set Streamer configuration CSR
        set_streamer_simd_csr(tempLoop0_C, tempLoop1_C, tempStride0_GEMM_C_out,
                        tempStride1_GEMM_C_out, DMAtempStride0_C_in, DMAtempStride1_C_in, (int32_t)delta_local_GEMM_C_out, (int32_t)delta_local_C_in);

        // Set simd configuration CSR
        uint32_t csr0 =
            gen_csr0_config(input_zp_i, output_zp_i, shift_i, max_int_i);
        uint32_t csr1 = gen_csr1_config(min_int_i, double_round_i);
        uint32_t csr2 = gen_csr2_config(multiplier_i);

        // Set simd configuration CSR
        set_simd_csr(csr0, csr1, csr2, tempLoop0_C * tempLoop1_C);

        uint32_t simd_start = snrt_mcycle();

        // Set CSR to start Streamer
        start_streamer_simd();

        // Set CSR to start simd
        start_simd();

        // Wait until Streamer and simd accelerator finish
        wait_streamer_simd();

        uint32_t simd_end = snrt_mcycle();
        uint32_t simd_cycle = read_simd_perf_counter();

        // Compare SNAX streamer-simd result with golden python model
        err += check_simd_result(tempLoop0_C, tempLoop1_C, DMAtempStride0_C_in,
                           DMAtempStride1_C_in, (int8_t *)local_C_in, C_golden_SIMD);
        printf("Post-processing for GEMM'S output data C finished. error: %d\n", err);
        printf("SIMD cycles: %d \n", simd_cycle);
    }

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    /****************************************************************************
    * Perform data reshuffling for post-processed C
    ****************************************************************************/

    // Perform data reshuffling for C using data reshuffler core
    // From tiledrowmajor to tiledcolmajor
    if (snrt_global_core_idx() == 2) {

        // Set data reshuffler configuration CSR
        set_data_reshuffler_csr(tempLoop1_C, tempLoop0_C, tempStride0_C_in,
                        tempStride1_C_in, spatialStride1_C_in, tempStride0_C_out, tempStride1_C_out, spatialStride1_C_out, (int32_t)delta_local_C_in, (int32_t)delta_local_C_out, transpose_C);

        uint32_t data_reshuffler_start = snrt_mcycle();

        // Set CSR to start data reshuffler
        start_data_reshuffler();

        // Wait for data-reshuffler to finish
        wait_data_reshuffler();

        uint32_t data_reshuffler_end = snrt_mcycle();
        uint32_t dr_cycle = read_data_reshuffler_perf_counter();
        err += check_data_reshuffler_result(tempLoop1_C, tempLoop0_C, tempStride0_C_out,
                            tempStride1_C_out, spatialStride1_C_out, (int8_t *)local_C_out, C_data_layout_golden);
        // printf("Data reshuffling for post-processed C finished. error: %d\n", err);
    };

    snrt_cluster_hw_barrier();
    if (snrt_global_core_idx() == 0) {
        printf("Data reshuffling for post-processed C finished. error: %d\n", err);
    }
    snrt_cluster_hw_barrier();

    /****************************************************************************
    * Move D data from L3 to L1 and perform data reshuffling for D
    ****************************************************************************/

    int8_t *local_D_in, *local_D_out;

    // Allocate space in TCDM
    local_D_in = (int8_t*)(snrt_l1_next() + delta_local_D_in);
    local_D_out = (int8_t*)(snrt_l1_next() + delta_local_D_out);

    if (snrt_is_dm_core()) {
        load_data_reshuffler_test_data(tempLoop0_D, tempLoop1_D, DMAtempStride0_D_in,
                        DMAtempStride1_D_in, DMAspatialStride1_D_in, local_D_in, D);
    }

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    /****************************************************************************
    * Perform GEMM on D and C using GEMM core, E = D * C, int8 -> int32
    ****************************************************************************/

    int32_t *local_E_in;
    local_E_in = (int32_t*)(snrt_l1_next() + delta_local_E_in);

    if (snrt_global_core_idx() == 0) {

        // Set Streamer configuration CSR
        set_streamer_csr(tempLoop1_C, tempLoop0_C, tempLoop1_D, tempStride0_D_in, tempStride1_D_in, spatialStride1_D_in, tempStride0_C_out, tempStride1_C_out, spatialStride1_C_out,
                         tempStride0_GEMM_E_out, tempStride1_GEMM_E_out, spatialStride1_GEMM_E_out, delta_local_D_in, delta_local_C_out,
                         delta_local_E_in);

        // Set GEMM configuration CSR
        uint32_t subtraction_setting =
            gen_subtraction_config(subtraction_d, subtraction_c);

        // Set GEMM configuration CSR
        set_block_gemm_csr(tempLoop1_C, tempLoop0_C, tempLoop1_D, subtraction_setting);

        uint32_t gemm_start = snrt_mcycle();

        // Set CSR to start Streamer
        set_streamer_start();

        // Set CSR to start GEMM
        set_block_gemm_start();

        // Wait until Streamer and GEMM accelerator finish
        wait_streamer_gemm();

        uint32_t gemm_end = snrt_mcycle();
        uint32_t gemm_cycle = read_gemm_perf_counter();

        // Compare SNAX GEMM result with golden model
        err += check_result(local_E_in, E_golden, Batch, tempLoop0_C, tempLoop1_D, tempStride0_GEMM_E_out,
                            tempStride1_GEMM_E_out, strideC);
        printf("GEMM on D and C finished. error: %d\n", err);
        printf("GEMM cycles: %d \n", gemm_cycle);
    };

    return err;
}
