// Copyright 2023 KU Leuven.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

#include "snax-data-reshuffler-lib.h"

// Set STREAMER configuration CSR
void set_data_reshuffler_csr(int tempLoop0, int tempLoop1, int tempStride0_in, int tempStride1_in, int spatialStride1_in, int tempStride0_out,
                       int tempStride1_out, int spatialStride1_out, int32_t delta_local_in, int32_t delta_local_out, bool transpose) {
    write_csr(960+0, transpose);

    // temporal loop bounds, from innermost to outermost
    write_csr(960+8+0, tempLoop0);
    write_csr(960+8+1, tempLoop1);

    // temporal strides for data reader (In)
    write_csr(960+8+2, tempStride0_in);
    write_csr(960+8+3, tempStride1_in);

    // temporal strides for data writer (Out)
    write_csr(960+8+4, tempStride0_out);
    write_csr(960+8+5, tempStride1_out);

    // fixed spatial strides for data reader (In)
    write_csr(960+8+6, spatialStride1_in);

    // fixed spatial strides for data writer (Out)
    write_csr(960+8+7, spatialStride1_out);

    // base ptr for data reader (In)
    write_csr(960+8+8, (uint32_t)(delta_local_in + snrt_l1_next()));

    // base ptr for data writer (Out)
    write_csr(960+8+9, (uint32_t)(delta_local_out + snrt_l1_next()));

}

// Set CSR to start STREAMER
void start_data_reshuffler() { write_csr(960+8+11, 1); }

void wait_data_reshuffler() {
    write_csr(960+8+11, 0);
}

void start_then_wait_data_reshuffler(){
    snrt_mcycle();
    write_csr(960+8+11, 1);
    write_csr(960+8+11, 0);
    write_csr(960+8+11, 0);
    snrt_mcycle();
}

uint32_t read_data_reshuffler_perf_counter(){
    uint32_t perf_counter = read_csr(960+8+10);
    return perf_counter;
}

void load_data_reshuffler_test_data(int tempLoop0, int tempLoop1, int tempStride0,
                         int tempStride1, int spatialStride1, int8_t* base_ptr_local,
                         int8_t* base_ptr_l2){
    int8_t* addr_in;
    int8_t* addr_In;

    for (int loop1 = 0; loop1 < tempLoop1; loop1++) {
        for (int loop0 = 0; loop0 < tempLoop0; loop0++) {
            for (int spatial_i_1 = 0; spatial_i_1 < spatial_len_1; spatial_i_1++) {
                addr_in =
                    base_ptr_local + loop1 * tempStride1 + loop0 * tempStride0 + spatial_i_1 * spatialStride1;
                addr_In =
                    base_ptr_l2 + loop1 * tempLoop0 * spatial_len + loop0 * spatial_len + spatial_i_1 * spatial_len_1;
                snrt_dma_start_1d(addr_in, addr_In, spatial_len_0 * sizeof(int8_t));
            }
        }
    }
}

uint32_t check_data_reshuffler_result(int tempLoop0, int tempLoop1, int tempStride0,
                           int tempStride1, int spatialStride1, int8_t* base_ptr_local,
                           int8_t* base_ptr_l2){
    int8_t* addr_out;
    int8_t* addr_Out;
    uint32_t error = 0;

    for (int loop1 = 0; loop1 < tempLoop1; loop1++) {
        for (int loop0 = 0; loop0 < tempLoop0; loop0++) {
            for (int spatial_i_1 = 0; spatial_i_1 < spatial_len_1; spatial_i_1++) {
                for (int spatial_i_0 = 0; spatial_i_0 < spatial_len_0; spatial_i_0++) {
                    addr_out =
                        base_ptr_local + loop1 * tempStride1 + loop0 * tempStride0 + spatial_i_1 * spatialStride1 + spatial_i_0;
                    addr_Out =
                        base_ptr_l2 + loop1 * tempLoop0 * spatial_len + loop0 * spatial_len + spatial_i_1 * spatial_len_1 + spatial_i_0;
                    if ((int8_t)*addr_out != (int8_t)*addr_Out) {
                        // printf("Error: addr_out = %d, addr_Out = %d\n", (int8_t)*addr_out, (int8_t)*addr_Out);
                        error++;
                    }
                }
            }
        }
    }

    return error;

}
