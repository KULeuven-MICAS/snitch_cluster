
#include "data_bak.h"
#include "snrt.h"
#include "stdint.h"
#include <stdbool.h>
#include "snax_gemm_lib.h"

// gen random data
// allocate space in TCDM
// write data from l3 to tcdm
// config csr
// wait until finish
// check result

int32_t gen_size_config(uint8_t Batch, uint8_t M, uint8_t K, uint8_t N){
    return ((int32_t)Batch << 24) | ((int32_t)M << 16) | ((int32_t)K << 8) | (int32_t)N;
}

bool base_gemm(int m, int k, int n, int8_t * A, int8_t * B, int32_t* C_cpu){

    if (snrt_is_compute_core()) {
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                // C_cpu[i * n + j] = 0;
                for (int s = 0; s < k; s++) {
                    C_cpu[i * n + j] =
                        C_cpu[i * n + j] +
                        (int32_t)A[i * k + s] * (int32_t)B[s + j * k];
                }
            }
        }
    };

    return 0;

}

bool batch_gemm_cpu(uint8_t Batch, uint8_t M, uint8_t K, uint8_t N, int8_t* A, int8_t* B, int32_t* C, uint32_t ldA, uint32_t ldB,uint32_t ldC, uint32_t strideA,uint32_t strideB,uint32_t strideC){

    int8_t* start_addr_a = A;
    int8_t* start_addr_b = B;
    int32_t* start_addr_c = C;
    int8_t* addr_a;
    int8_t* addr_b;
    int32_t* addr_c;

    // Read the mcycle CSR (this is our way to mark/delimit a specific code
    // region for benchmarking)
    uint32_t start_cycle = snrt_mcycle();
    
    if (snrt_is_compute_core()) {
        for (int b = 0; b < Batch; b++) {
            for (int m = 0; m < M; m++) {
                for (int n = 0; n < N; n++) {
                    for (int k = 0; k < K; k++) {
                        addr_a = start_addr_a + (b * strideA + m * ldA + k * baseAddrIncrementA) / sizeof(int8_t);
                        addr_b = start_addr_b + (b * strideB + n * ldB + k * baseAddrIncrementB) / sizeof(int8_t);
                        addr_c = start_addr_c + (b * strideC + m * ldC + n * baseAddrIncrementC) / sizeof(int32_t);
                        base_gemm(meshRow, tileSize, meshCol, addr_a, addr_b, addr_c);
                    }
                }
            }
        } 
    }

    // Read the mcycle CSR
    uint32_t end_cycle = snrt_mcycle();
    printf("cycle number for CPU to do matrix multiply: %d \n",
            end_cycle - start_cycle);

    return 0;
}

bool set_batch_gemm(uint8_t Batch, uint8_t M, uint8_t K, uint8_t N, int8_t *local_a, int8_t *local_b, int32_t *local_c,uint32_t ldA, uint32_t ldB,uint32_t ldC, uint32_t strideA,uint32_t strideB,uint32_t strideC){

    // Set addresses
    write_csr(0x3c0, (uint32_t)local_a);
    write_csr(0x3c1, (uint32_t)local_b);
    write_csr(0x3c2, (uint32_t)local_c);

    write_csr(0x3c3, gen_size_config(Batch, M, K ,N));

    write_csr(0x3c4,ldA);
    write_csr(0x3c5,ldB);
    write_csr(0x3c6,ldC);

    write_csr(0x3c7,strideA);
    write_csr(0x3c8,strideB);
    write_csr(0x3c9,strideC);

    // CSR start
    write_csr(0x3ca, 1);

    uint32_t break_poll;

    while(1){
        // STATE_CSR is the CSR address for accelerator status
        break_poll = read_csr(0x3ca);
        if(break_poll == 1){
            break;
        };
    };

    return 0;

}

uint32_t check_result(int32_t* output, int32_t* output_golden,
                      uint32_t length){
    /*
     * Compare output to output_golden with length
     */
    uint32_t err = 0;
    for (uint32_t i = 0; i < length; i++) {
        // Check if output is same as golden output
        if (output[i] != output_golden[i]) {
            printf("%dth not equal: output %d, golden %d \n",i, output[i],output_golden[i]);
            err++;
        };
    };
    return err;
}

int main() {
    // Set err value for checking
    int err = 0;

    // Prepare addresses in TCDM
    int8_t *local_a, *local_b;
    int32_t *local_c;

    // Allocate space in TCDM
    uint32_t m = M * meshRow;
    uint32_t k = K * tileSize;
    uint32_t n = N * meshRow;
    local_a = (int8_t *)snrt_l1_next();
    local_b = local_a + m * k * sizeof(int8_t) + 64;
    local_c = (int32_t *)(local_b + n * k * sizeof(int8_t));

    uint32_t dma_pre_load = snrt_mcycle();

    // Transfer data from L3 to L1
    // Using DMA only
    if (snrt_is_dm_core()) {
        snrt_dma_start_1d(local_a, A, m * k * sizeof(int8_t));
        snrt_dma_start_1d(local_b, B, n * k * sizeof(int8_t));
    }

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    if (snrt_is_compute_core()) {
        // This marks the start of the accelerator style of MAC operation
        uint32_t csr_set = snrt_mcycle();

        uint32_t ldA,ldB,ldC,strideA,strideB,strideC;
        ldA = 128;
        ldB = 128;
        ldC = 512;
        strideA = 0;
        strideB = 0;
        strideC = 0;

        // Start of CSR start and poll until accelerator finishes
        uint32_t gemm_start = snrt_mcycle();

        set_batch_gemm(Batch, M, K ,N,local_a,local_b,local_c,ldA,ldB,ldC,strideA,strideB,strideC);

        uint32_t gemm_end = snrt_mcycle();

        printf("cycle number for Gemm to do matrix multiply: %d \n",
               gemm_end - dma_pre_load);

        // for (int i = 0; i < M * meshRow; i++) {
        //     for (int j = 0; j < N * meshCol; j++) {
        //         printf("C[%d][%d] = %d\n", i, j, *(local_c + (i * n + j)));
        //     }
        // }

        uint32_t end_of_check = snrt_mcycle();

        err = check_result(local_c,C_golden,m*n);
        printf("gemm err: %d\n",err);
        
    };

    snrt_cluster_hw_barrier();

    if(snrt_is_compute_core()){
        batch_gemm_cpu(Batch,M,K,N,A,B,C_cpu,128,128,512,0,0,0);

        err = check_result(C_cpu,C_golden,m*n);
        // for (int i = 0; i < M * meshRow; i++) {
        //     for (int j = 0; j < N * meshCol; j++) {
        //         printf("C_cpu[%d][%d] = %d\n", i, j, *(C_cpu + (i * n + j)));
        //     }
        // }    
        printf("cpu err: %d\n",err);        
    }

    return err;
}
