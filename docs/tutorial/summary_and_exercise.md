# Summarizing the Steps

Congratulations! You're now an expert in using the SNAX shell. Let's review the major steps you worked on.

1 - Building your accelerator.

- We first built the toy SNAX ALU accelerator.
- The important component is to have an accelerator shell that complies with the interface of our system.

2 - Configuring the CSR manager for your accelerator.

- Specifying the planned number of read-write (RW) and read-only (RO) registers.

3 - Configuring the streamer for your accelerator.

- Specifying the number of read and write ports of your accelerator.
- Configuring the data widths, FIFO depths, and even the spatial parallelism considerations.

4 - Configuring the system according to your needs.

- Attaching the accelerator configurations.
- Specifying the memory sizes.

5 - Setting up the filelist and makefiles.

- Modifying the `Bender.yml` to add the file list.
- Modifying `Makefiles` 

6 - Programming your system.

- Making the C code.
- Making the data generation.
- Building the software.

7 - Profiling your system.

- Using waveforms.
- Using stack tracing with `spike`.

# Summarizing Commands

For building hardware you do:

```bash
make CFG_OVERRIDE=cfg/snax-alu.hjson bin/snitch_cluster.vlt
```

For building software you do:

```bash
make CFG_OVERRIDE=cfg/snax-alu.hjson SELECT_RUNTIME=rtl-generic SELECT_TOOLCHAIN=llvm-generic sw
```

# You Need an Exercise to Get Strong!!!

With everything you've learned, let's do a simple exercise for a new accelerator! The figure below shows the accelerator data path of interest:


## Accelerator Datapath Specifications

There are specific features for this accelerator:

- Let's name the accelerator `snax_exercise`

- Name your accelerator configuration file as `snax_exercise.hjson`

- The accelerator processes the kernel:

```C
O = 0;
parfor (int i = 0; i < 16; i++):
    O += A[i]*B[i]
O += bias
```
- Taking note that the `parfor` indicates that the MAC process needs to be process spatially in 16 parallel ports.

- The accelerator is an oversimplified MAC with a bias addition that takes in 32 inputs, 16 parallel ports for input A and 16 parallel ports for input B.

- Each input port takes in 64 bits of data. Each input port for A and B is multiplied together and accumulated at the end. This should be done fully-combinationally.

- We also add a feature that adds a 64-bit fixed bias.

- Since the bias is 64-bits wide, you need to set the upper and lower bits of the bias through CSR registers.

- The output produces a single 128-bit output.

- For the inputs and outputs, make sure to comply with the decoupled interface.

- The CSR registers it needs to have are tabulated below:

| register name     | register offset  | type    | description                                         |
| :---------------: | :--------------: | :-----: |:--------------------------------------------------- |
| upper bias        | 0                | RW      | Upper 32 bits of the bias.                          |
| lower bias        | 1                | RW      | Lower 32 bits of the bias.                          |
| num. of iter.     | 2                | RW      | Number of iterations to process.                    |
| accelerator start | 3                | RW      | Set 1 to LSB only to start the accelerator          |
| busy              | 4                | RO      | Busy status. 1 - busy, 0 - idle                     |
| perf. counter     | 5                | RO      | Performance counter indicating number of cycles     |


## CSR Manager and Streamer Specifications

For the CSR manager, you just need to ensure that the register configurations matches that of accelerator's register specs.

For the streamer you have the following specifications:

- You need to feed 1,024 bits for input ports A and B. Then you split them inside the accelerator's data path, just like in the `snax_alu` example.

- This necessitates 32 TCDM ports for all the inputs.

- The output is just a single 128-bit port output and hence leads to 2 TCDM ports only.

- This leads to a total of 34 TCDM ports for the streamer.

- Use a depth of 16 for all FIFOs.

- Let's keep 1 loop dimension only.

!!! note

    Don't worry about having 34 TCDM ports. We've seen worse...

## Some Helpful Guidance

- You could just copy the `snax_alu` example but be warned about the changes in the interface.

- When in doubt, the wrapper generation is useful for providing the appropriate interface. For example, you can generate the file and investigate if the configurations you put produce the correct files. Moreover, the generated `snax_exercise_wrapper.sv` should guide you towards the interfaces that you need to prepare for your `snax_exercise_acc_shell.sv`.

- For the `snax_exercise` directory, you would practically have 1 CSR manager, and the main accelerator shell. As for the PEs or combinational logic, it's up to you to decide.

