// Copyright 2020 KU Leuven.
// Solderpad Hardware License, Version 0.51, see LICENSE for details.
// SPDX-License-Identifier: SHL-0.51

// Ryan Antonio <ryan.antonio@esat.kuleuven.be>

//-------------------------------
// SNAX interface translator for converting
// Snitch accelerator ports to 
// CSR ports
//-------------------------------
module snax_interface_translator #(
    parameter type      acc_req_t = logic,
    parameter type      acc_rsp_t = logic
)(
    //-------------------------------
    // Clocks and reset
    //-------------------------------
    input  logic        clk_i,
    input  logic        rst_ni,

    //-------------------------------
    // Request
    //-------------------------------
    input  acc_req_t    snax_req_i,
    input  logic        snax_qvalid_i,
    output logic        snax_qready_o,

    //-------------------------------
    // Response
    //-------------------------------
    output acc_rsp_t    snax_resp_o,
    output logic        snax_pvalid_o,
    input  logic        snax_pready_i,

    //-----------------------------
    // Simplified CSR control ports
    //-----------------------------
    // Request
    output logic [31:0] csr_req_bits_data_i,
    output logic [31:0] csr_req_bits_addr_i,
    output logic        csr_req_bits_write_i,
    output logic        csr_req_valid_i,
    input  logic        csr_req_ready_o,

    // Response
    output logic        csr_rsp_ready_i,
    input  logic        csr_rsp_valid_o,
    input  logic [31:0] csr_rsp_bits_data_o
);

    //-------------------------------
    // Local parameter
    //-------------------------------
    localparam int unsigned CsrAddrOFfset = 32'h3c0;

    //-------------------------------
    // Request handler
    //-------------------------------
    logic write_csr;

    always_comb begin
        if (!rst_ni) begin
            write_csr = 1'b0;
        end else if (snax_qvalid_i) begin
            unique casez (snax_req_i.data_op)
                CSRRS, CSRRSI, CSRRC, CSRRCI: begin
                    write_csr = 1'b0;
                end
                default: begin
                    write_csr = 1'b1;
                end
            endcase
        end else begin
            write_csr = 1'b0;
        end
    end

    assign io_csr_req_bits_data_i  = snax_req_i.data_arga[31:0];
    assign io_csr_req_bits_addr_i  = snax_req_i.data_argb - CsrAddrOFfset;
    assign io_csr_req_bits_write_i = write_csr;
    assign io_csr_req_valid_i      = snax_qvalid_i;
    assign snax_qready_o           = io_csr_req_ready_o;

    //-------------------------------
    // Response handler
    //-------------------------------
    // TODO: Need to fix the response port actually
    // Such that it handles the correct id
    // rsp
    assign io_csr_rsp_ready_i = snax_pready_i;
    assign snax_pvalid_o      = io_csr_rsp_valid_o;
    assign snax_resp_o.data   = io_csr_rsp_bits_data_o;
    assign snax_resp_o.id     = snax_req_i.id;
    assign snax_resp_o.error  = 1'b0;

endmodule
