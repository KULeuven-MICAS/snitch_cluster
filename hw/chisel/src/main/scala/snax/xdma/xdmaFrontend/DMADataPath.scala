package snax.xdma.xdmaFrontend

import chisel3._
import chisel3.util._

import snax.utils._

import snax.xdma.commonCells.DecoupledBufferConnect._
import snax.xdma.commonCells.BitsConcat._

import snax.xdma.commonCells._
import snax.xdma.xdmaStreamer.{Reader, Writer, AddressGenUnitCfgIO}
import snax.xdma.designParams._

// Todo: the decoupled signal cut should be added inbetween extensions to avoid long combinatorial path?
// New operand difinition <|> in commonCells.scala

// The ReaderWriterCfg Class that used for interface between local Datapath and DMA Ctrl
class ReaderWriterCfg(param: ReaderWriterDataPathParam) extends Bundle {
    val agu_cfg = new AddressGenUnitCfgIO(param = param.rwParam.agu_param) // Buffered within AGU
    val ext_cfg = if (param.extParam.length != 0) {
        Vec(
          param.extParam.map { i => i.io.csr_i.length }.reduce(_ + _),
          UInt(32.W)
        ) // Buffered within Extension Base Module
    } else Vec(0, UInt(32.W))

    // The config forwarding technics is easy to be implemented: Just by reading agu_cfg.Ptr, the destination can be determined
    // However, the data forwarding is still challenging: Shall we use the current DMA to move the data? (I suggest that we do this in the initial implementation)
    // Serialize function to convert config into one long UInt
    def serialize(): UInt = {
        ext_cfg.asUInt ++ agu_cfg.Bounds.asUInt ++ agu_cfg.Strides.asUInt ++ agu_cfg.Ptr
    }

    // Deserialize function to convert long UInt back to config
    // The conversion is done from LSB to MSB
    // After the conversion, the remaining data is returned for further conversion
    def deserialize(data: UInt): UInt = {
        var remainingData = data

        // Assigning Ptr
        agu_cfg.Ptr := remainingData(agu_cfg.Ptr.getWidth - 1, 0)
        remainingData = remainingData(remainingData.getWidth - 1, agu_cfg.Ptr.getWidth)

        // Assigning Strides
        agu_cfg.Strides := remainingData(agu_cfg.Strides.asUInt.getWidth - 1, 0)
            .asTypeOf(agu_cfg.Strides)
        remainingData = remainingData(remainingData.getWidth - 1, agu_cfg.Strides.asUInt.getWidth)

        // Assigning Bounds
        agu_cfg.Bounds := remainingData(agu_cfg.Strides.asUInt.getWidth - 1, 0)
            .asTypeOf(agu_cfg.Bounds)
        remainingData = remainingData(remainingData.getWidth - 1, agu_cfg.Bounds.asUInt.getWidth)

        // Assigning ext_cfg
        ext_cfg := remainingData(ext_cfg.asUInt.getWidth - 1, 0).asTypeOf(ext_cfg)
        remainingData = remainingData(remainingData.getWidth - 1, ext_cfg.asUInt.getWidth)
        remainingData
    }
}

class DMADataPath(readerparam: ReaderWriterDataPathParam, writerparam: ReaderWriterDataPathParam)
    extends Module {
    val io = IO(new Bundle {
        // All config signal for reader and writer
        val reader_cfg = Input(new ReaderWriterCfg(readerparam))
        val writer_cfg = Input(new ReaderWriterCfg(writerparam))

        val loopBack_i = Input(Bool()) // Unbuffered
        // Two start signal will inform the new cfg is available, trigger agu, and inform all extension that a stream is coming
        val reader_start_i = Input(Bool())
        val writer_start_i = Input(Bool())
        // Two busy signal only go down if a stream fully passthrough the reader / writter.
        // reader_busy_o signal == 0 indicates that the reader side is available for next task
        val reader_busy_o = Output(Bool())
        // writer_busy_o signal == 0 indicates that the writer side is available for next task
        val writer_busy_o = Output(Bool())

        // TCDM request and response signal
        val tcdm_reader = new Bundle {
            val req = Vec(
              readerparam.rwParam.tcdm_param.numChannel,
              Decoupled(
                new TcdmReq(
                  readerparam.rwParam.tcdm_param.addrWidth,
                  readerparam.rwParam.tcdm_param.dataWidth
                )
              )
            )
            val rsp = Vec(
              readerparam.rwParam.tcdm_param.numChannel,
              Flipped(Valid(new TcdmRsp(tcdmDataWidth = readerparam.rwParam.tcdm_param.dataWidth)))
            )
        }
        val tcdm_writer = new Bundle {
            val req = Vec(
              writerparam.rwParam.tcdm_param.numChannel,
              Decoupled(
                new TcdmReq(
                  writerparam.rwParam.tcdm_param.addrWidth,
                  writerparam.rwParam.tcdm_param.dataWidth
                )
              )
            )
        }

        // The data for the cluster-level in/out
        // Cluster-level input <> Writer
        // Cluster-level output <> Reader
        val cluster_data_i = Flipped(
          Decoupled(
            UInt(
              (writerparam.rwParam.tcdm_param.dataWidth * writerparam.rwParam.tcdm_param.numChannel).W
            )
          )
        )
        val cluster_data_o = Decoupled(
          UInt(
            (readerparam.rwParam.tcdm_param.dataWidth * readerparam.rwParam.tcdm_param.numChannel).W
          )
        )
    })

    val reader = Module(new Reader(readerparam.rwParam))
    val writer = Module(new Writer(writerparam.rwParam))

    // Connect TCDM memory to reader and writer
    reader.io.tcdm_req <> io.tcdm_reader.req
    reader.io.tcdm_rsp <> io.tcdm_reader.rsp
    writer.io.tcdm_req <> io.tcdm_writer.req

    // Connect the wire (ctrl plane)
    reader.io.cfg := io.reader_cfg.agu_cfg
    reader.io.start := io.reader_start_i
    // reader_busy_o is connected later as the busy signal from the signal is needed

    writer.io.cfg := io.writer_cfg.agu_cfg
    writer.io.start := io.writer_start_i
    // writer_busy_o is connected later as the busy signal from the signal is needed

    // Connect the extension
    // Reader Side
    val reader_data_after_extension = Wire(chiselTypeOf(reader.io.data))

    // No extension is provided, the reader.io.data is directly connected to the out
    if (readerparam.extParam.length == 0) {
        reader.io.data <> reader_data_after_extension
        io.reader_busy_o := reader.io.busy | (~reader.io.bufferEmpty)
    } else {
        // There is some extension available: connect them
        // Connect CSR interface
        var remainingCSR =
            io.reader_cfg.ext_cfg.toIndexedSeq // Give an alias to all extension's csr for a easier manipulation
        for (i <- readerparam.extParam) {
            i.io.csr_i := remainingCSR.take(i.io.csr_i.length)
            remainingCSR = remainingCSR.drop(i.io.csr_i.length)
        }
        if (remainingCSR.length != 0)
            println("Debug: Some remaining CSRs are unconnected at reader. Check the code. ")

        // Connect Start signal
        readerparam.extParam.foreach { i => i.io.start_i := io.reader_start_i }

        // Connect Data
        // The new <|> operator to implement a Decoupled Signal Cut in between the connection <> had been implemented, but haven't go through the detailed test. Shall we provide this function to the user?
        reader.io.data <> readerparam.extParam.head.io.data_i
        readerparam.extParam.last.io.data_o <> reader_data_after_extension
        if (readerparam.extParam.length > 1)
            readerparam.extParam.zip(readerparam.extParam.tail).foreach { case (a, b) =>
                a.io.data_o <> b.io.data_i
            }

        // Connect busy
        // Reader side is busy if reader is busy (addressgen is busy or addressgen fifo is non-empty) or data fifo is non-empty or any extension is busy
        io.reader_busy_o := reader.io.busy | (~reader.io.bufferEmpty) | (readerparam.extParam
            .map { _.ext_busy_o }
            .reduce(_ | _))

        // Suggest a name for each extension
        for (i <- 0 until readerparam.extParam.length)
            readerparam
                .extParam(i)
                .suggestName("reader_ext_" + i.toString() + "_" + readerparam.extParam(i).extName)

    }

    // Writer side
    val writer_data_before_extension = Wire(chiselTypeOf(writer.io.data))

    // No extension is provided, the writer_data_before_extension is directly connected to the writer.io.data
    if (writerparam.extParam.length == 0) {
        writer_data_before_extension <> writer.io.data
        io.writer_busy_o := writer.io.busy | (~writer.io.bufferEmpty)
    } else {
        // There is some extension available: connect them
        // Connect CSR interface
        var remainingCSR =
            io.writer_cfg.ext_cfg.toIndexedSeq // Give an alias to all extension's csr for a easier manipulation
        for (i <- writerparam.extParam) {
            i.io.csr_i := remainingCSR.take(i.io.csr_i.length)
            remainingCSR = remainingCSR.drop(i.io.csr_i.length)
        }
        if (remainingCSR.length != 0)
            println("Debug: Some remaining CSRs are unconnected at writer. Check the code. ")

        // Connect Start signal
        writerparam.extParam.foreach { i => i.io.start_i := io.writer_start_i }

        // Connect Data
        // The new <|> operator to implement a Decoupled Signal Cut in between the connection <> had been implemented, but haven't go through the detailed test. Shall we provide this function to the user?
        writer_data_before_extension <> writerparam.extParam.head.io.data_i
        writerparam.extParam.last.io.data_o <> writer.io.data
        if (writerparam.extParam.length > 1)
            writerparam.extParam.zip(writerparam.extParam.tail).foreach { case (a, b) =>
                a.io.data_o <> b.io.data_i
            }

        // Connect busy
        // Writer side is busy if writer is busy (addressgen is busy or addressgen fifo is non-empty) or data fifo is non-empty or any extension is busy
        io.writer_busy_o := writer.io.busy | (~writer.io.bufferEmpty) | (writerparam.extParam
            .map { _.ext_busy_o }
            .reduce(_ | _))

        // Suggest a name for each extension
        for (i <- 0 until writerparam.extParam.length)
            writerparam
                .extParam(i)
                .suggestName("writer_ext_" + i.toString() + "_" + writerparam.extParam(i).extName)
    }

    // The following code only tackle with reader_data_after_extension and writer_data_before_extension: they should be either loopbacked or forwarded to the external interface (cluster_data_i / cluster_data_o)
    val readerDemux = Module(new DemuxDecoupled(chiselTypeOf(reader_data_after_extension.bits)))
    val writerMux = Module(new MuxDecoupled(chiselTypeOf(writer_data_before_extension.bits)))

    readerDemux.io.sel := io.loopBack_i
    writerMux.io.sel := io.loopBack_i
    readerDemux.io.in <|> reader_data_after_extension
    writerMux.io.out <|> writer_data_before_extension
    // Why there is a problem?
    readerDemux.io.out(1) <> writerMux.io.in(1)
    readerDemux.io.out(0) <> io.cluster_data_o
    writerMux.io.in(0) <> io.cluster_data_i
}

// Below is the class to determine if chisel generate Verilog correctly

object DMADataPath_SystemVerilogEmitter extends App {
    println(
      getVerilogString(
        new DMADataPath(
          readerparam = new ReaderWriterDataPathParam(
            rwParam = new ReaderWriterParam,
            extParam = Seq()
          ),
          writerparam = new ReaderWriterDataPathParam(
            rwParam = new ReaderWriterParam,
            extParam = Seq()
          )
        )
      )
    )
}

class Serializer_Deserializer_Tester(param: ReaderWriterDataPathParam) extends Module {
    val io = IO(new Bundle {
        val in = Input(new ReaderWriterCfg(param))
        val out_serialized = Output(UInt(512.W))
        val out = Output(new ReaderWriterCfg(param))
    })

    io.out_serialized := io.in.serialize()
    val out = Wire(new ReaderWriterCfg(param))
    out.deserialize(io.out_serialized)
    io.out := out
}

object Serializer_Deserializer_Tester_SystemVerilogEmitter extends App {
    println(
      getVerilogString(
        new Serializer_Deserializer_Tester(
          new ReaderWriterDataPathParam(
            rwParam = new ReaderWriterParam
          )
        )
      )
    )
}
