
#include "data.h"

#include "snax-gemm-lib.h"

#include "snax-gemm-params.h"

// gen random data
// allocate space in TCDM
// write data from L3 to TCDM
// config csr
// start
// wait until finish
// check result

int main() {
    // Set err value for checking
    int err = 0;

    // Prepare addresses in TCDM
    int8_t *local_a, *local_b;
    int32_t* local_c;

    // Allocate space in TCDM
    local_a = (int8_t*)snrt_l1_next();
    local_b = local_a + delta_local_a * sizeof(int8_t);
    local_c = (int32_t*)(local_b + delta_local_b * sizeof(int8_t));

    uint32_t dma_pre_load = snrt_mcycle();

    // Transfer data from L3 to L1
    // Using DMA only
    load_input_data(Batch, M, K, N, local_a, local_b, A, B, strideInnermostA,
                    strideInnermostB, ldA, ldB, strideA, strideB);

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    if (snrt_is_compute_core()) {
        // Pack matrix size setting to one CSR
        uint32_t size_setting = gen_size_config(Batch, M, K, N);

        uint32_t gemm_start = snrt_mcycle();

        // Set GEMM configuration CSR
        set_batch_gemm(size_setting, local_a, local_b, local_c,
                       strideInnermostA, strideInnermostB, strideInnermostC,
                       ldA, ldB, ldC, strideA, strideB, strideC);

        // Set CSR to start GEMM and poll until GEMM accelerator finishes
        start_batch_gemm();
        wait_batch_gemm();

        uint32_t gemm_end = snrt_mcycle();

        printf("cycle number for Gemm to do matrix multiply: %d \n",
               gemm_end - gemm_start);

        // Compare SNAX GEMM result with golden model
        err += check_result(local_c, C_golden, Batch, M, N, strideInnermostC,
                           ldC, strideC);
        printf("gemm err: %d\n", err);
    };

    snrt_cluster_hw_barrier();

    if (snrt_is_compute_core()) {
        // Also perform calculation on CPU

        // Read the mcycle CSR (this is our way to mark/delimit a specific code
        // region for benchmarking)
        uint32_t start_cycle = snrt_mcycle();

        batch_gemm_cpu(Batch, M, K, N, A, B, C_cpu, strideInnermostA,
                       strideInnermostB, strideInnermostC, ldA, ldB, ldC,
                       strideA, strideB, strideC);

        // Read the mcycle CSR
        uint32_t end_cycle = snrt_mcycle();
        printf("cycle number for CPU to do matrix multiply: %d \n",
               end_cycle - start_cycle);

        // Compare CPU result with golden model
        err += check_result(C_cpu, C_golden, Batch, M, N, strideInnermostC, ldC,
                           strideC);

        printf("cpu err: %d\n", err);
    }

    return err;
}
