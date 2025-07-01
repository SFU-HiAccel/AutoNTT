import logging
import math

from types import SimpleNamespace

from dse.common.helper_functions import nearest_lower_power_of_two
from dse.common.helper_functions import calc_log2
from dse.common.helper_functions import evaluate_polynomial

from dse.dse_config import BRAM_WIDTH, BRAM_DEPTH
from dse.dse_config import URAM_WIDTH, URAM_DEPTH
from dse.dse_config import GLOBAL_TARGET_FREQ_MHZ
from dse.dse_config import AXI_INTERCONNECT_RESOURCES

from code_generators.iterative.TFs.TF_common import fwd_bufWiseTFGroupSizeGen_halfPEsDistBufTogether

# Variables define
ITER_POLY_BUF_PIPE_DEPTH = 4

# Resource model values
polyBuf_resource_model_table = {
    "LUT": [33.851, 18.579],
    "FF": [273.94, 0.9642]
}

tfBuf_resource_model_table = {
    "LUT": [178.17, 1.9182],
    "FF": [138.31, 3.7187]
}

# Calculate latency and throughput
def calc_comp_latency_cycles(iterativeConfigsVar):
    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE
    logN = iterativeConfigsVar.DSEParamsVar.logN

    BU_pipe_depth = iterativeConfigsVar.DSEParamsVar.BU_PIPELINE_DEPTH_CYCLES
    
    total_pipeline_depth = BU_pipe_depth + ITER_POLY_BUF_PIPE_DEPTH*2  # multiply by 2 because start pipeline and flush pipeline

    num_data_per_iter = POLY_SIZE//(2*iterativeConfigsVar.NUM_BU)

    exp_latency_cycles = (num_data_per_iter+total_pipeline_depth)*logN

    iterativeConfigsVar.COMPUTE_LATECY_CYCLES = exp_latency_cycles

    logging.getLogger("calc_comp_latency_cycles").trace(f"compute cycles = {iterativeConfigsVar.COMPUTE_LATECY_CYCLES}")

# Given number of cycles in expected_max_cycles, 
# starting from DRAM_PORT_WIDTH, this function iterate through different port widths to match following criterias:
# 1. minimize number of #ports
# 2. maximize time takes to load/store poly data
# 3. but, the time is still less than expected_max_cycles
# And returns min_num_ports and min_port_width
# It is important to notice that this only returns required for either poly loading or storing
def calc_best_BW_for_poly_load_or_store(iterativeConfigsVar, NUM_BU, expected_max_cycles):
    DRAM_WORD_SIZE = iterativeConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE

    min_num_ports = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS
    min_port_width = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    calc_num_ports = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS
    calc_port_width = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    data_per_buffer = POLY_SIZE//NUM_BU #NUM_BU = number of buffers
    # Given this port width, calculate required number of ports to load/store withing given cycle budget
    max_num_of_seq_buffers = expected_max_cycles//data_per_buffer # how many sequential loads can be done within given cycle budget
    if(max_num_of_seq_buffers!=0): # at least one sequential loads could be supported within the expected max cycles 
        buffers_per_one_access = calc_port_width // DRAM_WORD_SIZE
        possible_num_of_seq_buffers = nearest_lower_power_of_two(max_num_of_seq_buffers) # seq number has to be two to the power number
        num_of_buffers_per_port = possible_num_of_seq_buffers * buffers_per_one_access
        calc_num_ports = max(NUM_BU // num_of_buffers_per_port, 1)
    else: # or it was not able to support at one sequential load. Hence, setting it to max number of ports available
        logging.getLogger("calc_best_BW_for_poly_load_or_store").trace(f"With max port width {calc_port_width}, at least one poly buffer (size = {data_per_buffer}) was not able to load within {expected_max_cycles} cycles.")
        calc_num_ports = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS

    min_num_ports = calc_num_ports
    min_port_width = calc_port_width
    if(calc_num_ports==1): #it just needed 1 port with full DRAM width and probably width can go further down to minimize
        calc_port_width = calc_port_width // 2
        while(calc_port_width >= DRAM_WORD_SIZE): # DRAM_WORD_SIZE is the lowest port width can go
            # Given this port width, calculate required number of ports to load/store withing given cycle budget
            buffers_per_one_access = calc_port_width // DRAM_WORD_SIZE
            num_of_buffers_per_port = possible_num_of_seq_buffers * buffers_per_one_access
            calc_num_ports = max(NUM_BU // num_of_buffers_per_port, 1)

            if(calc_num_ports == 1): # even with lower width, still only need one port->better
                min_num_ports = calc_num_ports
                min_port_width = calc_port_width
            else: # number of required ports are more than 1->optimum width has already achived, further going down need more ports
                break
        
             #update the width to be half, which makes it always follows 2 to the power numbers
            calc_port_width = calc_port_width // 2

    logging.getLogger("calc_best_BW_for_poly_load_or_store").trace(f"Per limb optimum #ports = {min_num_ports}, port width = {min_port_width}")

    return min_num_ports, min_port_width


# Given number of cycles in expected_max_cycles, 
# starting from DRAM_PORT_WIDTH, this function iterate through different port widths to match following criterias:
# 1. minimize number of #ports
# 2. maximize time takes to load TF data
# 3. but, the time is still less than COMP_LATENCY_CYCLES*percentage
# And min_num_ports and min_port_width
# Following decisons are taken based on the current way of TF loading
# 1. in NTT, entire TF group is used, while in INTT, only one entire TF group is being used. Rest 
# includes only single value from each TF group (check the eqns in paper). Hence, TF loading for NTT
# takes more time and priority is given for that.
# 2. Usually last buffers gets more data due to their indexes contain many 1s.
# Hence, when checking how many sequential buffers can be combined, the calculation starts from the last buffer
# and comes to the previous buffers.
# 3. Currently when coelescing data, consecutive buffers are combined together. Hence, coelesced buffers contains different
# number of TF data. For example, when 8 consecutive buffers combined together, 8th buffer(idx is 7) contains more TF than others. 
# Currently, zero padding is done for data loading when other buffers do not have data. Therefore, when calculating load counters, 
# considering the TFs in the last buffer(i.e., 8th one) is enough.
def calc_best_BW_for_TF_load(iterativeConfigsVar, NUM_BU, expected_max_cycles):
    DRAM_WORD_SIZE = iterativeConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE

    min_num_ports = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS
    min_port_width = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    calc_num_ports = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS
    calc_port_width = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    #### get an array for FWD NTT TF groups for each buffer ####
    # Create simple parameter with arguments
    params = SimpleNamespace(NUM_BU=NUM_BU, logBU=calc_log2(NUM_BU))
    FWD_sizeArr = fwd_bufWiseTFGroupSizeGen_halfPEsDistBufTogether(params)

    #TF group size
    TF_grp_size = POLY_SIZE//(2*NUM_BU)

    # Given this port width, calculate required number of ports to load/store withing given cycle budget
    buffers_per_one_access = calc_port_width // DRAM_WORD_SIZE
    max_num_of_seq_buffers = 0 # how many sequential loads can be done within given cycle budget
    TF_load_counter = 0
    for buf_idx in range(NUM_BU//2-1, -1, (-1)*buffers_per_one_access):
        num_of_tfs_in_buf = FWD_sizeArr[buf_idx] * TF_grp_size
        if( (TF_load_counter+num_of_tfs_in_buf) <= expected_max_cycles): # adding new buffer for seq loading will not exceed the time limit
            TF_load_counter = TF_load_counter+num_of_tfs_in_buf
            max_num_of_seq_buffers += 1
        else: # seq load amount has reached the limit of expected_max_cycles
            break
    possible_num_of_seq_buffers = nearest_lower_power_of_two(max_num_of_seq_buffers) # seq number has to be two to the power number
    if(possible_num_of_seq_buffers!=0): # at least one sequential loads could be supported within the expected max cycles
        num_of_buffers_per_port = possible_num_of_seq_buffers * buffers_per_one_access
        calc_num_ports = max((NUM_BU//2) // num_of_buffers_per_port, 1) # total num of TF buffers = NUM_BU//2
    else: # or it was not able to support at least one sequential load. Hence, setting it to max number of ports available
        logging.getLogger("calc_best_BW_for_TF_load").trace(f"With max port width {calc_port_width}, at least last TF buffer (size = {FWD_sizeArr[NUM_BU//2-1] * TF_grp_size}) was not able to load within {expected_max_cycles} cycles.")
        calc_num_ports = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS

    min_num_ports = calc_num_ports
    min_port_width = calc_port_width
    if(calc_num_ports==1): #it just needed 1 port with full DRAM width and probably width can go further down to minimize
        calc_port_width = calc_port_width // 2
        while(calc_port_width >= DRAM_WORD_SIZE): # DRAM_WORD_SIZE is the lowest port width can go
            # Given this port width, calculate required number of ports to load/store withing given cycle budget
            buffers_per_one_access = calc_port_width // DRAM_WORD_SIZE
            max_num_of_seq_buffers = 0
            TF_load_counter = 0
            for buf_idx in range(NUM_BU//2-1, -1, (-1)*buffers_per_one_access):
                num_of_tfs_in_buf = FWD_sizeArr[buf_idx] * TF_grp_size
                if( (TF_load_counter+num_of_tfs_in_buf) <= expected_max_cycles): # adding new buffer for seq loading will not exceed the time limit
                    TF_load_counter = TF_load_counter+num_of_tfs_in_buf
                    max_num_of_seq_buffers += 1
                else: # seq load amount has reached the limit of expected_max_cycles
                    break
            possible_num_of_seq_buffers = nearest_lower_power_of_two(max_num_of_seq_buffers) # seq number has to be two to the power number
            if(possible_num_of_seq_buffers!=0): # at least one sequential loads could be supported within the expected max cycles
                num_of_buffers_per_port = possible_num_of_seq_buffers * buffers_per_one_access
                calc_num_ports = max((NUM_BU//2) // num_of_buffers_per_port, 1) # total num of TF buffers = NUM_BU//2
            else: # or it was not able to support at least one sequential load. Hence, setting it to max number of ports available
                calc_num_ports = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS

            if(calc_num_ports == 1): # even with lower width, still only need one port->better
                min_num_ports = calc_num_ports
                min_port_width = calc_port_width
            else: # number of required ports are more than 1->optimum width has already achived, further going down need more ports
                break
        
             #update the width to be half, which makes it always follows 2 to the power numbers
            calc_port_width = calc_port_width // 2

    logging.getLogger("calc_best_BW_for_TF_load").trace(f"Per limb optimum #ports = {min_num_ports}, port width = {min_port_width}")

    return min_num_ports, min_port_width

# For given number of ports and port width, this function calculates the polynomial load/store time
# This is calculated without considering load and store function's pipeline depth.
def calc_poly_load_or_store_cycles(iterativeConfigsVar):
    DRAM_WORD_SIZE = iterativeConfigsVar.DSEParamsVar.DRAM_WORD_SIZE

    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE
    NUM_BU = iterativeConfigsVar.NUM_BU
    POLY_LS_PORTS_PER_PARA_LIMB = iterativeConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = iterativeConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB

    values_per_buffer = POLY_SIZE//NUM_BU
    num_buffers_per_port = NUM_BU//POLY_LS_PORTS_PER_PARA_LIMB
    num_parallel_buffers_per_cycle = POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB//DRAM_WORD_SIZE
    total_sequential_buffers = num_buffers_per_port//num_parallel_buffers_per_cycle

    total_cycles_to_load_data = total_sequential_buffers*values_per_buffer

    logging.getLogger("calc_poly_load_or_store_cycles").trace(f"Poly load or store time = {total_cycles_to_load_data}")

    return total_cycles_to_load_data

# For given number of ports and port width, this function calculates the tf load time
# This is calculated without considering load and store function's pipeline depth.
# When calculating this, FWD TFs are considered as FWD takes more TFs than INV.
# Also last port's load time is considered as the last port take more time due to last buffers tend to have more data.
def calc_tf_load_cycles(iterativeConfigsVar):
    DRAM_WORD_SIZE = iterativeConfigsVar.DSEParamsVar.DRAM_WORD_SIZE

    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE
    NUM_BU = iterativeConfigsVar.NUM_BU
    TF_PORTS_PER_PARA_LIMB = iterativeConfigsVar.TF_PORTS_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = iterativeConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB

    #TF group size
    TF_grp_size = POLY_SIZE//(2*NUM_BU)

    num_buffers_per_port = (NUM_BU//2)//TF_PORTS_PER_PARA_LIMB
    num_parallel_buffers_per_cycle = TF_DRAM_PORT_WIDTH_PER_PARA_LIMB//DRAM_WORD_SIZE
    total_sequential_buffers = num_buffers_per_port//num_parallel_buffers_per_cycle

    #### get an array for FWD NTT TF groups for each buffer ####
    # Create simple parameter with arguments
    params = SimpleNamespace(NUM_BU=NUM_BU, logBU=calc_log2(NUM_BU))
    FWD_sizeArr = fwd_bufWiseTFGroupSizeGen_halfPEsDistBufTogether(params)

    TF_load_counter = 0
    for seq_load_idx in range(total_sequential_buffers):
        buf_idx = num_buffers_per_port*(TF_PORTS_PER_PARA_LIMB-1) + seq_load_idx*num_parallel_buffers_per_cycle + num_parallel_buffers_per_cycle-1
        num_of_tfs_in_buf = FWD_sizeArr[buf_idx] * TF_grp_size
        TF_load_counter = TF_load_counter+num_of_tfs_in_buf

    logging.getLogger("calc_tf_load_cycles").trace(f"TF load time = {TF_load_counter}")

    return TF_load_counter

# Calculate latency and throughput
def calc_latency_throughput(iterativeConfigsVar):
    COMPUTE_LATECY_CYCLES = iterativeConfigsVar.COMPUTE_LATECY_CYCLES
    DOUBLE_BUF_EN = iterativeConfigsVar.DOUBLE_BUF_EN
    POLY_LOAD_OR_STORE_LATENCY_CYCLES = iterativeConfigsVar.POLY_LOAD_OR_STORE_LATENCY_CYCLES
    TF_LOAD_LATENCY_CYCLES = iterativeConfigsVar.TF_LOAD_LATENCY_CYCLES

    exp_latency_cycles = 0

    if(DOUBLE_BUF_EN): # load and store times are hidden
        exp_latency_cycles = COMPUTE_LATECY_CYCLES
    else:
        exp_latency_cycles = COMPUTE_LATECY_CYCLES + max(2*POLY_LOAD_OR_STORE_LATENCY_CYCLES, TF_LOAD_LATENCY_CYCLES)

    exp_latency_s = exp_latency_cycles / (GLOBAL_TARGET_FREQ_MHZ*1000000)
    exp_latency_ms = exp_latency_s*1000

    exp_throughput = math.floor(1 / exp_latency_s)

    iterativeConfigsVar.EXPECTED_LATENCY_MS = exp_latency_ms
    iterativeConfigsVar.EXPECTED_THROUGHPUT = exp_throughput

    logging.getLogger("calc_latency_throughput").trace(f"Expected latency = {iterativeConfigsVar.EXPECTED_LATENCY_MS} ms, expected throughput(#NTT/s) = {iterativeConfigsVar.EXPECTED_THROUGHPUT}")

def calc_DRAM_ports_utilization(iterativeConfigsVar):
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS
    DRAM_PORT_WIDTH = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH
    
    DOUBLE_BUF_EN = iterativeConfigsVar.DOUBLE_BUF_EN

    POLY_LS_PORTS_PER_PARA_LIMB = iterativeConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = iterativeConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB

    TF_PORTS_PER_PARA_LIMB = iterativeConfigsVar.TF_PORTS_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = iterativeConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB

    poly_ls_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)) * POLY_LS_PORTS_PER_PARA_LIMB
    tf_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB)) * TF_PORTS_PER_PARA_LIMB
    
    total_ports = 0
    if (DOUBLE_BUF_EN):
        total_ports = poly_ls_ports*2 + tf_ports
    else:
        total_ports = poly_ls_ports + tf_ports

    iterativeConfigsVar.DESIGN_RESOURCES["offchip_ports"] = total_ports

# Calculate DSP resource utilization
def calc_DSP_utilization(iterativeConfigsVar):
    NUM_BU = iterativeConfigsVar.NUM_BU
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS

    num_of_dsps_per_BU = iterativeConfigsVar.DSEParamsVar.BU_RESOURCE["DSP"]

    total_DSPs = num_of_dsps_per_BU * NUM_BU * PARA_LIMBS

    iterativeConfigsVar.DESIGN_RESOURCES["DSP"] = total_DSPs

def calc_BRAM_utilization_for_poly(iterativeConfigsVar):
    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE
    WORD_SIZE = iterativeConfigsVar.DSEParamsVar.WORD_SIZE
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS

    DOUBLE_BUF_EN = iterativeConfigsVar.DOUBLE_BUF_EN

    num_of_poly_buffers = iterativeConfigsVar.NUM_BU

    poly_values_per_buf = POLY_SIZE//num_of_poly_buffers

    if(poly_values_per_buf < (BRAM_DEPTH//2)): # BRAM 18k can work as 36bitx512
        BRAMs_per_buffer = math.ceil(WORD_SIZE/(2*BRAM_WIDTH)) * math.ceil(poly_values_per_buf/(BRAM_DEPTH//2))
    else:
        BRAMs_per_buffer = math.ceil(WORD_SIZE/BRAM_WIDTH) * math.ceil(poly_values_per_buf/BRAM_DEPTH)

    total_BRAMs = 0

    if(DOUBLE_BUF_EN):
        total_BRAMs = BRAMs_per_buffer * 3 * num_of_poly_buffers * PARA_LIMBS # 3 buffers are required with double buffering
    else:
        total_BRAMs = BRAMs_per_buffer * 2 * num_of_poly_buffers * PARA_LIMBS # 2 buffers are required by algorithm
    
    return total_BRAMs

# Only consider FWD as FWD takes more resources
def calc_URAM_utilization_for_tf(iterativeConfigsVar):
    NUM_BU = iterativeConfigsVar.NUM_BU
    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE
    WORD_SIZE = iterativeConfigsVar.DSEParamsVar.WORD_SIZE
    DOUBLE_BUF_EN = iterativeConfigsVar.DOUBLE_BUF_EN
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS

    num_of_tf_buffers = NUM_BU//2
    
    #### get an array for FWD NTT TF groups for each buffer ####
    # Create simple parameter with arguments
    params = SimpleNamespace(NUM_BU=NUM_BU, logBU=calc_log2(NUM_BU))
    FWD_sizeArr = fwd_bufWiseTFGroupSizeGen_halfPEsDistBufTogether(params)

    #TF group size
    TF_grp_size = POLY_SIZE//(2*NUM_BU)

    total_URAMs = 0

    for buf_idx in range(num_of_tf_buffers):
        tf_values_per_buf = FWD_sizeArr[buf_idx] * TF_grp_size
        URAMs_per_buffer = math.ceil(WORD_SIZE/URAM_WIDTH) * math.ceil(tf_values_per_buf/URAM_DEPTH)

        if(DOUBLE_BUF_EN):
            total_URAMs += URAMs_per_buffer * 2 * PARA_LIMBS
        else:
            total_URAMs += URAMs_per_buffer * PARA_LIMBS
    
    return total_URAMs

# Calculate BRAM and URAM resource utilization
# Prioritize assigning polynomial buffer to BRAM (reason is given the paper)
# Prioritize assigning TFs to URAM to balance the resources.
# TODO: 1. Add the case where URAM is not available
# TODO: 2. Add the case where URAM is not enough, but BRAM is enough to accomodate both Poly and remaining TFs
def calc_BRAM_URAM_utilization(iterativeConfigsVar):

    # get number of BRAMs required for polynomials
    iterativeConfigsVar.DESIGN_RESOURCES["BRAM"] = calc_BRAM_utilization_for_poly(iterativeConfigsVar)
    
    # get number of URAMs required for TFs
    iterativeConfigsVar.DESIGN_RESOURCES["URAM"] = calc_URAM_utilization_for_tf(iterativeConfigsVar)

def calc_LUT_utilization(iterativeConfigsVar):
    WORD_SIZE = iterativeConfigsVar.DSEParamsVar.WORD_SIZE
    NUM_BU = iterativeConfigsVar.NUM_BU
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS

    polyBuf_LUT_mod_args = polyBuf_resource_model_table["LUT"]
    tfBuf_LUT_mod_args = tfBuf_resource_model_table["LUT"]

    BU_LUTs = iterativeConfigsVar.DSEParamsVar.BU_RESOURCE["LUT"]
    polyBuf_LUTs = round(evaluate_polynomial(WORD_SIZE, polyBuf_LUT_mod_args))
    tfBuf_LUTs = round(evaluate_polynomial(WORD_SIZE, tfBuf_LUT_mod_args))

    AXI_interconnect_LUTs = iterativeConfigsVar.DESIGN_RESOURCES["offchip_ports"] * AXI_INTERCONNECT_RESOURCES["LUT"]

    total_LUTs = (BU_LUTs*NUM_BU + polyBuf_LUTs*NUM_BU + tfBuf_LUTs*(NUM_BU//2)) * PARA_LIMBS + AXI_interconnect_LUTs

    iterativeConfigsVar.DESIGN_RESOURCES["LUT"] = total_LUTs

def calc_FF_utilization(iterativeConfigsVar):
    WORD_SIZE = iterativeConfigsVar.DSEParamsVar.WORD_SIZE
    NUM_BU = iterativeConfigsVar.NUM_BU
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS

    polyBuf_FF_mod_args = polyBuf_resource_model_table["FF"]
    tfBuf_FF_mod_args = tfBuf_resource_model_table["FF"]

    BU_FFs = iterativeConfigsVar.DSEParamsVar.BU_RESOURCE["FF"]
    polyBuf_FFs = round(evaluate_polynomial(WORD_SIZE, polyBuf_FF_mod_args))
    tfBuf_FFs = round(evaluate_polynomial(WORD_SIZE, tfBuf_FF_mod_args))

    AXI_interconnect_FFs = iterativeConfigsVar.DESIGN_RESOURCES["offchip_ports"] * AXI_INTERCONNECT_RESOURCES["FF"]

    total_FFs = (BU_FFs*NUM_BU + polyBuf_FFs*NUM_BU + tfBuf_FFs*(NUM_BU//2)) * PARA_LIMBS + AXI_interconnect_FFs

    iterativeConfigsVar.DESIGN_RESOURCES["FF"] = total_FFs
    

# Calculate resource utilization
def calc_resource_utilization(iterativeConfigsVar):

    # Calc number of DRAM ports
    calc_DRAM_ports_utilization(iterativeConfigsVar)

    # Calc DSP usage
    calc_DSP_utilization(iterativeConfigsVar)

    # Calc BRAM and URAM usage
    calc_BRAM_URAM_utilization(iterativeConfigsVar)

    # Calc LUT usage
    calc_LUT_utilization(iterativeConfigsVar)

    # Calc FF usage
    calc_FF_utilization(iterativeConfigsVar)

    DSP = iterativeConfigsVar.DESIGN_RESOURCES["DSP"]
    BRAM = iterativeConfigsVar.DESIGN_RESOURCES["BRAM"]
    URAM = iterativeConfigsVar.DESIGN_RESOURCES["URAM"]
    LUT = iterativeConfigsVar.DESIGN_RESOURCES["LUT"]
    FF = iterativeConfigsVar.DESIGN_RESOURCES["FF"]
    offchip_ports = iterativeConfigsVar.DESIGN_RESOURCES["offchip_ports"]

    logging.getLogger("calc_resource_utilization").trace(f"Resources:: DSP = {DSP}, BRAM = {BRAM}, URAM = {URAM}, LUT = {LUT}, FF = {FF}, DRAM ports = {offchip_ports}")
