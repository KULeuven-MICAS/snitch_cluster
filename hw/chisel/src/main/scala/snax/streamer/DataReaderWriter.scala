package snax.streamer

import snax.utils._

import chisel3._
import chisel3.util._

class DataReaderWriterIO(
    params: DataMoverParams
) extends Bundle {

  /* Signals to and from TCDM */
  // tcdm request ports
  val tcdm_req = (Vec(
    params.tcdmPortsNum,
    Decoupled(new TcdmReq(params.addrWidth, params.tcdmDataWidth))
  ))

  // tcdm response
  val tcdm_rsp =
    Vec(params.tcdmPortsNum, Flipped(Valid(new TcdmRsp(params.tcdmDataWidth))))

  /* Signals to go 2 temporal address generation units, one for reader and one for writer. */
  // signals for write request address generation
  val ptr_agu_i = Vec(2, Flipped(Decoupled(UInt(params.addrWidth.W))))

  val spatialStrides_csr_i = Vec(
    2,
    Flipped(
      Decoupled(Vec(params.spatialDim, UInt(params.addrWidth.W)))
    )
  )
  // input signal from the temporal address generation unit to indicate
  // all the temporal addresses have been produced
  val addr_gen_done = Vec(2, Input(Bool()))

  // output signal to indicate the data movement process is done
  val data_movement_done = Vec(2, Output(Bool()))

  /* Signals to and from accelerator X side */
  // output data -> going to the fifo
  val data_fifo_o = Decoupled(UInt(params.fifoWidth.W))

  // valid data from the queue
  val data_fifo_i = Flipped(Decoupled(UInt(params.fifoWidth.W)))

  assert(
    params.fifoWidth == params.tcdmPortsNum * params.tcdmDataWidth,
    "fifoWidth should match with TCDM datawidth for now!"
  )

}

// the DataReaderWriter class is a module that can both reads and writes data
// It instantiates a DataReader and a DataWriter module, each has its own seperate set of CSR, temporal/spatial address generation unit...
// The reader and writer work in dependetly but share the reqeust ports to TCDM
// To decide whether to read or write, the DataReaderWriter module uses a control signal
// When one of the DataReader or DataWriter needs send request to TCDM (read fifo empty or write fifo not empty), choose the one that needs to send request
// when both DataReader and DataWriter needs to send request, choose the writer first
// When none of them needs to send request, chill a bit
class DataReaderWriter(
    params: DataMoverParams,
    tagName: String = ""
) extends Module
    with RequireAsyncReset {
  override val desiredName = tagName + "DataReaderWriter"

  val io = IO(new DataReaderWriterIO(params))
  io.suggestName("io")

  val data_reader = Module(
    new DataReader(
      params,
      tagName
    )
  )

  val data_writer = Module(
    new DataWriter(
      params,
      tagName
    )
  )

  // select read or write mode
  val isReadMode = WireInit(false.B)
  val writeValid = WireInit(false.B)

  // when both reader and writer need to send request, choose the writer
  writeValid := data_writer.io.tcdm_req.map(_.valid).reduce(_ || _)
  when(writeValid) {
    isReadMode := false.B
  }.otherwise {
    isReadMode := true.B
  }

  when(isReadMode) {
    data_reader.io.tcdm_req <> io.tcdm_req
    data_writer.io.tcdm_req.foreach(_.ready := false.B)
  }.otherwise {
    data_writer.io.tcdm_req <> io.tcdm_req
    data_reader.io.tcdm_req.foreach(_.ready := false.B)
  }

  /* connect signals for reader */
  data_reader.io.tcdm_rsp <> io.tcdm_rsp

  data_reader.io.ptr_agu_i <> io.ptr_agu_i(0)
  data_reader.io.spatialStrides_csr_i <> io.spatialStrides_csr_i(0)
  data_reader.io.addr_gen_done <> io.addr_gen_done(0)
  data_reader.io.data_movement_done <> io.data_movement_done(0)

  data_reader.io.data_fifo_o <> io.data_fifo_o

  /* connect signals for writer */

  data_writer.io.ptr_agu_i <> io.ptr_agu_i(1)
  data_writer.io.spatialStrides_csr_i <> io.spatialStrides_csr_i(1)
  data_writer.io.addr_gen_done <> io.addr_gen_done(1)
  data_writer.io.data_movement_done <> io.data_movement_done(1)

  data_writer.io.data_fifo_i <> io.data_fifo_i
}

// Scala main function for generating system verilog file for the DataReaderWriter module
object DataReaderWriter {
  val dataMover = DataMoverParams(
    tcdmPortsNum = 8,
    spatialBounds = Seq(8, 8),
    fifoWidth = 512,
    elementWidth = 8,
    spatialDim = 2
  )
  def main(args: Array[String]): Unit = {
    val outPath = args.headOption.getOrElse("generated/datamover")
    emitVerilog(
      new DataReaderWriter(dataMover),
      Array("--target-dir", outPath)
    )
  }
}
