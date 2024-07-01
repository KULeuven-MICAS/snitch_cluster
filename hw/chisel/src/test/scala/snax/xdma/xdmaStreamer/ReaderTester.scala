package snax.xdma.xdmaStreamer

import chisel3._
import chisel3.util._
import chiseltest._
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.flatspec.AnyFlatSpec

import chiseltest.internal.TesterThreadList
import scala.util.Random

import snax.xdma.designParams._

object romGenerator {
  var generatedData = Seq[BigInt]()
  def generateContent(length: Int, width: Int): Unit = {
    // Create a random generator
    val rnd = new Random()

    // Generate a sequence of BigInt numbers
    // Each number is randomly generated within the range [0, 2^width - 1]
    generatedData = Seq.fill(length) {
      BigInt(width, rnd)
    }

  }
}

// object romGenerator {
//     var data = Seq[BigInt]()
//     def intialize(length: Int, Width: Int): Unit = {
//         val ret = collection.mutable.Seq[BigInt]()
//         println(BigInt(Random.nextLong()) % (BigInt(1) << Width))
//         for (i <- 0 until length) {ret.appended((Random.nextLong() % (BigInt(1) << Width)))}
//         data = ret.toSeq
//     }
// }

class testROM(content: Seq[BigInt]) extends Module {
  // require(content.length == 16 * 1024)
  val io = IO(new Bundle {
    val tcdm_req = Vec(8, Flipped(Decoupled(UInt(17.W))))
    val tcdm_rsp = Vec(8, Valid(UInt(64.W)))
  })
  val fake_reg = Wire(Vec(content.length, UInt(64.W)))
  content.zip(fake_reg).foreach { case (a, b) => b := a.U }

  val tcdm_rsp_nodelay = for (i <- 0 until 8) yield {
    io.tcdm_req(i).ready := true.B
    val tcdm_rsp_data = Wire(UInt())
    val tcdm_rsp_valid = Wire(Bool())
    tcdm_rsp_data := fake_reg(io.tcdm_req(i).bits)
    when(io.tcdm_req(i).fire) {
      tcdm_rsp_valid := true.B
    }.otherwise {
      tcdm_rsp_valid := false.B
    }
    (tcdm_rsp_data, tcdm_rsp_valid)
  }
  io.tcdm_rsp.zip(tcdm_rsp_nodelay).foreach {
    case (a, b) => {
      a.valid := RegNext(RegNext(b._2))
      a.bits := RegNext(RegNext(b._1))
    }
  }
}

// object printTestROMVerilog extends App {
//     val content = romGenerator.generateContent(8, 64)
//     // println(content)
//     println(getVerilogString(new testROM(romGenerator.generatedData)))
//     emitVerilog(new testROM(romGenerator.generatedData), Array("--target-dir", "generated/"))
// }

class Reader_Wrapper(param: ReaderWriterParam) extends Module {
  val io = IO(new Bundle {
    val cfg = Input(new AddressGenUnitCfgIO(param.agu_param))
    val data = Decoupled(UInt((param.tcdm_param.dataWidth * param.tcdm_param.numChannel).W))
    // The signal trigger the start of Address Generator. The non-empty of address generator will cause data requestor to read the data
    val start = Input(Bool())
    // The module is busy if addressgen is busy or fifo in addressgen is not empty
    val busy = Output(Bool())
    // The reader's buffer is empty
    val bufferEmpty = Output(Bool())
  })

  val reader = Module(new Reader(param))

  val fake_tcdm = Module(new testROM(romGenerator.generatedData))

  reader.io.cfg := io.cfg
  io.data <> reader.io.data
  reader.io.start := io.start
  io.busy := reader.io.busy
  io.bufferEmpty := reader.io.bufferEmpty

  fake_tcdm.io.tcdm_req.zip(reader.io.tcdm_req).foreach { case (a, b) =>
    a.valid := b.valid
    b.ready := a.ready
    a.bits := b.bits.addr
  }
  fake_tcdm.io.tcdm_rsp.zip(reader.io.tcdm_rsp).foreach { case (a, b) =>
    b.valid := a.valid
    b.bits.data := a.bits
  }
}

// object Reader_Wrapper_Printer extends App {
//     romGenerator.generateContent(16 * 1024, 64)
//     emitVerilog(new Reader_Wrapper(new ReaderWriterParam), Array("--target-dir", "generated"))
// }

class Reader_Tester extends AnyFreeSpec with ChiselScalatestTester {
  romGenerator.generateContent(128, 64)

  "Reader's behavior is as expected" in test(new Reader_Wrapper(new ReaderWriterParam))
    .withAnnotations(Seq(WriteVcdAnnotation, VerilatorBackendAnnotation)) { dut =>
      // The accessed address is 1KB (0x0 - 0x400)
      // Configure AGU
      dut.io.cfg.Ptr.poke(0x0.U)
      // 8 parfor, 4 tempfor x 4tempfor
      dut.io.cfg.Bounds(0).poke(8)
      dut.io.cfg.Bounds(1).poke(4)
      dut.io.cfg.Bounds(2).poke(4)
      // 8 parfor continuous, 4 tempfor having the distance of 128B (read one superbank skip one superbank)
      // 4 tempfor having the distance of 1024B (finish read 4 SB in 8 SB, skip the consiquent 8SB)
      dut.io.cfg.Strides(0).poke(8)
      dut.io.cfg.Strides(1).poke(64)
      dut.io.cfg.Strides(2).poke(256)

      dut.io.start.poke(true)
      dut.clock.step()
      dut.io.start.poke(false)
      // Waiting for the AGU to begin
      while (dut.io.busy.peekBoolean() == false) dut.clock.step()
      dut.io.data.ready.poke(true.B)
      var i: Int = 0
      while (i < 16) {
        if (dut.io.data.valid.peekBoolean() == true) {
          println(dut.io.data.bits.peek())
          i += 1
        }
        dut.clock.step()
      }
      dut.clock.step(2)
    }
}
