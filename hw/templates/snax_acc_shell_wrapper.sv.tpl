<%
  import math

  num_input_ports  = len(cfg["snax_streamer_cfg"]["data_reader_params"]["tcdm_ports_num"])
  num_output_ports = len(cfg["snax_streamer_cfg"]["data_writer_params"]["tcdm_ports_num"])

%>
//-------------------------------
// This accelerator wrapper is just
// a suggested template for wrapping
// signals that can fit snuggly into 
// the SNAX shell.
//-------------------------------

module ${cfg["tag_name"]}_wrapper #(  
  // Put your custom parameters here
  // ...
  // Generated parameters
  parameter int unsigned NumInputPorts  = ${num_input_ports },
  parameter int unsigned NumOutputPorts = ${num_output_ports},
  parameter int unsigned DataWidth      = ${cfg["tcdm_data_width"]},
  parameter int unsigned RegDataWidth   = 32,
  parameter int unsigned RegAddrWidth   = 32
)(
  //-------------------------------
  // Clocks and reset
  //-------------------------------
  input  logic                      clk_i,
  input  logic                      rst_ni,
  
  //-----------------------------
  // Accelerator ports
  //-----------------------------
  // Note that these have very specific data widths
  // found from the configuration file

  // Ports from accelerator to streamer
% for idx, dw in enumerate(cfg["snax_streamer_cfg"]["fifo_writer_params"]["fifo_width"]):
  output logic [${dw-1}:0] acc2stream_${idx}_data_o,
  output logic acc2stream_${idx}_valid_o,
  input  logic acc2stream_${idx}_ready_i,

% endfor
  // Ports from streamer to accelerator
% for idx, dw in enumerate(cfg["snax_streamer_cfg"]["fifo_reader_params"]["fifo_width"]):
  input  logic [${dw-1}:0] stream2acc_${idx}_data_i,
  input  logic stream2acc_${idx}_valid_i,
  output logic stream2acc_${idx}_ready_o,

% endfor
  //-------------------------------
  // CSR manager ports
  //-------------------------------
  input  logic [  RegAddrWidth-1:0] csr_addr_i,
  input  logic [  RegDataWidth-1:0] csr_wr_data_i,
  input  logic                      csr_wr_en_i,
  input  logic                      csr_req_valid_i,
  output logic                      csr_req_ready_o,
  output logic [  RegDataWidth-1:0] csr_rd_data_o,
  output logic                      csr_rsp_valid_o,
  input  logic                      csr_rsp_ready_i
);


  //-------------------------------
  // Add your CSR block here
  //-------------------------------

  //-------------------------------
  // Add your accelerator datapaths here
  //-------------------------------

endmodule
