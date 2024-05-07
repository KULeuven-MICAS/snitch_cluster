simd=`bender path snax-streamer-simd-dev`
gemm=`bender path snax-streamer-gemm-dev`
sd=`bender path snax-data-reshuffler-dev`
cd $simd && make `pwd`/rtl/streamer-simd/streamer_simd_wrapper.sv
cd $gemm && make `pwd`/rtl/streamer-gemm/streamer_gemm_wrapper.sv
cd $sd && make `pwd`/tests/tb/tb_stream_dev_reshuffler.sv
