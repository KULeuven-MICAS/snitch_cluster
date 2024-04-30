<%
  import math

  num_loop_dim = cfg["temporalAddrGenUnitParams"]["loopDim"]
  num_data_mover = (len(cfg["dataReaderParams"]["tcdmPortsNum"]) + len(cfg["dataWriterParams"]["tcdmPortsNum"])) 
  num_dmove_x_loop_dim = num_data_mover * num_loop_dim
  num_spatial_dim = sum(cfg["dataReaderParams"]["spatialDim"]) + sum(cfg["dataWriterParams"]["spatialDim"])
  
  csr_num = num_loop_dim + num_dmove_x_loop_dim + num_data_mover + num_spatial_dim + 1
  csr_width = math.ceil(math.log2(csr_num))
%>
//-----------------------------
// Streamer wrapper
//-----------------------------
module streamer_wrapper #(
  parameter int unsigned NarrowDataWidth = ${cfg["tcdmDataWidth"]},
  parameter int unsigned TCDMDepth = ${cfg["tcdmDepth"]},
  parameter int unsigned TCDMReqPorts = ${sum(cfg["dataReaderParams"]["tcdmPortsNum"]) + sum(cfg["dataWriterParams"]["tcdmPortsNum"])},
  parameter int unsigned NrBanks = ${cfg["numBanks"]},
  parameter int unsigned TCDMSize = NrBanks * TCDMDepth * (NarrowDataWidth/8),
  parameter int unsigned TCDMAddrWidth = $clog2(TCDMSize)
)(

  //-----------------------------
  // Clocks and reset
  //-----------------------------
  input logic clk_i,
  input logic rst_ni,

  //-----------------------------
  // Accelerator ports
  //-----------------------------
  // Output ports from accelerator to streamer
% for idx, dw in enumerate(cfg["fifoWriterParams"]['fifoWidth']):
  input logic [${dw-1}:0] acc2stream_data_${idx}_bits_i,
  input logic acc2stream_data_${idx}_valid_i,
  output logic acc2stream_data_${idx}_ready_o,

% endfor
  // Input ports from streamer to accelerator
% for idx, dw in enumerate(cfg["fifoReaderParams"]['fifoWidth']):
  output logic [${dw-1}:0] stream2acc_data_${idx}_bits_o,
  output logic stream2acc_data_${idx}_valid_o,
  input logic stream2acc_data_${idx}_ready_i,

% endfor
  //-----------------------------
  // TCDM ports
  //-----------------------------
  // Request
  output logic [TCDMReqPorts-1:0] tcdm_req_write_o,
  output logic [TCDMReqPorts-1:0][TCDMAddrWidth-1:0] tcdm_req_addr_o,
  output logic [TCDMReqPorts-1:0][3:0] tcdm_req_amo_o, //Note that tcdm_req_amo_i is 4 bits based on reqrsp definition
  output logic [TCDMReqPorts-1:0][NarrowDataWidth-1:0] tcdm_req_data_o,
  output logic [TCDMReqPorts-1:0][4:0] tcdm_req_user_core_id_o, //Note that tcdm_req_user_core_id_i is 5 bits based on Snitch definition
  output logic [TCDMReqPorts-1:0] tcdm_req_user_is_core_o,
  output logic [TCDMReqPorts-1:0][NarrowDataWidth/8-1:0] tcdm_req_strb_o,
  output logic [TCDMReqPorts-1:0] tcdm_req_q_valid_o,

  // Response
  input logic [TCDMReqPorts-1:0] tcdm_rsp_q_ready_i,
  input logic [TCDMReqPorts-1:0] tcdm_rsp_p_valid_i,
  input logic [TCDMReqPorts-1:0][NarrowDataWidth-1:0] tcdm_rsp_data_i,

  //-----------------------------
  // CSR control ports
  //-----------------------------
  // Request
  input logic [31:0] io_csr_req_bits_data_i,
  input logic [31:0] io_csr_req_bits_addr_i,
  input logic io_csr_req_bits_write_i,
  input logic io_csr_req_valid_i,
  output logic io_csr_req_ready_o,

  // Response
  input logic io_csr_rsp_ready_i,
  output logic io_csr_rsp_valid_o,
  output logic [31:0] io_csr_rsp_bits_data_o
);

  // Fixed ports that are defaulted
  // towards the TCDM from the streamer
  always_comb begin
    for(int i = 0; i < TCDMReqPorts; i++ ) begin
      tcdm_req_amo_o[i] = '0;
      tcdm_req_user_core_id_o[i] = '0;
      tcdm_req_user_is_core_o[i] = '0;
      tcdm_req_strb_o[i] = '1;
    end
  end

  // Streamer module that is generated
  // with template mechanics
  StreamerTop i_streamer_top (	
    //-----------------------------
    // Clocks and reset
    //-----------------------------
    .clock ( clk_i   ),
    .reset ( ~rst_ni ),

    //-----------------------------
    // Accelerator ports
    //-----------------------------
% for idx, dw in enumerate(cfg["fifoWriterParams"]['fifoWidth']):
    .io_data_accelerator2streamer_data_${idx}_bits ( acc2stream_data_${idx}_bits_i ),
    .io_data_accelerator2streamer_data_${idx}_valid ( acc2stream_data_${idx}_valid_i ),
    .io_data_accelerator2streamer_data_${idx}_ready ( acc2stream_data_${idx}_ready_o ),

% endfor
% for idx, dw in enumerate(cfg["fifoReaderParams"]['fifoWidth']):
    .io_data_streamer2accelerator_data_${idx}_bits ( stream2acc_data_${idx}_bits_o ),
    .io_data_streamer2accelerator_data_${idx}_valid ( stream2acc_data_${idx}_valid_o ),
    .io_data_streamer2accelerator_data_${idx}_ready ( stream2acc_data_${idx}_ready_i ),

% endfor
    //-----------------------------
    // TCDM Ports
    //-----------------------------
    // Request
% for idx in range(0, sum(cfg["dataReaderParams"]["tcdmPortsNum"]) + sum(cfg["dataWriterParams"]["tcdmPortsNum"])):
    .io_data_tcdm_rsp_${idx}_bits_data ( tcdm_rsp_data_i[${idx}] ),
    .io_data_tcdm_rsp_${idx}_valid ( tcdm_rsp_p_valid_i[${idx}] ),
    .io_data_tcdm_req_${idx}_ready ( tcdm_rsp_q_ready_i[${idx}] ),

% endfor
    // Response
% for idx in range(0, sum(cfg["dataReaderParams"]["tcdmPortsNum"]) + sum(cfg["dataWriterParams"]["tcdmPortsNum"])):
    .io_data_tcdm_req_${idx}_valid ( tcdm_req_q_valid_o[${idx}] ),
    .io_data_tcdm_req_${idx}_bits_addr ( tcdm_req_addr_o[${idx}] ),
    .io_data_tcdm_req_${idx}_bits_write ( tcdm_req_write_o[${idx}] ),
    .io_data_tcdm_req_${idx}_bits_data ( tcdm_req_data_o[${idx}] ),

% endfor
    //-----------------------------
    // CSR control ports
    //-----------------------------
    // Request
    .io_csr_req_bits_data ( io_csr_req_bits_data_i ),
    .io_csr_req_bits_addr ( io_csr_req_bits_addr_i ),
    .io_csr_req_bits_write ( io_csr_req_bits_write_i ),
    .io_csr_req_valid ( io_csr_req_valid_i ),
    .io_csr_req_ready ( io_csr_req_ready_o ),

    // Response
    .io_csr_rsp_bits_data ( io_csr_rsp_bits_data_o ),	
    .io_csr_rsp_valid ( io_csr_rsp_valid_o ),
    .io_csr_rsp_ready ( io_csr_rsp_ready_i )
  );

endmodule