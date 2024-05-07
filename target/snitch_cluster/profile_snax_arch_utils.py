# // Copyright 2023 KU Leuven.
# // Licensed under the Apache License, Version 2.0, see LICENSE for details.
# // SPDX-License-Identifier: Apache-2.0
# //
# // Xiaoling Yi <xiaoling.yi@esat.kuleuven.be>

import os
import hjson
import re
import csv
import math
import random

common_dir = {
    #// hardware configuration
    "Batch": 1,
    "strideC": 0,
    "spatial_len_0": 8,
    "spatial_len_1": 8,
    "tileSize": 8,
    "meshRow": 8,
    "meshCol": 8
}

def build_hw(arch_name):
    # Build the hardware and software
    cmd = "make clean && ./gen_acc_files.sh && ./gen_acc_files.sh"
    os.system(cmd)
    cmd = f"make CFG_OVERRIDE=cfg/{arch_name}.hjson bin/snitch_cluster.vlt > run.log"
    os.system(cmd)


def build_sw(sw_exp_name, wl_size):
    # gen run-time config for exp2
    delta = 8
    if sw_exp_name == "snax-wide-gemm-data-reshuffler" or sw_exp_name == "snax-wide-gemm-snitch-reshuffler":
        run_time_cfg = {
            "tempLoop0_A": wl_size["K"],
            "tempLoop1_A": wl_size["M"],
            "DMAtempStride0_A_in": 64,
            "DMAtempStride1_A_in": 64 * wl_size["K"],
            "DMAspatialStride1_A_in": 8,
            "tempStride0_A_in": 8,
            "tempStride1_A_in": 64 * wl_size["K"],
            "spatialStride1_A_in": 8 * wl_size["K"],
            "tempStride0_A_out": 64,
            "tempStride1_A_out": 64 * wl_size["K"],
            "spatialStride1_A_out": 8,
            "delta_local_A_in": 0,
            "delta_local_A_out": 64 * wl_size["K"] * wl_size["M"],
            "transpose_A": 0,
            "tempLoop0_B": wl_size["K"],
            "tempLoop1_B": wl_size["N"],
            "DMAtempStride0_B_in": 64,
            "DMAtempStride1_B_in": 64 * wl_size["K"],
            "DMAspatialStride1_B_in": 8,
            "tempStride0_B_in": 8,
            "tempStride1_B_in": 64 * wl_size["K"],
            "spatialStride1_B_in": 8 * wl_size["K"],
            "tempStride0_B_out": 64,
            "tempStride1_B_out": 64 * wl_size["K"],
            "spatialStride1_B_out": 8,
            "delta_local_B_in": 64 * wl_size["K"] * wl_size["M"] * 2,
            "delta_local_B_out": 64 * wl_size["K"] * wl_size["M"] * 2 + 64 * wl_size["K"] * wl_size["N"],
            "transpose_B": 0,
            "tempLoop0_C": wl_size["N"],
            "tempLoop1_C": wl_size["M"],
            "DMAtempStride0_C_in": 256,
            "DMAtempStride1_C_in": 256 * wl_size["N"],
            "DMAspatialStride1_C_in": 32,
            "tempStride0_C_in": 512,
            "tempStride1_C_in": 32,
            "spatialStride1_C_in": 256,
            "tempStride0_C_out": 256,
            "tempStride1_C_out": 512,
            "spatialStride1_C_out": 32,
            "delta_local_C_in": 64 * wl_size["K"] * wl_size["M"] * 2 + 64 * wl_size["K"] * wl_size["N"] * 2,
            "delta_local_C_out": 8192,
            "transpose_C": 0,
        }
        run_time_cfg.update(common_dir)

    if sw_exp_name == "snax-streamer-gemm-data-layout":
        run_time_cfg = {
            "Batch": 1,
            "K": wl_size["K"],
            "N": wl_size["N"],
            "M": wl_size["M"],
            "DMA_strideInnermostA": 64,
            "DMA_strideInnermostB": 64,
            "DMA_ldA": 64 * wl_size["K"],
            "DMA_ldB": 64 * wl_size["K"],
            "spatialA": 8 * wl_size["K"],
            "spatialB": 8 * wl_size["K"],
            "spatialC": 32,
            "strideInnermostA": 8,
            "strideInnermostB": 8,
            "strideInnermostC": 256,
            "strideHalfC": 0,
            "ldA": 64 * wl_size["K"],
            "ldB": 64 * wl_size["K"],
            "ldC": 256 * wl_size["N"],
            "strideA": 0,
            "strideB": 0,
            "strideC": 0,
            "tileSize": 8,
            "meshRow": 8,
            "meshCol": 8,
            "delta_local_a": 0,
            "delta_local_b": 64 * wl_size["K"] * wl_size["M"] + delta,
            "delta_local_c": 64 * wl_size["K"] * wl_size["M"] + 64 * wl_size["K"] * wl_size["N"] + delta
        }

    # gen run-time config for exp3
    delta_reduce_contention = 8
    run_time_cfg_common_narrow_narrow = {
            "tempLoop0_A": wl_size["K"],
            "tempLoop1_A": wl_size["M"],
            "DMAtempStride0_A_in": 64,
            "DMAtempStride1_A_in": 64 * wl_size["K"],
            "DMAspatialStride1_A_in": 8,
            "tempStride0_A_in": 8,
            "tempStride1_A_in": 64 * wl_size["K"],
            "spatialStride1_A_in": 8 * wl_size["K"],
            "tempStride0_A_out": 64,
            "tempStride1_A_out": 64 * wl_size["K"],
            "spatialStride1_A_out": 8,
            "delta_local_A_in": 0,
            "delta_local_A_out": 0,
            "transpose_A": 0,
            "tempLoop0_B": wl_size["K"],
            "tempLoop1_B": wl_size["N"],
            "DMAtempStride0_B_in": 64,
            "DMAtempStride1_B_in": 64 * wl_size["K"],
            "DMAspatialStride1_B_in": 8,
            "tempStride0_B_in": 8,
            "tempStride1_B_in": 64 * wl_size["K"],
            "spatialStride1_B_in": 8 * wl_size["K"],
            "tempStride0_B_out": 64,
            "tempStride1_B_out": 64 * wl_size["K"],
            "spatialStride1_B_out": 8,
            "delta_local_B_in": 64 * wl_size["K"] * wl_size["M"] + delta_reduce_contention,
            "delta_local_B_out": 0,
            "transpose_B": 0,
            # GEMM out for C
            "tempStride0_GEMM_C_out": 256,
            "tempStride1_GEMM_C_out": 256 * wl_size["N"],
            "spatialStride1_GEMM_C_out": 32,
            "delta_local_GEMM_C_out": 64 * wl_size["K"] * wl_size["M"] + 64 * wl_size["K"] * wl_size["N"] + delta_reduce_contention,
            # SIMD out for C
            "tempLoop0_C": wl_size["N"],
            "tempLoop1_C": wl_size["M"],
            "DMAtempStride0_C_in": 64,
            "DMAtempStride1_C_in": 64 * wl_size["N"],
            "DMAspatialStride1_C_in": 8,
    }

    run_time_cfg_common_wide_wide = {
            "tempLoop0_A": wl_size["K"],
            "tempLoop1_A": wl_size["M"],
            "DMAtempStride0_A_in": 64,
            "DMAtempStride1_A_in": 64 * wl_size["K"],
            "DMAspatialStride1_A_in": 8,
            "tempStride0_A_in": 8,
            "tempStride1_A_in": 64 * wl_size["K"],
            "spatialStride1_A_in": 8 * wl_size["K"],
            "tempStride0_A_out": 64,
            "tempStride1_A_out": 64 * wl_size["K"],
            "spatialStride1_A_out": 8,
            "delta_local_A_in": 0,
            "delta_local_A_out": 64 * wl_size["K"] * wl_size["M"],
            "transpose_A": 0,
            "tempLoop0_B": wl_size["K"],
            "tempLoop1_B": wl_size["N"],
            "DMAtempStride0_B_in": 64,
            "DMAtempStride1_B_in": 64 * wl_size["K"],
            "DMAspatialStride1_B_in": 8,
            "tempStride0_B_in": 8,
            "tempStride1_B_in": 64 * wl_size["K"],
            "spatialStride1_B_in": 8 * wl_size["K"],
            "tempStride0_B_out": 64,
            "tempStride1_B_out": 64 * wl_size["K"],
            "spatialStride1_B_out": 8,
            "delta_local_B_in": 64 * wl_size["K"] * wl_size["M"] * 2,
            "delta_local_B_out": 64 * wl_size["K"] * wl_size["M"] * 2 + 64 * wl_size["K"] * wl_size["N"],
            "transpose_B": 0,
            # GEMM out for C
            "tempStride0_GEMM_C_out": 256,
            "tempStride1_GEMM_C_out": 256 * wl_size["N"],
            "spatialStride1_GEMM_C_out": 32,
            "delta_local_GEMM_C_out": 64 * wl_size["K"] * wl_size["M"] * 2 + 64 * wl_size["K"] * wl_size["N"] * 2,
            # SIMD out for C
            "tempLoop0_C": wl_size["N"],
            "tempLoop1_C": wl_size["M"],
            "DMAtempStride0_C_in": 64,
            "DMAtempStride1_C_in": 64 * wl_size["N"],
            "DMAspatialStride1_C_in": 8,
    }

    if sw_exp_name == "snax-narrow-gemm-narrow-simd-dr" or sw_exp_name == "snax-wide-gemm-wide-simd-dr":
        transpose_C = 1
    elif sw_exp_name == "snax-narrow-gemm-narrow-simd-dr-c-left" or sw_exp_name == "snax-wide-gemm-wide-simd-dr-c-left":
        transpose_C = 0

    if sw_exp_name == "snax-narrow-gemm-narrow-simd-dr":
        run_time_cfg = {
            # input strides of data reshuffle
            "tempStride0_C_in": 64,
            "tempStride1_C_in": 64 * wl_size["M"],
            "spatialStride1_C_in": 8,
            # output strides of data reshuffle
            "tempStride0_C_out": 64,
            "tempStride1_C_out": 64 * wl_size["M"],
            "spatialStride1_C_out": 8,
            "delta_local_C_in": 64 * wl_size["K"] * wl_size["M"] + 64 * wl_size["K"] * wl_size["N"] + 256 * wl_size["N"] * wl_size["M"] + delta_reduce_contention,
            "delta_local_C_out": 0,
            "transpose_C": transpose_C,
            # DR configuration for D
            "tempLoop0_D": wl_size["M"],
            "tempLoop1_D": wl_size["M2"],
            "DMAtempStride0_D_in": 64,
            "DMAtempStride1_D_in": 64 * wl_size["M"],
            "DMAspatialStride1_D_in": 8,
            "tempStride0_D_in": 8,
            "tempStride1_D_in": 64 * wl_size["M"],
            "spatialStride1_D_in": 8 * wl_size["M"],
            "tempStride0_D_out": 64,
            "tempStride1_D_out": 64 * wl_size["M"],
            "spatialStride1_D_out": 8,
            "delta_local_D_in": 64 * wl_size["N"] * wl_size["M"] + delta_reduce_contention,
            "delta_local_D_out": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["M"] * wl_size["M2"] + delta_reduce_contention,
            "transpose_D": 0,
            # configuration for E
            "tempStride0_GEMM_E_out": 256,
            "tempStride1_GEMM_E_out": 256 * wl_size["N"],
            "spatialStride1_GEMM_E_out": 32,
            "delta_local_E_in": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["M"] * wl_size["M2"] * 2 + delta_reduce_contention * 2,
        }

    if sw_exp_name == "snax-narrow-gemm-narrow-simd-dr-c-left":
        run_time_cfg = {
            # input strides of data reshuffle
            "tempStride0_C_in": 64,
            "tempStride1_C_in": 64 * wl_size["M"],
            "spatialStride1_C_in": 8,
            # output strides of data reshuffle
            "tempStride0_C_out": 64,
            "tempStride1_C_out": 64 * wl_size["M"],
            "spatialStride1_C_out": 8,
            "delta_local_C_in": 64 * wl_size["K"] * wl_size["M"] + 64 * wl_size["K"] * wl_size["N"] + 256 * wl_size["N"] * wl_size["M"],
            "delta_local_C_out": 0,
            "transpose_C": transpose_C,
            # DR configuration for D
            "tempLoop0_D": wl_size["N"],
            "tempLoop1_D": wl_size["N2"],
            "DMAtempStride0_D_in": 64,
            "DMAtempStride1_D_in": 64 * wl_size["N"],
            "DMAspatialStride1_D_in": 8,
            "tempStride0_D_in": 8,
            "tempStride1_D_in": 64 * wl_size["N"],
            "spatialStride1_D_in": 8 * wl_size["N"],
            "tempStride0_D_out": 64,
            "tempStride1_D_out": 64 * wl_size["N"],
            "spatialStride1_D_out": 8,
            "delta_local_D_in": 64 * wl_size["N"] * wl_size["M"],
            "delta_local_D_out": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["N"] * wl_size["N2"],
            "transpose_D": 0,
            # configuration for E
            "tempStride0_GEMM_E_out": 256,
            "tempStride1_GEMM_E_out": 256 * wl_size["N2"],
            "spatialStride1_GEMM_E_out": 32,
            "delta_local_E_in": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["N"] * wl_size["N2"] * 2,
        }

    if sw_exp_name == "snax-wide-gemm-wide-simd-dr":
        run_time_cfg = {
            # input strides of data reshuffle
            "tempStride0_C_in": 64,
            "tempStride1_C_in": 64 * wl_size["M"],
            "spatialStride1_C_in": 8,
            # output strides of data reshuffle
            "tempStride0_C_out": 64,
            "tempStride1_C_out": 64 * wl_size["M"],
            "spatialStride1_C_out": 8,
            "delta_local_C_in": 64 * wl_size["K"] * wl_size["M"] * 2 + 64 * wl_size["K"] * wl_size["N"] * 2 + 256 * wl_size["N"] * wl_size["M"],
            "delta_local_C_out": 0,
            "transpose_C": transpose_C,
            # DR configuration for D
            "tempLoop0_D": wl_size["M"],
            "tempLoop1_D": wl_size["M2"],
            "DMAtempStride0_D_in": 64,
            "DMAtempStride1_D_in": 64 * wl_size["M"],
            "DMAspatialStride1_D_in": 8,
            "tempStride0_D_in": 8,
            "tempStride1_D_in": 64 * wl_size["M"],
            "spatialStride1_D_in": 8 * wl_size["M"],
            "tempStride0_D_out": 64,
            "tempStride1_D_out": 64 * wl_size["M"],
            "spatialStride1_D_out": 8,
            "delta_local_D_in": 64 * wl_size["N"] * wl_size["M"],
            "delta_local_D_out": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["M"] * wl_size["M2"],
            "transpose_D": 0,
            # configuration for E
            "tempStride0_GEMM_E_out": 256,
            "tempStride1_GEMM_E_out": 256 * wl_size["N"],
            "spatialStride1_GEMM_E_out": 32,
            "delta_local_E_in": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["M"] * wl_size["M2"] * 2,
        }

    if sw_exp_name == "snax-wide-gemm-wide-simd-dr-c-left":
        run_time_cfg = {
            # input strides of data reshuffle
            "tempStride0_C_in": 64,
            "tempStride1_C_in": 64 * wl_size["M"],
            "spatialStride1_C_in": 8,
            # output strides of data reshuffle
            "tempStride0_C_out": 64,
            "tempStride1_C_out": 64 * wl_size["M"],
            "spatialStride1_C_out": 8,
            "delta_local_C_in": 64 * wl_size["K"] * wl_size["M"] * 2 + 64 * wl_size["K"] * wl_size["N"] * 2 + 256 * wl_size["N"] * wl_size["M"],
            "delta_local_C_out": 0,
            "transpose_C": transpose_C,
            # DR configuration for D
            "tempLoop0_D": wl_size["N"],
            "tempLoop1_D": wl_size["N2"],
            "DMAtempStride0_D_in": 64,
            "DMAtempStride1_D_in": 64 * wl_size["N"],
            "DMAspatialStride1_D_in": 8,
            "tempStride0_D_in": 8,
            "tempStride1_D_in": 64 * wl_size["N"],
            "spatialStride1_D_in": 8 * wl_size["N"],
            "tempStride0_D_out": 64,
            "tempStride1_D_out": 64 * wl_size["N"],
            "spatialStride1_D_out": 8,
            "delta_local_D_in": 64 * wl_size["N"] * wl_size["M"],
            "delta_local_D_out": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["N"] * wl_size["N2"],
            "transpose_D": 0,
            # configuration for E
            "tempStride0_GEMM_E_out": 256,
            "tempStride1_GEMM_E_out": 256 * wl_size["N2"],
            "spatialStride1_GEMM_E_out": 32,
            "delta_local_E_in": 64 * wl_size["N"] * wl_size["M"] + 64 * wl_size["N"] * wl_size["N2"] * 2,
        }

    if sw_exp_name == "snax-narrow-gemm-narrow-simd-dr" or sw_exp_name == "snax-narrow-gemm-narrow-simd-dr-c-left":
        run_time_cfg.update(common_dir)
        run_time_cfg.update(run_time_cfg_common_narrow_narrow)
    if sw_exp_name == "snax-wide-gemm-wide-simd-dr" or sw_exp_name == "snax-wide-gemm-wide-simd-dr-c-left":
        run_time_cfg.update(common_dir)
        run_time_cfg.update(run_time_cfg_common_wide_wide)

    # Write the run-time config to a hjson file
    json_filename = f"sw/apps/{sw_exp_name}/data/params.hjson"
    with open(json_filename, 'w') as f:
        hjson.dump(run_time_cfg, f)
        
    # Build the software
    cmd = f"rm sw/apps/{sw_exp_name}/build/{sw_exp_name}.elf ; make DEBUG=ON sw > sw_build.log"
    os.system(cmd)

def run_sw_exp(sw_exp_name, wl_size):
    # build the software
    build_sw(sw_exp_name, wl_size)
    # Run the software experiment
    tag = ''.join([f'{key}_{value}_' for key, value in wl_size.items()])
    res_file = f"sw/apps/{sw_exp_name}/data/res_{tag}.txt"
    cmd = f"bin/snitch_cluster.vlt sw/apps/{sw_exp_name}/build/{sw_exp_name}.elf > {res_file}"
    os.system(cmd)

def parse_traces(dr_core_id, dr_csr):
    # Parse the traces
    cmd = "make traces"
    os.system(cmd)
    dr_cycle_num = []
    trace_filename = f"logs/trace_hart_0000000{dr_core_id}.txt"

    # Parse the traces
    dr_reg = ""
    find_dr_num = False
    with open(trace_filename, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if find_dr_num:
                if dr_reg in line:
                    cycle = re.findall(r'\b\d+\b', line)[-1]
                    dr_cycle_num.append(cycle)
                    find_dr_num = False
            else:
                if dr_csr in line:
                    find_dr_num = True
                    dr_reg = line.split()[-3][:-1]
    return dr_cycle_num

def parse_results(sw_exp_name, wl_size, parse_dr_results = False, parse_dr_idx = 1, parse_dr_csr = "unknown_3d2"):
    res_dir = {
        "sw_exp_name": sw_exp_name,
        "wl_size": wl_size,
        "CSR_cycle": 0,
        "DR_CSR_cycle": 0,
        "GEMM_CSR_cycle": 0,
        "SIMD_CSR_cycle": 0,
        "WIDE_GEMM_STREAMER_CSR_cycle": 0,
        "NARROW_GEMM_STREAMER_CSR_cycle": 0,
        "SIMD_STREAMER_CSR_cycle": 0,
        "GeMM_cycle": [],
        "SIMD_cycle": [],
        "DR_cycle": [],  
        "SN_R_cycle": [],
        "Utilization_GEMM": 0,
        "Utilization_SIMD": 0,
        "Utilization_DR": 0,
    }

    # Parse the results
    tag = ''.join([f'{key}_{value}_' for key, value in wl_size.items()])
    res_file = f"sw/apps/{sw_exp_name}/data/res_{tag}.txt"
    with open(res_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if "GEMM cycles:" in line:
                res_dir["GeMM_cycle"].append(re.findall(r'\d+', line))
            if "SIMD cycles:" in line:
                res_dir["SIMD_cycle"].append(re.findall(r'\d+', line))
            if "Reshuffle A cycles:" in line:
                res_dir["SN_R_cycle"].append(re.findall(r'\d+', line))
            if "Reshuffle B cycles:" in line:
                res_dir["SN_R_cycle"].append(re.findall(r'\d+', line))

    DR_CSR_cycle = 11
    SIMD_CSR_cycle = 4
    GeMM_CSR_cycle = 4
    WIDE_GEMM_STREAMER_CSR_cycle = 12
    NARROW_GEMM_STREAMER_CSR_cycle = 15
    SIMD_STREAMER_CSR_cycle = 8

    '''
    csr setting numbers for exp2
    '''
    if sw_exp_name == "snax-streamer-gemm-data-layout":
        res_dir["NARROW_GEMM_STREAMER_CSR_cycle"] = NARROW_GEMM_STREAMER_CSR_cycle * 1
        res_dir["GEMM_CSR_cycle"] = GeMM_CSR_cycle

    if sw_exp_name == "snax-wide-gemm-data-reshuffler":
        res_dir["WIDE_GEMM_STREAMER_CSR_cycle"] = WIDE_GEMM_STREAMER_CSR_cycle * 1
        res_dir["GEMM_CSR_cycle"] = GeMM_CSR_cycle
        res_dir["DR_CSR_cycle"] = DR_CSR_cycle * 2
    
    if sw_exp_name == "snax-wide-gemm-snitch-reshuffler":
        res_dir["WIDE_GEMM_STREAMER_CSR_cycle"] = WIDE_GEMM_STREAMER_CSR_cycle * 1
        res_dir["GEMM_CSR_cycle"] = GeMM_CSR_cycle

    '''
    csr setting numbers for exp3
    '''
    if sw_exp_name == "snax-narrow-gemm-narrow-simd-dr":
        res_dir["NARROW_GEMM_STREAMER_CSR_cycle"] = NARROW_GEMM_STREAMER_CSR_cycle * 2
        res_dir["GEMM_CSR_cycle"] = GeMM_CSR_cycle * 2
        res_dir["SIMD_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
        res_dir["SIMD_STREAMER_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
        res_dir["DR_CSR_cycle"] = DR_CSR_cycle * 1

    if sw_exp_name == "snax-narrow-gemm-narrow-simd-dr-c-left":
        res_dir["NARROW_GEMM_STREAMER_CSR_cycle"] = NARROW_GEMM_STREAMER_CSR_cycle * 2
        res_dir["GEMM_CSR_cycle"] = GeMM_CSR_cycle * 2
        res_dir["SIMD_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
        res_dir["SIMD_STREAMER_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
    
    if sw_exp_name == "snax-wide-gemm-wide-simd-dr":
        res_dir["WIDE_GEMM_STREAMER_CSR_cycle"] = WIDE_GEMM_STREAMER_CSR_cycle * 2
        res_dir["GEMM_CSR_cycle"] = GeMM_CSR_cycle * 2
        res_dir["SIMD_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
        res_dir["SIMD_STREAMER_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
        res_dir["DR_CSR_cycle"] = DR_CSR_cycle * 4

    if sw_exp_name == "snax-wide-gemm-wide-simd-dr-c-left":
        res_dir["WIDE_GEMM_STREAMER_CSR_cycle"] = WIDE_GEMM_STREAMER_CSR_cycle * 2
        res_dir["GEMM_CSR_cycle"] = GeMM_CSR_cycle * 2
        res_dir["SIMD_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
        res_dir["SIMD_STREAMER_CSR_cycle"] = SIMD_STREAMER_CSR_cycle * 1
        res_dir["DR_CSR_cycle"] = DR_CSR_cycle * 3

    csr_sum = 0

    for key, value in res_dir.items():
        if "CSR" in key and key != "CSR_cycle":
            if type(value) == list:
                csr_sum += sum(value)
            else:
                csr_sum += (value)

    res_dir["CSR_cycle"] = csr_sum

    # Calculate the utilization
    if sw_exp_name == "snax-streamer-gemm-data-layout":
        if res_dir["GEMM_CSR_cycle"] != []:
            res_dir["Utilization_GEMM"] = wl_size["M"] * wl_size["N"] * wl_size["K"] / int(res_dir["GeMM_cycle"][0][0])
        else:
            res_dir["Utilization_GEMM"] = 0
            
    # if res_dir["SIMD_CSR_cycle"] != []:
    #     res_dir["Utilization_SIMD"] = wl_size["M"] * wl_size["N"] / int(res_dir["SIMD_cycle"][0][0])
    # else:
    #     res_dir["Utilization_SIMD"] = 0
    
    # Parse the DR results from traces (can not be parsed from the res.txt file)            
    if parse_dr_results:
        res_dir["DR_cycle"] = parse_traces(parse_dr_idx, parse_dr_csr)
    return res_dir

def write_csv(filename, res_list):
    # Define the field names
    if len(res_list) == 0:
        field_names = "empty_list.csv"
    else:
        field_names = res_list[0].keys()

    # Specify the CSV file path
    csv_file_path = filename

    # Open the CSV file in write mode
    with open(csv_file_path, mode='w', newline='') as file:
        # Create a CSV writer object
        writer = csv.DictWriter(file, fieldnames=field_names)

        # Write the header
        writer.writeheader()

        # Write each row of data
        for row in res_list:
            writer.writerow(row)

def build_wide_gemm_snitch_reshuffler():
    arch_name = "snax-wide-gemm"
    build_hw(arch_name)

def build_wide_gemm_data_reshuffler():
    arch_name = "snax-wide-gemm-data-reshuffler"
    build_hw(arch_name)

def build_streamer_gemm():
    arch_name = "snax-streamer-gemm"
    build_hw(arch_name)

def build_narrow_gemm_narrow_simd_dr():
    arch_name = "snax-narrow-gemm-narrow-simd-data-reshuffler"
    build_hw(arch_name)

def build_wide_gemm_wide_simd_dr():
    arch_name = "snax-wide-gemm-wide-simd-data-reshuffler"
    build_hw(arch_name)


def build_data_reshuffler():
    arch_name = "snax-data-reshuffler"
    build_hw(arch_name)

def memory_size(M, K, N):
    delta = 8
    return math.ceil((M * K + K * N + M * N * 4 + delta) / 1024)

def comp_tiled_size(matrix_size_m, matrix_size_k, matrix_size_n):
    # print(math.ceil(matrix_size_m / 8) , math.ceil(matrix_size_k / 8) , math.ceil(matrix_size_n / 8))
    # print(math.ceil(matrix_size_m / 8) * math.ceil(matrix_size_k / 8) * math.ceil(matrix_size_n / 8))
    return { "M": math.ceil(matrix_size_m / 8), "K": math.ceil(matrix_size_k / 8), "N": math.ceil(matrix_size_n / 8) }

def wide_gemm_data_reshuffler_mem_size(wl_size):
    memory_size = wl_size["K"] * wl_size["M"] * 2 + wl_size["K"] * wl_size["N"] * 2 + 4 * wl_size["N"] * wl_size["M"]
    return memory_size / 1024
