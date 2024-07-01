package snax.xdma.designParams

import chisel3.util.log2Up

/* 
 *  This is the collection of all design Params
 *  Design Params is placed all together with companion object to avoid multiple definition of one config & config conflict
 */


 // tcdm Params

class tcdmParam(
    val addrWidth: Int = 17,    // 128kB tcdm size
    val dataWidth: Int = 64,    // Connect to narrow xbar
    val numChannel: Int = 8,    // With eight channels
    val tcdmSize: Int = 128     // The size of tcdm
)

object tcdmParam {
    def apply(addrWidth: Int, dataWidth: Int, numChannel: Int, tcdmSize: Int) =
        new tcdmParam(addrWidth, dataWidth, numChannel, tcdmSize)
    def apply() = new tcdmParam(addrWidth = 17, dataWidth = 64, numChannel = 8, tcdmSize = 128)
}

// Streamer Params

class AddressGenUnitParam (
    val dimension: Int, 
    val addressWidth: Int, 
    val spatialUnrollingFactor: Int, 
    val outputBufferDepth: Int
)

object AddressGenUnitParam {
    // The Very Simple instantiation of the Param    
    def apply() = new AddressGenUnitParam(dimension = 2, addressWidth = 48, spatialUnrollingFactor = 8, outputBufferDepth = 8)
    def apply(dimension: Int, addressWidth: Int, spatialUnrollingFactor: Int, outputBufferDepth: Int) = new AddressGenUnitParam(dimension = dimension, addressWidth = addressWidth, spatialUnrollingFactor = spatialUnrollingFactor, outputBufferDepth = outputBufferDepth)
}


class ReaderWriterParam(
    dimension: Int = 3,
    tcdmDataWidth: Int = 64,
    tcdmSize: Int = 128, 
    tcdmAddressWidth: Int = 48, 
    numChannel: Int = 8,
    addressBufferDepth: Int = 8,
    dataBufferDepth: Int = 8
) {
    val agu_param = AddressGenUnitParam(
      dimension = dimension,
      addressWidth = tcdmAddressWidth,
      spatialUnrollingFactor = numChannel,
      outputBufferDepth = addressBufferDepth
    )

    val tcdm_param = tcdmParam(
      addrWidth = tcdmAddressWidth,
      dataWidth = tcdmDataWidth,
      numChannel = numChannel, 
      tcdmSize = tcdmSize
    )

    // Data buffer's depth
    val bufferDepth = dataBufferDepth
}


// DMA Params
import snax.xdma.xdmaFrontend.DMAExtension
class ReaderWriterDataPathParam(
    val rwParam: ReaderWriterParam,
    // val writerparam: ReaderWriterParam,
    val extParam: Seq[DMAExtension] = Seq[DMAExtension](),
    // val writerext: Seq[DMAExtension] = Seq[DMAExtension]()
)

class DMAExtensionParam(
    val userCsrNum: Int = 0, 
    val dataWidth: Int = 512
)

class DMACtrlParam(
    val readerparam: ReaderWriterParam,
    val writerparam: ReaderWriterParam,
    val readerextparam: Seq[DMAExtensionParam] = Seq[DMAExtensionParam](),
    val writerextparam: Seq[DMAExtensionParam] = Seq[DMAExtensionParam]()
)