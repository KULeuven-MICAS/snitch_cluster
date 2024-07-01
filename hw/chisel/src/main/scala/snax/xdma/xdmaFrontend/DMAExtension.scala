package snax.xdma.xdmaFrontend

import chisel3._
import chisel3.util._

import snax.utils._
import snax.xdma.commonCells._
import snax.xdma.designParams._

/** The base module for the DMA Extension
  * All the DMA Extensions should be extended from the following module
  * After extension, the following step is necessary
  * 1) override either @compressionRatio (if your output data beat is less than input) \
  *                 or @decompressionRatio (if your output data beat is more than input)
  * 2) override        @extName to give a name to the option
  * 3) Connect ext_data_i to your module's datapath input: ext_data_i <> userDefinedInput
  * 4) Connect ext_data_o to your module's datapath output: ext_data_o <> userDefinedOutput
  * 5) Connect CSR to your module <> userDefinedCSR := ext_csr_i
  * 6) Connect Start signal: userDefinedStart := ext_start_i. The start signal is used to inform extension a new stream is coming
  * 7) Connect Busy signal: ext_busy_o := userDefinedBusy. As the extension does not know the length of the stream, the extension should pull down the signal when ther is data inside the extension (under processing)
  */

class DMAExtension(param: DMAExtensionParam) extends Module with RequireAsyncReset {
  require(param.dataWidth > 0)
  require(param.userCsrNum >= 0)

  val compressionRatio =
    1 // If this signal is not 1, it indecate that the length of input is **compressionRatio** times as large as output
  val decompressionRatio =
    1 // If this signal is not 1, it indecate that the length of output is **DecompressionRatio** times as large as input
  require((compressionRatio == 1) ^ (decompressionRatio == 1)) // Only one of them can be non - one
  require(compressionRatio > 0 && decompressionRatio > 1) // Neither of them can be zero
  val extName = "name_overrides" // The name that will be included in the synthesized module name

  val io = new Bundle {
    val csr_i = Input(Vec(param.userCsrNum + 1, UInt(32.W))) // CSR with the first one always byPass signal
    val start_i = Input(Bool()) // The start signal triggers the local register to buffer the csr information
    val data_i = Flipped(Decoupled(UInt(param.dataWidth.W)))
    val data_o = Decoupled(UInt(param.dataWidth.W))
    val busy_o = Output(Bool())
  }

  private val bypass = io.csr_i.head(0)
  private val bypass_data = Wire(Decoupled(UInt(param.dataWidth.W)))
  val ext_data_i = Wire(Decoupled(UInt(param.dataWidth.W)))
  val ext_data_o = Wire(Decoupled(UInt(param.dataWidth.W)))
  val ext_csr_i = io.csr_i.tail
  val ext_start_i = io.start_i
  val ext_busy_o = Wire(Bool())
  io.busy_o := ext_busy_o

  // Structure to bypass extension: Demux
  private val InputDemux = Module(new DemuxDecoupled(UInt(param.dataWidth.W), numOutput = 2))
  InputDemux.io.sel := bypass
  InputDemux.io.in <> io.data_i
  // When bypass is 0, io.out(0) is connected with extension's input
  InputDemux.io.out(0) <> ext_data_i
  // When bypass is 1, io.out(1) is connected to bypass signal
  InputDemux.io.out(1) <> bypass_data

  // Structure to bypass extension: Mux
  private val OutputMux = Module(new MuxDecoupled(UInt(param.dataWidth.W), numInput = 2))
  OutputMux.io.sel := bypass
  OutputMux.io.out <> io.data_o
  // When bypass is 0, io.in(0) is connected with extension's output
  OutputMux.io.in(0) <> ext_data_o
  // When bypass is 1, io.in(1) is connected to bypass signal
  OutputMux.io.in(1) <> bypass_data
}
