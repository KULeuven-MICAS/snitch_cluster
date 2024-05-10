package snax.csr_manager

import snax.utils._

import chisel3._
import chisel3.util._

class CsrManagerWithReadOnlyIO(
    csrNum: Int,
    csrNumReadOnly: Int,
    csrAddrWidth: Int
) extends CsrManagerIO(csrNum, csrAddrWidth) {

  val read_only_csr = Input(Vec(csrNumReadOnly, UInt(csrAddrWidth.W)))

}

class CsrManagerWithReadOnly(
    csrNum: Int,
    csrNumReadOnly: Int,
    csrAddrWidth: Int,
    csrModuleTagName: String = ""
) extends CsrManager(csrNum, csrAddrWidth, csrModuleTagName) {
  override val desiredName = csrModuleTagName + "CsrManagerWithReadOnly"

  override lazy val io = IO(
    new CsrManagerWithReadOnlyIO(csrNum, csrNumReadOnly, csrAddrWidth)
  )

  override def address_range_assert() = {
    when(io.csr_config_in.req.valid) {
      when(io.csr_config_in.req.bits.write === 1.B) {
        assert(
          io.csr_config_in.req.bits.addr < csrNum.U,
          "csr write address overflow!"
        )
      }.otherwise {
        assert(
          0.U <= io.csr_config_in.req.bits.addr && (io.csr_config_in.req.bits.addr < csrNum.U + csrNumReadOnly.U),
          "csr read address overflow!"
        )
      }
    }
  }

  when(read_csr) {
    when(io.csr_config_in.req.bits.addr < csrNum.U) {
      io.csr_config_in.rsp.bits.data := csr(io.csr_config_in.req.bits.addr)
    }.otherwise {
      io.csr_config_in.rsp.bits.data := io.read_only_csr(
        io.csr_config_in.req.bits.addr - csrNum.U
      )
    }
    io.csr_config_in.rsp.valid := 1.B
  }.elsewhen(read_csr_busy) {
    io.csr_config_in.rsp.bits.data := read_csr_buffer
    io.csr_config_in.rsp.valid := 1.B
  }.otherwise {
    io.csr_config_in.rsp.valid := 0.B
    io.csr_config_in.rsp.bits.data := 0.U
  }
  
}
