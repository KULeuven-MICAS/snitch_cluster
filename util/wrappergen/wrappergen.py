#!/usr/bin/env python3
# -------------------------------------------------------
# This wrappergen is specific to configure the templates
# and wrappers towards the SNAX shell
# -------------------------------------------------------
from mako.lookup import TemplateLookup
from mako.template import Template
from jsonref import JsonRef
import hjson
import argparse
import os


# Extract json file
def get_config(cfg_path: str):
    with open(cfg_path, "r") as jsonf:
        srcfull = jsonf.read()

    # Format hjson file
    cfg = hjson.loads(srcfull, use_decimal=True)
    cfg = JsonRef.replace_refs(cfg)
    return cfg


# Read template
def get_template(tpl_path: str) -> Template:
    dir_name = os.path.dirname(tpl_path)
    file_name = os.path.basename(tpl_path)
    tpl_list = TemplateLookup(directories=[dir_name], output_encoding="utf-8")
    tpl = tpl_list.get_template(file_name)
    return tpl


# Generate file
def gen_file(cfg, tpl, target_path: str, file_name: str) -> None:
    # Check if path exists first if no, create directory
    if not (os.path.exists(target_path)):
        os.makedirs(target_path)
    
    # Writing file
    file_path = target_path + file_name
    with open(file_path, "w") as f:
        f.write(str(tpl.render_unicode(cfg=cfg)))
    return


# Main function run and parsing
def main():
    # Parse all arguments
    parser = argparse.ArgumentParser(
        description="Wrapper generator for any file. \
            Inputs are simply the template and configuration files."
    )
    parser.add_argument(
        "--cfg_path",
        type=str,
        default="./",
        help="Points to the configuration file path",
    )
    parser.add_argument(
        "--tpl_path", type=str, default="./", help="Points to the streamer template file path"
    )
    parser.add_argument(
        "--streamer_chisel_path", type=str, default="./", help="Points to the streamer chisel source path"
    )
    parser.add_argument(
        "--gen_path", type=str, default="./", help="Points to the output directory"
    )

    # Get the list of parsing
    args = parser.parse_args()

    # Grab config and template then generate the combination of two
    cfg = get_config(args.cfg_path)

    # First grab all accelerator configurations
    num_cores = len(cfg['cluster']['hives'][0]['cores'])
    cfg_cores = cfg['cluster']['hives'][0]['cores']

    # Cycle through each core and check if they have accelerator configs
    # Then dump them into a dictionary set
    num_core_w_acc = 0
    acc_cfgs = []
    acc_streamer_cfgs = []

    for i in range(len(cfg_cores)):
        if('snax_acc_cfg' in cfg_cores[i]):
            num_core_w_acc += 1
            acc_cfgs.append(cfg_cores[i]['snax_acc_cfg'])
            acc_streamer_cfgs.append(cfg_cores[i]['snax_acc_cfg']['snax_streamer_cfg'])
    
    # Placing the TCDM components again into compiled streamer configurations
    for i in range(len(acc_streamer_cfgs)):
        acc_streamer_cfgs[i].update({"tcdmDataWidth":cfg['cluster']['data_width']})
        acc_streamer_cfgs[i].update({"tcdmDmaDataWidth":cfg['cluster']['dma_data_width']})
        tcdm_depth = cfg['cluster']['tcdm']['size'] * 1024 // cfg['cluster']['tcdm']['banks'] // 8
        acc_streamer_cfgs[i].update({"tcdmDepth":tcdm_depth})
        acc_streamer_cfgs[i].update({"numBanks":cfg['cluster']['tcdm']['banks']})
        acc_streamer_cfgs[i].update({"tagName":acc_cfgs[i]['snax_acc_name']})
        print(acc_streamer_cfgs[i])


    

    # Generate template out of given configurations
    # TODO: Make me a generation for the necessary files!
    for i in range(len(acc_cfgs)):

        # Generate the parameter files for chisel streamer generation
        target_path = args.streamer_chisel_path
        file_name = "StreamParamGen.scala"
        tpl_scala_param_file = args.tpl_path + "stream_param_gen.scala.tpl"
        tpl_scala_param = get_template(tpl_scala_param_file)
        gen_file(cfg=acc_streamer_cfgs[i], tpl=tpl_scala_param, target_path=target_path, file_name=file_name)

        # This first one generates the streamer wrappers
        target_path = args.gen_path + acc_cfgs[i]['snax_acc_name'] + '/'
        file_name = acc_cfgs[i]['snax_acc_name'] + "_streamer_wrapper.sv"
        tpl_streamer_wrapper_file = args.tpl_path + "snax_streamer_wrapper.sv.tpl"
        tpl_streamer_wrapper = get_template(tpl_streamer_wrapper_file)
        gen_file(cfg=acc_streamer_cfgs[i], tpl=tpl_streamer_wrapper, target_path=target_path, file_name=file_name)

        # CSR manager scala parameter generation
        target_path = args.streamer_chisel_path
        file_name = "CsrManParamGen.scala"
        tpl_scala_param_file = args.tpl_path + "csrman_param_gen.scala.tpl"
        tpl_scala_param = get_template(tpl_scala_param_file)
        gen_file(cfg=acc_streamer_cfgs[i], tpl=tpl_scala_param, target_path=target_path, file_name=file_name)

if __name__ == "__main__":
    main()