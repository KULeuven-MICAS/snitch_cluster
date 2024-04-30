package streamer

import chisel3._
import chisel3.util._

// the DataReaderWriter class is a module that can both reads and writes data
// It instantiates a DataReader and a DataWriter module, each has its own seperate set of CSR, temporal/spatial address generation unit... 
// The reader and writer work in dependetly but share the reqeust ports to TCDM
// To decide whether to read or write, the DataReaderWriter module uses a control signal
// When one of the DataReader or DataWriter needs send request to TCDM (read fifo empty or write fifo not empty), choose the one that needs to send request
// when both DataReader and DataWriter needs to send request, choose the writer first
// When none of them needs to send request, chill a bit
class DataReaderWriter extends Module {
  val io = IO(new Bundle {

  })


}
