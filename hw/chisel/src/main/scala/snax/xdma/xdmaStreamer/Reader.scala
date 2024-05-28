package snax.xdma.xdmaStreamer

import chisel3._
import chisel3.util._

import snax.utils._
import snax.xdma.commonCells._

// The reader takes the address from the AGU, offer to requestor, and responser collect the data from TCDM and pushed to FIFO packer to recombine into 512 bit data

class ReaderWriterParam(
    dimension: Int = 3,
    tcdmAddressWidth: Int = 17,
    tcdmDataWidth: Int = 64,
    numChannel: Int = 8,
    addressBufferDepth: Int = 8,
    dataBufferDepth: Int = 8
) {
    val agu_param = AddressGenUnitParam(
      dimension = dimension,
      addressWidth = tcdmAddressWidth,
      spatialUnrollingFactor = numChannel,
      outputBufferDepth = addressBufferDepth
    )

    val tcdm_param = tcdmParam(
      addrWidth = tcdmAddressWidth,
      dataWidth = tcdmDataWidth,
      numChannel = numChannel
    )

    // Data buffer's depth
    val bufferDepth = dataBufferDepth
}

class Reader(param: ReaderWriterParam) extends Module {
    val io = IO(new Bundle {
        val cfg = Input(new AddressGenUnitCfgIO(param.agu_param))
        val tcdm_req = Vec(
          param.tcdm_param.numChannel,
          Decoupled(
            new TcdmReq(
              addrWidth = param.tcdm_param.addrWidth,
              tcdmDataWidth = param.tcdm_param.dataWidth
            )
          )
        )
        val tcdm_rsp = Vec(
          param.tcdm_param.numChannel,
          Flipped(Valid(new TcdmRsp(tcdmDataWidth = param.tcdm_param.dataWidth)))
        )
        val data = Decoupled(UInt((param.tcdm_param.dataWidth * param.tcdm_param.numChannel).W))
        // The signal trigger the start of Address Generator. The non-empty of address generator will cause data requestor to read the data
        val start = Input(Bool())
        // The module is busy if addressgen is busy or fifo in addressgen is not empty
        val busy = Output(Bool())
        // The reader's buffer is empty
        val bufferEmpty = Output(Bool())

    })

    // Address Generator
    val addressgen = Module(new AddressGenUnit(param.agu_param))

    // Requestors to send address to TCDM
    val requestors = Module(
      new DataRequestors(
        tcdmDataWidth = param.tcdm_param.dataWidth,
        tcdmAddressWidth = param.tcdm_param.addrWidth,
        numChannel = param.tcdm_param.numChannel,
        isReader = true
      )
    )

    // Responsors to receive the data from TCDM
    val responsers = Module(
      new DataResponsers(
        tcdmDataWidth = param.tcdm_param.dataWidth,
        numChannel = param.tcdm_param.numChannel
      )
    )

    // Output FIFOs to combine the data from the output of responsers
    val dataBuffer = Module(
      new snax.xdma.commonCells.complexQueue(
        inputWidth = param.tcdm_param.dataWidth,
        outputWidth = param.tcdm_param.dataWidth * param.tcdm_param.numChannel,
        depth = param.bufferDepth
      )
    )

    addressgen.io.cfg := io.cfg
    addressgen.io.start := io.start
    requestors.io.in.addr <> addressgen.io.addr
    requestors.io.in.ResponsorReady.get := responsers.io.out.ResponsorReady
    requestors.io.out.tcdm_req <> io.tcdm_req
    responsers.io.tcdm_rsp <> io.tcdm_rsp
    dataBuffer.io.in <> responsers.io.out.data
    dataBuffer.io.out.head <> io.data

    io.busy := addressgen.io.busy | (~addressgen.io.bufferEmpty)

    // The debug signal from the dataBuffer to see if AGU and requestor / responser works correctly: It should be high when valid signal at the combined output is low
    io.bufferEmpty := dataBuffer.io.allEmpty
}

object ReaderPrinter extends App {
    println(getVerilogString(new Reader(new ReaderWriterParam)))
}
