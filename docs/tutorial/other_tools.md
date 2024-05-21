# Other Tools

There are two useful tools for debugging and verifying your work. (1) Dumping waveform VCD files and (2) program stack tracing.

# Dumping Wavefors with VCD Files

To dump VCD files through simulation we only need to add the `--vcd` when running simulations.

```bash
bin/snitch_cluster.vlt sw/apps/snax-alu/build/snax-alu.elf --vcd
```
The dumped file will be named as `sim.vcd`. You can view this with your favorite waveform viewing tool:

```
gtkwave sim.vcd &
```

!!! note

    If you're using the codespace, you need to download the `sim.vcd` file first and open it locally in your personal work space.

# Program Tracing with Spike

Spike is a nice tool for converting disassembly files into traces of the simulation. When your run the simulations with:

```bash
bin/snitch_cluster.vlt sw/apps/snax-alu/build/snax-alu.elf
```
This creates a set of log files under the `./target/snitch_cluster/logs/.` directory. Then you should see `.dasm` files: 

```
trace_hart_00000.dasm
trace_hart_00001.dasm
```

These are disassembly files for each core. `trace_hart_00000.dasm` is for core 0 which is the core with the SNAX ALU accelerator, while `trace_hart_00001.dasm` is for core 1 which is the core with the DMA. We would like to convert these files into traces that are more readable. We will use `spike` for this.

## Installing Spike

1 - Navigate to `./target/snitch_cluster/work-vlt/riscv-isa-sim/.`

2 - Configure the `spike` installation with:

```bash
./configure --prefix=/opt/spike/
```

3 - Install `spike` and wait for a while for this to finish. This will take quite some time.

```bash
make install -j
```

4 - Add to path environment:

```bash
export PATH="/opt/spike/bin:$PATH"
```

5 - Check if `spike` is correctly installed:

```bash
spike -h
```

## Running Traces

We can now generate traces. Make sure you are in the ``./target/snitch_cluster/` directory.

1 - Run simulations first:

```bash
bin/snitch_cluster.vlt sw/apps/snax-alu/build/snax-alu.elf
```

2 - Make traces:

```bash
make traces
```

## Investigating Traces

