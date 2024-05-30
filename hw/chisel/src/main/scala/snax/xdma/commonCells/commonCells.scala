package snax.xdma.commonCells

import chisel3._
import chisel3.util._
import chisel3.reflect.DataMirror
import chisel3.internal.throwException
import chisel3.internal.throwException

/** The complexQueue to do multiple channel in / single concatenated out or single channel in /
  * multiple splitted out fifo The user defined params include:
  * @param inputWidth:
  *   the width of the input
  * @param outputWidth:
  *   the width of the output
  * @param depth:
  *   the depth of the FIFO If inputWidth is smaller than outputWidth, then it will be the first
  *   option If inputWidth is larger than outputWidth, then it will be the second option No matter
  *   which case, the big width one should equal to integer times of the small width one
  */
class complexQueue(inputWidth: Int, outputWidth: Int, depth: Int) extends Module {
    val bigWidth = Seq(inputWidth, outputWidth).max
    val smallWidth = Seq(inputWidth, outputWidth).min
    require(
      bigWidth % smallWidth == 0,
      message = "The Bigger datawidth should be interger times of smaller width! "
    )
    val numChannel = bigWidth / smallWidth
    require(depth > 0)

    val io = IO(new Bundle {
        val in = Flipped(
          Vec(
            {
                if (inputWidth == bigWidth) 1 else numChannel
            },
            Decoupled(UInt(inputWidth.W))
          )
        )
        val out = Vec(
          {
              if (outputWidth == bigWidth) 1 else numChannel
          },
          Decoupled(UInt(outputWidth.W))
        )
        val allEmpty = Output(Bool())
        val anyFull = Output(Bool())
    })

    val queues = for (i <- 0 until numChannel) yield {
        Module(new Queue(UInt(smallWidth.W), depth))
    }

    if (io.in.length != 1) { // The input port has small width so that the valid signal and ready signal should be connected directly to the input
        io.in.zip(queues).foreach { case (i, j) => i <> j.io.enq }
    } else {
        // only ready when all signals are ready
        val enq_all_ready = queues.map(_.io.enq.ready).reduce(_ & _)
        io.in.head.ready := enq_all_ready
        // Only when all signals are ready, then valid signals in each channels can be passed to FIFO
        queues.foreach(i => i.io.enq.valid := enq_all_ready & io.in.head.valid)
        // Connect all data
        queues.zipWithIndex.foreach {
            case (queue, i) => {
                queue.io.enq.bits := io.in.head
                    .bits(i * smallWidth + smallWidth - 1, i * smallWidth)
            }
        }
    }

    // The same thing for the output
    if (io.out.length != 1) { // The output port has small width so that the valid signal and ready signal should be connected directly to the input
        io.out.zip(queues).foreach { case (i, j) => i <> j.io.deq }
    } else {
        // only valid when all signals are valid
        val deq_all_valid = queues.map(_.io.deq.valid).reduce(_ & _)
        io.out.head.valid := deq_all_valid
        // Only when all signals are valid, then ready signals in each channels can be passed to FIFO
        queues.foreach(i => i.io.deq.ready := deq_all_valid & io.out.head.ready)
        // Connect all data
        io.out.foreach(_.bits := queues.map(i => i.io.deq.bits).reduce { (a, b) => Cat(b, a) })
    }

    // All empty signal is a debug signal and derived from sub channels: if all fifo is empty, then this signal is empty
    io.allEmpty := queues.map(queue => ~(queue.io.deq.valid)).reduce(_ & _)

    // Any full signal is a debug signal and derived from sub channels: if any fifo is full, then this signal is full
    io.anyFull := queues.map(queue => ~(queue.io.enq.ready)).reduce(_ | _)
}

/** The 1in, 2out Demux for Decoupled signal
  * As the demux is the 1in, 2out system, we don't need to consider the demux of bits
  */
class DemuxDecoupled[T <: Data](dataType: T) extends Module {
    val io = IO(new Bundle {
        val in = Flipped(Decoupled(dataType))
        val out = Vec(2, Decoupled(dataType))
        val sel = Input(Bool())
    })

    // Demux logic
    io.out(0).bits := io.in.bits
    io.out(1).bits := io.in.bits

    when(io.sel) {
        io.out(1).valid := io.in.valid
        io.in.ready := io.out(1).ready
        io.out(0).valid := false.B // Unselected output should not be valid
    }.otherwise {
        io.out(0).valid := io.in.valid
        io.in.ready := io.out(0).ready
        io.out(1).valid := false.B // Unselected output should not be valid
    }
}

/** The 1in, 2out Demux for Decoupled signal
  */
class MuxDecoupled[T <: Data](dataType: T) extends Module {
    val io = IO(new Bundle {
        val in = Vec(2, Flipped(Decoupled(dataType)))
        val out = Decoupled(dataType)
        val sel = Input(Bool())
    })

    // Mux logic
    when(io.sel) {
        io.out.valid := io.in(1).valid
        io.out.bits := io.in(1).bits
        io.in(1).ready := io.out.ready
        io.in(0).ready := false.B // Unselected input should not be ready
    }.otherwise {
        io.out.valid := io.in(0).valid
        io.out.bits := io.in(0).bits
        io.in(0).ready := io.out.ready
        io.in(1).ready := false.B // Unselected input should not be ready
    }
}

/** The definition of <|> connector for decoupled signal It automatically determine the signal
  * direction, connect leftward Decoupled signal and rightward Decoupled signal \ and insert one
  * level of pipeline in between to avoid long combinatorial datapath
  */
object DecoupledBufferConnect {
    implicit class BufferedDecoupledConnectionOp[T <: Data](val left: DecoupledIO[T]) {
        // This class defines the implicit class for the new operand <|>
        def <|>(
            right: DecoupledIO[T]
        )(implicit sourceInfo: chisel3.experimental.SourceInfo): Unit = {
            val buffer = Module(new Queue(chiselTypeOf(left.bits), entries = 1))
            if (
              DataMirror.hasOuterFlip(left) == false && 
              DataMirror.hasOuterFlip(right) == true
            ) { // Left is the output
                left <> buffer.io.enq
                buffer.io.deq <> right
            } else if (
              DataMirror.hasOuterFlip(left) == true && 
              DataMirror.hasOuterFlip(right) == false
            ){ // Right is the input
                right <> buffer.io.enq
                buffer.io.deq <> left
            } else throw new Exception("<|> cannot determine the direction at left and right")
        }
    }
}
