// Copyright 2023 KU Leuven.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

#include "data.h"

#include "snax-gemm-lib.h"

#include "snax-streamer-gemm-lib.h"

#include "snax-data-reshuffler-lib.h"

void snitch_data_reshuffler(int tempLoop0, int tempLoop1,
                            int tempStride0_in, int tempStride1_in, int spatialStride1_in,
                            int tempStride0_out, int tempStride1_out, int spatialStride1_out,
                            int8_t* local_in, int8_t* local_out, bool transpose    
                            ) {

    for (int loop1 = 0; loop1 < tempLoop1; loop1++) {
        for (int loop0 = 0; loop0 < tempLoop0; loop0++) {
            for (int spatial_i_1 = 0; spatial_i_1 < spatial_len_1; spatial_i_1++) {
                for( int spatial_i_0 = 0; spatial_i_0 < spatial_len_0; spatial_i_0++) {
                    if(transpose){
                        *(local_out + loop1 * tempStride1_out + loop0 * tempStride0_out +  spatialStride1_out * spatial_i_1 + spatial_i_0) =
                        *(local_in  + loop1 * tempStride1_in  + loop0 * tempStride0_in  +  spatialStride1_in * spatial_i_0  + spatial_i_1);
                    } else {
                        *(local_out + loop1 * tempStride1_out + loop0 * tempStride0_out +  spatialStride1_out * spatial_i_1 + spatial_i_0) =
                        *(local_in  + loop1 * tempStride1_in  + loop0 * tempStride0_in  +  spatialStride1_in * spatial_i_1  + spatial_i_0);
                    }
                    
                }
            }
        }
    }
    return;
}


int main() {

    // Set err value for checking
    int err = 0;

    int repeat_times = 2;
    
    // Prepare addresses in TCDM
    int8_t *local_A_in, *local_A_out, *local_B_in, *local_B_out;

    // Allocate space in TCDM
    local_A_in = (int8_t*)(snrt_l1_next() + delta_local_A_in);
    local_A_out = (int8_t*)(snrt_l1_next() + delta_local_A_out);
    local_B_in = (int8_t*)(snrt_l1_next() + delta_local_B_in);
    local_B_out = (int8_t*)(snrt_l1_next() + delta_local_B_out);

    uint32_t dma_pre_load = snrt_mcycle();

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

    if (snrt_global_core_idx() == 0) {

        for (int i = 0; i < repeat_times; i++){
            uint32_t data_reshuffler_start = snrt_mcycle();

            // Set Streamer configuration CSR
            snitch_data_reshuffler(tempLoop0_A, tempLoop1_A, tempStride0_A_in,
                            tempStride1_A_in, spatialStride1_A_in, tempStride0_A_out, tempStride1_A_out, spatialStride1_A_out, local_A_in, local_A_out, transpose_A);

            uint32_t data_reshuffler_end = snrt_mcycle();

            printf("Reshuffle A cycles: %d  \n", data_reshuffler_end-data_reshuffler_start);
        }
        
    };

    snrt_cluster_hw_barrier();

    err = 0;
    if (snrt_global_core_idx() == 0) {
        for (int i = 0; i < repeat_times; i++){
            uint32_t data_reshuffler_start = snrt_mcycle();

            // Set Streamer configuration CSR
            snitch_data_reshuffler(tempLoop0_B, tempLoop1_B, tempStride0_B_in,
                            tempStride1_B_in, spatialStride1_B_in, tempStride0_B_out, tempStride1_B_out, spatialStride1_B_out, local_B_in, local_B_out, transpose_B);

            uint32_t data_reshuffler_end = snrt_mcycle();
            
            printf("Reshuffle B cycles: %d \n", data_reshuffler_end-data_reshuffler_start);
        }
    };
    
    snrt_cluster_hw_barrier();

    int32_t* local_C_in, *local_C_out;
    local_C_in = (int32_t*)(snrt_l1_next() + delta_local_C_in);
    local_C_out = (int32_t*)(snrt_l1_next() + delta_local_C_out);

    err = 0;

    if (snrt_global_core_idx() == 0) {
        uint32_t gemm_start = snrt_mcycle();

        // Set Streamer configuration CSR
        set_streamer_csr(tempLoop0_A, tempLoop1_B, tempLoop1_A, tempStride0_A_out, tempStride1_A_out, spatialStride1_A_out, tempStride0_B_out, tempStride1_B_out, spatialStride1_B_out,
                         DMAtempStride0_C_in, DMAtempStride1_C_in, DMAspatialStride1_C_in, delta_local_A_out, delta_local_B_out,
                         delta_local_C_in);
        // Set GEMM configuration CSR
        uint32_t subtraction_setting =
            gen_subtraction_config(subtraction_a, subtraction_b);

        set_block_gemm_csr(tempLoop0_A, tempLoop1_B, tempLoop1_A, subtraction_setting);

        // Set CSR to start Streamer
        set_streamer_start();

        // Set CSR to start GEMM
        set_block_gemm_start();

        // Poll until Streamer and GEMM accelerator finish
        wait_streamer_gemm();

        uint32_t gemm_end = snrt_mcycle();

        uint32_t gemm_streamer_cycle = read_gemm_streamer_perf_counter();
        printf("GEMM Streamer cycles: %d \n", gemm_streamer_cycle);
        uint32_t gemm_cycle = read_gemm_perf_counter();
        printf("GEMM cycles: %d \n", gemm_cycle);

        // Compare SNAX GEMM result with golden model
        err += check_result(local_C_in, C_golden, Batch, tempLoop1_B, tempLoop1_A, DMAtempStride0_C_in,
                            DMAtempStride1_C_in, strideC);

        printf("GEMM on A and B finished. error: %d\n", err);

    };

    // snrt_cluster_hw_barrier();

    // // perform data reshuffler on C, from tiled row major to row major
    // // err = 0;
    // if (snrt_global_core_idx() == 0) {
    //     uint32_t data_reshuffler_start = snrt_mcycle();

    //     // Set Streamer configuration CSR
    //     set_data_reshuffler_csr(tempLoop1_B, tempLoop1_A, tempStride0_C_in,
    //                     tempStride1_C_in, spatialStride1_C_in, tempStride0_C_out, tempStride1_C_out, spatialStride1_C_out, (int32_t)delta_local_C_in, (int32_t)delta_local_C_out, transpose_C);

    //     // Set CSR to start Streamer
    //     start_data_reshuffler();

    //     wait_data_reshuffler();

    //     uint32_t data_reshuffler_end = snrt_mcycle();

    //     // Compare SNAX streamer-data-reshuffler result with golden python model
    //     err += check_result(local_C_out, C_golden, Batch, tempLoop1_B, tempLoop1_A, tempStride0_C_out,
    //                         tempStride1_C_out, strideC);
    //     // printf("Data reshuffler on C finished. error: %d\n", err);
    // };

    // snrt_cluster_hw_barrier();
    
    // if(snrt_global_core_idx() == 1) {
    //     printf("SNAX GEMM + Data Reshuffler test finished. error: %d\n", err);
    // }

    return err;
}
