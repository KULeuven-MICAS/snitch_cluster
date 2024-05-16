# Architectural Overview

In this tutorial, we will build a simple SNAX system supporting one simple ALU accelerator. The figure below shows the target architecture:

Some notable characteristics (from top to bottom) are:

1 - It has a memory that is 128kB large, with 32 banks where each bank has 64 bits of data width. We call this memory the tighly coupled data memory (TCDM).

2 - There is a complex TCDM interconnect that handles data transfers from Snitch CPU cores, accelerator core, the DMA and an AXI port.

3 - There exists Snitch CPU cores that control the accelerator. The Snitch is a light-weight RV32I core for minimal management and dispatching commands to the accelerator. A separate CPU core is given to the DMA to allow parallel operations.

4 - The accelerator sits in a shell marked by the yellow highlight. This shell provides control and data interfaces to the accelerator (SNAX ALU). The SNAX shell provides a control and status register (CSR) manager and a data streamer.

5 - The control and status register (CSR) manager handles CSR requests from a CPU core to the accelerator.

6 - The data streamers provide flexible data access for the accelerators. These design and run time flexible streamers are provided as support for managing data that gets into the ALU.

7 - There is a DMA to transfer data from the outside memory into the local TCDM. The programmer has full control of this DMA.

8 - There are shared instruction caches for the CPU cores.

9 - AXI narrow and wide interconnects for data transactions to wards the outside of the SNAX cluster.

As we go through the tutorial, you will see that several of these components are design-time configurable. A user can add their own custom accelerator within the broken lines of the SNAX shell. They only need to comply with the control interface coming from a CSR manager and a streamer interface for accessing data from memory.


# What Do You Need to Build This System?




# General Directory Structure


## TODO:
- Do this in a top-down approach.
- Describe the whole system of interest
    - Be sure to include a diagram for this
- Describe the general flow on what files to configure.
    - Use a flow chart for this.
- Describe the directory structure here.
