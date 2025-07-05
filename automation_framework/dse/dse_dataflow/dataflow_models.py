import math
import logging

from types import SimpleNamespace

from dse.common.helper_functions import calc_log2
from dse.common.helper_functions import nearest_lower_power_of_two
from dse.common.helper_functions import evaluate_polynomial

from dse.dse_config import BRAM_WIDTH, BRAM_DEPTH
from dse.dse_config import URAM_WIDTH, URAM_DEPTH
from dse.dse_config import GLOBAL_TARGET_FREQ_MHZ
from dse.dse_config import AXI_INTERCONNECT_RESOURCES

from code_generators.dataflow.poly_load_store.poly_load_store import calc_poly_load_store_port_num

from code_generators.dataflow.TFs.TF_load import calc_TF_load_port_num

#### Variables define ####

# Pipeline depths 
# TODO: update shuffler depths according to split stratergies and incorporate in the model

IN_SEL_PIPE_DEPTH = 3
OUT_SEL_PIPE_DEPTH = 3
SHUFFLER_PIPE_DEPTH = 13 # shuffler_in = 3, shuffler_buf = 4, shuffler_out_shift =  3, shuffler_out_shuff = 3
LOAD_STORE_PIPE_DEPTH = 3

# Resource model values
# coeffients are recorded in ascending order
TFBuf_resource_model_table = {
    "LUT": [84.801, 6.5369],
    "FF": [137.9, 6.3299]
}

in_out_fifo_resource_model_table = {
    "LUT": [61.196, 3.4592],
    "FF": [21.351, 4.7117]
}

in_selector_resource_model_table = {
    "LUT": [78.744, 4.3979],
    "FF": [70.723, 2.5622]
}

out_selector_resource_model_table = {
    "LUT": [73.603, 4.4923],
    "FF": [51.726, 3.4411]
}

shuffler_in_resource_model_table = {
    "LUT": [17.852, 6.3247],
    "FF": [28.128, 3.0069]
}

shuffler_buf_single_resource_model_table = {
    "LUT": [417.52, 3.3243],
    "FF": [179.4, 0.9928]
}

shuffler_out_resource_model_table = {
    "LUT": [49.075, 7.9789],
    "FF": [40.731, 4.3422]
}

# This function finds the largest dataflow architecture design based on the available BU per single parallel limb.
# Essentiallt, dataflow architecture needs logN stages.
def get_max_BU_design_in_dataflow_arch(dataflowConfigsVar):
    NUM_BU_BUDGET = dataflowConfigsVar.DSEParamsVar.NUM_BU_BUDGET
    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS
    logN = dataflowConfigsVar.DSEParamsVar.logN
    DRAM_WORD_SIZE = dataflowConfigsVar.DSEParamsVar.DRAM_WORD_SIZE

    BUs_per_para_limb = (NUM_BU_BUDGET // PARA_LIMBS)

    max_vertical_BUs = BUs_per_para_limb // logN
    possible_vertical_BUs = nearest_lower_power_of_two(max_vertical_BUs)

    # Adjusting for current maximum supported BUGs
    if((DRAM_WORD_SIZE==32) and (possible_vertical_BUs>32)):
        logging.getLogger("get_max_BU_design_in_dataflow_arch").warning(f"Largest dataflow design BUG is detected as ({ possible_vertical_BUs } x { calc_log2(2*possible_vertical_BUs) } BUG). Since maximum supported BUG for log(q)<=32 is (32x6 BUG), adjusting largest design to use (32x6 BUG)")
        possible_vertical_BUs = 32
    elif((DRAM_WORD_SIZE==64) and (possible_vertical_BUs>16)):
        logging.getLogger("get_max_BU_design_in_dataflow_arch").warning(f"Largest dataflow design BUG is detected as ({ possible_vertical_BUs } x { calc_log2(2*possible_vertical_BUs) } BUG). Since maximum supported BUG for 32<log(q)<=64 is (16x5 BUG), adjusting largest design to use (16x5 BUG)")
        possible_vertical_BUs = 16

    dataflowConfigsVar.V_BUG_SIZE = possible_vertical_BUs
    if(dataflowConfigsVar.V_BUG_SIZE != 0):
        dataflowConfigsVar.H_BUG_SIZE = calc_log2(2*dataflowConfigsVar.V_BUG_SIZE)
    else:
        dataflowConfigsVar.H_BUG_SIZE = 0
    dataflowConfigsVar.NUM_BU = dataflowConfigsVar.V_BUG_SIZE * logN
    dataflowConfigsVar.V_TOTAL_DATA = 2 * dataflowConfigsVar.V_BUG_SIZE

    logging.getLogger("get_max_BU_design_in_dataflow_arch").trace(f"Largest dataflow design BUG: ({ dataflowConfigsVar.V_BUG_SIZE } x { dataflowConfigsVar.H_BUG_SIZE } BUG), Total BUs = { dataflowConfigsVar.NUM_BU }")

def set_next_largest_design(dataflowConfigsVar):
    logN = dataflowConfigsVar.DSEParamsVar.logN
    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE

    dataflowConfigsVar.V_BUG_SIZE = V_BUG_SIZE // 2
    if(dataflowConfigsVar.V_BUG_SIZE != 0):
        dataflowConfigsVar.H_BUG_SIZE = calc_log2(2*dataflowConfigsVar.V_BUG_SIZE)
    else:
        dataflowConfigsVar.H_BUG_SIZE = 0
    dataflowConfigsVar.NUM_BU = dataflowConfigsVar.V_BUG_SIZE * logN
    dataflowConfigsVar.V_TOTAL_DATA = 2 * dataflowConfigsVar.V_BUG_SIZE

    logging.getLogger("set_next_largest_design").trace(f"Next largest dataflow design BUG: ({ dataflowConfigsVar.V_BUG_SIZE } x { dataflowConfigsVar.H_BUG_SIZE } BUG), Total BUs = { dataflowConfigsVar.NUM_BU }")

# This function calculates the shuffler buffer depth for each shuffler and return it as an array
def calc_shuffler_buf_depth(dataflowConfigsVar):
    logN = dataflowConfigsVar.DSEParamsVar.logN
    POLY_SIZE = dataflowConfigsVar.DSEParamsVar.POLY_SIZE
    H_BUG_SIZE = dataflowConfigsVar.H_BUG_SIZE
    V_TOTAL_DATA = dataflowConfigsVar.V_TOTAL_DATA

    num_shufflers = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1
    
    shuf_buf_depth_arr = []

    for shuffler_id in range(num_shufflers):

        if shuffler_id != (num_shufflers - 1):
            buffer_size = (1 << (shuffler_id * H_BUG_SIZE)) << (H_BUG_SIZE + 1)
        else: #if the last shuffler
            if( (logN%H_BUG_SIZE) != 0 ): # if a partial BUG
                buffer_size = POLY_SIZE//V_TOTAL_DATA
            else: # not a partial BUG
                buffer_size = (1 << (shuffler_id * H_BUG_SIZE)) << (H_BUG_SIZE + 1) >> 1
        shuf_buf_depth_arr.append(buffer_size)
    
    return shuf_buf_depth_arr

# This function calculates the shuffler buffer delay for each round and return it as an array
# Delaye is equal to buffer_size/2 for each shuffler except the last one. 
# Delaye is equal to buffer_size in the last shuffler. 
def dataflow_calc_buf_delay(dataflowConfigsVar):

    logN = dataflowConfigsVar.DSEParamsVar.logN
    H_BUG_SIZE = dataflowConfigsVar.H_BUG_SIZE

    num_shufflers = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1
    
    shuf_buf_depth_arr = calc_shuffler_buf_depth(dataflowConfigsVar)

    shuf_wait_cycles = []

    for shuffler_id in range(num_shufflers):
        buffer_depth = shuf_buf_depth_arr[shuffler_id]
        
        if shuffler_id != (num_shufflers - 1):
            wait_cycles = buffer_depth >> 1
        else: #if the last shuffler
            wait_cycles = buffer_depth

        shuf_wait_cycles.append(wait_cycles)
        
    return shuf_wait_cycles

# Calculate latency and throughput
def calc_comp_latency_cycles(dataflowConfigsVar):
    POLY_SIZE = dataflowConfigsVar.DSEParamsVar.POLY_SIZE
    logN = dataflowConfigsVar.DSEParamsVar.logN

    BU_PIPELINE_DEPTH_CYCLES = dataflowConfigsVar.DSEParamsVar.BU_PIPELINE_DEPTH_CYCLES
    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = dataflowConfigsVar.H_BUG_SIZE
    V_TOTAL_DATA = dataflowConfigsVar.V_TOTAL_DATA

    num_shufflers = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1

    #calc number of inputs
    num_of_inputs = POLY_SIZE//V_TOTAL_DATA

    #### calc pipeline depth ####
    pipeline_depth = 0 
    # Load and store tasks
    pipeline_depth += LOAD_STORE_PIPE_DEPTH*2 
    
    # All BUs accross BUGs
    pipeline_depth += BU_PIPELINE_DEPTH_CYCLES*logN
    
    # All shufflers except their internal wait time
    pipeline_depth += SHUFFLER_PIPE_DEPTH*num_shufflers
    
    #calc buf delay in each round
    buf_delay_table = dataflow_calc_buf_delay(dataflowConfigsVar)

    #calc compute time
    exp_latency_cycles = pipeline_depth
    #1st calc time for the rounds going throgh shuffler
    for shuff_idx in range(num_shufflers): #only going through shuffler (num_of_rounds-1) time

        buf_delay = buf_delay_table[shuff_idx]
        
        exp_latency_cycles += buf_delay

    #And num_of_inputs time is taken to output all the outputs
    exp_latency_cycles += num_of_inputs

    dataflowConfigsVar.COMPUTE_LATECY_CYCLES = exp_latency_cycles

    logging.getLogger("calc_comp_latency_cycles").trace(f"compute cycles = {dataflowConfigsVar.COMPUTE_LATECY_CYCLES}")



# Poly load/store ports in dataflow architecture do not depend on the number of cycles, but on the design width i.e., total number of vertical BUs.
# It is important to notice that this only returns required for either poly loading or storing
def calc_best_BW_for_poly_load_or_store(dataflowConfigsVar):

    DRAM_WORD_SIZE = dataflowConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
    DRAM_PORT_WIDTH = dataflowConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH
    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE

    CONCAT_FACTOR = V_BUG_SIZE << 1

    params = SimpleNamespace(
                                DRAM_WORD_SIZE=DRAM_WORD_SIZE,
                                CONCAT_FACTOR = CONCAT_FACTOR,
                                DEFAULT_DRAM_PORT_WIDTH=DRAM_PORT_WIDTH
                                )

    min_port_width, min_num_ports = calc_poly_load_store_port_num(params)

    logging.getLogger("calc_best_BW_for_poly_load_or_store").trace(f"Per limb optimum #ports = {min_num_ports}, port width = {min_port_width}")

    return min_num_ports, min_port_width


# With the current implementation, we dedicate port(s) per each BUG and for the last layer.
# For each above there can be one or more ports deployed based on the parallelism required.
# This function use the code generator's code to calculate required amount of TF ports.
def calc_best_BW_for_TF_load(dataflowConfigsVar):
    DRAM_WORD_SIZE = dataflowConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
    DRAM_PORT_WIDTH = dataflowConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    logN = dataflowConfigsVar.DSEParamsVar.logN
    H_BUG_SIZE = dataflowConfigsVar.H_BUG_SIZE
    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE
    
    CONCAT_FACTOR = V_BUG_SIZE << 1
    LAST_H_BU_NUM = logN % H_BUG_SIZE
    
    params = SimpleNamespace(
                            DRAM_WORD_SIZE=DRAM_WORD_SIZE,
                            CONCAT_FACTOR = CONCAT_FACTOR,
                            DEFAULT_DRAM_PORT_WIDTH=DRAM_PORT_WIDTH,
                            logN=logN,
                            LAST_H_BU_NUM=LAST_H_BU_NUM,
                            H_BU_NUM=H_BUG_SIZE
                            )
    
    TF_port_width, TF_ports_per_single_load_seg, total_TF_ports = calc_TF_load_port_num(params)

    logging.getLogger("calc_best_BW_for_TF_load").trace(f"Per limb optimum #ports per load segment = {TF_ports_per_single_load_seg}, #segments = {total_TF_ports//TF_ports_per_single_load_seg}, # total ports = {total_TF_ports},  port width = {TF_port_width}")

    return total_TF_ports, TF_ports_per_single_load_seg, TF_port_width


# Calculate latency and throughput
def calc_latency_throughput(dataflowConfigsVar):
    POLY_SIZE = dataflowConfigsVar.DSEParamsVar.POLY_SIZE
    COMPUTE_LATECY_CYCLES = dataflowConfigsVar.COMPUTE_LATECY_CYCLES
    V_TOTAL_DATA = dataflowConfigsVar.V_TOTAL_DATA

    exp_latency_cycles = COMPUTE_LATECY_CYCLES

    exp_latency_s = exp_latency_cycles / (GLOBAL_TARGET_FREQ_MHZ*1000000)
    exp_latency_ms = exp_latency_s*1000

    # In the dataflow architecture, after initial latency, every cycle release a new data for new polynomail. 
    # During this calculation assume DDR access period is same as the global target frequency 250MHz. There is a slight different with HBM, in which it usually is 225 MHz.
    cycles_to_output_poly = POLY_SIZE//V_TOTAL_DATA
    exp_throughput = (GLOBAL_TARGET_FREQ_MHZ*1000000 - exp_latency_cycles)//cycles_to_output_poly + 1 # +1 is for the 1st input included in exp_latency_cycles

    dataflowConfigsVar.EXPECTED_LATENCY_MS = exp_latency_ms
    dataflowConfigsVar.EXPECTED_THROUGHPUT = exp_throughput

    logging.getLogger("calc_latency_throughput").trace(f"Expected latency = {dataflowConfigsVar.EXPECTED_LATENCY_MS} ms, expected throughput(#NTT/s) = {dataflowConfigsVar.EXPECTED_THROUGHPUT}")

def calc_DRAM_ports_utilization(dataflowConfigsVar):
    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS
    DRAM_PORT_WIDTH = dataflowConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    POLY_LS_PORTS_PER_PARA_LIMB = dataflowConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = dataflowConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB

    V_TF_PORTS_PER_PARA_LIMB = dataflowConfigsVar.V_TF_PORTS_PER_PARA_LIMB
    H_TF_PORTS_PER_PARA_LIMB = dataflowConfigsVar.H_TF_PORTS_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = dataflowConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB

    poly_ls_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)) * POLY_LS_PORTS_PER_PARA_LIMB
    tf_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB)) * V_TF_PORTS_PER_PARA_LIMB * H_TF_PORTS_PER_PARA_LIMB

    total_ports = poly_ls_ports*2 + tf_ports

    dataflowConfigsVar.DESIGN_RESOURCES["offchip_ports"] = total_ports

# Calculate DSP resource utilization
def calc_DSP_utilization(dataflowConfigsVar):
    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS
    logN = dataflowConfigsVar.DSEParamsVar.logN
    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE

    num_of_dsps_per_BU = dataflowConfigsVar.DSEParamsVar.BU_RESOURCE["DSP"]

    total_DSPs = num_of_dsps_per_BU * (V_BUG_SIZE * logN) * PARA_LIMBS

    dataflowConfigsVar.DESIGN_RESOURCES["DSP"] = total_DSPs


def calc_BRAM_utilization_for_poly(dataflowConfigsVar):
    
    logN = dataflowConfigsVar.DSEParamsVar.logN
    WORD_SIZE = dataflowConfigsVar.DSEParamsVar.WORD_SIZE
    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS
    V_TOTAL_DATA = dataflowConfigsVar.V_TOTAL_DATA
    H_BUG_SIZE = dataflowConfigsVar.H_BUG_SIZE
    
    #### Shuffler buffers ####
    num_shufflers = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1

    num_of_shuffler_buffers = V_TOTAL_DATA

    shuf_buf_depth_arr = calc_shuffler_buf_depth(dataflowConfigsVar)

    total_BRAMs = 0

    for shuff_idx in range(num_shufflers):
        buffer_depth = shuf_buf_depth_arr[shuff_idx]
        if(buffer_depth < (BRAM_DEPTH//2)): # BRAM 18k can work as 36bitx512
            BRAMs_per_buffer = math.ceil(WORD_SIZE/(2*BRAM_WIDTH)) * math.ceil(buffer_depth/(BRAM_DEPTH//2))
        else:    
            BRAMs_per_buffer = math.ceil(WORD_SIZE/BRAM_WIDTH) * math.ceil(buffer_depth/BRAM_DEPTH)
        total_brams_for_shuffler_buffers = BRAMs_per_buffer * num_of_shuffler_buffers
        total_BRAMs += total_brams_for_shuffler_buffers
    
    total_BRAMs *= PARA_LIMBS # adjust for parallel limbs
    
    return total_BRAMs

# Calculate URAMs for TFs
# In data flow architecture, TFs in each stage s can be calculated as (2^s)
# However, based on the parallelism available (parallel BUs in BUG for each stage), all the data may not be required in each buffer.
# Hence, only required TFs are stored.
# In some stages (e.g., stage 0), only 1 TF is required. In this kind of stages, TFs are replicated, but a URAM is not used as its just one value.
# TF buffer calculation is done based on the generate_double_buffer_TFArr_declaration function in code_generators.dataflow.TFs.TF_buffers
def calc_URAM_utilization_for_tf(dataflowConfigsVar):

    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE
    
    WORD_SIZE = dataflowConfigsVar.DSEParamsVar.WORD_SIZE
    logN = dataflowConfigsVar.DSEParamsVar.logN
    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS

    total_URAMs = 0

    for stage in range(logN):
        tf_total = 1 << stage

        if V_BUG_SIZE == 1: # if single BU in a BUG case
            if(tf_total >= 32): # only if TF depth is greater than 32, buffers are getting assigned to URAMs
                URAMs_per_buffer = math.ceil(WORD_SIZE/URAM_WIDTH) * math.ceil(tf_total/URAM_DEPTH)
                num_of_TF_buffers_per_layer = 1
                URAMs_per_layer = URAMs_per_buffer * 2 * num_of_TF_buffers_per_layer # multiply by 2 for double buffer
                total_URAMs += URAMs_per_layer
        else:
            if tf_total > (V_BUG_SIZE // 2): # if all TFs can NOT be stored accross avaialble buffer (= (V_BUG_SIZE // 2))) in the layer, then only mapped into URAMs
                tfarr_dim1 = V_BUG_SIZE // 2
                tfarr_dim2 = tf_total // (V_BUG_SIZE // 2) if (tf_total // (V_BUG_SIZE // 2)) != 0 else 1
                if tfarr_dim2 >= 32: # if the depth is greater than 32, then only we bind storage to URAMs. Otherwise, we let the tool decide, which usualy goes to LUTRAMs due to small size.
                    URAMs_per_buffer = math.ceil(WORD_SIZE/URAM_WIDTH) * math.ceil(tfarr_dim2/URAM_DEPTH)
                    num_of_TF_buffers_per_layer = tfarr_dim1
                    URAMs_per_layer = URAMs_per_buffer * 2 * num_of_TF_buffers_per_layer # multiply by 2 for double buffer
                    total_URAMs += URAMs_per_layer

    total_URAMs *= PARA_LIMBS # adjust for parallel limbs

    return total_URAMs

# Calculate BRAM and URAM resource utilization
# Prioritize assigning polynomial buffer to BRAM (reason is given the paper)
# Prioritize assigning TFs to URAM to balance the resources.
# TODO: 1. Add the case where URAM is not available
# TODO: 2. Add the case where URAM is not enough, but BRAM is enough to accomodate both Poly and remaining TFs
def calc_BRAM_URAM_utilization(dataflowConfigsVar):

    # get number of BRAMs required for polynomials
    dataflowConfigsVar.DESIGN_RESOURCES["BRAM"] = calc_BRAM_utilization_for_poly(dataflowConfigsVar)
    
    # get number of URAMs required for TFs
    dataflowConfigsVar.DESIGN_RESOURCES["URAM"] = calc_URAM_utilization_for_tf(dataflowConfigsVar)

# TODO : include FIFOs in the LUTs calculation
# TODO : adjust LUTs calculation based on the shuffler split condition  'if H_BU_NUM >= 5 or buffer_size > 8192:'
# TODO : adjust LUTs calculation based on each shuffler resource model
# TODO : further fine tune LUTs in TFBuf based on whether the buffer has been assigned to URAMs or not
def calc_LUT_utilization(dataflowConfigsVar):
    WORD_SIZE = dataflowConfigsVar.DSEParamsVar.WORD_SIZE
    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS
    logN = dataflowConfigsVar.DSEParamsVar.logN

    NUM_BU = dataflowConfigsVar.NUM_BU
    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = dataflowConfigsVar.H_BUG_SIZE
    V_TOTAL_DATA = dataflowConfigsVar.V_TOTAL_DATA

    tfBuf_LUT_mod_args = TFBuf_resource_model_table["LUT"]
    shuffler_in_LUT_mod_args = shuffler_in_resource_model_table["LUT"]
    shuffler_buf_single_LUT_mod_args = shuffler_buf_single_resource_model_table["LUT"]
    shuffler_out_LUT_mod_args = shuffler_out_resource_model_table["LUT"]

    BU_LUTs = dataflowConfigsVar.DSEParamsVar.BU_RESOURCE["LUT"]
    tfBuf_LUTs = round(evaluate_polynomial(WORD_SIZE, tfBuf_LUT_mod_args))
    shuffler_in_LUTs = round(evaluate_polynomial(WORD_SIZE, shuffler_in_LUT_mod_args))
    shuffler_buf_single_LUTs = round(evaluate_polynomial(WORD_SIZE, shuffler_buf_single_LUT_mod_args))
    shuffler_out_LUTs = round(evaluate_polynomial(WORD_SIZE, shuffler_out_LUT_mod_args))

    num_shufflers = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1

    total_LUTs_per_para_limb = 0
    total_LUTs = 0

    # add BU LUTs
    total_LUTs_per_para_limb += BU_LUTs * NUM_BU

    # add TFbuf LUTs
    total_LUTs_per_para_limb += ( tfBuf_LUTs * (V_BUG_SIZE//2) * logN )

    # add shuffler_in LUTs
    total_LUTs_per_para_limb += ( shuffler_in_LUTs * V_TOTAL_DATA ) * num_shufflers

    # add shuffler_buff LUTs
    total_LUTs_per_para_limb += ( shuffler_buf_single_LUTs * V_TOTAL_DATA ) * num_shufflers

    # add shuffler_out LUTs
    total_LUTs_per_para_limb += ( shuffler_out_LUTs * V_TOTAL_DATA ) * num_shufflers

    total_LUTs = total_LUTs_per_para_limb * PARA_LIMBS

    # add AXI interconnect LUTs
    AXI_interconnect_LUTs = dataflowConfigsVar.DESIGN_RESOURCES["offchip_ports"] * AXI_INTERCONNECT_RESOURCES["LUT"]

    total_LUTs += AXI_interconnect_LUTs

    dataflowConfigsVar.DESIGN_RESOURCES["LUT"] = total_LUTs


# TODO : include FIFOs in the FFs calculation
# TODO : adjust FFs calculation based on the shuffler split condition  'if H_BU_NUM >= 5 or buffer_size > 8192:'
# TODO : adjust FFs calculation based on each shuffler resource model
# TODO : further fine tune FFs in TFBuf based on whether the buffer has been assigned to URAMs or not
def calc_FF_utilization(dataflowConfigsVar):
    WORD_SIZE = dataflowConfigsVar.DSEParamsVar.WORD_SIZE
    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS
    logN = dataflowConfigsVar.DSEParamsVar.logN

    NUM_BU = dataflowConfigsVar.NUM_BU
    V_BUG_SIZE = dataflowConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = dataflowConfigsVar.H_BUG_SIZE
    V_TOTAL_DATA = dataflowConfigsVar.V_TOTAL_DATA

    tfBuf_FF_mod_args = TFBuf_resource_model_table["FF"]
    shuffler_in_FF_mod_args = shuffler_in_resource_model_table["FF"]
    shuffler_buf_single_FF_mod_args = shuffler_buf_single_resource_model_table["FF"]
    shuffler_out_FF_mod_args = shuffler_out_resource_model_table["FF"]

    BU_FFs = dataflowConfigsVar.DSEParamsVar.BU_RESOURCE["FF"]
    tfBuf_FFs = round(evaluate_polynomial(WORD_SIZE, tfBuf_FF_mod_args))
    shuffler_in_FFs = round(evaluate_polynomial(WORD_SIZE, shuffler_in_FF_mod_args))
    shuffler_buf_single_FFs = round(evaluate_polynomial(WORD_SIZE, shuffler_buf_single_FF_mod_args))
    shuffler_out_FFs = round(evaluate_polynomial(WORD_SIZE, shuffler_out_FF_mod_args))

    num_shufflers = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1

    total_FFs_per_para_limb = 0
    total_FFs = 0

    # add BU FFs
    total_FFs_per_para_limb += BU_FFs * NUM_BU

    # add TFbuf FFs
    total_FFs_per_para_limb += ( tfBuf_FFs * (V_BUG_SIZE//2) * logN )

    # add shuffler_in FFs
    total_FFs_per_para_limb += ( shuffler_in_FFs * V_TOTAL_DATA ) * num_shufflers

    # add shuffler_buff FFs
    total_FFs_per_para_limb += ( shuffler_buf_single_FFs * V_TOTAL_DATA ) * num_shufflers

    # add shuffler_out FFs
    total_FFs_per_para_limb += ( shuffler_out_FFs * V_TOTAL_DATA ) * num_shufflers

    total_FFs = total_FFs_per_para_limb * PARA_LIMBS

    # add AXI interconnect FFs
    AXI_interconnect_FFs = dataflowConfigsVar.DESIGN_RESOURCES["offchip_ports"] * AXI_INTERCONNECT_RESOURCES["FF"]

    total_FFs += AXI_interconnect_FFs

    dataflowConfigsVar.DESIGN_RESOURCES["FF"] = total_FFs

# Calculate resource utilization
def calc_resource_utilization(dataflowConfigsVar):

    # Calc number of DRAM ports
    calc_DRAM_ports_utilization(dataflowConfigsVar)

    # Calc DSP usage
    calc_DSP_utilization(dataflowConfigsVar)

    # Calc BRAM and URAM usage
    calc_BRAM_URAM_utilization(dataflowConfigsVar)

    # Calc LUT usage
    calc_LUT_utilization(dataflowConfigsVar)

    # Calc FF usage
    calc_FF_utilization(dataflowConfigsVar)

    DSP = dataflowConfigsVar.DESIGN_RESOURCES["DSP"]
    BRAM = dataflowConfigsVar.DESIGN_RESOURCES["BRAM"]
    URAM = dataflowConfigsVar.DESIGN_RESOURCES["URAM"]
    LUT = dataflowConfigsVar.DESIGN_RESOURCES["LUT"]
    FF = dataflowConfigsVar.DESIGN_RESOURCES["FF"]
    offchip_ports = dataflowConfigsVar.DESIGN_RESOURCES["offchip_ports"]

    logging.getLogger("calc_resource_utilization").trace(f"Resources:: DSP = {DSP}, BRAM = {BRAM}, URAM = {URAM}, LUT = {LUT}, FF = {FF}, DRAM ports = {offchip_ports}")