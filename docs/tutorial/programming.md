# Programming Your Design

Once the build is finished we are now ready to program our accelerator! The only thing we need to keep track of is the set registers that our accelerators are using. The major tasks in this section are to:

1. Make a program in C.
2. Generate a data header file using a data generation script.
3. Modify `Makefiles` for the build.
4. Building the program.
5. Run the program.

We will make a simple program that does the following:

1. Load data from the external memory to the TCDM memory.
2. Configure the streamer registers and start the streamer.
3. Configure the SNAX ALU and start the accelerator.
4. Check if the data is correct.
5. Print results.

# Make the C-Code for SNAX ALU

You can find all application programs in `./target/snitch_cluster/sw/apps/.`. Currently, there are several existing programs, but we'll look into the `snax-alu` directory. You should see the tree:

```
├── target/snitch_cluster/sw/apps
│   ├── snax-alu
│   |   ├── data
|   |   |   ├── datagen.py
|   |   |   └── Makefile
|   |   ├── src
|   |   |   └── snax-alu.c
│   |   └── Makefile
```

Let's study the C program under the `./target/snitch_cluster/sw/apps/snax-alu/src/snax-alu.c`. Take time to check out the file before proceeding. First let's look at the included header files:

```C
#include "snrt.h"
#include "data.h"
```

The `snrt.h` is a Snitch run-time header file for all pre-built functions made by the Snitch platform. You can find details in `./target/snitch_cluster/sw/runtime/rtl/src/snrt.h`. However, several definitions inside `snrt.h` are located in `./sw/snRuntime/src/.`. 

The `data.h` will contain the data that we need later. This will be automatically generated by the `datagen.py` script, which is invoked by the `Makefile`.

## Allocating Memory and Performing Memory Transfers

Inside the `main()` function we begin with declaring the pointers for the data addresses. Consider the code snippet below: 

```C
// Allocates space in TCDM
uint64_t *local_a, *local_b, *local_o;

local_a = (uint64_t *)snrt_l1_next();
local_b = local_a + DATA_LEN;
local_o = local_b + DATA_LEN;
```
We will use `a` and `b` for inputs and `o` for the output. In the code snippet below the `snrt_l1_next()` is a built-in Snitch run-time function that assigns the start of the base address of the TCDM. You can find the function definition in `./sw/snRuntime/src/alloc.h`. 

The `DATA_LEN` is a `uint64_t` data indicating the total number of elements we need to process in our program. You can find this in the generated `data.h` later.

The first section is to run the Snitch with a DMA core to transfer data from an external memory (L3) to the local TCDM (L1) memory. See the code snippet below:

```C
if (snrt_is_dm_core()) {
    // This measures the start of cycle count
    // for preloading the data to the L1 memory
    uint32_t start_dma_load = snrt_mcycle();

    // The DATA_LEN is found in data.h
    size_t vector_size = DATA_LEN * sizeof(uint64_t);
    snrt_dma_start_1d(local_a, A, vector_size);
    snrt_dma_start_1d(local_b, B, vector_size);

    // Measure the end of the transfer process
    uint32_t end_dma_load = snrt_mcycle();
}
```

The `snrt_is_dm_core()` function indicates that the assigned tasks within the condition are for the DMA core only. If it's not a DMA core then it won't run the tasks inside it.

The `snrt_mcycle()` is used to measure the current cycle count of the system. We use this later for tracking the number of cycles it needs to run a certain piece of code. We'll discuss more about tracing in the [Other Tools](./other_tools.md) section later.

Observe that the `snrt_mcycle()` is located at the start and end of the DMA tasks. We want to measure the number of cycles it needs for the DMA to transfer the data from L2 to L1.

Next, we transfer the data through the `snrt_dma_start_1d()` function where the arguments are the destination, source, and the number of bytes to transfer. You can find the function definition in `./sw/snRuntime/src/dma.h`.

`local_a` and `local_b` are the destinations inside the TCDM L1 memory. Data arrays `A` and `B` are declared inside the `data.h` and it is stored in the L2. `vectore_size` is of course the amount of data to transfer.

## Synchronizing Cores

After the DMA tasks, we need to run a hardware barrier:

```C
// Synchronize cores by setting up a
// fence barrier for the DMA and accelerator core
snrt_cluster_hw_barrier();
```

Since we are doing parallel programming, hardware barriers are program fences to synchronize the timing of the cores. When we run the program from the start of the main, both the Snitch core with the SNAX ALU accelerator and DMA core are running in parallel.

However, since the assignment of the DMA tasks is for the DMA core only, the Snitch core attached to the SNAX ALU skips the task assignment and runs the `snrt_cluster_hw_barrier();` immediately. You can find the function definition in `./sw/snRuntime/src/sync.h`.

When the function is called, the Snitch core enters a stall state waiting for all Snitch cores to run the same function. When all Snitch cores reach the function, then the cores proceed to do the next tasks. The figure below visualizes this sequence:

![image](https://github.com/KULeuven-MICAS/snitch_cluster/assets/26665295/9b797246-3040-465c-85bb-fe107c621861)

When the DMA core finishes the transfer, the next task assignment is for the compute core to which the SNAX ALU is connected. We use the `snrt_is_compute_core()` function to indicate if the core is a computing core. You can find the function definition in `./sw/snRuntime/src/team.h`. Since we only have 1 compute core, then this condition is enough. 

!!! note

    If there is more than 1 core, we need to use the `snrt_cluster_core_idx()` which returns the core number. You can find the source code in `./sw/snRuntime/src/team.h`. The core number depends on how you arrange the cores in the configuration file. The last core is always the DMA core. 


## Programming the Accelerator

The first task is configuring the CSR registers for the streamers and the accelerator. In our system, we first configure the streamer CSRs and then the accelerator CSRs.

The register addressing then always starts with the streamer configurations, and then the accelerator configurations. The table below shows the relative and actual CSR addressing:

|  register name          |  relative register addr  |   CSR address  |
| :-----------------:     | :-----------------------:| :------------: |
| temporal loop bound     | 0                        |   x3c0         | 
| temporal stride 0       | 1                        |   x3c1         | 
| temporal stride 1       | 2                        |   x3c2         | 
| temporal stride 2       | 3                        |   x3c3         | 
| spatial stride 0        | 4                        |   x3c4         | 
| spatial stride 1        | 5                        |   x3c5         |      
| spatial stride 2        | 6                        |   x3c6         |      
| base addr 0             | 7                        |   x3c7         | 
| base addr 1             | 8                        |   x3c8         | 
| base addr 2             | 9                        |   x3c9         | 
| streamer start          | 10                       |   x3ca         | 
| streamer perf. counter  | 11                       |   x3cb         |  
| mode                    | 12                       |   x3cc         |
| length                  | 13                       |   x3cd         |
| ALU acceleartor start   | 14                       |   x3ce         |
| busy                    | 15                       |   x3cf         |
| alu perf. counter       | 16                       |   x3d0         |

!!! note

    In our SNAX system, we reserved the CSR address spaces from 0x3c0 up to 0x5ff. We always begin with 0x3c0.

In the `snax-alu.c` file you can see that we can write the CSR registers directly. The `write_csr` and `read_csr` functions call inline assembly calls for `csrw` and `csrr` RISCV CSR instructions, respectively:

```C
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
write_csr(0x3c0, LOOP_ITER);
write_csr(0x3c1, 32);
write_csr(0x3c2, 32);
write_csr(0x3c3, 64);
write_csr(0x3c4, 8);
write_csr(0x3c5, 8);
write_csr(0x3c6, 8);
write_csr(0x3c7, (uint64_t)local_a);
write_csr(0x3c8, (uint64_t)local_b);
write_csr(0x3c9, (uint64_t)local_o);
write_csr(0x3ca, 1);
```

The sequence above first configures the streamers and then starts the streamers. Recall that our streamer supports the following loop for accessing data:

```
for(i = 0; i < N; i++):
  # Parfor equivalent
  parfor(j = 0; j < 4; j++):
    target_address[j] = base_address + temporal_stride*i + spatial_stride*j;
```
Where `N` is the configured temporal loop-bound register. The `base_address` for each port `A`, `B`, and `OUT` are configured with `(uint64_t)local_a`, `(uint64_t)local_b`, and `(uint64_t)local_o`, respectively.

The temporal strides for each input are 32 bytes, but the output is 64 bytes. These addresses are in bytes. We need 32 for the inputs because that's 8 bytes (64 bits) per PE and we have 4 PEs and therefore, 32 bytes of temporal stride. The output is 64 because we need 16 bytes (128 bits) per PE and we have 4 PEs and therefore, 64 bytes of temporal stride.

All spatial strides are 8 because, for each TCDM port connected to the streamer, it will automatically increment or point to the next bank which is 8 in byte addresses (each bank is 64bit or 8 bytes).

Finally, the start signal for the streamer is configured by writing 1 to the LSB of the start register.

The accelerator registers are configured next. Take note of the starting address. The code snippet below shows the CSR setup for the accelerator. 

```C
//------------------------------
// 2nd set the CSRs of the accelerator
// 0x3cc - mode of the ALU (RW)
//       - 0 for add, 1 for sub, 2 for mul, 3 for XOR
// 0x3cd - length of data (RW)
// 0x3ce - send configurations to accelerator (RW)
// 0x3cf - busy status (RO)
// 0x3d0 - performance counter (RO)
//------------------------------
write_csr(0x3cc, MODE);
write_csr(0x3cd, LOOP_ITER);
write_csr(0x3ce, 1);
```
The `MODE` and `LOOP_ITER` are in the `data.h` file. The `LOOP_ITER` is the effective number of loops while considering the spatial parallelism. For example, if we have 100 elements (each is 64-bit wide), then with a spatial parallelism of 4 PEs, we only need to process 25 cycles so the `LOOP_ITER` is 25. 

The last register written on address `0x3ce` is the start signal of the accelerator. Once started, the accelerator and streamer work together to process the data.

We can monitor and poll the busy status of the accelerator by reading on register address `0x3cf`. The busy signal is high when the accelerator is still processing data.

```C
// Do this to poll the accelerator
while (read_csr(0x3cf)) {
};
```

## Verifying Results

Once complete, we can check and compare the results in the TCDM and the golden answer stored in L2 memory. The golden output `OUT` is declared in `data.h`.

```C
// Compare results and check if the
// accelerator returns correct answers
// For every incorrect answer, increment err
uint64_t check_val;

for (uint32_t i = 0; i < DATA_LEN; i++) {
    // Need to combine upper 64bit bank
    // with the lower 64 bit bank
    check_val = *(local_o + i * 2) + *(local_o + i * 2 + 1);
    if (check_val != OUT[i]) {
        err++;
    }
}
```

Finally, we can print some performance counters at the end:

```C
// Read performance counter
uint32_t perf_count = read_csr(0x3d0);

printf("Accelerator Done! \n");
printf("Accelerator Cycles: %d \n", perf_count);
printf("Number of errors: %d \n", err);

```

In summary, you only need to first preload the data into the local TCDM, configure the CSR registers, wait for the accelerator to finish, and then finally profile the performance!

## Generating Data

You can have your own custom data generation script within the data section. Here, we provide one for the SNAX ALU example.

The data processed is defined in the `data.h` included file. Inside the `./target/snitch_cluster/sw/apps/snax-alu/data/data.h`. This file is only generated when you run the `./target/snitch_cluster/sw/apps/snax-alu/data/datagen.py` Python script. To generate data you can run:

```bash
./datagen.py --mode=0 --length=20 > data.h
```

The `datagen.py` runs and prints the data into the terminal IO and therefore we need to dump it into the `data.h` file. The `--mode` pertains to what kind of kernel to use in the accelerator. 0 is for add, 1 is for sub, 2 is for mul, and 3 is for XOR. The `--length` pertains to the data lengths.

After generating the script you can investigate the contents of the `data.h`. You should see:

- `MODE` - is the mode that the accelerator will use.
- `DATA_LEN` - is the length of data to be processed.
- `LOOP_ITER` - is the data length divided by the amount of parallelism.
- `A` and `B` - are the input data.
- `OUT` - is the golden output to which the outputs are compared.

!!! note

    Generating the `data.h` is already automatic by the `Makefile` we have. Therefore you don't need to run the `datagen.py` manually before building the program.

# Modifying Makefiles

With the source code and data generation script in place, we set up `Makefiles` to ensure the build is automatic.

1 - You can find the data generation `Makefile` in `./target/snitch_cluster/sw/apps/snax-alu/data/Makefile`. Make sure to encode the parameters you need.

2 - Next is the program `./target/snitch_cluster/sw/apps/snax-alu/Makefile`. Make sure that the `APP` name and `SRCS` name are consistent with the `snax-alu` and `snax-alu.c`, respectively.

3 - Then, modify the `./target/snitch_cluster/sw/apps/Makefile` and add the source name `snax-alu` as part of the subdirectories: `SUBDIRS += snax-alu`.

# Building and Running Your Program

Building and running your program is easy. First, navigate to `./target/snitch_cluster` then invoke:

```
make CFG_OVERRIDE=cfg/snax-alu.hjson SELECT_RUNTIME=rtl-generic SELECT_TOOLCHAIN=llvm-generic sw
```

Run your program with:


```
bin/snitch_cluster.vlt sw/apps/snax-alu/build/snax-alu.elf
```

# Some Exercises

Let's try some exercises to see if you understand where to find details.

<details>
<summary> What is the default mode and how much data is processed in the default setting? </summary>
    The default mode is 0 for addition and we will process 320 elements.
</details>

<details>
<summary> Where can I find the definition of the functions `snrt_is_compute_core()` and `snrt_is_dm_core()`  </summary>
    You can find them at `./sw/snRuntime/src/team.h`.
</details>

<details>
<summary> If there is an incorrect answer in the C code, what will the simulation return? </summary>
    The return value of the `main()` function returns the `err` value. If the main returns a value that isn't 0, an error is thrown.
</details>

