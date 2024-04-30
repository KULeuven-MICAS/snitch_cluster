package streamer

import chisel3._
import org.scalatest.flatspec.AnyFlatSpec
import chiseltest._
import scala.math.BigInt
import org.scalatest.matchers.should.Matchers
import org.scalatest.Tag

// manual test for spatial address generation unit
// TODO: automated random configuration test and automated results check
class SpatialAddrGenUnitTest
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  "DUT" should "pass" in {
    test(new SpatialAddrGenUnit(SpatialAddrGenUnitParams())).withAnnotations(
      Seq(WriteVcdAnnotation)
    ) { dut =>
      dut.clock.step(5)
      // random config generation
      val strides =
        Seq.fill(SpatialAddrGenUnitTestParameters.loopDim)(
          (
            scala.util.Random.nextInt(10).U
          )
        )

      // sending these configuration to the dut
      for (i <- 0 until SpatialAddrGenUnitTestParameters.loopDim) {
        val us = strides(i)
        dut.io.strides_i(i).poke(us)
      }
      dut.io.ptr_i.poke(16.U)
      dut.io.valid_i.poke(1.B)

      dut.clock.step(5)

    }
  }
}
