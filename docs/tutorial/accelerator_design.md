# Accelerator Design

Let's first dive into the SNAX shell which is the encapsulated yellow-box from the main figure in [Architectural Overview](./architectural_overview.md). The figure below is the same shell but with more signal details:


We labeled a few important details about the shell:

1 - The entire SNAX accelerator wrapper encapsulates the streamers, the CSR manager, and the accelerator data path.

2 - The CSR manager handles the CSR read and write transactions between the Snitch core and the accelerator data path. Towards the Snitch core side, CSR transactions are handled with decoupled interfaces (`csr_req_*` and `csr_rsp_*`) of request and responses. Towards the accelerator side, the read-write registers (`register_rw_set`) uses a decoupled interface (`register_rw_valid` and `register_rw_ready`) while the read-only registers (`register_ro_set`) is a direct mapping. There are more details in [CSR Manager Design](./csrman_design.md).

3 - The streamer provides flexible data access from the L1 TCDM to the accelerator. It serves as an intermediate interface ebtween the TCDM interconnect and the accelerator. On the interconnect side the streamer controls the TCDM request and response (`tcdm_req` and `tcdm_rsp`) interfaces towards the memory. On the accelerator side, the streamer has its own data decoupled interfaces (`acc2stream_*` and `stream2acc_*`). The direction from accelerator to streamer are write-only ports while the direction from streamer to accelerator are read-only ports. More details are in [Streamer Design](./streamer_design.md).

4 - The accelerator data path is the focus of this section. In our example, we will use a very simple ALU datapath with basic operations only. The SNAX ALU is already built for you. You can find it under the `./hw/snax_alu/` directory. Take time to check the simple design.

# SNAX ALU Accelerator Datapath

The figure below shows the SNAX ALU datapath:

Again, we label points of interest:

1 - 

## Accelerator Architecture

## Modes and Features

## Interfaces

## Timing Diagrams



## TODOs:
- Describe the accelerator of interest
- Show a detailed block diagram of the signals
- Mention and describe what the CSR Manager does
- Describe the CSRs to be used
    - Mode: +, -, x, XOR
    - Data length
    - Start
    - Busy
    - Counter
- Have a timing diagram interface to describe what happens for the signals
- Indicate which repository to see this structure
