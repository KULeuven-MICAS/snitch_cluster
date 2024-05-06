<%
  import math

  num_loop_dim = cfg["temporalAddrGenUnitParams"]["loopDim"]
  num_data_mover = (len(cfg["dataReaderParams"]["tcdmPortsNum"]) + len(cfg["dataWriterParams"]["tcdmPortsNum"])) 
  num_dmove_x_loop_dim = num_data_mover * num_loop_dim
  num_spatial_dim = sum(cfg["dataReaderParams"]["spatialDim"]) + sum(cfg["dataWriterParams"]["spatialDim"])
  
  csr_num = num_loop_dim + num_dmove_x_loop_dim + num_data_mover + num_spatial_dim + 1
  csr_width = math.ceil(math.log2(csr_num))
%>
//-------------------------------
// Streamer-MUL wrapper
// This is the entire accelerator
// That connecst to the TCDM subsystem
//-------------------------------
module ${cfg["tagName"]}_top_wrapper # (
  parameter int unsigned NarrowDataWidth = ${cfg["tcdmDataWidth"]},
  parameter int unsigned TCDMDepth       = ${cfg["tcdmDepth"]},
  parameter int unsigned TCDMReqPorts    = ${sum(cfg["dataReaderParams"]["tcdmPortsNum"]) + sum(cfg["dataWriterParams"]["tcdmPortsNum"])},
  parameter int unsigned TCDMSize        = TCDMReqPorts * TCDMDepth * (NarrowDataWidth/8),
  parameter int unsigned TCDMAddrWidth   = $clog2(TCDMSize),
  parameter int unsigned SpatPar         = ${cfg["dataReaderParams"]["spatialBounds"][0][0]},
  parameter int unsigned RegCount 		   = 32,
  parameter int unsigned RegDataWidth    = 32,
	parameter int unsigned RegAddrWidth    = $clog2(RegCount)
)(
  //-----------------------------
  // Clocks and reset
  //-----------------------------
  input  logic clk_i,
  input  logic rst_ni,

  //-----------------------------
  // TCDM ports
  //-----------------------------
  // Request
  output logic [TCDMReqPorts-1:0]                        tcdm_req_write_o,
  output logic [TCDMReqPorts-1:0][TCDMAddrWidth-1:0]     tcdm_req_addr_o,
  output logic [TCDMReqPorts-1:0][3:0]                   tcdm_req_amo_o, //Note that tcdm_req_amo_i is 4 bits based on reqrsp definition
  output logic [TCDMReqPorts-1:0][NarrowDataWidth-1:0]   tcdm_req_data_o,
  output logic [TCDMReqPorts-1:0][4:0]                   tcdm_req_user_core_id_o, //Note that tcdm_req_user_core_id_i is 5 bits based on Snitch definition
  output logic [TCDMReqPorts-1:0]                        tcdm_req_user_is_core_o,
  output logic [TCDMReqPorts-1:0][NarrowDataWidth/8-1:0] tcdm_req_strb_o,
  output logic [TCDMReqPorts-1:0]                        tcdm_req_q_valid_o,

  // Response
  input  logic [TCDMReqPorts-1:0]                        tcdm_rsp_q_ready_i,
  input  logic [TCDMReqPorts-1:0]                        tcdm_rsp_p_valid_i,
  input  logic [TCDMReqPorts-1:0][NarrowDataWidth-1:0]   tcdm_rsp_data_i,

  //-----------------------------
  // CSR control ports
  //-----------------------------
  // Request
  input  logic [31:0] snax_req_data_i,
  input  logic [31:0] snax_req_addr_i,
  input  logic        snax_req_write_i,
  input  logic        snax_req_valid_i,
  output logic        snax_req_ready_o,

  // Response
  input  logic        snax_rsp_ready_i,
  output logic        snax_rsp_valid_o,
  output logic [31:0] snax_rsp_data_o
);

  // Ports from accelerator to streamer
% for idx, dw in enumerate(cfg["fifoWriterParams"]['fifoWidth']):
  logic [${dw-1}:0] acc2stream_data_${idx}_bits;
  logic acc2stream_data_${idx}_valid;
  logic acc2stream_data_${idx}_ready;

% endfor
  // Ports from streamer to accelerator
% for idx, dw in enumerate(cfg["fifoReaderParams"]['fifoWidth']):
  logic [${dw-1}:0] stream2acc_data_${idx}_bits;
  logic stream2acc_data_${idx}_valid;
  logic stream2acc_data_${idx}_ready;

% endfor

  //-----------------------------
  // CSR MUXing
  //-----------------------------
  logic [1:0][RegAddrWidth-1:0] acc_csr_req_addr;
  logic [1:0][RegDataWidth-1:0] acc_csr_req_data;
	logic [1:0] acc_csr_req_wen;
	logic [1:0] acc_csr_req_valid;
	logic [1:0] acc_csr_req_ready;
	logic [1:0][RegDataWidth-1:0] acc_csr_rsp_data;
	logic [1:0] acc_csr_rsp_valid;
	logic [1:0] acc_csr_rsp_ready;

  //-------------------------------
  // MUX and DEMUX for control signals
  // That separate between streamer CSR
  // and ALU CSRs
  //-------------------------------
  csr_mux_demux #(
    .AddrSelOffSet        ( 8            ),
    .TotalRegCount        ( RegCount     ),
    .RegDataWidth         ( RegDataWidth ),
  ) i_csr_mux_demux (
    //-------------------------------
    // Input Core
    //-------------------------------
    .csr_req_addr_i       ( snax_req_addr_i  ),
    .csr_req_data_i       ( snax_req_data_i  ),
    .csr_req_wen_i        ( snax_req_write_i ),
    .csr_req_valid_i      ( snax_req_valid_i ),
    .csr_req_ready_o      ( snax_req_ready_o ),
    .csr_rsp_data_o       ( snax_rsp_data_o  ),
    .csr_rsp_valid_o      ( snax_rsp_valid_o ),
    .csr_rsp_ready_i      ( snax_rsp_ready_i ),

    //-------------------------------
    // Output Port
    //-------------------------------
    .acc_csr_req_addr_o   ( acc_csr_req_addr  ),
    .acc_csr_req_data_o   ( acc_csr_req_data  ),
    .acc_csr_req_wen_o    ( acc_csr_req_wen   ),
    .acc_csr_req_valid_o  ( acc_csr_req_valid ),
    .acc_csr_req_ready_i  ( acc_csr_req_ready ),
    .acc_csr_rsp_data_i   ( acc_csr_rsp_data  ),
    .acc_csr_rsp_valid_i  ( acc_csr_rsp_valid ),
    .acc_csr_rsp_ready_o  ( acc_csr_rsp_ready )
  );

  //-----------------------------
  // Accelerator
  //-----------------------------
  // Note: This is the part that needs to be consistent
  // It needs to have the correct connections to the control and data ports!
  ${cfg["tagName"]}_wrapper #(
    .SpatPar          ( SpatPar                 ),
    .DataWidth        ( NarrowDataWidth         )
  ) i_simple_alu_wrapper (
    //-------------------------------
    // Clocks and reset
    //-------------------------------
    .clk_i            ( clk_i                   ),
    .rst_ni           ( rst_ni                  ),
    //-------------------------------
    // Accelerator ports
    //-------------------------------
    .a_i              ( stream2acc_data_0_bits  ),
    .a_valid_i        ( stream2acc_data_0_valid ),
    .a_ready_o        ( stream2acc_data_0_ready ),
    .b_i              ( stream2acc_data_1_bits  ),
    .b_valid_i        ( stream2acc_data_1_valid ),
    .b_ready_o        ( stream2acc_data_1_ready ),
    .result_o         ( acc2stream_data_0_bits  ),
    .result_valid_o   ( acc2stream_data_0_valid ),
    .result_ready_i   ( acc2stream_data_0_ready ),
    //-----------------------------
    // CSR control ports
    //-----------------------------
    // Request
    .csr_addr_i       ( acc_csr_req_addr[0]   ),
    .csr_wr_data_i    ( acc_csr_req_data[0]   ),
    .csr_wr_en_i      ( acc_csr_req_wen[0]    ),
    .csr_req_valid_i  ( acc_csr_req_valid[0]  ),
    .csr_req_ready_o  ( acc_csr_req_ready[0]  ),
    // Response
    .csr_rd_data_o    ( acc_csr_rsp_data[0]   ),
    .csr_rsp_valid_o  ( acc_csr_rsp_valid[0]  ),
    .csr_rsp_ready_i  ( acc_csr_rsp_ready[0]  )
  );

  //-----------------------------
  // Streamer Wrapper
  //-----------------------------
  ${cfg["tagName"]}_streamer_wrapper #(
    .NarrowDataWidth            ( NarrowDataWidth         ),
    .TCDMDepth                  ( TCDMDepth               ),
    .TCDMReqPorts               ( TCDMReqPorts            ),
    .TCDMSize                   ( TCDMSize                ),
    .TCDMAddrWidth              ( TCDMAddrWidth           )
  ) i_streamer_wrapper (
    //-----------------------------
    // Clocks and reset
    //-----------------------------
    .clk_i                      ( clk_i                   ),
    .rst_ni                     ( rst_ni                  ),

    //-----------------------------
    // Accelerator ports
    //-----------------------------
    // Ports from acclerator to streamer
    % for idx, dw in enumerate(cfg["fifoWriterParams"]['fifoWidth']):
    .acc2stream_data_${idx}_bits_i  ( acc2stream_data_${idx}_bits ),
    .acc2stream_data_${idx}_valid_i ( acc2stream_data_${idx}_valid ),
    .acc2stream_data_${idx}_ready_o ( acc2stream_data_${idx}_ready ),

    % endfor
    // Ports from streamer to accelerator
    % for idx, dw in enumerate(cfg["fifoReaderParams"]['fifoWidth']):
    .stream2acc_data_${idx}_bits_o  ( stream2acc_data_${idx}_bits ),
    .stream2acc_data_${idx}_valid_o ( stream2acc_data_${idx}_valid ),
    .stream2acc_data_${idx}_ready_i ( stream2acc_data_${idx}_ready ),

    % endfor

    //-----------------------------
    // TCDM ports 
    //-----------------------------
    // Request
    .tcdm_req_write_o         ( tcdm_req_write_o        ),
    .tcdm_req_addr_o          ( tcdm_req_addr_o         ),
    .tcdm_req_amo_o           ( tcdm_req_amo_o          ), 
    .tcdm_req_data_o          ( tcdm_req_data_o         ),
    .tcdm_req_user_core_id_o  ( tcdm_req_user_core_id_o ), 
    .tcdm_req_user_is_core_o  ( tcdm_req_user_is_core_o ),
    .tcdm_req_strb_o          ( tcdm_req_strb_o         ),
    .tcdm_req_q_valid_o       ( tcdm_req_q_valid_o      ),
    // Response
    .tcdm_rsp_q_ready_i       ( tcdm_rsp_q_ready_i      ),
    .tcdm_rsp_p_valid_i       ( tcdm_rsp_p_valid_i      ),
    .tcdm_rsp_data_i          ( tcdm_rsp_data_i         ),

    //-----------------------------
    // CSR control ports
    //-----------------------------
    // Request
    .io_csr_req_bits_data_i   ( acc_csr_req_data[1]   ),
    .io_csr_req_bits_addr_i   ( acc_csr_req_addr[1]   ),
    .io_csr_req_bits_write_i  ( acc_csr_req_wen[1]    ),
    .io_csr_req_valid_i       ( acc_csr_req_valid[1]  ),
    .io_csr_req_ready_o       ( acc_csr_req_ready[1]  ),
    // Response
    .io_csr_rsp_ready_i       ( acc_csr_rsp_ready[1]  ),
    .io_csr_rsp_valid_o       ( acc_csr_rsp_valid[1]  ),
    .io_csr_rsp_bits_data_o   ( acc_csr_rsp_data[1]   )
  );





endmodule