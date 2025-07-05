import logging
import math

from code_generators.modmul.config import NAIVE_RED, BARRETT, MONTGOMERY, WLM, CUSTOM_REDUCTION

from dse.common.BU.BU_models import calc_BU_pipe_depth
from dse.common.BU.BU_models import calc_BU_DSPs
from dse.common.BU.BU_models import calc_BU_LUTs
from dse.common.BU.BU_models import calc_BU_FFs
from dse.common.BU.BU_models import get_custom_reduction_BU_attributes

from dse.dse_config import GLOBAL_TARGET_FREQ_MHZ

# Calculate BU pipeline depth and resources
def calc_BU_attributes(DSEParamsVar):

    if(DSEParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        BU_pipeline_depth, DSPs_per_BU, LUTs_per_BU, FFs_per_BU = get_custom_reduction_BU_attributes(DSEParamsVar)
    else:
        # get BU pipeline depth cycles
        BU_pipeline_depth = calc_BU_pipe_depth(DSEParamsVar)

        # get BU resources
        DSPs_per_BU = calc_BU_DSPs(DSEParamsVar)
        LUTs_per_BU = calc_BU_LUTs(DSEParamsVar)
        FFs_per_BU = calc_BU_FFs(DSEParamsVar)


    DSEParamsVar.BU_PIPELINE_DEPTH_CYCLES = BU_pipeline_depth
    DSEParamsVar.BU_RESOURCE["DSP"] = DSPs_per_BU
    DSEParamsVar.BU_RESOURCE["LUT"] = LUTs_per_BU
    DSEParamsVar.BU_RESOURCE["FF"] = FFs_per_BU

    logging.getLogger("calc_BU_attributes").debug(f"BU details: DSPs = {DSPs_per_BU}, LUTs = {LUTs_per_BU}, FFs = {FFs_per_BU}, Depth = {BU_pipeline_depth}")

# Based on the WORD_SIZE, reduction type and available #DSPs
# this function calculate the possible maximum number of BUs.
def calc_BU_budget(DSEParamsVar):
    num_of_dsps = DSEParamsVar.DEVICE_RESOURCES["DSP"]
    num_of_dsps_per_BU = DSEParamsVar.BU_RESOURCE["DSP"]
    
    #Calculate number of possible BUs based on the DSP count
    num_of_max_BUs = num_of_dsps//num_of_dsps_per_BU

    logging.getLogger("calc_BU_budget").debug(f"#DSPs = {num_of_dsps}, #DSPs per BU = {num_of_dsps_per_BU}, Possible #BUs = {num_of_max_BUs}")
    logging.getLogger("calc_BU_budget").info(f"Calculated possible maximum #BUs as {num_of_max_BUs}")

    return num_of_max_BUs


# Based on the given BW, calculate number of DRAM ports user have specified to use
def calc_num_dram_ports(DSEParamsVar):
    allowed_max_bw = DSEParamsVar.DEVICE_RESOURCES["offchip_BW"]
    DRAM_BW_PER_PORT = DSEParamsVar.DRAM_BW_PER_PORT

    number_of_ports = math.floor(allowed_max_bw//DRAM_BW_PER_PORT)

    logging.getLogger("calc_num_dram_ports").debug(f"Allowed BW = {allowed_max_bw} GB/s, BW per port = {DRAM_BW_PER_PORT} GB/s, Possible maximum #DRAM ports = {number_of_ports}")
    logging.getLogger("calc_num_dram_ports").info(f"Calculated possible maximum #DRAM ports as {number_of_ports}")

    return number_of_ports

# Based on the WORD_SIZE set DRAM_WORD_SIZE which is the minimum data width allocated in DRAM data for each data
def calc_DRAM_WORD_SIZE(DSEParamsVar):
    DRAM_WORD_SIZE= 64 if (DSEParamsVar.WORD_SIZE>32) else 32
    return DRAM_WORD_SIZE

def calc_dse_precompute(DSEParamsVar):

    # Calculate number of DRAM ports allowed based on the BW provided
    DSEParamsVar.NUM_DRAM_PORTS = calc_num_dram_ports(DSEParamsVar)

    # Update DRAM_WORD_SIZE parameter
    DSEParamsVar.DRAM_WORD_SIZE = calc_DRAM_WORD_SIZE(DSEParamsVar)

    # Set target frequency
    DSEParamsVar.TARGET_FREQ_MHZ = GLOBAL_TARGET_FREQ_MHZ
    logging.getLogger("calc_dse_precompute").info(f"Setting target clock frequency to {DSEParamsVar.TARGET_FREQ_MHZ} MHz")

    # Calculate BU pipeline depth and resources
    calc_BU_attributes(DSEParamsVar)
    
    # Calculate number of BUs based on DSPs
    DSEParamsVar.NUM_BU_BUDGET = calc_BU_budget(DSEParamsVar)

# Out of all the designs this function selects the lowest latency design
def select_best_design(iterativeConfigsVar, dataflowConfigsVar, hybridConfigsVar):
    candidates = [
        iterativeConfigsVar,
        dataflowConfigsVar,
        hybridConfigsVar
    ]

    # Filter out any None candidates, in case some are missing
    candidates = [c for c in candidates if c is not None]

    # Use min() with a key to compare based on EXPECTED_LATENCY_MS
    best_config = min(candidates, key=lambda config: config.EXPECTED_LATENCY_MS)

    logging.getLogger("select_best_design").info(f"Selected the best option as AutoNTT-{best_config.ARCH_IDENTITY}.")
    logging.getLogger("select_best_design").info(f"Estimated performance of the selected design: Latency = {best_config.EXPECTED_LATENCY_MS} ms, Throughput = {best_config.EXPECTED_THROUGHPUT} NTT/s")
    logging.getLogger("select_best_design").info(f"Estimated resources of the selected design: LUT = {best_config.DESIGN_RESOURCES['LUT']}, FF = {best_config.DESIGN_RESOURCES['FF']}, DSP = {best_config.DESIGN_RESOURCES['DSP']}, BRAM = {best_config.DESIGN_RESOURCES['BRAM']}, URAM = {best_config.DESIGN_RESOURCES['URAM']}, DRAM Ports = {best_config.DESIGN_RESOURCES['offchip_ports']}")

    return best_config