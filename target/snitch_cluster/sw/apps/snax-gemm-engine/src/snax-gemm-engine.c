
#include "data.h"
#include "snrt.h"

int main() {
    // Set err value for checking
    int err = 0;

    // Prepare addresses in TCDM
    uint8_t *local_a, *local_b;
    uint32_t *local_c;

    uint32_t tic, toc;

    // Allocate space in TCDM
    local_a = (uint8_t *)snrt_l1_next();
    local_b = local_a + m * k * sizeof(uint8_t);
    local_c = (uint32_t *)(local_b + n * k * sizeof(uint8_t));

    // Transfer data from L3 to L1
    // Using DMA only
    if (snrt_is_dm_core()) {
        tic = snrt_mcycle();
        tic = snrt_mcycle();

        snrt_dma_start_1d(local_a, A, m * k * sizeof(uint8_t));
        snrt_dma_start_1d(local_b, B, n * k * sizeof(uint8_t));

        toc = snrt_mcycle();

        printf("DMA transfer cycles: %d \n",
                toc - tic);
        
    }

    // Wait for DMA to finish
    snrt_cluster_hw_barrier();

    

    // Base MM calculation
    if (snrt_is_compute_core()) {
        // Setting of CSRs
        tic = snrt_mcycle();

        // Set addresses
        write_csr(0x3c0, (uint32_t)local_a);
        write_csr(0x3c1, (uint32_t)local_b);
        write_csr(0x3c2, (uint32_t)local_c);

        // CSR start
        write_csr(0x3c3, 0);

        toc = snrt_mcycle();

        printf("Cycles: %d \n", toc - tic);

        // Check if result is not equal to golden result
        for (uint32_t i = 0; i < m; i++) {
            for (uint32_t j = 0; j < n; j++) {
                if (C_golden[i * n + j] != *(local_c + (i * n + j))) {
                    err += 1;
                };
            }
        }
    };

    return err;
}