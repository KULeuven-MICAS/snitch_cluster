// Copyright 2023 KU Leuven.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

#include "data.h"

#include "snax-gemm-lib.h"

#include "snax-streamer-gemm-lib.h"

#include "snax-streamer-gemm-conv-lib.h"

// two exp for two conv2d
// firstly, using explicit im2col to map conv2d to gemm
// using normal streamer for gemm to compute (3 loops)

// secondlly, using implicit im2col to map conv2d to gemm
// using streamer for conv to compute (many loops)

// simple test with 1x1 convolution
// i = (1, 2, 4, 8)
// w = (8, 1, 1, 8)
// o = (1, 2, 4, 8)
// stride = 1
// padding = 0

// larger conv2d
// i = (1, 32, 32, 16)
// w = (16, 3, 3, 16)
// o = (1, 32, 32, 16)
// stride = 1
// padding = 1
// needs 256KB TCDM

int main() {
    // Set err value for checking
    int err = 0;

    // Prepare addresses in TCDM
    int8_t *local_a, *local_b;
    int32_t* local_c;

    // Allocate space in TCDM
    local_a = (int8_t*)(snrt_l1_next() + delta_local_a);
    local_b = (int8_t*)(snrt_l1_next() + delta_local_b);
    local_c = (int32_t*)(snrt_l1_next() + delta_local_c);

    // Transfer data from L3 to L1
    // Using DMA only
    if (snrt_is_dm_core()) {
        load_conv_input_data(Nbatch, H + 2 * pad_h, W + 2 * pad_w, Cin, local_a, A);
        load_weight_data(Cout, Kh, Kw, Cin, local_b, B);
    }

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    if (snrt_global_core_idx() == 0) {
        // uint32_t gemm_start = snrt_mcycle();

        // Set Streamer configuration CSR
        set_conv_streamer_csr(
            Aslstride0, Aslstride1, Atlbound0, Atlstride0, Atlbound1,
            Atlstride1, Atlbound2, Atlstride2, Atlbound3, Atlstride3, Atlbound4,
            Atlstride4, Atlbound5, Atlstride5, Bslstride0, Bslstride1,
            Btlbound0, Btlstride0, Btlbound1, Btlstride1, Btlbound2, Btlstride2,
            Cslstride0, Cslstride1, Ctlbound0, Ctlstride0, Ctlbound1,
            Ctlstride1, Ctlbound2, Ctlstride2, delta_local_a, delta_local_b,
            delta_local_c);

        // Set CSR to start Streamer
        set_conv_streamer_start();

        // Set GEMM configuration CSR
        uint32_t subtraction_setting =
            gen_subtraction_config(subtraction_a, subtraction_b);

        set_conv_block_gemm_csr(K, N, M, subtraction_setting);

        // Set CSR to start GEMM
        set_conv_block_gemm_start();

        // Poll until Streamer and GEMM accelerator finish
        wait_conv_streamer_gemm();

        err += check_conv_result(local_c, C_direct_conv2d, Batch, M, N);
        printf("SNAX GEMM Conv2d: %s, err = %d \n", err ? "FAIL" : "PASS", err);

    };

    return err;
}
