package snax.csr_manager

import chisel3._
import org.scalatest.flatspec.AnyFlatSpec
import chiseltest._
import scala.math.BigInt
import org.scalatest.matchers.should.Matchers
import org.scalatest.Tag
import scala.util.control.Breaks._

class CsrManagerWithReadOnlyTest
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers
    with HasCsrManagerTest {

  "DUT" should "pass" in {
    test(
      new CsrManagerWithReadOnly(
        CsrManagerWithReadOnlyTestParameters.csrNum,
        CsrManagerWithReadOnlyTestParameters.csrNumReadOnly,
        CsrManagerWithReadOnlyTestParameters.csrAddrWidth
      )
    ).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      base_csr_manager_test(dut)

      // ***********************************************************************
      // test read only csr
      // ***********************************************************************

      // drive the read only csr
      dut.io.read_only_csr(0).poke(1.U)
      dut.io.read_only_csr(1).poke(2.U)

      // check the read value
      assert(
        1 == read_csr(
          dut,
          0 + CsrManagerWithReadOnlyTestParameters.csrNum
        ).litValue
      )
      assert(
        2 == read_csr(
          dut,
          1 + CsrManagerWithReadOnlyTestParameters.csrNum
        ).litValue
      )

      // drive the read only csr
      dut.io.read_only_csr(0).poke(3.U)
      dut.io.read_only_csr(1).poke(4.U)

      // check the read value
      assert(
        3 == read_csr(
          dut,
          0 + CsrManagerWithReadOnlyTestParameters.csrNum
        ).litValue
      )
      assert(
        4 == read_csr(
          dut,
          1 + CsrManagerWithReadOnlyTestParameters.csrNum
        ).litValue
      )

    }
  }
}
