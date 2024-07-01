package snax.xdma.commonCells.CustomExport

import chisel3._

import java.io._

object output{
    def Save_String_to_File(text: String, filename: String): Unit = {
        require(!text.isEmpty())
        require(!filename.isEmpty())
        val pw = new PrintWriter(filename)
        pw.write(text)
        pw.close()
    }

    def emitSystemVerilogFile(gen: => RawModule, args: Array[String] = Array.empty, firtoolOpts: Array[String] = Array("--disable-all-randomization")): Unit = circt.stage.ChiselStage.emitSystemVerilogFile(gen, args, firtoolOpts)

    def printSystemVerilog(gen: => RawModule, args: Array[String] = Array.empty, firtoolOpts: Array[String] = Array("--disable-all-randomization")): Unit = println(circt.stage.ChiselStage.emitSystemVerilog(gen, args, firtoolOpts))


    def emitCHIRRTLFile(gen: => RawModule, path: String = ""): Unit = Save_String_to_File(circt.stage.ChiselStage.emitCHIRRTL(gen), path + "/" + circt.stage.ChiselStage.convert(gen).main + ".fir")

    def printCHIRRTL(gen: => RawModule): Unit = println(circt.stage.ChiselStage.emitCHIRRTL(gen))
}