// Copyright 2021 ETH Zurich and University of Bologna.
// Solderpad Hardware License, Version 0.51, see LICENSE for details.
// SPDX-License-Identifier: SHL-0.51

${disclaimer}

<%def name="icache_cfg(prop)">
  % for lw in cfg['hives']:
    ${lw['icache'][prop]}${',' if not loop.last else ''}
  % endfor
</%def>

<%def name="core_cfg(prop)">\
  % for c in cfg['cores']:
${c[prop]}${', ' if not loop.last else ''}\
  % endfor
</%def>\

<%def name="core_cfg_flat(prop)">\
${cfg['nr_cores']}'b\
  % for c in cfg['cores'][::-1]:
${int(c[prop])}\
  % endfor
</%def>\

<%def name="core_isa(isa)">\
${cfg['nr_cores']}'b\
  % for c in cfg['cores'][::-1]:
${int(getattr(c['isa_parsed'], isa))}\
  % endfor
</%def>\

<%def name="ssr_cfg(core, ssr_fmt_str, none_str, inner_sep)">\
% for core in cfg['cores']:
  % for s in list(reversed(core['ssrs'] + [None]*(cfg['num_ssrs_max']-len(core['ssrs'])))):
${("    '{" if loop.first else ' ') + \
    (ssr_fmt_str.format(**s) if s is not None else none_str) \
    + (inner_sep if not loop.last else '}')}\
  % endfor
${',' if not loop.last else ''}
% endfor
</%def>\

// These includes are necessary for pre-defined typedefs
`include "axi/typedef.svh"
`include "tcdm_interface/typedef.svh"

// Main cluster package
// verilog_lint: waive-start package-filename
package ${cfg['pkg_name']};

  // Base and pre-calculated parameters
  localparam int unsigned NrCores = ${cfg['nr_cores']};
  localparam int unsigned NrHives = ${cfg['nr_hives']};

  localparam int unsigned AddrWidth = ${cfg['addr_width']};
  localparam int unsigned NarrowDataWidth = ${cfg['data_width']};
  localparam int unsigned WideDataWidth = ${cfg['dma_data_width']};

  localparam int unsigned NarrowIdWidthIn = ${cfg['id_width_in']};
  localparam int unsigned NrMasters = 3;
  localparam int unsigned NarrowIdWidthOut = $clog2(NrMasters) + NarrowIdWidthIn;

  localparam int unsigned NrDmaMasters = 2 + ${cfg['nr_hives']};
  localparam int unsigned WideIdWidthIn = ${cfg['dma_id_width_in']};
  localparam int unsigned WideIdWidthOut = $clog2(NrDmaMasters) + WideIdWidthIn;

  localparam int unsigned CoreIDWidth = cf_math_pkg::idx_width(NrCores);

  localparam int unsigned TCDMDepth = ${cfg['tcdm']['depth']};
  localparam int unsigned NrBanks = ${cfg['tcdm']['banks']};

  localparam int unsigned NarrowUserWidth = ${cfg['user_width']};
  localparam int unsigned WideUserWidth = ${cfg['dma_user_width']};

  localparam int unsigned ICacheLineWidth [NrHives] = '{${icache_cfg('cacheline')}};
  localparam int unsigned ICacheLineCount [NrHives] = '{${icache_cfg('depth')}};
  localparam int unsigned ICacheSets [NrHives] = '{${icache_cfg('sets')}};

  localparam int unsigned Hive [NrCores] = '{${core_cfg('hive')}};

  // SRAM configurations
  typedef struct packed {
% for field, width in cfg['sram_cfg_fields'].items():
    logic [${width-1}:0] ${field};
% endfor
  } sram_cfg_t;

  typedef struct packed {
    sram_cfg_t icache_tag;
    sram_cfg_t icache_data;
    sram_cfg_t tcdm;
  } sram_cfgs_t;

  // Re-defined typedefs used for other typedefs
  typedef logic [AddrWidth-1:0]         addr_t;
  typedef logic [NarrowDataWidth-1:0]   data_t;
  typedef logic [NarrowDataWidth/8-1:0] strb_t;
  typedef logic [WideDataWidth-1:0]     data_dma_t;
  typedef logic [WideDataWidth/8-1:0]   strb_dma_t;
  typedef logic [NarrowIdWidthIn-1:0]   narrow_in_id_t;
  typedef logic [NarrowIdWidthOut-1:0]  narrow_out_id_t;
  typedef logic [WideIdWidthIn-1:0]     wide_in_id_t;
  typedef logic [WideIdWidthOut-1:0]    wide_out_id_t;
  typedef logic [NarrowUserWidth-1:0]   user_t;
  typedef logic [WideUserWidth-1:0]     user_dma_t;

  // Typedefs for the AXI connections
  `AXI_TYPEDEF_ALL(narrow_in, addr_t, narrow_in_id_t, data_t, strb_t, user_t)
  `AXI_TYPEDEF_ALL(narrow_out, addr_t, narrow_out_id_t, data_t, strb_t, user_t)
  `AXI_TYPEDEF_ALL(wide_in, addr_t, wide_in_id_t, data_dma_t, strb_dma_t, user_dma_t)
  `AXI_TYPEDEF_ALL(wide_out, addr_t, wide_out_id_t, data_dma_t, strb_dma_t, user_dma_t)

  localparam int unsigned TCDMMemAddrWidth = $clog2(TCDMDepth);
  localparam int unsigned TCDMSize = NrBanks * TCDMDepth * (NarrowDataWidth/8);
  localparam int unsigned TCDMAddrWidth = $clog2(TCDMSize);
  typedef logic [TCDMAddrWidth-1:0] tcdm_addr_t;

  // TCDM definitions
  typedef struct packed {
    logic [CoreIDWidth-1:0] core_id;
    bit                     is_core;
  } tcdm_user_t;

  `TCDM_TYPEDEF_ALL(tcdm, tcdm_addr_t, data_t, strb_t, tcdm_user_t)

  // Accelerator definitions for SNAX and other Snitch L0 accelerators
  // (e.g., of L0 accelerators - DMA, FPSS, and so on)
  typedef struct packed {
    snitch_pkg::acc_addr_e   addr;
    logic [4:0]  id;
    logic [31:0] data_op;
    data_t       data_arga;
    data_t       data_argb;
    addr_t       data_argc;
  } acc_req_t;

  typedef struct packed {
    logic [4:0] id;
    logic       error;
    data_t      data;
  } acc_resp_t;

  // Function pre-calculations
  function automatic snitch_pma_pkg::rule_t [snitch_pma_pkg::NrMaxRules-1:0] get_cached_regions();
    automatic snitch_pma_pkg::rule_t [snitch_pma_pkg::NrMaxRules-1:0] cached_regions;
    cached_regions = '{default: '0};
% for i, cp in enumerate(cfg['pmas']['cached']):
    cached_regions[${i}] = '{base: ${to_sv_hex(cp[0], cfg['addr_width'])}, mask: ${to_sv_hex(cp[1], cfg['addr_width'])}};
% endfor
    return cached_regions;
  endfunction

  localparam snitch_pma_pkg::snitch_pma_t SnitchPMACfg = '{
      NrCachedRegionRules: ${len(cfg['pmas']['cached'])},
      CachedRegion: get_cached_regions(),
      default: 0
  };

  // FPU configurations per FPU that has a core
  localparam fpnew_pkg::fpu_implementation_t FPUImplementation [${cfg['nr_cores']}] = '{
  % for c in cfg['cores']:
    '{
        PipeRegs: // FMA Block
                  '{
                    '{  ${cfg['timing']['lat_comp_fp32']}, // FP32
                        ${cfg['timing']['lat_comp_fp64']}, // FP64
                        ${cfg['timing']['lat_comp_fp16']}, // FP16
                        ${cfg['timing']['lat_comp_fp8']}, // FP8
                        ${cfg['timing']['lat_comp_fp16_alt']}, // FP16alt
                        ${cfg['timing']['lat_comp_fp8_alt']}  // FP8alt
                      },
                    '{1, 1, 1, 1, 1, 1},   // DIVSQRT
                    '{${cfg['timing']['lat_noncomp']},
                      ${cfg['timing']['lat_noncomp']},
                      ${cfg['timing']['lat_noncomp']},
                      ${cfg['timing']['lat_noncomp']},
                      ${cfg['timing']['lat_noncomp']},
                      ${cfg['timing']['lat_noncomp']}},   // NONCOMP
                    '{${cfg['timing']['lat_conv']},
                      ${cfg['timing']['lat_conv']},
                      ${cfg['timing']['lat_conv']},
                      ${cfg['timing']['lat_conv']},
                      ${cfg['timing']['lat_conv']},
                      ${cfg['timing']['lat_conv']}},   // CONV
                    '{${cfg['timing']['lat_sdotp']},
                      ${cfg['timing']['lat_sdotp']},
                      ${cfg['timing']['lat_sdotp']},
                      ${cfg['timing']['lat_sdotp']},
                      ${cfg['timing']['lat_sdotp']},
                      ${cfg['timing']['lat_sdotp']}}    // DOTP
                    },
        UnitTypes: '{'{fpnew_pkg::MERGED,
                       fpnew_pkg::MERGED,
                       fpnew_pkg::MERGED,
                       fpnew_pkg::MERGED,
                       fpnew_pkg::MERGED,
                       fpnew_pkg::MERGED},  // FMA
% if c["Xdiv_sqrt"]:
                    '{fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED}, // DIVSQRT
% else:
                    '{fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED}, // DIVSQRT
% endif
                    '{fpnew_pkg::PARALLEL,
                        fpnew_pkg::PARALLEL,
                        fpnew_pkg::PARALLEL,
                        fpnew_pkg::PARALLEL,
                        fpnew_pkg::PARALLEL,
                        fpnew_pkg::PARALLEL}, // NONCOMP
                    '{fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED},   // CONV
% if c["xfdotp"]:
                    '{fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED,
                        fpnew_pkg::MERGED}},  // DOTP
% else:
                    '{fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED,
                        fpnew_pkg::DISABLED}}, // DOTP
% endif
        PipeConfig: fpnew_pkg::${cfg['timing']['fpu_pipe_config']}
    }${',\n' if not loop.last else '\n'}\
  % endfor
  };

  localparam snitch_ssr_pkg::ssr_cfg_t [${cfg['num_ssrs_max']}-1:0] SsrCfgs [${cfg['nr_cores']}] = '{
${ssr_cfg(core, "'{{{indirection:d}, {isect_master:d}, {isect_master_idx:d}, {isect_slave:d}, "\
  "{isect_slave_spill:d}, {indir_out_spill:d}, {num_loops}, {index_width}, {pointer_width}, "\
  "{shift_width}, {rpt_width}, {index_credits}, {isect_slave_credits}, {data_credits}, "\
  "{mux_resp_depth}}}", "/*None*/ '0", ',\n     ')}\
  };

  localparam logic [${cfg['num_ssrs_max']}-1:0][4:0] SsrRegs [${cfg['nr_cores']}] = '{
${ssr_cfg(core, '{reg_idx}', '/*None*/ 0', ',')}\
  };

  // Forward potentially optional configuration parameters
  localparam logic [9:0] CfgBaseHartId      =  (${to_sv_hex(cfg['cluster_base_hartid'], 10)});
  localparam addr_t    	 CfgClusterBaseAddr = (${to_sv_hex(cfg['cluster_base_addr'], cfg['addr_width'])});

endpackage
// verilog_lint: waive-stop package-filename

// Main snitch or SNAX cluster wrapper
module ${cfg['name']}_wrapper (
  input  logic                                   clk_i,
  input  logic                                   rst_ni,
  input  logic [${cfg['pkg_name']}::NrCores-1:0] debug_req_i,
  input  logic [${cfg['pkg_name']}::NrCores-1:0] meip_i,
  input  logic [${cfg['pkg_name']}::NrCores-1:0] mtip_i,
  input  logic [${cfg['pkg_name']}::NrCores-1:0] msip_i,
  input  logic [9:0]                             hart_base_id_i,
  input  logic [${cfg['addr_width']-1}:0]                            cluster_base_addr_i,
  input  logic                                   clk_d2_bypass_i,
  input  ${cfg['pkg_name']}::sram_cfgs_t         sram_cfgs_i,
  input  ${cfg['pkg_name']}::narrow_in_req_t     narrow_in_req_i,
  output ${cfg['pkg_name']}::narrow_in_resp_t    narrow_in_resp_o,
  output ${cfg['pkg_name']}::narrow_out_req_t    narrow_out_req_o,
  input  ${cfg['pkg_name']}::narrow_out_resp_t   narrow_out_resp_i,
  output ${cfg['pkg_name']}::wide_out_req_t      wide_out_req_o,
  input  ${cfg['pkg_name']}::wide_out_resp_t     wide_out_resp_i,
  input  ${cfg['pkg_name']}::wide_in_req_t       wide_in_req_i,
  output ${cfg['pkg_name']}::wide_in_resp_t      wide_in_resp_o
);

  // Internal local parameters to be hooked into the Snitch / SNAX cluster
  localparam int unsigned NumIntOutstandingLoads [${cfg['nr_cores']}] = '{${core_cfg('num_int_outstanding_loads')}};
  localparam int unsigned NumIntOutstandingMem [${cfg['nr_cores']}] = '{${core_cfg('num_int_outstanding_mem')}};
  localparam int unsigned NumFPOutstandingLoads [${cfg['nr_cores']}] = '{${core_cfg('num_fp_outstanding_loads')}};
  localparam int unsigned NumFPOutstandingMem [${cfg['nr_cores']}] = '{${core_cfg('num_fp_outstanding_mem')}};
  localparam int unsigned NumDTLBEntries [${cfg['nr_cores']}] = '{${core_cfg('num_dtlb_entries')}};
  localparam int unsigned NumITLBEntries [${cfg['nr_cores']}] = '{${core_cfg('num_itlb_entries')}};
  localparam int unsigned NumSequencerInstr [${cfg['nr_cores']}] = '{${core_cfg('num_sequencer_instructions')}};
  localparam int unsigned NumSsrs [${cfg['nr_cores']}] = '{${core_cfg('num_ssrs')}};
  localparam int unsigned SsrMuxRespDepth [${cfg['nr_cores']}] = '{${core_cfg('ssr_mux_resp_depth')}};
  localparam int unsigned SnaxTcdmPorts [${cfg['nr_cores']}] = '{${core_cfg('snax_tcdm_ports')}};

  // SNAX accelerator ports
  ${cfg['pkg_name']}::acc_req_t  [${cfg['pkg_name']}::NrCores-1:0] snax_req;
  logic      [${cfg['pkg_name']}::NrCores-1:0] snax_qvalid;
  logic      [${cfg['pkg_name']}::NrCores-1:0] snax_qready;
  ${cfg['pkg_name']}::acc_resp_t [${cfg['pkg_name']}::NrCores-1:0] snax_resp;
  logic      [${cfg['pkg_name']}::NrCores-1:0] snax_pvalid;
  logic      [${cfg['pkg_name']}::NrCores-1:0] snax_pready;
  logic      [${cfg['pkg_name']}::NrCores-1:0] snax_barrier;
  ## This set of lines are for the internal pre-calculations for SNAX ports
  <%
    extract_port_num_list = []
    for i in range(len(cfg['cores'])):
      extract_port_num_list.append(cfg['cores'][i]['snax_tcdm_ports'])
    
    offset_list = []
    init_offset = 0

    for i in range(len(extract_port_num_list)):
      offset_list.append(init_offset)
      init_offset += extract_port_num_list[i]
  %>
  // SNAX TCDM wires
  // Wires need to be declared before use
  ${cfg['pkg_name']}::tcdm_req_t [${init_offset-1}:0] snax_tcdm_req;
  ${cfg['pkg_name']}::tcdm_rsp_t [${init_offset-1}:0] snax_tcdm_rsp;

  // Snitch cluster under test.
  snitch_cluster #(
    .PhysicalAddrWidth (${cfg['addr_width']}),
    .NarrowDataWidth (${cfg['data_width']}),
    .WideDataWidth (${cfg['dma_data_width']}),
    .NarrowIdWidthIn (${cfg['pkg_name']}::NarrowIdWidthIn),
    .WideIdWidthIn (${cfg['pkg_name']}::WideIdWidthIn),
    .NarrowUserWidth (${cfg['pkg_name']}::NarrowUserWidth),
    .WideUserWidth (${cfg['pkg_name']}::WideUserWidth),
    .BootAddr (${to_sv_hex(cfg['boot_addr'], 32)}),
    .narrow_in_req_t (${cfg['pkg_name']}::narrow_in_req_t),
    .narrow_in_resp_t (${cfg['pkg_name']}::narrow_in_resp_t),
    .narrow_out_req_t (${cfg['pkg_name']}::narrow_out_req_t),
    .narrow_out_resp_t (${cfg['pkg_name']}::narrow_out_resp_t),
    .wide_out_req_t (${cfg['pkg_name']}::wide_out_req_t),
    .wide_out_resp_t (${cfg['pkg_name']}::wide_out_resp_t),
    .wide_in_req_t (${cfg['pkg_name']}::wide_in_req_t),
    .wide_in_resp_t (${cfg['pkg_name']}::wide_in_resp_t),
    .NrHives (${cfg['nr_hives']}),
    .NrCores (${cfg['nr_cores']}),
    .TCDMDepth (${cfg['pkg_name']}::TCDMDepth),
    .ZeroMemorySize (${cfg['zero_mem_size']}),
    .ClusterPeriphSize (${cfg['cluster_periph_size']}),
    .NrBanks (${cfg['tcdm']['banks']}),
    .DMANumAxInFlight (${cfg['dma_axi_req_fifo_depth']}),
    .DMAReqFifoDepth (${cfg['dma_req_fifo_depth']}),
    .ICacheLineWidth (${cfg['pkg_name']}::ICacheLineWidth),
    .ICacheLineCount (${cfg['pkg_name']}::ICacheLineCount),
    .ICacheSets (${cfg['pkg_name']}::ICacheSets),
    .VMSupport (${int(cfg['vm_support'])}),
    .RVE (${core_isa('e')}),
    .RVF (${core_isa('f')}),
    .RVD (${core_isa('d')}),
    .XDivSqrt (${core_cfg_flat('Xdiv_sqrt')}),
    .XF16 (${core_cfg_flat('xf16')}),
    .XF16ALT (${core_cfg_flat('xf16alt')}),
    .XF8 (${core_cfg_flat('xf8')}),
    .XF8ALT (${core_cfg_flat('xf8alt')}),
    .XFVEC (${core_cfg_flat('xfvec')}),
    .XFDOTP (${core_cfg_flat('xfdotp')}),
    .Xdma (${core_cfg_flat('xdma')}),
    .Xssr (${core_cfg_flat('xssr')}),
    .Xfrep (${core_cfg_flat('xfrep')}),
    .TotalSnaxTcdmPorts(${init_offset}),
    .FPUImplementation (${cfg['pkg_name']}::FPUImplementation),
    .SnitchPMACfg (${cfg['pkg_name']}::SnitchPMACfg),
    .NumIntOutstandingLoads (NumIntOutstandingLoads),
    .NumIntOutstandingMem (NumIntOutstandingMem),
    .NumFPOutstandingLoads (NumFPOutstandingLoads),
    .NumFPOutstandingMem (NumFPOutstandingMem),
    .NumDTLBEntries (NumDTLBEntries),
    .NumITLBEntries (NumITLBEntries),
    .NumSsrsMax (${cfg['num_ssrs_max']}),
    .NumSsrs (NumSsrs),
    .SsrMuxRespDepth (SsrMuxRespDepth),
    .SsrRegs (${cfg['pkg_name']}::SsrRegs),
    .SsrCfgs (${cfg['pkg_name']}::SsrCfgs),
    .NumSequencerInstr (NumSequencerInstr),
    .Hive (${cfg['pkg_name']}::Hive),
    .Topology (snitch_pkg::${cfg['tcdm']['topology']}),
    .Radix (${int(cfg['tcdm']['radix'])}),
    .NumSwitchNets (${int(cfg['tcdm']['num_switch_nets'])}),
    .SwitchLfsrArbiter (${int(cfg['tcdm']['switch_lfsr_arbiter'])}),
    .RegisterOffloadReq (${int(cfg['timing']['register_offload_req'])}),
    .RegisterOffloadRsp (${int(cfg['timing']['register_offload_rsp'])}),
    .RegisterCoreReq (${int(cfg['timing']['register_core_req'])}),
    .RegisterCoreRsp (${int(cfg['timing']['register_core_rsp'])}),
    .RegisterTCDMCuts (${int(cfg['timing']['register_tcdm_cuts'])}),
    .RegisterExtWide (${int(cfg['timing']['register_ext_wide'])}),
    .RegisterExtNarrow (${int(cfg['timing']['register_ext_narrow'])}),
    .RegisterFPUReq (${int(cfg['timing']['register_fpu_req'])}),
    .RegisterFPUIn (${int(cfg['timing']['register_fpu_in'])}),
    .RegisterFPUOut (${int(cfg['timing']['register_fpu_out'])}),
    .RegisterSequencer (${int(cfg['timing']['register_sequencer'])}),
    .IsoCrossing (${int(cfg['timing']['iso_crossings'])}),
    .NarrowXbarLatency (axi_pkg::${cfg['timing']['narrow_xbar_latency']}),
    .WideXbarLatency (axi_pkg::${cfg['timing']['wide_xbar_latency']}),
    .WideMaxMstTrans (${cfg['wide_trans']}),
    .WideMaxSlvTrans (${cfg['wide_trans']}),
    .NarrowMaxMstTrans (${cfg['narrow_trans']}),
    .NarrowMaxSlvTrans (${cfg['narrow_trans']}),
    .sram_cfg_t (${cfg['pkg_name']}::sram_cfg_t),
    .sram_cfgs_t (${cfg['pkg_name']}::sram_cfgs_t),
    .CaqDepth (${int(cfg['caq_depth'])}),
    .CaqTagWidth (${int(cfg['caq_tag_width'])}),
    .DebugSupport (${int(cfg['enable_debug'])}),
    .AliasRegionEnable (${int(cfg['alias_region_enable'])}),
    .AliasRegionBase (${int(cfg['alias_region_base'])}),
    .DebugSupport (${int(cfg['enable_debug'])}),
    .acc_req_t (${cfg['pkg_name']}::acc_req_t),
    .acc_resp_t (${cfg['pkg_name']}::acc_resp_t),
    .tcdm_req_t (${cfg['pkg_name']}::tcdm_req_t),
    .tcdm_rsp_t (${cfg['pkg_name']}::tcdm_rsp_t)
  ) i_cluster (
    .clk_i,
    .rst_ni,
% if cfg['enable_debug']:
    .debug_req_i,
% else:
    .debug_req_i ('0),
% endif
    .meip_i,
    .mtip_i,
    .msip_i,
% if cfg['cluster_base_expose']:
    .hart_base_id_i,
    .cluster_base_addr_i,
% else:
    .hart_base_id_i (snitch_cluster_pkg::CfgBaseHartId),
    .cluster_base_addr_i (snitch_cluster_pkg::CfgClusterBaseAddr),
% endif
% if cfg['timing']['iso_crossings']:
    .clk_d2_bypass_i,
% else:
    .clk_d2_bypass_i (1'b0),
% endif
    .snax_req_o (snax_req),
    .snax_qvalid_o (snax_qvalid),
    .snax_qready_i (snax_qready),
    .snax_resp_i (snax_resp),
    .snax_pvalid_i (snax_pvalid),
    .snax_pready_o (snax_pready),
    .snax_tcdm_req_i (snax_tcdm_req),
    .snax_tcdm_rsp_o (snax_tcdm_rsp),
    .snax_barrier_i  (snax_barrier),
% if cfg['sram_cfg_expose']:
    .sram_cfgs_i (sram_cfgs_i),
% else:
    .sram_cfgs_i (${cfg['pkg_name']}::sram_cfgs_t'('0)),
%endif
    .narrow_in_req_i,
    .narrow_in_resp_o,
    .narrow_out_req_o,
    .narrow_out_resp_i,
    .wide_out_req_o,
    .wide_out_resp_i,
    .wide_in_req_i,
    .wide_in_resp_o
  );

  // Accelerator instances if there are accelerator ports
  // If there are not accelerator ports, we tie the input signals to 0
% for idx, c in enumerate(cfg['cores']):
  % if c['snax_acc'] == "snax_gemm_wrapper":
  ${c['snax_acc']} # (
    .DataWidth ( ${cfg['pkg_name']}::NarrowDataWidth ),
    .SnaxTcdmPorts ( SnaxTcdmPorts[${idx}] ),
    .acc_req_t ( ${cfg['pkg_name']}::acc_req_t ),
    .acc_rsp_t ( ${cfg['pkg_name']}::acc_resp_t ),
    .tcdm_req_t ( ${cfg['pkg_name']}::tcdm_req_t ),
    .tcdm_rsp_t ( ${cfg['pkg_name']}::tcdm_rsp_t )
  ) i_${c['snax_acc']}_${idx}  (
    .clk_i ( clk_i ),
    .rst_ni ( rst_ni ),
    .snax_req_i ( snax_req[${idx}] ),
    .snax_qvalid_i ( snax_qvalid[${idx}] ),
    .snax_qready_o ( snax_qready[${idx}] ),
    .snax_resp_o ( snax_resp[${idx}] ),
    .snax_pvalid_o ( snax_pvalid[${idx}] ),
    .snax_pready_i ( snax_pready[${idx}] ),
    .snax_tcdm_req_o ( snax_tcdm_req[${offset_list[idx+1]-1}:${offset_list[idx]}] ),
    .snax_tcdm_rsp_i ( snax_tcdm_rsp[${offset_list[idx+1]-1}:${offset_list[idx]}] )
  );

  assign snax_barrier[${idx}] = '0;

  % elif c['snax_acc'] != "none":

  ${c['snax_acc']} # (
    .DataWidth ( ${cfg['pkg_name']}::NarrowDataWidth ),
    .SnaxTcdmPorts ( SnaxTcdmPorts[${idx}] ),
    .acc_req_t ( ${cfg['pkg_name']}::acc_req_t ),
    .acc_rsp_t ( ${cfg['pkg_name']}::acc_resp_t ),
    .tcdm_req_t ( ${cfg['pkg_name']}::tcdm_req_t ),
    .tcdm_rsp_t ( ${cfg['pkg_name']}::tcdm_rsp_t )
  ) i_${c['snax_acc']}_${idx}  (
    .clk_i ( clk_i ),
    .rst_ni ( rst_ni ),
    .snax_req_i ( snax_req[${idx}] ),
    .snax_qvalid_i ( snax_qvalid[${idx}] ),
    .snax_qready_o ( snax_qready[${idx}] ),
    .snax_resp_o ( snax_resp[${idx}] ),
    .snax_pvalid_o ( snax_pvalid[${idx}] ),
    .snax_pready_i ( snax_pready[${idx}] ),
    .snax_barrier_o ( snax_barrier[${idx}] ),
    .snax_tcdm_req_o ( snax_tcdm_req[${offset_list[idx+1]-1}:${offset_list[idx]}] ),
    .snax_tcdm_rsp_i ( snax_tcdm_rsp[${offset_list[idx+1]-1}:${offset_list[idx]}] )
  );

  % else:

  assign snax_qready[${idx}] = '0;
  assign snax_resp[${idx}] = '0;
  assign snax_pvalid[${idx}] = '0;
  assign snax_barrier[${idx}] = '0;
  
  % endif
% endfor


endmodule
