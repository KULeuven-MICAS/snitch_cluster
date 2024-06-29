package snax.xdma.commonCells

import chisel3._
import chisel3.util._
import chisel3.reflect.DataMirror
import chisel3.internal.throwException
import chisel3.internal.throwException

/** The complexQueue_Concat to do multiple channel in / single concatenated out or single channel in
  * / multiple splitted out fifo The user defined params include:
  * @param inputWidth:
  *   the width of the input
  * @param outputWidth:
  *   the width of the output
  * @param depth:
  *   the depth of the FIFO If inputWidth is smaller than outputWidth, then it will be the first
  *   option If inputWidth is larger than outputWidth, then it will be the second option No matter
  *   which case, the big width one should equal to integer times of the small width one
  */
class complexQueue_Concat(inputWidth: Int, outputWidth: Int, depth: Int) extends Module {
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

/** The complexQueue to do N-channels in / 1 N-Vec channel out. The user defined params include:
  * @param dataType:
  *   the type of one channel
  * @param N
  *
  * @param depth:
  *   the depth of the FIFO If inputWidth is smaller than outputWidth, then it will be the first
  *   option If inputWidth is larger than outputWidth, then it will be the second option No matter
  *   which case, the big width one should equal to integer times of the small width one
  */
class complexQueue_NtoOne[T <: Data](dataType: T, N: Int, depth: Int) extends Module {
    require(
      N > 1,
      message = "N should be greater than 1"
    )
    require(depth > 0)

    val io = IO(new Bundle {
        val in = Flipped(Vec(N, Decoupled(dataType)))
        val out = Decoupled(Vec(N, dataType))
        val allEmpty = Output(Bool())
        val anyFull = Output(Bool())
    })

    val queues = for (i <- 0 until N) yield {
        Module(new Queue(dataType, depth))
    }

    io.in.zip(queues).foreach { case (i, j) => i <> j.io.enq }
    io.out.bits.zip(queues) .foreach { case (i, j) => i := j.io.deq.bits }
    io.out.valid := queues.map(i => i.io.deq.valid).reduce(_ & _)
    val dequeue_ready = io.out.valid & io.out.ready
    queues.foreach(_.io.deq.ready := dequeue_ready)

    // All empty signal is a debug signal and derived from sub channels: if all fifo is empty, then this signal is empty
    io.allEmpty := queues.map(queue => ~(queue.io.deq.valid)).reduce(_ & _)

    // Any full signal is a debug signal and derived from sub channels: if any fifo is full, then this signal is full
    io.anyFull := queues.map(queue => ~(queue.io.enq.ready)).reduce(_ | _)
}

/** The complexQueue to do 1 N-Vec channel in / N-channels out. The user defined params include:
  * @param dataType:
  *   the type of one channel
  * @param N
  *
  * @param depth:
  *   the depth of the FIFO If inputWidth is smaller than outputWidth, then it will be the first
  *   option If inputWidth is larger than outputWidth, then it will be the second option No matter
  *   which case, the big width one should equal to integer times of the small width one
  */

class complexQueue_OnetoN[T <: Data](dataType: T, N: Int, depth: Int) extends Module {
    require(
      N > 1,
      message = "N should be greater than 1"
    )
    require(depth > 0)

    val io = IO(new Bundle {
        val in = Flipped(Decoupled(Vec(N, dataType)))
        val out = Vec(N, Decoupled(dataType))
        val allEmpty = Output(Bool())
        val anyFull = Output(Bool())
    })

    val queues = for (i <- 0 until N) yield {
        Module(new Queue(dataType, depth))
    }

    io.out.zip(queues).foreach { case (i, j) => i <> j.io.deq }
    io.in.bits.zip(queues) .foreach { case (i, j) => j.io.enq.bits := i }
    io.in.ready := queues.map(i => i.io.enq.ready).reduce(_ & _)
    val enqueue_valid = io.in.valid & io.in.ready
    queues.foreach(_.io.enq.valid := enqueue_valid)

    // All empty signal is a debug signal and derived from sub channels: if all fifo is empty, then this signal is empty
    io.allEmpty := queues.map(queue => ~(queue.io.deq.valid)).reduce(_ & _)

    // Any full signal is a debug signal and derived from sub channels: if any fifo is full, then this signal is full
    io.anyFull := queues.map(queue => ~(queue.io.enq.ready)).reduce(_ | _)
}


/** The 1in, N-out Demux for Decoupled signal As the demux is the 1in, 2out system, we don't need to
  * consider the demux of bits
  */
class DemuxDecoupled[T <: Data](dataType: T, numOutput: Int) extends Module {
    val io = IO(new Bundle {
        val in = Flipped(Decoupled(dataType))
        val out = Vec(numOutput, Decoupled(dataType))
        val sel = Input(UInt(log2Ceil(numOutput).W))
    })
    // Default assigns
    io.in.ready := false.B
    // Demux logic
    for (i <- 0 until numOutput) {
        io.out(i).bits := io.in.bits
        when(io.sel === i.U) {
            io.out(i).valid := io.in.valid
            io.in.ready := io.out(i).ready
        } otherwise {
            io.out(i).valid := false.B // Unselected output should not be valid
        }
    }
}

/** The N-in, 1out Demux for Decoupled signal
  */
class MuxDecoupled[T <: Data](dataType: T, numInput: Int) extends Module {
    val io = IO(new Bundle {
        val in = Vec(numInput, Flipped(Decoupled(dataType)))
        val out = Decoupled(dataType)
        val sel = Input(UInt(log2Ceil(numInput).W))
    })
    // Default assigns
    io.out.valid := false.B
    io.out.bits := 0.U
    // Mux logic
    for (i <- 0 until numInput) {
        when(io.sel === i.U) {
            io.out.valid := io.in(i).valid
            io.in(i).ready := io.out.ready
            io.out.bits := io.in(i).bits
        } otherwise {
            io.in(i).ready := false.B // Unselected input should not be ready
        }
    }
}

/** The definition of <|> connector for decoupled signal It automatically determine the signal
  * direction, connect leftward Decoupled signal and rightward Decoupled signal \ and insert one
  * level of pipeline in between to avoid long combinatorial datapath
  */
object DecoupledBufferConnect {
    implicit class BufferedDecoupledConnectionOp[T <: Data](val left: DecoupledIO[T]) {
        // This class defines the implicit class for the new operand <|> for DecoupleIO
        def <|>(
            right: DecoupledIO[T]
        )(implicit sourceInfo: chisel3.experimental.SourceInfo): Unit = {
            val buffer = Module(new Queue(chiselTypeOf(left.bits), entries = 1))
            buffer.suggestName("cut1")
            if (
              DataMirror.hasOuterFlip(left) == false &&
              DataMirror.hasOuterFlip(right) == true
            ) { // Left is the output
                left <> buffer.io.enq
                buffer.io.deq <> right
            } else if (
              DataMirror.hasOuterFlip(left) == true &&
              DataMirror.hasOuterFlip(right) == false
            ) { // Right is the output
                right <> buffer.io.enq
                buffer.io.deq <> left
            } else throw new Exception("<|> cannot determine the direction at left and right")
        }

        def <||>(
            right: DecoupledIO[T]
        )(implicit sourceInfo: chisel3.experimental.SourceInfo): Unit = {
            val buffer = Module(new Queue(chiselTypeOf(left.bits), entries = 2))
            buffer.suggestName("cut2")
            if (
              DataMirror.hasOuterFlip(left) == false &&
              DataMirror.hasOuterFlip(right) == true
            ) { // Left is the output
                left <> buffer.io.enq
                buffer.io.deq <> right
            } else if (
              DataMirror.hasOuterFlip(left) == true &&
              DataMirror.hasOuterFlip(right) == false
            ) { // Right is the output
                right <> buffer.io.enq
                buffer.io.deq <> left
            } else throw new Exception("<||> cannot determine the direction at left and right")
        }

        def <|||>(
            right: DecoupledIO[T]
        )(implicit sourceInfo: chisel3.experimental.SourceInfo): Unit = {
            val buffer = Module(new Queue(chiselTypeOf(left.bits), entries = 3))
            buffer.suggestName("cut3")
            if (
              DataMirror.hasOuterFlip(left) == false &&
              DataMirror.hasOuterFlip(right) == true
            ) { // Left is the output
                left <> buffer.io.enq
                buffer.io.deq <> right
            } else if (
              DataMirror.hasOuterFlip(left) == true &&
              DataMirror.hasOuterFlip(right) == false
            ) { // Right is the output
                right <> buffer.io.enq
                buffer.io.deq <> left
            } else throw new Exception("<|||> cannot determine the direction at left and right")
        }
    }
}

object BitsConcat {
    implicit class UIntConcatOp[T <: Bits](val left: T) {
        // This class defines the implicit class for the new operand ++ for UInt
        def ++(
            right: T
        )(implicit sourceInfo: chisel3.experimental.SourceInfo): T =
            Cat(left, right).asInstanceOf[T]
    }
}
