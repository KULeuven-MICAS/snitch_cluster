package snax.xdma.xdmaFrontend

import chisel3._
import chisel3.util._

import snax.utils._
import snax.xdma.commonCells._
import snax.xdma.commonCells.DecoupledBufferConnect._
import snax.xdma.commonCells.BitsConcat._

import snax.xdma.xdmaStreamer.{Reader, Writer, AddressGenUnitCfgIO}
import snax.xdma.designParams._

import snax.csr_manager._
import snax.xdma.commonCells

class DMACtrlIO(
    readerparam: ReaderWriterDataPathParam,
    writerparam: ReaderWriterDataPathParam,
    axiWidth: Int = 512
) extends Bundle {
    // Local DMADatapath control signal (Which is connected to DMADataPath)
    val localDMADataPath = new Bundle {
        val reader_cfg_o = Output(new ReaderWriterCfg(readerparam))
        val writer_cfg_o = Output(new ReaderWriterCfg(writerparam))

        val reader_loopBack_o = Output(Bool()) // Unbuffered, pay attention!
        val writer_loopBack_o = Output(Bool()) // Unbuffered, pay attention!
        // Two start signal will inform the new cfg is available, trigger agu, and inform all extension that a stream is coming
        val reader_start_o = Output(Bool())
        val writer_start_o = Output(Bool())
        // Two busy signal only go down if a stream fully passthrough the reader / writter, which is provided by DataPath
        // These signals should be readable by the outside; these two will also be used to determine whether the next task can be executed.
        val reader_busy_i = Input(Bool())
        val writer_busy_i = Input(Bool())
    }
    // Remote control signal, which include the signal from other cluster or signal to other cluster. Both of them is AXI related, serialized signal
    // The remote control signal will contain only src information, in other words, the DMA system can proceed remote read or local read, but only local write
    val remoteDMADataPath = new Bundle {
        val fromRemote = Flipped(Decoupled(UInt(axiWidth.W)))
        val toRemote = Decoupled(UInt(axiWidth.W))
    }
    // This is the port for CSR Manager to SNAX port
    val csrIO = new SnaxCsrIO(csrAddrWidth = 32)
}

// The internal sturctured class that used to store the CFG of reader and writer
// The serialized version of this class will be the actual output and input of the DMACtrl (which is to AXI)
// It is the ReaderWriterCfg class, with loopBack signal (early judgement) and Ptr of the opposite side (So that the Data can be forwarded to the remote side)
class ReaderWriterCfgInternal(param: ReaderWriterDataPathParam)
    extends ReaderWriterCfg(param: ReaderWriterDataPathParam) {
    val loopBack = Bool()
    val oppositePtr = UInt(param.rwParam.tcdm_param.addrWidth.W)
    override def serialize(): UInt = {
        super.serialize() ++ loopBack.asUInt ++ oppositePtr
    }

    override def deserialize(data: UInt): UInt = {
        var remainingData = data;

        // Assigning oppositePtr
        oppositePtr := remainingData(oppositePtr.getWidth - 1, 0)
        remainingData = remainingData(remainingData.getWidth - 1, oppositePtr.getWidth)

        // Assigning loopBack
        loopBack := remainingData(0)
        remainingData = remainingData(remainingData.getWidth - 1, 1)

        // Assigning remaining wires
        remainingData = super.deserialize(remainingData)
        remainingData
    }

}

class SrcConfigRouter(dataType: ReaderWriterCfgInternal, tcdmSize: Int) extends Module {
    val io = IO(new Bundle {
        val clusterBaseAddress = Input(dataType.agu_cfg.Ptr)
        val from = Flipped(new Bundle {
            val remote = Decoupled(dataType)
            val local = Decoupled(dataType)
        })
        val to = new Bundle {
            val remote = Decoupled(dataType)
            val local = Decoupled(dataType)
        }
    })

    val from_arbiter = Module(new Arbiter(dataType, 2))
    from_arbiter.io.in(0) <> io.from.local
    from_arbiter.io.in(1) <> io.from.remote

    val to_demux = Module(new DemuxDecoupled(dataType = dataType, numOutput = 3))
    from_arbiter.io.out <|> to_demux.io.in

    // At the output of FIFO: Do the rule check
    val cType_local :: cType_remote :: cType_discard :: Nil = Enum(3)
    val cValue = Wire(cType_discard)

    when (to_demux.io.in.bits.agu_cfg.Ptr(to_demux.io.in.bits.agu_cfg.Ptr.getWidth - 1, log2Up(tcdmSize) + 10) === io.clusterBaseAddress(to_demux.io.in.bits.agu_cfg.Ptr.getWidth - 1, log2Up(tcdmSize) + 10)) {
        cValue := cType_local   // When cfg has the Ptr that fall within local TCDM, the data should be forwarded to the local ctrl path
    } .elsewhen (to_demux.io.in.bits.agu_cfg.Ptr === 0.U) {
        cValue := cType_discard // When cfg has the Ptr that is zero, This means that the frame need to be thrown away. This is important as when the data is moved from DRAM to TCDM or vice versa, DRAM part is handled by iDMA, thus only one config instead of two is submitted
    } .otherwise {
        cValue := cType_remote  // For the remaining condition, the config is forward to remote DMA
    }

    to_demux.io.sel := cValue
    // Port local is connected to the outside
    to_demux.io.out(cType_local.litValue.toInt) <> io.to.local
    // Port remote is connected to the outside
    to_demux.io.out(cType_remote.litValue.toInt) <> io.to.remote
    // Port discard is not connected and will always be discarded
    to_demux.io.out(cType_discard.litValue.toInt).ready := true.B
}

class DstConfigRouter(dataType: ReaderWriterCfgInternal, tcdmSize: Int) extends Module {
    val io = IO(new Bundle {
        val clusterBaseAddress = Input(dataType.agu_cfg.Ptr)
        val from = Flipped(new Bundle {
            val local = Decoupled(dataType)
        })
        val to = new Bundle {
            val local = Decoupled(dataType)
        }
    })
    val to_demux = Module(new DemuxDecoupled(dataType = dataType, numOutput = 2))
    io.from.local <|> to_demux.io.in

    // At the output of cut: Do the rule check
    val cType_local :: cType_discard :: Nil = Enum(2)
    val cValue = Wire(cType_discard)

    when (to_demux.io.in.bits.agu_cfg.Ptr(to_demux.io.in.bits.agu_cfg.Ptr.getWidth - 1, log2Up(tcdmSize) + 10) === io.clusterBaseAddress(to_demux.io.in.bits.agu_cfg.Ptr.getWidth - 1, log2Up(tcdmSize) + 10)) {
        cValue := cType_local   // When cfg has the Ptr that fall within local TCDM, the data should be forwarded to the local ctrl path
    } .otherwise {
        cValue := cType_discard // For all other case, this frame needs to be discarded
    }

    to_demux.io.sel := cValue
    // Port local is connected to the outside
    to_demux.io.out(cType_local.litValue.toInt) <> io.to.local
    // Port discard is not connected and will always be discarded
    to_demux.io.out(cType_discard.litValue.toInt).ready := true.B
}


class DMACtrl(
    readerparam: ReaderWriterDataPathParam,
    writerparam: ReaderWriterDataPathParam,
    axiWidth: Int = 512
) extends Module {
    val io = IO(new Bundle {
        val dmactrl = new DMACtrlIO(
          readerparam = readerparam,
          writerparam = writerparam,
          axiWidth = axiWidth
        )
        val clusterBaseAddress = Output(UInt(readerparam.rwParam.tcdm_param.addrWidth.W))
    })

    val csrmanager = Module(
      new CsrManager(
        csrNumReadWrite = 2 + // Reader Pointer needs two CSRs
            readerparam.rwParam.agu_param.dimension * 2 + // Strides + Bounds for read
            {
                if (readerparam.extParam.length == 0) 0
                else readerparam.extParam.map { i => i.io.csr_i.length }.reduce(_ + _)
            } + // The total num of param on reader extension
            2 + // Writer Pointer needs two CSRs
            writerparam.rwParam.agu_param.dimension * 2 + // Strides + Bounds for write
            {
                if (writerparam.extParam.length == 0) 0
                else writerparam.extParam.map { i => i.io.csr_i.length }.reduce(_ + _)
            }, // The total num of param on writer
        csrNumReadOnly = 0,
        // Set to zero at current, but it should be used by returning the finished DMA requests (A simple Counter? )
        csrAddrWidth = 32
      )
    )

    csrmanager.io.csr_config_in <> io.dmactrl.csrIO

    val preRuleCheck_src = Wire(new ReaderWriterCfg(readerparam))
    val preRuleCheck_dst = Wire(new ReaderWriterCfg(writerparam))
    var remainingCSR = csrmanager.io.csr_config_out.bits.toIndexedSeq

    // Pack the unstructured signal from csrManager to structured signal: Src side
    // Connect agu_cfg.Ptr
    preRuleCheck_src.agu_cfg.Ptr := Cat(remainingCSR(1), remainingCSR(0))
    remainingCSR = remainingCSR.tail.tail

    // Connect agu_cfg.Bounds
    for (i <- 0 until preRuleCheck_src.agu_cfg.Bounds.length) {
        preRuleCheck_src.agu_cfg.Bounds(i) := remainingCSR.head
        remainingCSR = remainingCSR.tail
    }

    // Connect agu_cfg.Strides
    for (i <- 0 until preRuleCheck_src.agu_cfg.Strides.length) {
        preRuleCheck_src.agu_cfg.Strides(i) := remainingCSR.head
        remainingCSR = remainingCSR.tail
    }

    // Connect extension signal
    for (i <- 0 until preRuleCheck_src.ext_cfg.length) {
        preRuleCheck_src.ext_cfg(i) := remainingCSR.head
        remainingCSR = remainingCSR.tail
    }

    // Pack the unstructured signal from csrManager to structured signal: Dst side
    // Connect agu_cfg.Ptr
    preRuleCheck_dst.agu_cfg.Ptr := Cat(remainingCSR(1), remainingCSR(0))
    remainingCSR = remainingCSR.tail.tail

    // Connect agu_cfg.Bounds
    for (i <- 0 until preRuleCheck_dst.agu_cfg.Bounds.length) {
        preRuleCheck_dst.agu_cfg.Bounds(i) := remainingCSR.head
        remainingCSR = remainingCSR.tail
    }

    // Connect agu_cfg.Strides
    for (i <- 0 until preRuleCheck_dst.agu_cfg.Strides.length) {
        preRuleCheck_dst.agu_cfg.Strides(i) := remainingCSR.head
        remainingCSR = remainingCSR.tail
    }

    // Connect extension signal
    for (i <- 0 until preRuleCheck_dst.ext_cfg.length) {
        preRuleCheck_dst.ext_cfg(i) := remainingCSR.head
        remainingCSR = remainingCSR.tail
    }

    if (remainingCSR.length > 1) println("There is some error in CSR -> Structured CFG assigning")

    // New class that pack the loopBack signal with the ReaderWriterCfg -> ReaderWriterCfgInternal (Local command)
    val preRoute_src_local = Decoupled(new ReaderWriterCfgInternal(readerparam))
    val preRoute_dst_local = Decoupled(new ReaderWriterCfgInternal(writerparam))
    val preRoute_loopBack =
        preRuleCheck_src.agu_cfg.Ptr(preRuleCheck_src.agu_cfg.Ptr.getWidth - 1, log2Up(readerparam.rwParam.tcdm_param.tcdmSize) + 10) === preRuleCheck_dst.agu_cfg.Ptr(preRuleCheck_dst.agu_cfg.Ptr.getWidth - 1, log2Up(readerparam.rwParam.tcdm_param.tcdmSize) + 10)

    // Connect bits
    preRoute_src_local.bits := preRuleCheck_src
    preRoute_dst_local.bits := preRuleCheck_dst
    preRoute_src_local.bits.loopBack := preRoute_loopBack
    preRoute_dst_local.bits.loopBack := preRoute_loopBack
    preRoute_src_local.bits.oppositePtr := preRoute_dst_local.bits.agu_cfg.Ptr
    preRoute_dst_local.bits.oppositePtr := preRoute_src_local.bits.agu_cfg.Ptr

    // Connect Valid and bits: Only when both preRoutes are ready, postRulecheck is ready
    csrmanager.io.csr_config_out.ready := preRoute_src_local.ready & preRoute_dst_local.ready
    preRoute_src_local.valid := csrmanager.io.csr_config_out.ready & csrmanager.io.csr_config_out.valid
    preRoute_dst_local.valid := csrmanager.io.csr_config_out.ready & csrmanager.io.csr_config_out.valid


    // Cfg Frame Routing at src side
    val preRoute_src_remote = Decoupled(new ReaderWriterCfgInternal(readerparam))
    preRoute_src_remote.bits.deserialize(io.dmactrl.remoteDMADataPath.fromRemote.bits)
    preRoute_src_remote.valid := io.dmactrl.remoteDMADataPath.fromRemote.valid
    io.dmactrl.remoteDMADataPath.fromRemote.ready := preRoute_src_remote.ready

    // Command Router 
    val srcCfgRouter = Module(new SrcConfigRouter(dataType = preRoute_src_local.bits, tcdmSize = readerparam.rwParam.tcdm_param.tcdmSize))
    
    srcCfgRouter.io.from.local <> preRoute_src_local
    srcCfgRouter.io.from.remote <> preRoute_src_remote

    val postRoute_src_local = Decoupled(new ReaderWriterCfgInternal(readerparam))
    val postRoute_src_remote = Decoupled(new ReaderWriterCfgInternal(readerparam))
    srcCfgRouter.io.to.local <> postRoute_src_local
    srcCfgRouter.io.to.remote <> postRoute_src_remote

    // Connect Port 3 to AXI Mst
    io.dmactrl.remoteDMADataPath.toRemote.bits := postRoute_src_remote.bits.serialize()
    io.dmactrl.remoteDMADataPath.toRemote.valid := postRoute_src_remote.valid
    postRoute_src_remote.ready := io.dmactrl.remoteDMADataPath.toRemote.ready

    // Cfg Frame Routing at dst side: The fake router that only buffer the config and pop out invalid command
    // Command Router 
    val dstCfgRouter = Module(new DstConfigRouter(dataType = preRoute_src_local.bits, tcdmSize = writerparam.rwParam.tcdm_param.tcdmSize))

    val postRoute_dst_local = Decoupled(new ReaderWriterCfgInternal(writerparam))
    postRoute_dst_local <> dstCfgRouter.io.to.local

    // Loopback / Non-loopback seperation for pseudo-OoO commit
    val src_LoopbackDemux = Module(new DemuxDecoupled(postRoute_src_local.bits, numOutput = 2))
    val dst_LoopbackDemux = Module(new DemuxDecoupled(postRoute_dst_local.bits, numOutput = 2))

    // (1) is loopback; (0) is non-loopback
    src_LoopbackDemux.io.sel := postRoute_src_local.bits.loopBack
    dst_LoopbackDemux.io.sel := postRoute_dst_local.bits.loopBack
    src_LoopbackDemux.io.in <> postRoute_src_local
    dst_LoopbackDemux.io.in <> postRoute_dst_local

    // Optional FIFO for loopback cfg is not added
    val srcCfg_Loopback = src_LoopbackDemux.io.out(1)
    val srcCfg_NonLoopback = Decoupled(new ReaderWriterCfgInternal(readerparam))
    // Optional FIFO for loopback cfg is added (Depth = 2)
    srcCfg_NonLoopback <||> src_LoopbackDemux.io.out(0)
    // Optional FIFO for loopback cfg is not added
    val dstCfg_Loopback = dst_LoopbackDemux.io.out(1)
    val dstCfg_NonLoopback = Decoupled(new ReaderWriterCfgInternal(writerparam))
    // Optional FIFO for loopback cfg is added (Depth = 2)
    dstCfg_NonLoopback <||> dst_LoopbackDemux.io.out(0)
    
    val srcCfgArbiter = Module(new Arbiter(srcCfg_NonLoopback.bits, 2))
    val dstCfgArbiter = Module(new Arbiter(dstCfg_NonLoopback.bits, 2))
    srcCfgArbiter.io.in(0) <> srcCfg_Loopback
    srcCfgArbiter.io.in(1) <> srcCfg_NonLoopback
    dstCfgArbiter.io.in(0) <> dstCfg_Loopback
    dstCfgArbiter.io.in(1) <> dstCfg_NonLoopback

    // Connect these two cfg to the actual input: Need two small (Mealy) FSMs to manage the start signal and pop out the consumed cfg
    val s_idle :: s_waitbusy :: s_busy :: Nil = Enum(3)

    val current_state_src = RegInit(s_idle)
    val current_state_dst = RegInit(s_idle)
    val next_state_src = Wire(s_idle)
    val next_state_dst = Wire(s_idle)

    current_state_src := next_state_src
    current_state_dst := next_state_dst

    // Default value: Not pop out config, not start reader/writer, not change state
    next_state_src := current_state_src
    next_state_dst := current_state_dst
    io.dmactrl.localDMADataPath.reader_start_o := false.B
    io.dmactrl.localDMADataPath.writer_start_o := false.B
    srcCfgArbiter.io.out.ready := false.B
    dstCfgArbiter.io.out.ready := false.B

    // Control signals in Src Path
    switch(current_state_src){
        is (s_idle) {
            when(srcCfgArbiter.io.out.valid & (~io.dmactrl.localDMADataPath.reader_busy_i)) {
                next_state_src := s_waitbusy
                io.dmactrl.localDMADataPath.reader_start_o := true.B
            }
        }
        is (s_waitbusy) {
            when(io.dmactrl.localDMADataPath.reader_busy_i) {
                next_state_src := s_busy
            }
        }
        is (s_busy) {
            when(~io.dmactrl.localDMADataPath.reader_busy_i) {
                next_state_src := s_idle
                srcCfgArbiter.io.out.ready := true.B
            }
        }
    }

    // Control signals in Dst Path
    switch(current_state_dst){
        is (s_idle) {
            when(dstCfgArbiter.io.out.valid & (~io.dmactrl.localDMADataPath.writer_busy_i)) {
                next_state_dst := s_waitbusy
                io.dmactrl.localDMADataPath.writer_start_o := true.B
            }
        }
        is (s_waitbusy) {
            when(io.dmactrl.localDMADataPath.writer_busy_i) {
                next_state_dst := s_busy
            }
        }
        is (s_busy) {
            when(~io.dmactrl.localDMADataPath.writer_busy_i) {
                next_state_dst := s_idle
                dstCfgArbiter.io.out.ready := true.B
            }
        }
    }

    // Data Signals in Src Path
    io.dmactrl.localDMADataPath.reader_cfg_o := srcCfgArbiter.io.out.bits
    // Data Signals in Dst Path
    io.dmactrl.localDMADataPath.writer_cfg_o := dstCfgArbiter.io.out.bits
}
