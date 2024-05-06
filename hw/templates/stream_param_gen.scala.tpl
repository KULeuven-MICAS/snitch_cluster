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

/** Parameter definitions fifoWidthReader - FIFO width for the data readers
  * fifoDepthReader - FIFO depth for the data readers fifoWidthWriter - FIFO
  * width for the data writers fifoDepthWriter - FIFO depth for the data writers
  * dataReaderNum - number of data readers dataWriterNum - number of data
  * writers dataReaderTcdmPorts - the number of connections to TCDM ports for
  * each data reader dataWriterTcdmPorts - the number of connections to TCDM
  * ports for each data writer readElementWidth - single data element width for
  * each data reader, useful for generating unrolling addresses
  * writeElementWidth - single data element width for each data writer, useful
  * for generating unrolling addresses tcdmDataWidth - data width for each TCDm
  * port spatialBoundsReader - spatial unrolling factors (your parfor) for
  * each data reader spatialBoundsWriter - spatial unrolling factors (your
  * parfor) for each data writer temporalLoopDim - the dimension of the temporal
  * loop temporalLoopBoundWidth - the register width for storing the temporal
  * loop bound addrWidth - the address width stationarity - accelerator
  * stationarity feature for each data mover (data reader and data writer)
  */

// Streamer parameters
object StreamerParametersGen extends CommonParams {
  def temporalAddrGenUnitParams: TemporalAddrGenUnitParams =
    TemporalAddrGenUnitParams(
      loopDim = ${cfg["temporalAddrGenUnitParams"]["loopDim"]},
      loopBoundWidth = ${cfg["temporalAddrGenUnitParams"]["loopBoundWidth"]},
      addrWidth = ${tcdm_addr_width}
    )
  def fifoReaderParams: Seq[FIFOParams] = Seq(
% for idx in range(0,len(cfg["fifoReaderParams"]["fifoWidth"])):
    FIFOParams(\
${cfg["fifoReaderParams"]["fifoWidth"][idx]},\
${cfg["fifoReaderParams"]["fifoDepth"][idx]})\
${', ' if not loop.last else ''}
% endfor
  )
  def fifoWriterParams: Seq[FIFOParams] = Seq(
% for idx in range(0,len(cfg["fifoWriterParams"]["fifoWidth"])):
    FIFOParams(\
${cfg["fifoWriterParams"]["fifoWidth"][idx]},\
${cfg["fifoWriterParams"]["fifoDepth"][idx]})\
${', ' if not loop.last else ''}
% endfor
  )
  def dataReaderParams: Seq[DataMoverParams] = Seq(
% for idx in range(0,len(cfg["dataReaderParams"]["tcdmPortsNum"])):
    DataMoverParams(
      tcdmPortsNum = ${cfg["dataReaderParams"]["tcdmPortsNum"][idx]},
      spatialBounds = Seq(\
  % for c in cfg["dataReaderParams"]["spatialBounds"][idx]:
${c}${', ' if not loop.last else ''}\
  % endfor
),
      spatialDim = ${cfg["dataReaderParams"]["spatialDim"][idx]},
      elementWidth = ${cfg["dataReaderParams"]["elementWidth"][idx]},
      fifoWidth = fifoReaderParams(${idx}).width
    )${', ' if not loop.last else ''}
% endfor
  )
  def dataWriterParams: Seq[DataMoverParams] = Seq(
 % for idx in range(0,len(cfg["dataWriterParams"]["tcdmPortsNum"])):
    DataMoverParams(
      tcdmPortsNum = ${cfg["dataWriterParams"]["tcdmPortsNum"][idx]},
      spatialBounds = Seq(\
  % for c in cfg["dataWriterParams"]["spatialBounds"][idx]:
${c}${', ' if not loop.last else ''}\
  % endfor
),
      spatialDim = ${cfg["dataWriterParams"]["spatialDim"][idx]},
      elementWidth = ${cfg["dataWriterParams"]["elementWidth"][idx]},
      fifoWidth = fifoWriterParams(${idx}).width
    )${', ' if not loop.last else ''}
% endfor
  )
  def stationarity = Seq(${list_elem('stationarity')})
}

object StreamerTopGen {
  def main(args: Array[String]) : Unit = {
    val outPath = args.headOption.getOrElse("../../../../rtl/.")
    emitVerilog(
      new StreamerTop(
        StreamerParams(
          temporalAddrGenUnitParams =
            StreamerParametersGen.temporalAddrGenUnitParams,
          fifoReaderParams = StreamerParametersGen.fifoReaderParams,
          fifoWriterParams = StreamerParametersGen.fifoWriterParams,
          stationarity = StreamerParametersGen.stationarity,
          dataReaderParams = StreamerParametersGen.dataReaderParams,
          dataWriterParams = StreamerParametersGen.dataWriterParams,
          tagName = "${cfg["tagName"]}"
        )
      ),
      Array("--target-dir", outPath)
    )
  }
}