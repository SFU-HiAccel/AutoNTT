
def gen_Makefile(bestArchConfigVar):
	ARCH_IDENTITY = bestArchConfigVar.ARCH_IDENTITY
	PLATFORM_FILE = bestArchConfigVar.PLATFORM_FILE
	
	content = ""
	
	content += "###Current workdir###" + "\n"
	content += "PWD = $(shell readlink -f .)" + "\n"
	content += "" + "\n"

	content += "###Platform File###" + "\n"
	content += "# platform=xilinx_u50_gen3x16_xdma_5_202210_1" + "\n"
	content += "# platform=xilinx_u280_gen3x16_xdma_1_202211_1" + "\n"
	content += "platform=" + PLATFORM_FILE + "\n"
	content += "" + "\n"

	content += "###Default Vitis_HLS directory###" + "\n"
	content += "XILINX_HLS?=/mnt/glusterfs/tools/Xilinx/Vitis_HLS/2023.2" + "\n"
	content += "" + "\n"

	content += "###TAPA Parameters###" + "\n"
	content += "CLOCK_PERIOD=4" + "\n"
	content += "MAX_SERCH_TIME=600" + "\n"
	content += "MAX_SYNTH_JOBS=12" + "\n"
	content += "" + "\n"

	content += "###Archive Directory Name###" + "\n"
	content += "ARCHIVE_NAME = build_archive_$(shell date +%Y%m%d_%H%M%S)" + "\n"
	content += "" + "\n"

	content += "###Commands###" + "\n"

	content += "csim_compile:" + "\n"
	if (ARCH_IDENTITY=="I"):
		content += "	g++ ntt_kernel.cpp ntt_test.cpp -o ntt -I$(XILINX_HLS)/include/ -O2 -ltapa -lfrt -lglog -lgflags -lOpenCL -std=c++17 -DBU_BUF_FIFO_DEPTH=1024" + "\n"
	else:
		content += "	g++ ntt_kernel.cpp ntt_test.cpp -o ntt -I$(XILINX_HLS)/include/ -O2 -ltapa -lfrt -lglog -lgflags -lOpenCL -std=c++17" + "\n"
	content += "" + "\n"
	content += "#-fsanitize=address -g" + "\n"
	content += "" + "\n"

	content += "csim_run:" + "\n"
	content += "	./ntt" + "\n"
	content += "" + "\n"

	content += "csim:" + "\n"
	content += "	make csim_compile" + "\n"
	content += "	make csim_run" + "\n"
	content += "" + "\n"

	content += "tapa_wo_autobridge:" + "\n"
	content += "	tapac -o NTT_kernel.$(platform).hw.xo ntt_kernel.cpp \\" + "\n"
	content += "	--platform $(platform) \\" + "\n"
	content += "	--top NTT_kernel \\" + "\n"
	content += "	--connectivity link_config.ini \\" + "\n"
	content += "	--clock-period $(CLOCK_PERIOD) \\" + "\n"
	
	if(ARCH_IDENTITY=="I"):
		if(bestArchConfigVar.DOUBLE_BUF_EN):
			if(bestArchConfigVar.POLY_LS_PORTS>9):
				content += "	--read-only-args \"polyVectorIn_G[0-9][0-9]\" \\" + "\n"
				content += "	--write-only-args \"polyVectorOut_G[0-9][0-9]\" \\" + "\n"
			else:
				content += "	--read-only-args \"polyVectorIn_G[0-9]\" \\" + "\n"
				content += "	--write-only-args \"polyVectorOut_G[0-9]\" \\" + "\n"

	if(bestArchConfigVar.TF_PORTS>9):
		content += "	--read-only-args \"TFArr_G[0-9][0-9]\" \\" + "\n"
	else:
		content += "	--read-only-args \"TFArr_G[0-9]\" \\" + "\n"

	content += "	--work-dir NTT_kernel.$(platform).hw.xo.tapa" + "\n"
	content += "" + "\n"

	content += "tapa_wi_autobridge:" + "\n"
	content += "	tapac -o NTT_kernel.$(platform).hw.xo ntt_kernel.cpp \\" + "\n"
	content += "	--platform $(platform) \\" + "\n"
	content += "	--top NTT_kernel \\" + "\n"
	content += "	--connectivity link_config.ini \\" + "\n"
	content += "	--clock-period $(CLOCK_PERIOD) \\" + "\n"

	if(ARCH_IDENTITY=="I"):
		if(bestArchConfigVar.DOUBLE_BUF_EN):
			if(bestArchConfigVar.POLY_LS_PORTS>9):
				content += "	--read-only-args \"polyVectorIn_G[0-9][0-9]\" \\" + "\n"
				content += "	--write-only-args \"polyVectorOut_G[0-9][0-9]\" \\" + "\n"
			else:
				content += "	--read-only-args \"polyVectorIn_G[0-9]\" \\" + "\n"
				content += "	--write-only-args \"polyVectorOut_G[0-9]\" \\" + "\n"

	if(bestArchConfigVar.TF_PORTS>9):
		content += "	--read-only-args \"TFArr_G[0-9][0-9]\" \\" + "\n"
	else:
		content += "	--read-only-args \"TFArr_G[0-9]\" \\" + "\n"

	content += "	--enable-floorplan \\" + "\n"
	content += "	--min-area-limit 0 \\" + "\n"
	content += "	--floorplan-output constraint.tcl \\" + "\n"
	content += "	--enable-synth-util \\" + "\n"
	content += "	--enable-hbm-binding-adjustment \\" + "\n"
	content += "	--max-parallel-synth-jobs $(MAX_SYNTH_JOBS) \\" + "\n"
	content += "	--max-search-time $(MAX_SERCH_TIME) \\" + "\n"
	content += "	--work-dir NTT_kernel.$(platform).hw.xo.tapa" + "\n"
	content += "	make append_gen_post_synth_resource" + "\n"
	content += "" + "\n"

	content += "#--floorplan-pre-assignments floorplan-region-to-instances.json \\" + "\n"
	content += "# --floorplan-strategy QUICK_FLOORPLANNING \\" + "\n"
	content += "" + "\n"

	content += "#Appending report_accelerator_utilization command to constraint.tcl file will generate resource utilization after synthesis" + "\n"
	content += "append_gen_post_synth_resource: constraint.tcl" + "\n"
	content += "	-$(shell mkdir -p resource_synth)" + "\n"
	content += "	$(shell echo \"\" >> constraint.tcl)" + "\n"
	content += "	$(shell echo \"\" >> constraint.tcl)" + "\n"
	content += "	$(shell echo \"\" >> constraint.tcl)" + "\n"
	content += "	$(shell echo \"\" >> constraint.tcl)" + "\n"
	content += "	$(shell echo \"report_accelerator_utilization -kernels { level0_i:level0_i/ulp/NTT_kernel/inst/NTT_kernel_inner_0:NTT_kernel } -file $(PWD)/resource_synth/kernel_util_Full_Routed.rpt -name kernel_util_Full_Routed -json\" >> constraint.tcl)" + "\n"
	content += "" + "\n"

	content += "#Calling report_accelerator_utilization command after the build to generate resource utilization after post placement/route" + "\n"
	content += "gen_post_route_resource: vitis_run_hw/NTT_kernel_$(platform).xclbin.info" + "\n"
	content += "	-$(shell mkdir -p resource_post_place)" + "\n"
	content += "	-$(shell touch gen_post_place_resource.tcl)" + "\n"
	content += "	$(shell echo \"open_project $(PWD)/vitis_run_hw/NTT_kernel_$(platform).temp/link/vivado/vpl/prj/prj.xpr\" >> gen_post_place_resource.tcl)" + "\n"
	content += "	$(shell echo \"open_run impl_1\" >> gen_post_place_resource.tcl)" + "\n"
	content += "	$(shell echo \"report_accelerator_utilization -kernels { level0_i:level0_i/ulp/NTT_kernel/inst/NTT_kernel_inner_0:NTT_kernel } -file $(PWD)/resource_post_place/kernel_util_Full_Routed.rpt -name kernel_util_Full_Routed -json\" >> gen_post_place_resource.tcl)" + "\n"
	content += "	$(shell echo \"exit\" >> gen_post_place_resource.tcl)" + "\n"
	content += "	vivado -mode tcl -source gen_post_place_resource.tcl > vivado_gen_post_place_resource.log" + "\n"
	content += "" + "\n"

	content += "append_route_aggressive_explore: NTT_kernel.$(platform).hw_generate_bitstream.sh" + "\n"
	content += "	$(shell sed -i '/PLACEMENT_STRATEGY=\"EarlyBlockPlacement\"/a ROUTE_STRATEGY=\"AggressiveExplore\"' NTT_kernel.$(platform).hw_generate_bitstream.sh)" + "\n"
	content += "	$(shell sed -i 's/ROUTE_DESIGN\.ARGS\.DIRECTIVE=\$$STRATEGY/ROUTE_DESIGN.ARGS.DIRECTIVE=\$$ROUTE_STRATEGY/' NTT_kernel.$(platform).hw_generate_bitstream.sh)" + "\n"
	content += "" + "\n"

	content += "run_fast_cosim:" + "\n"
	content += "	./ntt --bitstream=NTT_kernel.$(platform).hw.xo -xosim_work_dir cosim_workdir -xosim_save_waveform cosim_waveform" + "\n"
	content += "" + "\n"

	content += "build_cosim:" + "\n"
	content += "	$(shell sed -i 's/^TARGET=hw/# TARGET=hw/' NTT_kernel.$(platform).hw_generate_bitstream.sh)" + "\n"
	content += "	$(shell sed -i 's/^# TARGET=hw_emu/TARGET=hw_emu/' NTT_kernel.$(platform).hw_generate_bitstream.sh)" + "\n"
	content += "	$(shell sed -i 's/^# DEBUG=-g/DEBUG=-g/' NTT_kernel.$(platform).hw_generate_bitstream.sh)" + "\n"
	content += "	chmod +x NTT_kernel.$(platform).hw_generate_bitstream.sh" + "\n"
	content += "	./NTT_kernel.$(platform).hw_generate_bitstream.sh" + "\n"
	content += "" + "\n"

	content += "gen_cosim_debug_config:" + "\n"
	content += "	-$(shell touch xrt.ini)" + "\n"
	content += "	echo \"[Emulation]\" >> xrt.ini" + "\n"
	content += "	echo \"user_pre_sim_script=dump_waveforms.tcl\" >> xrt.ini" + "\n"
	content += "	echo \"debug_mode=batch\" >> xrt.ini" + "\n"
	content += "	echo \"\" >> xrt.ini" + "\n"
	content += "	echo \"[Debug]\" >> xrt.ini" + "\n"
	content += "	echo \"opencl_trace=true\" >> xrt.ini" + "\n"
	content += "	echo \"trace_buffer_size=10G\" >> xrt.ini" + "\n"
	content += "	-$(shell touch dump_waveforms.tcl)" + "\n"
	content += "	echo \"log_wave -r *\" >> dump_waveforms.tcl" + "\n"
	content += "	echo \"run all\" >> dump_waveforms.tcl" + "\n"
	content += "	echo \"exit\" >> dump_waveforms.tcl" + "\n"
	content += "	echo \"\" >> dump_waveforms.tcl" + "\n"
	content += "" + "\n"

	content += "run_cosim:" + "\n"
	content += "	make gen_cosim_debug_config" + "\n"
	content += "	./ntt --bitstream=vitis_run_hw_emu/NTT_kernel_$(platform).xclbin" + "\n"
	content += "" + "\n"

	content += "build_hw:" + "\n"
	content += "	chmod +x NTT_kernel.$(platform).hw_generate_bitstream.sh" + "\n"
	content += "	./NTT_kernel.$(platform).hw_generate_bitstream.sh" + "\n"
	content += "	make gen_post_route_resource" + "\n"
	content += "" + "\n"

	content += "run_hw:" + "\n"
	content += "	./ntt --bitstream=vitis_run_hw/NTT_kernel_$(platform).xclbin" + "\n"
	content += "" + "\n"

	content += "archive_build:" + "\n"
	content += "	mkdir -p $(ARCHIVE_NAME)/vitis_run_hw" + "\n"
	content += "	mkdir -p $(ARCHIVE_NAME)/autobridge" + "\n"
	content += "	mkdir -p $(ARCHIVE_NAME)/vitis_build_imp_rpt" + "\n"
	content += "	cp NTT_kernel.*.hw.xo.tapa/autobridge/floorplan-region-to-instances.json $(ARCHIVE_NAME)/autobridge -rf" + "\n"
	content += "	cp NTT_kernel.*.hw.xo.tapa/autobridge/autobridge-*.log $(ARCHIVE_NAME)/autobridge -rf" + "\n"
	content += "	-cp resource_synth $(ARCHIVE_NAME)/ -rf" + "\n"
	content += "	cp vitis_run_hw/NTT_kernel*.xclbin $(ARCHIVE_NAME)/vitis_run_hw/" + "\n"
	content += "	cp vitis_run_hw/NTT_kernel*.xclbin.info $(ARCHIVE_NAME)/vitis_run_hw/" + "\n"
	content += "	cp vitis_run_hw/NTT_kernel_$(platform).temp/reports/link/imp/impl_1_full_util_routed.rpt $(ARCHIVE_NAME)/vitis_build_imp_rpt/" + "\n"
	content += "	cp vitis_run_hw/NTT_kernel_$(platform).temp/reports/link/imp/impl_1_hw_bb_locked_timing_summary_postroute_physopted.rpt $(ARCHIVE_NAME)/vitis_build_imp_rpt/" + "\n"
	content += "	gzip $(ARCHIVE_NAME)/vitis_build_imp_rpt/impl_1_full_util_routed.rpt" + "\n"
	content += "	gzip $(ARCHIVE_NAME)/vitis_build_imp_rpt/impl_1_hw_bb_locked_timing_summary_postroute_physopted.rpt" + "\n"
	content += "	-cp resource_post_place $(ARCHIVE_NAME)/ -rf" + "\n"
	content += "" + "\n"

	content += "clean:" + "\n"
	content += "	rm -rf ntt" + "\n"
	content += "	rm -rf NTT_kernel.$(platform).hw.xo" + "\n"
	content += "	rm -rf NTT_kernel.$(platform).hw.xo.tapa" + "\n"
	content += "	rm -rf NTT_kernel.$(platform).hw_generate_bitstream.sh" + "\n"
	content += "	rm -rf NTT_kernel.$(platform).hw_emu.xclbin" + "\n"
	content += "	rm -rf NTT_kernel.$(platform).hw_emu.xclbin.info" + "\n"
	content += "	rm -rf NTT_kernel.$(platform).hw_emu.xclbin.link_summary" + "\n"
	content += "	rm -rf *.log" + "\n"
	content += "	rm -rf vivado*.jou" + "\n"
	content += "	rm -rf _x" + "\n"
	content += "	rm -rf .Xil" + "\n"
	content += "	rm -rf cosim_waveform cosim_workdir" + "\n"
	content += "	rm -rf vitis_run_hw" + "\n"
	content += "	rm -rf vitis_run_hw_emu" + "\n"
	content += "	rm -rf .ipcache .Xil" + "\n"
	content += "	-rm -rf /tmp/.frt.*" + "\n"
	content += "	rm -rf constraint.tcl" + "\n"
	content += "	rm -rf gen_post_place_resource.tcl" + "\n"
	content += "	rm -rf resource_synth" + "\n"
	content += "	rm -rf resource_post_place" + "\n"
	content += "	rm -rf xrt.ini" + "\n"
	content += "	rm -rf xrt.run_summary" + "\n"
	content += "	rm -rf dump_waveforms.tcl" + "\n"
	content += "	rm -rf *.wdb" + "\n"
	content += "	rm -rf *.csv" + "\n"
	content += "" + "\n"
	content += ".PHONY:" + "\n"
	content += "	make clean" + "\n"
	content += "	make csim_compile" + "\n"
	content += "	make tapa_complete" + "\n"
	content += "	make build_hw" + "\n"

	return content