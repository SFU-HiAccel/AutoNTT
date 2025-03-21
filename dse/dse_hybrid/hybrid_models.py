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

from code_generators.hybrid.TFs.TF_load import gen_tf_load_counters
from code_generators.hybrid.TFs.TF_buffers import gen_tf_buf_config

#### Variables define ####

# Pipeline depths 
# TODO: update shuffler depths according to split stratergies and incorporate in the model

IN_SEL_PIPE_DEPTH = 3
SHUFFLER_PIPE_DEPTH = 13 # shuffler_in = 3, shuffler_buf = 4, shuffler_out_shift =  3, shuffler_out_shuff = 3
OUT_SEL_PIPE_DEPTH = 3


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

shuffler_out_shift_resource_model_table = {
    "LUT": [49.075, 7.9789],
    "FF": [40.731, 4.3422]
}

shuffler_out_shuffle_resource_model_table = {
    "LUT": [61.482, 5.7031],
    "FF": [16.428, 2.4068]
}

# This function finds the next largest hybrid architecture design.
# It 1st check if there is a design with the same number of BUs with a smaller BUG.
# If yes, returns that.
# If not, then check the next largest design that can have maximum one less BU.
# Starting from 2x2 BUG, it starts search and returns the design with highest number of BUs.
# Among all the BUG types, it prioritze design with the largest BUG.
def set_next_largest_design(hybridConfigsVar):
    NUM_BU = hybridConfigsVar.NUM_BU
    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE

    # To keep the next largest BUG arrangement
    max_total_num_BU = 0
    max_V_BUG_SIZE = 0
    max_H_BUG_SIZE = 0
    max_concat_factor = 0

    same_total_BUs_design_found = False

    #first check if the same num_BU can be achived with smaller BUGs
    new_V_BUG_SIZE = V_BUG_SIZE//2
    if(new_V_BUG_SIZE!=0):
        new_H_BUG_SIZE = calc_log2(2*new_V_BUG_SIZE)
    while(new_V_BUG_SIZE>1):
        total_BUs_in_new_BUG = new_V_BUG_SIZE * new_H_BUG_SIZE
        exp_concat_factor = NUM_BU//total_BUs_in_new_BUG
        possible_concat_factor = nearest_lower_power_of_two(exp_concat_factor)

        if(total_BUs_in_new_BUG * possible_concat_factor == NUM_BU):
            max_total_num_BU = NUM_BU
            max_V_BUG_SIZE = new_V_BUG_SIZE
            max_H_BUG_SIZE = new_H_BUG_SIZE
            max_concat_factor = possible_concat_factor

            same_total_BUs_design_found = True
            break
        else:
            new_V_BUG_SIZE = new_V_BUG_SIZE//2
            new_H_BUG_SIZE = calc_log2(2*new_V_BUG_SIZE)
    
    if(not(same_total_BUs_design_found)):#else
        new_V_BUG_SIZE = 2
        new_H_BUG_SIZE = calc_log2(2*new_V_BUG_SIZE)
        while(True):
            total_BUs_in_new_BUG = new_V_BUG_SIZE * new_H_BUG_SIZE
            exp_concat_factor = (NUM_BU-1)//total_BUs_in_new_BUG
            possible_concat_factor = nearest_lower_power_of_two(exp_concat_factor)
            
            if(possible_concat_factor<1): # Largest BUG possible achived
                break
            
            total_BUs_in_new_design = total_BUs_in_new_BUG * possible_concat_factor
            
            if(total_BUs_in_new_design>=max_total_num_BU): # prioritize larger BUGs 1st
                max_V_BUG_SIZE = new_V_BUG_SIZE
                max_H_BUG_SIZE = new_H_BUG_SIZE
                max_concat_factor = possible_concat_factor
                max_total_num_BU = total_BUs_in_new_design
            
            new_V_BUG_SIZE = new_V_BUG_SIZE*2
            new_H_BUG_SIZE = calc_log2(2*new_V_BUG_SIZE)

    hybridConfigsVar.V_BUG_SIZE = max_V_BUG_SIZE
    hybridConfigsVar.H_BUG_SIZE = max_H_BUG_SIZE
    hybridConfigsVar.BUG_CONCAT_FACTOR = max_concat_factor
    hybridConfigsVar.NUM_BU = max_total_num_BU

    hybridConfigsVar.V_TOTAL_DATA = 2 * hybridConfigsVar.V_BUG_SIZE * hybridConfigsVar.BUG_CONCAT_FACTOR

    if(hybridConfigsVar.V_BUG_SIZE != 0):
        hybridConfigsVar.logV_BUG_SIZE = calc_log2(hybridConfigsVar.V_BUG_SIZE)
    
    if(hybridConfigsVar.BUG_CONCAT_FACTOR != 0):
        hybridConfigsVar.logBUG_CONCAT_FACTOR = calc_log2(hybridConfigsVar.BUG_CONCAT_FACTOR)

    if(hybridConfigsVar.V_TOTAL_DATA != 0):
        hybridConfigsVar.log_V_TOTAL_DATA = calc_log2(hybridConfigsVar.V_TOTAL_DATA)

    logging.getLogger("set_next_largest_design").trace(f"Next design: ({ hybridConfigsVar.V_BUG_SIZE } x { hybridConfigsVar.H_BUG_SIZE } BUG) x { hybridConfigsVar.BUG_CONCAT_FACTOR } = { hybridConfigsVar.NUM_BU }")

# This function calculates the shuffler buffer delay for each round and return it as an array
def hybrid_buf_cal_buf_delay(hybridConfigsVar):

    logN = hybridConfigsVar.DSEParamsVar.logN
    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    BUG_CONCAT_FACTOR = hybridConfigsVar.BUG_CONCAT_FACTOR
    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA
    logV_BUG_SIZE = hybridConfigsVar.logV_BUG_SIZE
    logBUG_CONCAT_FACTOR = hybridConfigsVar.logBUG_CONCAT_FACTOR
    
    shuffleLimit = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1
    
    poly_group_total_num_line_table = []

    max_data_offset = (V_BUG_SIZE*2)

    for shuffler_id in range(shuffleLimit):

        nextTotalSupportingStages = ( logN - (shuffler_id+1)*H_BUG_SIZE ) if ( (shuffler_id+2)*H_BUG_SIZE > logN ) else ( H_BUG_SIZE )

        nextSupportingDistArr = []
        for i in range(H_BUG_SIZE):
            nextSupportingDistArr.append(1 << ( (shuffler_id+1)*H_BUG_SIZE + i ))
        

        shifFreqForNextDistArr = []
        for i in range(H_BUG_SIZE):
            shifFreqForNextDistArr.append(nextSupportingDistArr[i]//V_TOTAL_DATA)
        
        log_shift_freq = 0
        log_mini_shift_reset_freq = 0
        log_mini_shift_amount = 0

        if ( shifFreqForNextDistArr[0] == 0 ): #no shift at all and these all must be 0
            log_shift_freq = 0
            log_mini_shift_reset_freq = 0
            log_mini_shift_amount = 0
        
        elif(nextTotalSupportingStages==H_BUG_SIZE):
            log_shift_freq = ( (shuffler_id+1)*(H_BUG_SIZE) ) - ( logV_BUG_SIZE + logBUG_CONCAT_FACTOR + 1 )
            log_mini_shift_reset_freq = 0
            log_mini_shift_amount = 0
        
        else:
            log_shift_freq = ( (shuffler_id+1)*(H_BUG_SIZE) ) - ( logV_BUG_SIZE + logBUG_CONCAT_FACTOR + 1 )
            total_unique_sets = ( 2*V_BUG_SIZE*BUG_CONCAT_FACTOR ) // ( 1<<nextTotalSupportingStages )
            lastSupportedStageDist = 1 << shuffler_id*H_BUG_SIZE

            if(total_unique_sets>lastSupportedStageDist):
                log_mini_shift_reset_freq = shuffler_id*H_BUG_SIZE - logBUG_CONCAT_FACTOR
                log_mini_shift_amount = (logV_BUG_SIZE + 1 + logBUG_CONCAT_FACTOR) - (nextTotalSupportingStages + shuffler_id*H_BUG_SIZE)
            
            else:
                log_mini_shift_reset_freq = (logV_BUG_SIZE+1) - nextTotalSupportingStages
                log_mini_shift_amount = 0
        
        shift_counts = 0
        for i in range(H_BUG_SIZE):
            if( shifFreqForNextDistArr[i]==0 ):
                shift_counts+=1
            
        log_group_total_num_line = log_shift_freq + (logV_BUG_SIZE+1) - log_mini_shift_reset_freq - shift_counts - log_mini_shift_amount
        group_total_num_line = 1<<log_group_total_num_line
        poly_group_total_num_line_table.append(group_total_num_line)
        
    return poly_group_total_num_line_table

# Calculate latency and throughput
def calc_comp_latency_cycles(hybridConfigsVar):
    POLY_SIZE = hybridConfigsVar.DSEParamsVar.POLY_SIZE
    logN = hybridConfigsVar.DSEParamsVar.logN

    BU_PIPELINE_DEPTH_CYCLES = hybridConfigsVar.DSEParamsVar.BU_PIPELINE_DEPTH_CYCLES
    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA
    logV_BUG_SIZE = hybridConfigsVar.logV_BUG_SIZE
    logBUG_CONCAT_FACTOR = hybridConfigsVar.logBUG_CONCAT_FACTOR

    #calc pipeline depth
    pipeline_depth = IN_SEL_PIPE_DEPTH + BU_PIPELINE_DEPTH_CYCLES*H_BUG_SIZE + OUT_SEL_PIPE_DEPTH + SHUFFLER_PIPE_DEPTH
    
    #calc number of inputs
    num_of_inputs = POLY_SIZE//V_TOTAL_DATA

    #cal number of rounds data going through BUGs to complete the computation
    num_of_rounds = math.ceil(logN/H_BUG_SIZE)

    #calc buf delay in each round
    buf_delay_table = hybrid_buf_cal_buf_delay(hybridConfigsVar)

    #calc compute time
    exp_latency_cycles = 0
    #1st calc time for the rounds going throgh shuffler
    for round in range(num_of_rounds-1): #only going through shuffler (num_of_rounds-1) time

        buf_delay = buf_delay_table[round]

        #data go through BUG, reach poly buf, wait there until pattern matches and output. Time taken for this is calculated here
        time_to_ready_for_next_round = pipeline_depth + buf_delay

        if(time_to_ready_for_next_round<num_of_inputs): #next round wait till data in the previous round go
            exp_latency_cycles = exp_latency_cycles + num_of_inputs #therefore time=time till previous values are gone
        else:
            exp_latency_cycles = exp_latency_cycles + time_to_ready_for_next_round
    
    #After last round of shuffler it directly go through the BUG. Hence,
    exp_latency_cycles = exp_latency_cycles + pipeline_depth #hardcoding this value also to pipeline depth. this should actually be BUG_depth+output_selector+store

    #And num_of_inputs time is taken to output all the outputs
    exp_latency_cycles = exp_latency_cycles + num_of_inputs

    hybridConfigsVar.COMPUTE_LATECY_CYCLES = exp_latency_cycles

    logging.getLogger("calc_comp_latency_cycles").trace(f"compute cycles = {hybridConfigsVar.COMPUTE_LATECY_CYCLES}")



# Given number of cycles in expected_max_cycles, this function calculates the minimum number of ports and port width required
# to load polynomial data during the given time.
# It is important to notice that this only returns required for either poly loading or storing
def calc_best_BW_for_poly_load_or_store(hybridConfigsVar, expected_max_cycles):
    DRAM_WORD_SIZE = hybridConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
    DRAM_PORT_WIDTH = hybridConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH
    POLY_SIZE = hybridConfigsVar.DSEParamsVar.POLY_SIZE

    min_num_ports = hybridConfigsVar.DSEParamsVar.NUM_DRAM_PORTS
    min_port_width = hybridConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    calc_num_ports = hybridConfigsVar.DSEParamsVar.NUM_DRAM_PORTS
    calc_port_width = hybridConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA

    data_per_one_input_path = POLY_SIZE//V_TOTAL_DATA
    
    max_sequential_loads = expected_max_cycles//data_per_one_input_path
    possible_sequential_loads = nearest_lower_power_of_two(max_sequential_loads)
    required_parallel_data_paths = math.ceil(V_TOTAL_DATA/possible_sequential_loads)
    min_total_ports_width = required_parallel_data_paths * DRAM_WORD_SIZE

    min_num_ports = math.ceil(min_total_ports_width/DRAM_PORT_WIDTH)
    min_port_width = min(DRAM_PORT_WIDTH, min_total_ports_width)

    logging.getLogger("calc_best_BW_for_poly_load_or_store").trace(f"Per limb optimum #ports = {min_num_ports}, port width = {min_port_width}")

    return min_num_ports, min_port_width


# Given number of cycles in expected_max_cycles, this function calculates the minimum number of ports and port width required
# to load TF data during the given time.
# With the current implementation, the minimum number of ports required is equal to BW required to load data belonging to one TF buffer layer.
# With this minimum ports, it can sequentially load data going into different layers.
# However, since cummulative sum of sequential loading can be more than expected time, layers have to be split into different load groups(segments).
# This function finds the minimum such segments required to match expected_max_cycles and calculate #ports based on that.
def calc_best_BW_for_TF_load(hybridConfigsVar, expected_max_cycles):
    DRAM_WORD_SIZE = hybridConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
    DRAM_PORT_WIDTH = hybridConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    logN = hybridConfigsVar.DSEParamsVar.logN
    POLY_SIZE = hybridConfigsVar.DSEParamsVar.POLY_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    BUG_CONCAT_FACTOR = hybridConfigsVar.BUG_CONCAT_FACTOR
    
    num_segs = 1
    
    while(num_segs <= H_BUG_SIZE):
        
        params = SimpleNamespace(
                                logN=logN,
                                TF_LOAD_H_SEGS_PER_PARA_LIMB = num_segs,
                                POLY_SIZE=POLY_SIZE,
                                H_BUG_SIZE=H_BUG_SIZE,
                                V_BUG_SIZE=V_BUG_SIZE,
                                BUG_CONCAT_FACTOR=BUG_CONCAT_FACTOR
                                )
        
        FWD_TF_load_counter_per_seg, INV_TF_load_counter_per_seg = gen_tf_load_counters(params)
        logging.getLogger("calc_best_BW_for_TF_load").trace(f"Number of segments = {num_segs}, FWD TF load counters = {FWD_TF_load_counter_per_seg}, INV TF load counters = {INV_TF_load_counter_per_seg}")

        # Check if both FWD and INV load counters in each segment is within the given range
        matched_range = True
        for seg_id in range(num_segs):
            if(FWD_TF_load_counter_per_seg[seg_id] > expected_max_cycles):
                matched_range = False
            
            if(INV_TF_load_counter_per_seg[seg_id] > expected_max_cycles):
                matched_range = False

        if(matched_range): #found minimum number of segments required to keep the TF load within expected cycles
            break
    
        num_segs += 1

    total_vertical_TF_values = V_BUG_SIZE*BUG_CONCAT_FACTOR # V_BUG_SIZE/2 Buffers to support V_BUG_SIZE BUs. 2 values are loaded for each buffer.
    total_vertical_DRAM_port_wdith = total_vertical_TF_values * DRAM_WORD_SIZE

    TF_port_width = min(total_vertical_DRAM_port_wdith, DRAM_PORT_WIDTH)
    num_vertical_TF_ports = math.ceil(total_vertical_DRAM_port_wdith/DRAM_PORT_WIDTH)
    total_TF_ports = num_vertical_TF_ports * num_segs

    logging.getLogger("calc_best_BW_for_TF_load").trace(f"Per limb optimum #ports = {total_TF_ports}, port width = {TF_port_width}")

    return total_TF_ports, TF_port_width


# Calculate latency and throughput
def calc_latency_throughput(hybridConfigsVar):
    COMPUTE_LATECY_CYCLES = hybridConfigsVar.COMPUTE_LATECY_CYCLES

    exp_latency_cycles = COMPUTE_LATECY_CYCLES

    exp_latency_s = exp_latency_cycles / (GLOBAL_TARGET_FREQ_MHZ*1000000)
    exp_latency_ms = exp_latency_s*1000

    exp_throughput = math.floor(1 / exp_latency_s)

    hybridConfigsVar.EXPECTED_LATENCY_MS = exp_latency_ms
    hybridConfigsVar.EXPECTED_THROUGHPUT = exp_throughput

    logging.getLogger("calc_latency_throughput").trace(f"Expected latency = {hybridConfigsVar.EXPECTED_LATENCY_MS} ms, expected throughput(#NTT/s) = {hybridConfigsVar.EXPECTED_THROUGHPUT}")

def calc_DRAM_ports_utilization(hybridConfigsVar):
    PARA_LIMBS = hybridConfigsVar.DSEParamsVar.PARA_LIMBS
    DRAM_PORT_WIDTH = hybridConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    POLY_LS_PORTS_PER_PARA_LIMB = hybridConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = hybridConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB

    TF_PORTS_PER_PARA_LIMB = hybridConfigsVar.TF_PORTS_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = hybridConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB

    poly_ls_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)) * POLY_LS_PORTS_PER_PARA_LIMB
    tf_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB)) * TF_PORTS_PER_PARA_LIMB

    total_ports = poly_ls_ports*2 + tf_ports

    hybridConfigsVar.DESIGN_RESOURCES["offchip_ports"] = total_ports

# Calculate DSP resource utilization
def calc_DSP_utilization(hybridConfigsVar):
    PARA_LIMBS = hybridConfigsVar.DSEParamsVar.PARA_LIMBS
    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    BUG_CONCAT_FACTOR = hybridConfigsVar.BUG_CONCAT_FACTOR

    num_of_dsps_per_BU = hybridConfigsVar.DSEParamsVar.BU_RESOURCE["DSP"]

    total_DSPs = num_of_dsps_per_BU * (V_BUG_SIZE * H_BUG_SIZE * BUG_CONCAT_FACTOR) * PARA_LIMBS

    hybridConfigsVar.DESIGN_RESOURCES["DSP"] = total_DSPs


def calc_BRAM_utilization_for_poly(hybridConfigsVar):
    POLY_SIZE = hybridConfigsVar.DSEParamsVar.POLY_SIZE
    WORD_SIZE = hybridConfigsVar.DSEParamsVar.WORD_SIZE
    PARA_LIMBS = hybridConfigsVar.DSEParamsVar.PARA_LIMBS
    LS_FIFO_BUF_SIZE = hybridConfigsVar.LS_FIFO_BUF_SIZE
    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA
    
    #### Shuffler buffers ####
    num_of_shuffler_buffers = V_TOTAL_DATA

    poly_values_per_shuffler_buf = (POLY_SIZE/V_TOTAL_DATA)*2

    BRAMs_per_buffer = math.ceil(WORD_SIZE/BRAM_WIDTH) * math.ceil(poly_values_per_shuffler_buf/BRAM_DEPTH)
    
    total_brams_for_shuffler_buffers = BRAMs_per_buffer * num_of_shuffler_buffers

    total_BRAMs = 0
    
    total_BRAMs += total_brams_for_shuffler_buffers
    
    #### input output FIFOs ####
    if(LS_FIFO_BUF_SIZE==BRAM_DEPTH): # Input output FIFOs are mapped to BRAM
        total_brams_for_inp_out_FIFOs = math.ceil(WORD_SIZE/BRAM_WIDTH) * math.ceil(poly_values_per_shuffler_buf/BRAM_DEPTH) * V_TOTAL_DATA * 2 # Each channel has a FIFO and 2 is for input and output
        total_BRAMs += total_brams_for_inp_out_FIFOs
    
    total_BRAMs *= PARA_LIMBS # adjust for parallel limbs

    return total_BRAMs

# Calculate URAMs for TFs and POLY_LS_FIFOs
def calc_URAM_utilization_for_tf(hybridConfigsVar):

    POLY_SIZE = hybridConfigsVar.DSEParamsVar.POLY_SIZE
    WORD_SIZE = hybridConfigsVar.DSEParamsVar.WORD_SIZE
    logN = hybridConfigsVar.DSEParamsVar.logN
    PARA_LIMBS = hybridConfigsVar.DSEParamsVar.PARA_LIMBS

    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    logV_BUG_SIZE = hybridConfigsVar.logV_BUG_SIZE
    BUG_CONCAT_FACTOR = hybridConfigsVar.BUG_CONCAT_FACTOR
    logBUG_CONCAT_FACTOR = hybridConfigsVar.logBUG_CONCAT_FACTOR
    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA
    log_V_TOTAL_DATA = hybridConfigsVar.log_V_TOTAL_DATA
    LS_FIFO_BUF_SIZE = hybridConfigsVar.LS_FIFO_BUF_SIZE

    #### get an array of TF buffer size in each layer ####
    # Create simple parameter with arguments
    params = SimpleNamespace(
                            logN=logN,
                            POLY_SIZE=POLY_SIZE,
                            V_BUG_SIZE = V_BUG_SIZE,
                            H_BUG_SIZE = H_BUG_SIZE,
                            logV_BUG_SIZE = logV_BUG_SIZE,
                            BUG_CONCAT_FACTOR = BUG_CONCAT_FACTOR,
                            logBUG_CONCAT_FACTOR = logBUG_CONCAT_FACTOR,
                            V_TOTAL_DATA = V_TOTAL_DATA,
                            log_V_TOTAL_DATA = log_V_TOTAL_DATA,
                            TF_LOAD_H_SEGS_PER_PARA_LIMB = 1 # Do not have impact for TFarray size
                            )
    TFBuffersParamsVar = gen_tf_buf_config(params)
    TFArr_size = TFBuffersParamsVar.TFArr_size

    num_of_TF_buffers_per_layer = (V_BUG_SIZE//2) * BUG_CONCAT_FACTOR

    total_URAMs = 0

    for layer_idx in range(H_BUG_SIZE):
        tf_values_per_buf = TFArr_size[layer_idx]
        URAMs_per_buffer = math.ceil(WORD_SIZE/URAM_WIDTH) * math.ceil(tf_values_per_buf/URAM_DEPTH)

        URAMs_per_layer = URAMs_per_buffer * 2 * num_of_TF_buffers_per_layer # multiply by 2 for double buffer
        
        total_URAMs += URAMs_per_layer

    #### input output FIFOs ####
    if(LS_FIFO_BUF_SIZE>BRAM_DEPTH): # Input output FIFOs are mapped to BRAM
        total_URAMs_for_inp_out_FIFOs = math.ceil(WORD_SIZE/URAM_WIDTH) * math.ceil(LS_FIFO_BUF_SIZE/URAM_DEPTH) * V_TOTAL_DATA * 2 # Each channel has a FIFO and 2 is for input and output
        total_URAMs += total_URAMs_for_inp_out_FIFOs

    total_URAMs *= PARA_LIMBS # adjust for parallel limbs

    return total_URAMs

# Calculate BRAM and URAM resource utilization
# Prioritize assigning polynomial buffer to BRAM (reason is given the paper)
# Prioritize assigning TFs to URAM to balance the resources.
# TODO: 1. Add the case where URAM is not available
# TODO: 2. Add the case where URAM is not enough, but BRAM is enough to accomodate both Poly and remaining TFs
def calc_BRAM_URAM_utilization(hybridConfigsVar):

    # get number of BRAMs required for polynomials
    hybridConfigsVar.DESIGN_RESOURCES["BRAM"] = calc_BRAM_utilization_for_poly(hybridConfigsVar)
    
    # get number of URAMs required for TFs
    hybridConfigsVar.DESIGN_RESOURCES["URAM"] = calc_URAM_utilization_for_tf(hybridConfigsVar)


def calc_LUT_utilization(hybridConfigsVar):
    WORD_SIZE = hybridConfigsVar.DSEParamsVar.WORD_SIZE
    PARA_LIMBS = hybridConfigsVar.DSEParamsVar.PARA_LIMBS

    NUM_BU = hybridConfigsVar.NUM_BU
    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    BUG_CONCAT_FACTOR = hybridConfigsVar.BUG_CONCAT_FACTOR
    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA

    tfBuf_LUT_mod_args = TFBuf_resource_model_table["LUT"]
    in_out_fifo_LUT_mod_args = in_out_fifo_resource_model_table["LUT"]
    in_selector_LUT_mod_args = in_selector_resource_model_table["LUT"]
    out_selector_LUT_mod_args = out_selector_resource_model_table["LUT"]
    shuffler_in_LUT_mod_args = shuffler_in_resource_model_table["LUT"]
    shuffler_buf_single_LUT_mod_args = shuffler_buf_single_resource_model_table["LUT"]
    shuffler_out_shift_LUT_mod_args = shuffler_out_shift_resource_model_table["LUT"]
    shuffler_out_shuffle_LUT_mod_args = shuffler_out_shuffle_resource_model_table["LUT"]

    BU_LUTs = hybridConfigsVar.DSEParamsVar.BU_RESOURCE["LUT"]
    tfBuf_LUTs = round(evaluate_polynomial(WORD_SIZE, tfBuf_LUT_mod_args))
    in_out_fifo_LUTs = round(evaluate_polynomial(WORD_SIZE, in_out_fifo_LUT_mod_args))
    in_selector_LUTs = round(evaluate_polynomial(WORD_SIZE, in_selector_LUT_mod_args))
    out_selector_LUTs = round(evaluate_polynomial(WORD_SIZE, out_selector_LUT_mod_args))
    shuffler_in_LUTs = round(evaluate_polynomial(WORD_SIZE, shuffler_in_LUT_mod_args))
    shuffler_buf_single_LUTs = round(evaluate_polynomial(WORD_SIZE, shuffler_buf_single_LUT_mod_args))
    shuffler_out_shift_LUTs = round(evaluate_polynomial(WORD_SIZE, shuffler_out_shift_LUT_mod_args))
    shuffler_out_shuffle_LUTs = round(evaluate_polynomial(WORD_SIZE, shuffler_out_shuffle_LUT_mod_args))

    total_LUTs_per_para_limb = 0
    total_LUTs = 0

    # add BU LUTs
    total_LUTs_per_para_limb += BU_LUTs * NUM_BU

    # add TFbuf LUTs
    total_LUTs_per_para_limb += ( tfBuf_LUTs * (V_BUG_SIZE//2) * H_BUG_SIZE * BUG_CONCAT_FACTOR )

    # add input and output FIFOs LUTs
    total_LUTs_per_para_limb += ( in_out_fifo_LUTs * V_TOTAL_DATA * 2 )

    # add input_selector LUTs
    total_LUTs_per_para_limb += ( in_selector_LUTs * V_TOTAL_DATA )

    # add output_selector LUTs
    total_LUTs_per_para_limb += ( out_selector_LUTs * V_TOTAL_DATA )

    # add shuffler_in LUTs
    total_LUTs_per_para_limb += ( shuffler_in_LUTs * V_TOTAL_DATA )

    # add shuffler_buff LUTs
    total_LUTs_per_para_limb += ( shuffler_buf_single_LUTs * V_TOTAL_DATA )

    # add shuffler_out_shift LUTs
    total_LUTs_per_para_limb += ( shuffler_out_shift_LUTs * V_TOTAL_DATA )

    # add shuffler_out_shuffle LUTs
    total_LUTs_per_para_limb += ( shuffler_out_shuffle_LUTs * V_TOTAL_DATA )

    total_LUTs = total_LUTs_per_para_limb * PARA_LIMBS

    # add AXI interconnect LUTs
    AXI_interconnect_LUTs = hybridConfigsVar.DESIGN_RESOURCES["offchip_ports"] * AXI_INTERCONNECT_RESOURCES["LUT"]

    total_LUTs += AXI_interconnect_LUTs

    hybridConfigsVar.DESIGN_RESOURCES["LUT"] = total_LUTs

def calc_FF_utilization(hybridConfigsVar):
    WORD_SIZE = hybridConfigsVar.DSEParamsVar.WORD_SIZE
    PARA_LIMBS = hybridConfigsVar.DSEParamsVar.PARA_LIMBS

    NUM_BU = hybridConfigsVar.NUM_BU
    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    BUG_CONCAT_FACTOR = hybridConfigsVar.BUG_CONCAT_FACTOR
    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA

    tfBuf_FF_mod_args = TFBuf_resource_model_table["FF"]
    in_out_fifo_FF_mod_args = in_out_fifo_resource_model_table["FF"]
    in_selector_FF_mod_args = in_selector_resource_model_table["FF"]
    out_selector_FF_mod_args = out_selector_resource_model_table["FF"]
    shuffler_in_FF_mod_args = shuffler_in_resource_model_table["FF"]
    shuffler_buf_single_FF_mod_args = shuffler_buf_single_resource_model_table["FF"]
    shuffler_out_shift_FF_mod_args = shuffler_out_shift_resource_model_table["FF"]
    shuffler_out_shuffle_FF_mod_args = shuffler_out_shuffle_resource_model_table["FF"]

    BU_FFs = hybridConfigsVar.DSEParamsVar.BU_RESOURCE["FF"]
    tfBuf_FFs = round(evaluate_polynomial(WORD_SIZE, tfBuf_FF_mod_args))
    in_out_fifo_FFs = round(evaluate_polynomial(WORD_SIZE, in_out_fifo_FF_mod_args))
    in_selector_FFs = round(evaluate_polynomial(WORD_SIZE, in_selector_FF_mod_args))
    out_selector_FFs = round(evaluate_polynomial(WORD_SIZE, out_selector_FF_mod_args))
    shuffler_in_FFs = round(evaluate_polynomial(WORD_SIZE, shuffler_in_FF_mod_args))
    shuffler_buf_single_FFs = round(evaluate_polynomial(WORD_SIZE, shuffler_buf_single_FF_mod_args))
    shuffler_out_shift_FFs = round(evaluate_polynomial(WORD_SIZE, shuffler_out_shift_FF_mod_args))
    shuffler_out_shuffle_FFs = round(evaluate_polynomial(WORD_SIZE, shuffler_out_shuffle_FF_mod_args))

    total_FFs_per_para_limb = 0
    total_FFs = 0

    # add BU FFs
    total_FFs_per_para_limb += BU_FFs * NUM_BU

    # add TFbuf FFs
    total_FFs_per_para_limb += ( tfBuf_FFs * (V_BUG_SIZE//2) * H_BUG_SIZE * BUG_CONCAT_FACTOR )

    # add input and output FIFOs FFs
    total_FFs_per_para_limb += ( in_out_fifo_FFs * V_TOTAL_DATA * 2 )

    # add input_selector FFs
    total_FFs_per_para_limb += ( in_selector_FFs * V_TOTAL_DATA )

    # add output_selector FFs
    total_FFs_per_para_limb += ( out_selector_FFs * V_TOTAL_DATA )

    # add shuffler_in FFs
    total_FFs_per_para_limb += ( shuffler_in_FFs * V_TOTAL_DATA )

    # add shuffler_buff FFs
    total_FFs_per_para_limb += ( shuffler_buf_single_FFs * V_TOTAL_DATA )

    # add shuffler_out_shift FFs
    total_FFs_per_para_limb += ( shuffler_out_shift_FFs * V_TOTAL_DATA )

    # add shuffler_out_shuffle FFs
    total_FFs_per_para_limb += ( shuffler_out_shuffle_FFs * V_TOTAL_DATA )

    total_FFs = total_FFs_per_para_limb * PARA_LIMBS

    # add AXI interconnect FFs
    AXI_interconnect_FFs = hybridConfigsVar.DESIGN_RESOURCES["offchip_ports"] * AXI_INTERCONNECT_RESOURCES["FF"]

    total_FFs += AXI_interconnect_FFs

    hybridConfigsVar.DESIGN_RESOURCES["FF"] = total_FFs

# Calculate resource utilization
def calc_resource_utilization(hybridConfigsVar):

    # Calc number of DRAM ports
    calc_DRAM_ports_utilization(hybridConfigsVar)

    # Calc DSP usage
    calc_DSP_utilization(hybridConfigsVar)

    # Calc BRAM and URAM usage
    calc_BRAM_URAM_utilization(hybridConfigsVar)

    # Calc LUT usage
    calc_LUT_utilization(hybridConfigsVar)

    # Calc FF usage
    calc_FF_utilization(hybridConfigsVar)

    DSP = hybridConfigsVar.DESIGN_RESOURCES["DSP"]
    BRAM = hybridConfigsVar.DESIGN_RESOURCES["BRAM"]
    URAM = hybridConfigsVar.DESIGN_RESOURCES["URAM"]
    LUT = hybridConfigsVar.DESIGN_RESOURCES["LUT"]
    FF = hybridConfigsVar.DESIGN_RESOURCES["FF"]
    offchip_ports = hybridConfigsVar.DESIGN_RESOURCES["offchip_ports"]

    logging.getLogger("calc_resource_utilization").trace(f"Resources:: DSP = {DSP}, BRAM = {BRAM}, URAM = {URAM}, LUT = {LUT}, FF = {FF}, DRAM ports = {offchip_ports}")