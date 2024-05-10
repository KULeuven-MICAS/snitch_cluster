package snax.csr_manager

import chisel3._
import org.scalatest.flatspec.AnyFlatSpec
import chiseltest._

class CsrManagerWithReadOnlyGenerate extends AnyFlatSpec {

  emitVerilog(
    new CsrManagerWithReadOnly(
      csrNum = CsrManagerWithReadOnlyTestParameters.csrNum,
      csrNumReadOnly = CsrManagerWithReadOnlyTestParameters.csrNumReadOnly,
      csrAddrWidth = CsrManagerWithReadOnlyTestParameters.csrAddrWidth,
      csrModuleTagName = "test"
    ),
    Array("--target-dir", "generated/csr_manager")
  )

}
