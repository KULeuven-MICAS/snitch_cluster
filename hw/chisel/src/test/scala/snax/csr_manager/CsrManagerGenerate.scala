package snax.csr_manager

import chisel3._
import org.scalatest.flatspec.AnyFlatSpec
import chiseltest._

class CsrManagerTopGenerate extends AnyFlatSpec {

  emitVerilog(
    new CsrManager(
      CsrManagerTestParameters.csrNum,
      CsrManagerTestParameters.csrAddrWidth
    ),
    Array("--target-dir", "generated/csr_manager")
  )

}
