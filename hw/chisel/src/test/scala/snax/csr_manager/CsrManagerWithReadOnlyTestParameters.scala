package snax.csr_manager

import chisel3._
import chisel3.util._

object CsrManagerWithReadOnlyTestParameters {
  def csrNum = 10
  def csrNumReadOnly = 2
  def csrAddrWidth = 32
  def csrModuleTagName = "Test"
}
