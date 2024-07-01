package snax.xdma.xdmaFrontend

import chisel3._
import chisel3.util._

import snax.xdma.designParams._

import snax.xdma.commonCells._

object DMACtrlTester extends App {
  emitVerilog(
    new DMACtrl(
      readerparam = new ReaderWriterDataPathParam(new ReaderWriterParam, Seq()),
      writerparam = new ReaderWriterDataPathParam(new ReaderWriterParam, Seq())
    ),
    Array("--target-dir", "generated")
  )
  CustomExport.output.emitCHIRRTLFile(
    new DMACtrl(
      readerparam = new ReaderWriterDataPathParam(new ReaderWriterParam, Seq()),
      writerparam = new ReaderWriterDataPathParam(new ReaderWriterParam, Seq())
    ),
    path = "generated"
  )
}
