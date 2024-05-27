package snax.xdma.xdmaStreamer

import chisel3._
import chisel3.util._

import snax.utils._
import snax.xdma.commonCells._

class Writer(param: ReaderWriterParam) extends Module {
    val io = IO(new Bundle {
        val cfg = Input(new AddressGenUnitCfgIO(param.agu_param))
        val tcdm_req = Vec(param.tcdm_param.numChannel, Decoupled(new TcdmReq(addrWidth = param.tcdm_param.addrWidth, tcdmDataWidth = param.tcdm_param.dataWidth)))
        val data = Flipped(Decoupled(UInt((param.tcdm_param.dataWidth * param.tcdm_param.numChannel).W)))
        // The signal trigger the start of Address Generator. The non-empty of address generator will cause data requestor to read the data
        val start = Input(Bool())
        // The module is busy if addressgen is busy or fifo in addressgen is not empty
        val busy = Output(Bool())
        // The reader's buffer is empty
        val bufferEmpty = Output(Bool())
    })

    val addressgen = Module(new AddressGenUnit(param.agu_param))
    // Write Requestors
    // Requestors to send address and data to TCDM
    val requestors = Module(new DataRequestors(
        tcdmDataWidth = param.tcdm_param.dataWidth, 
        tcdmAddressWidth = param.tcdm_param.addrWidth, 
        numChannel = param.tcdm_param.numChannel, 
        isReader = false
    ))

    val dataBuffer = Module(new snax.xdma.commonCells.complexQueue(
        inputWidth = param.tcdm_param.dataWidth * param.tcdm_param.numChannel, 
        outputWidth = param.tcdm_param.dataWidth, 
        depth = param.bufferDepth
    ))

    addressgen.io.cfg := io.cfg
    addressgen.io.start := io.start
    
    requestors.io.in.addr <> addressgen.io.addr
    requestors.io.in.data.get <> dataBuffer.io.out
    requestors.io.out.tcdm_req <> io.tcdm_req


    dataBuffer.io.in.head <> io.data
    io.busy := addressgen.io.busy | (~addressgen.io.bufferEmpty)
    // Debug Signal
    io.bufferEmpty := addressgen.io.bufferEmpty
}

object WriterPrinter extends App {
    println(getVerilogString(new Writer(new ReaderWriterParam)))
}

object WriterEmitter extends App {
    emitVerilog(new Writer(new ReaderWriterParam), Array("--target-dir","generated") )
}