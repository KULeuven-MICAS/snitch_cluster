package snax_acc.simd

import chisel3._
import chisel3.util._
import chisel3.VecInit

// Rescale SIMD module
// This module implements this spec: specification: https://gist.github.com/jorendumoulin/83352a1e84501ec4a7b3790461fee2bf in parallel
class PipelinedRescaleSIMD(params: RescaleSIMDParams)
    extends Module
    with RequireAsyncReset {
  val io = IO(new RescaleSIMDIO(params))

  // generating parallel RescalePEs
  val lane = Seq.fill(params.laneLen)(Module(new RescalePE(params)))

  // control csr registers for storing the control data
  val ctrl_csr = Reg(new RescalePECtrl(params))

  // result from different RescalePEs
  val result = Wire(
    Vec(params.laneLen, SInt(params.outputType.W))
  )

  // the receiver isn't ready, needs to send several cycles
  val keep_output = RegInit(0.B)

  val simd_output_fire = WireInit(0.B)

  val write_counter = RegInit(0.U(32.W))

  // State declaration
  val sIDLE :: sBUSY :: Nil = Enum(2)
  val cstate = RegInit(sIDLE)
  val nstate = WireInit(sIDLE)

  // signals for state transition
  val config_valid = WireInit(0.B)
  val computation_finish = WireInit(0.B)

  // Changing states
  cstate := nstate

  chisel3.dontTouch(cstate)
  switch(cstate) {
    is(sIDLE) {
      when(config_valid) {
        nstate := sBUSY
      }.otherwise {
        nstate := sIDLE
      }

    }
    is(sBUSY) {
      when(computation_finish) {
        nstate := sIDLE
      }.otherwise {
        nstate := sBUSY
      }
    }
  }

  io.busy_o := cstate === sBUSY

  val performance_counter = RegInit(0.U(32.W))
  when(cstate === sBUSY) {
    performance_counter := performance_counter + 1.U
  }.elsewhen(config_valid) {
    performance_counter := 0.U
  }
  io.performance_counter := performance_counter

  config_valid := io.ctrl.fire

  // when config valid, store the configuration for later computation
  ctrl_csr.input_zp_i := io.ctrl.bits(0)(7, 0).asSInt
  ctrl_csr.output_zp_i := io.ctrl.bits(0)(15, 8).asSInt

  // this control input port is 32 bits, so it needs 1 csr
  ctrl_csr.multiplier_i := io.ctrl.bits(2).asSInt

  ctrl_csr.shift_i := io.ctrl.bits(0)(23, 16).asSInt
  ctrl_csr.max_int_i := io.ctrl.bits(0)(31, 24).asSInt

  ctrl_csr.min_int_i := io.ctrl.bits(1)(7, 0).asSInt

  // this control input port is only 1 bit
  ctrl_csr.double_round_i := io.ctrl.bits(1)(8).asBool

  // length of the data
  ctrl_csr.len := io.ctrl.bits(3)

  // state: pe in-compute or not
  val sNotCOMP :: sCOMP :: Nil = Enum(2)
  val compstate = RegInit(sNotCOMP)
  val ncompstate = WireInit(sNotCOMP)

  compstate := ncompstate
  
  chisel3.dontTouch(compstate)
  when(cstate === sBUSY){
    switch(compstate) {
      is(sNotCOMP){
        when(io.data.input_i.fire){
          ncompstate := sCOMP
        }.otherwise{
          ncompstate := sNotCOMP
        }
      }
      is(sCOMP){
        when(io.data.output_o.fire && !io.data.input_i.fire){
          ncompstate := sNotCOMP
        }.elsewhen(io.data.input_i.fire){
          ncompstate := sCOMP
        }.otherwise{
          ncompstate := sCOMP
        }
      }
    }
  }.otherwise{
    ncompstate := sNotCOMP
  }

  val lane_comp_cycle = params.dataLen / params.laneLen

  // lane computation process counter
  val pe_input_valid = WireInit(0.B)
  val pipe_input_counter = RegInit(0.U(32.W))

  pe_input_valid := io.data.input_i.fire || (compstate === sCOMP && pipe_input_counter =/= lane_comp_cycle.U)
  when(pe_input_valid && pipe_input_counter =/= lane_comp_cycle.U - 1.U){
    pipe_input_counter := pipe_input_counter + 1.U
  }.elsewhen(pe_input_valid && pipe_input_counter === lane_comp_cycle.U - 1.U){
    pipe_input_counter := 0.U
  }.elsewhen(compstate === sNotCOMP || cstate === sIDLE){
    pipe_input_counter := 0.U
  }

  // store the input data for params.laneLen - 1 lane
  val input_data_reg = RegInit(0.U(((params.dataLen - params.laneLen) * params.inputType).W))
  when(io.data.input_i.fire){
    input_data_reg := io.data.input_i.bits(params.dataLen * params.inputType - 1, params.laneLen * params.inputType)
  }.elsewhen(compstate === sCOMP && lane.map(_.io.valid_i).reduce(_ && _)){
    input_data_reg := input_data_reg >> (params.inputType.U * params.laneLen.U) 
  }

  val current_input_data = WireInit(0.U((params.laneLen * params.inputType).W))
  current_input_data := Mux(io.data.input_i.fire, io.data.input_i.bits(params.laneLen * params.inputType - 1, 0), input_data_reg(params.laneLen * params.inputType - 1, 0))

  // give each RescalePE right control signal and data
  // collect the result of each RescalePE
  for (i <- 0 until params.laneLen) {
    when(pe_input_valid){
      lane(i).io.input_i := current_input_data((i + 1) * params.inputType - 1, i * params.inputType).asSInt
      lane(i).io.valid_i := true.B
    }.otherwise{
      lane(i).io.input_i := 0.S
      lane(i).io.valid_i := false.B
    }
      lane(i).io.ctrl_i := ctrl_csr
      result(i) := lane(i).io.output_o
  }

  // lane output valid process counter
  val pipe_out_counter = RegInit(0.U(16.W))
  val lane_output_valid = lane.map(_.io.valid_o).reduce(_ && _)
  when(compstate === sCOMP && lane_output_valid && pipe_out_counter =/= lane_comp_cycle.U - 1.U){
    pipe_out_counter := pipe_out_counter + 1.U
  }.elsewhen(compstate === sCOMP && lane_output_valid && pipe_out_counter === lane_comp_cycle.U - 1.U){
    pipe_out_counter := 0.U
  }.elsewhen(compstate === sNotCOMP || cstate === sIDLE){
    pipe_out_counter := 0.U
  }

  // collect the valid output data
  val output_data_reg = RegInit(0.U((params.dataLen * params.outputType).W))
  when(lane_output_valid){
    output_data_reg := Cat(Cat(result.reverse), output_data_reg(params.dataLen * params.outputType - 1, params.laneLen * params.outputType))
  }

  // always valid for new input on less is sending last output
  val output_stall = WireInit(0.B)
  output_stall := io.data.output_o.valid & !io.data.output_o.ready
  io.data.input_i.ready := !keep_output && !output_stall && cstate === sBUSY && (pipe_out_counter === 0.U || pipe_out_counter === (lane_comp_cycle.U - 1.U))

  // if out valid but not ready, keep sneding output valid signal
  keep_output := output_stall

  // concat every result to a big data bus for output
  // if is keep sending output, send the stored result
  when(lane_output_valid && pipe_out_counter === lane_comp_cycle.U - 1.U){
    io.data.output_o.bits := Cat(Cat(result.reverse), output_data_reg(params.dataLen * params.outputType - 1, params.laneLen * params.outputType))
  }.otherwise{
    io.data.output_o.bits := output_data_reg
  }

  // first valid from RescalePE or keep sending valid if receiver side is not ready
  io.data.output_o.valid := (lane_output_valid && pipe_out_counter === lane_comp_cycle.U - 1.U) || keep_output

  simd_output_fire := io.data.output_o.fire
  when(simd_output_fire) {
    write_counter := write_counter + 1.U
  }.elsewhen(cstate === sIDLE) {
    write_counter := 0.U
  }

  computation_finish := (write_counter === ctrl_csr.len - 1.U) && simd_output_fire && cstate === sBUSY

  // always ready for configuration
  io.ctrl.ready := cstate === sIDLE

}

// Scala main function for generating system verilog file for the Rescale SIMD module
object PipelinedRescaleSIMD extends App {
  emitVerilog(
    new PipelinedRescaleSIMD(PipelinedConfig.rescaleSIMDConfig),
    Array("--target-dir", "generated/simd")
  )
}
