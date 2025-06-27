###Current workdir###
PWD = $(shell readlink -f .)

###Platform File###
# platform=xilinx_u50_gen3x16_xdma_5_202210_1
# platform=xilinx_u280_gen3x16_xdma_1_202211_1
platform=xilinx_u280_gen3x16_xdma_1_202211_1

###Default Vitis_HLS directory###
XILINX_HLS?=/mnt/glusterfs/tools/Xilinx/Vitis_HLS/2023.2

###TAPA Parameters###
CLOCK_PERIOD=4
MAX_SERCH_TIME=600
MAX_SYNTH_JOBS=12

###Archive Directory Name###
ARCHIVE_NAME = build_archive_$(shell date +%Y%m%d_%H%M%S)

###Commands###
csim_compile:
	g++ ntt_kernel.cpp ntt_test.cpp -o ntt -I$(XILINX_HLS)/include/ -O2 -ltapa -lfrt -lglog -lgflags -lOpenCL -std=c++17 -DBU_BUF_FIFO_DEPTH=1024

#-fsanitize=address -g

csim_run:
	./ntt

csim:
	make csim_compile
	make csim_run

tapa_wo_autobridge:
	tapac -o NTT_kernel.$(platform).hw.xo ntt_kernel.cpp \
	--platform $(platform) \
	--top NTT_kernel \
	--connectivity link_config.ini \
	--clock-period $(CLOCK_PERIOD) \
	--read-only-args "polyVectorIn_G[0-9]" \
	--write-only-args "polyVectorOut_G[0-9]" \
	--read-only-args "TFArr_G[0-9]" \
	--work-dir NTT_kernel.$(platform).hw.xo.tapa

tapa_wi_autobridge:
	tapac -o NTT_kernel.$(platform).hw.xo ntt_kernel.cpp \
	--platform $(platform) \
	--top NTT_kernel \
	--connectivity link_config.ini \
	--clock-period $(CLOCK_PERIOD) \
	--read-only-args "polyVectorIn_G[0-9]" \
	--write-only-args "polyVectorOut_G[0-9]" \
	--read-only-args "TFArr_G[0-9]" \
	--enable-floorplan \
	--min-area-limit 0 \
	--floorplan-output constraint.tcl \
	--enable-synth-util \
	--enable-hbm-binding-adjustment \
	--max-parallel-synth-jobs $(MAX_SYNTH_JOBS) \
	--max-search-time $(MAX_SERCH_TIME) \
	--work-dir NTT_kernel.$(platform).hw.xo.tapa
	make append_gen_post_synth_resource

#--floorplan-pre-assignments floorplan-region-to-instances.json \
# --floorplan-strategy QUICK_FLOORPLANNING \

#Appending report_accelerator_utilization command to constraint.tcl file will generate resource utilization after synthesis
append_gen_post_synth_resource: constraint.tcl
	-$(shell mkdir -p resource_synth)
	$(shell echo "" >> constraint.tcl)
	$(shell echo "" >> constraint.tcl)
	$(shell echo "" >> constraint.tcl)
	$(shell echo "" >> constraint.tcl)
	$(shell echo "report_accelerator_utilization -kernels { level0_i:level0_i/ulp/NTT_kernel/inst/NTT_kernel_inner_0:NTT_kernel } -file $(PWD)/resource_synth/kernel_util_Full_Routed.rpt -name kernel_util_Full_Routed -json" >> constraint.tcl)

#Calling report_accelerator_utilization command after the build to generate resource utilization after post placement/route
gen_post_route_resource: vitis_run_hw/NTT_kernel_$(platform).xclbin.info
	-$(shell mkdir -p resource_post_place)
	-$(shell touch gen_post_place_resource.tcl)
	$(shell echo "open_project $(PWD)/vitis_run_hw/NTT_kernel_$(platform).temp/link/vivado/vpl/prj/prj.xpr" >> gen_post_place_resource.tcl)
	$(shell echo "open_run impl_1" >> gen_post_place_resource.tcl)
	$(shell echo "report_accelerator_utilization -kernels { level0_i:level0_i/ulp/NTT_kernel/inst/NTT_kernel_inner_0:NTT_kernel } -file $(PWD)/resource_post_place/kernel_util_Full_Routed.rpt -name kernel_util_Full_Routed -json" >> gen_post_place_resource.tcl)
	$(shell echo "exit" >> gen_post_place_resource.tcl)
	vivado -mode tcl -source gen_post_place_resource.tcl > vivado_gen_post_place_resource.log

append_route_aggressive_explore: NTT_kernel.$(platform).hw_generate_bitstream.sh
	$(shell sed -i '/PLACEMENT_STRATEGY="EarlyBlockPlacement"/a ROUTE_STRATEGY="AggressiveExplore"' NTT_kernel.$(platform).hw_generate_bitstream.sh)
	$(shell sed -i 's/ROUTE_DESIGN\.ARGS\.DIRECTIVE=\$$STRATEGY/ROUTE_DESIGN.ARGS.DIRECTIVE=\$$ROUTE_STRATEGY/' NTT_kernel.$(platform).hw_generate_bitstream.sh)

run_fast_cosim:
	./ntt --bitstream=NTT_kernel.$(platform).hw.xo -xosim_work_dir cosim_workdir -xosim_save_waveform cosim_waveform

build_cosim:
	$(shell sed -i 's/^TARGET=hw/# TARGET=hw/' NTT_kernel.$(platform).hw_generate_bitstream.sh)
	$(shell sed -i 's/^# TARGET=hw_emu/TARGET=hw_emu/' NTT_kernel.$(platform).hw_generate_bitstream.sh)
	$(shell sed -i 's/^# DEBUG=-g/DEBUG=-g/' NTT_kernel.$(platform).hw_generate_bitstream.sh)
	chmod +x NTT_kernel.$(platform).hw_generate_bitstream.sh
	./NTT_kernel.$(platform).hw_generate_bitstream.sh

gen_cosim_debug_config:
	-$(shell touch xrt.ini)
	echo "[Emulation]" >> xrt.ini
	echo "user_pre_sim_script=dump_waveforms.tcl" >> xrt.ini
	echo "debug_mode=batch" >> xrt.ini
	echo "" >> xrt.ini
	echo "[Debug]" >> xrt.ini
	echo "opencl_trace=true" >> xrt.ini
	echo "trace_buffer_size=10G" >> xrt.ini
	-$(shell touch dump_waveforms.tcl)
	echo "log_wave -r *" >> dump_waveforms.tcl
	echo "run all" >> dump_waveforms.tcl
	echo "exit" >> dump_waveforms.tcl
	echo "" >> dump_waveforms.tcl

run_cosim:
	make gen_cosim_debug_config
	./ntt --bitstream=vitis_run_hw_emu/NTT_kernel_$(platform).xclbin

build_hw:
	chmod +x NTT_kernel.$(platform).hw_generate_bitstream.sh
	./NTT_kernel.$(platform).hw_generate_bitstream.sh
	make gen_post_route_resource

run_hw:
	./ntt --bitstream=vitis_run_hw/NTT_kernel_$(platform).xclbin

archive_build:
	mkdir -p $(ARCHIVE_NAME)/vitis_run_hw
	mkdir -p $(ARCHIVE_NAME)/autobridge
	mkdir -p $(ARCHIVE_NAME)/vitis_build_imp_rpt
	cp NTT_kernel.*.hw.xo.tapa/autobridge/floorplan-region-to-instances.json $(ARCHIVE_NAME)/autobridge -rf
	cp NTT_kernel.*.hw.xo.tapa/autobridge/autobridge-*.log $(ARCHIVE_NAME)/autobridge -rf
	-cp resource_synth $(ARCHIVE_NAME)/ -rf
	cp vitis_run_hw/NTT_kernel*.xclbin $(ARCHIVE_NAME)/vitis_run_hw/
	cp vitis_run_hw/NTT_kernel*.xclbin.info $(ARCHIVE_NAME)/vitis_run_hw/
	cp vitis_run_hw/NTT_kernel_$(platform).temp/reports/link/imp/impl_1_full_util_routed.rpt $(ARCHIVE_NAME)/vitis_build_imp_rpt/
	cp vitis_run_hw/NTT_kernel_$(platform).temp/reports/link/imp/impl_1_hw_bb_locked_timing_summary_postroute_physopted.rpt $(ARCHIVE_NAME)/vitis_build_imp_rpt/
	gzip $(ARCHIVE_NAME)/vitis_build_imp_rpt/impl_1_full_util_routed.rpt
	gzip $(ARCHIVE_NAME)/vitis_build_imp_rpt/impl_1_hw_bb_locked_timing_summary_postroute_physopted.rpt
	-cp resource_post_place $(ARCHIVE_NAME)/ -rf

clean:
	rm -rf ntt
	rm -rf NTT_kernel.$(platform).hw.xo
	rm -rf NTT_kernel.$(platform).hw.xo.tapa
	rm -rf NTT_kernel.$(platform).hw_generate_bitstream.sh
	rm -rf NTT_kernel.$(platform).hw_emu.xclbin
	rm -rf NTT_kernel.$(platform).hw_emu.xclbin.info
	rm -rf NTT_kernel.$(platform).hw_emu.xclbin.link_summary
	rm -rf *.log
	rm -rf vivado*.jou
	rm -rf _x
	rm -rf .Xil
	rm -rf cosim_waveform cosim_workdir
	rm -rf vitis_run_hw
	rm -rf vitis_run_hw_emu
	rm -rf .ipcache .Xil
	-rm -rf /tmp/.frt.*
	rm -rf constraint.tcl
	rm -rf gen_post_place_resource.tcl
	rm -rf resource_synth
	rm -rf resource_post_place
	rm -rf xrt.ini
	rm -rf xrt.run_summary
	rm -rf dump_waveforms.tcl
	rm -rf *.wdb
	rm -rf *.csv

.PHONY:
	make clean
	make csim_compile
	make tapa_complete
	make build_hw
