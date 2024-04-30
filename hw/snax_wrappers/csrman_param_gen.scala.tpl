<%
  import math

  tcdm_data_width = cfg["tcdmDataWidth"]
  tcdm_depth = cfg["tcdmDepth"]
  num_banks = cfg["numBanks"]
  tcdm_size = num_banks * tcdm_depth * (tcdm_data_width/8)
  tcdm_addr_width = math.ceil(math.log2(tcdm_size))
%>
<%def name="list_elem(prop)">\
  % for c in cfg[prop]:
${c}${', ' if not loop.last else ''}\
  % endfor
</%def>\
package streamer

import chisel3._
import chisel3.util._

// Scala main function for generating CsrManager system verilog file
object CsrManagerGen {
  def main(args: Array[String]) : Unit = {
    val outPath = args.headOption.getOrElse("../../../../rtl/.")
    emitVerilog(
      new CsrManager(
        csrManagerTestParameters.csrNum = ,
        csrManagerTestParameters.csrAddrWidth = 32,
        csrModuleTagName = "${cfg["tagName"]}"
      ),
      Array("--target-dir", outPath)
    )
  }
}
