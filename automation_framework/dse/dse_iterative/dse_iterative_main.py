import logging
import math
import copy

from dse.dse_config import iterativeConfigs
from dse.dse_config import OFF_CHIP_ACC_TO_COMP_THRESHOLD

from dse.dse_iterative.iterative_models import calc_comp_latency_cycles
from dse.dse_iterative.iterative_models import calc_best_BW_for_poly_load_or_store
from dse.dse_iterative.iterative_models import calc_best_BW_for_TF_load
from dse.dse_iterative.iterative_models import calc_poly_load_or_store_cycles
from dse.dse_iterative.iterative_models import calc_tf_load_cycles
from dse.dse_iterative.iterative_models import calc_latency_throughput
from dse.dse_iterative.iterative_models import calc_resource_utilization

from dse.common.helper_functions import verify_latency_throughput_targets
from dse.common.helper_functions import nearest_lower_power_of_two
from dse.common.helper_functions import verify_resource_targets

# Based on the available number of BU budget, this function returns the larget two to the power number
# as the starting point for iterative architecture's DSE
def get_max_BU_in_iter_arch(iterativeConfigsVar):
    NUM_BU_BUDGET = iterativeConfigsVar.DSEParamsVar.NUM_BU_BUDGET
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS

    nu_BU_budget_per_para_arch = NUM_BU_BUDGET//PARA_LIMBS
    return nearest_lower_power_of_two(nu_BU_budget_per_para_arch)

# Adding this function to check minimum requirements for AutoNTT-I DSE
def iterative_arch_min_requirements(iterativeConfigsVar):
    num_BU_in_iter_arch = iterativeConfigsVar.NUM_BU

    meet_requirements = True
    
    # Check minimum BU budget
    if(num_BU_in_iter_arch<2):
        logging.getLogger("iterative_arch_min_requirements").warning(f"AutoNTT-I needs resources for at least 2 BUs. Got only for {num_BU_in_iter_arch}. Hence, not running AutoNTT-I DSE")
        meet_requirements = False

    # Check minimum number of DRAM ports
    if(iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS<2):
        logging.getLogger("iterative_arch_min_requirements").warning(f"AutoNTT-I needs at least 2 DRAM ports for polynomials and TFs. Got only {iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS}. Hence, not running AutoNTT-I DSE")
        meet_requirements = False
    else: # this is a sanity check to check if the minimum #ports are given
        num_of_DRAM_WORDs_per_port = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH//iterativeConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
        min_num_of_ports_for_each_input = math.ceil(iterativeConfigsVar.DSEParamsVar.PARA_LIMBS / num_of_DRAM_WORDs_per_port) # number of minimum ports required for poly(assuming load and store being done using same ports) and TFs
        min_num_of_ports_required = min_num_of_ports_for_each_input*2
        logging.getLogger("iterative_arch_min_requirements").debug(f"Parallel limbs = {iterativeConfigsVar.DSEParamsVar.PARA_LIMBS}, #ports per input(poly/TF) = {min_num_of_ports_for_each_input}, required #ports = {min_num_of_ports_required}, received #ports = {iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS}")
        if(min_num_of_ports_required > iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS):
            logging.getLogger("iterative_arch_min_requirements").warning(f"AutoNTT-I needs at least {min_num_of_ports_required} DRAM ports to support {iterativeConfigsVar.DSEParamsVar.PARA_LIMBS} parallel limbs. Got only {iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS}. Hence, not running AutoNTT-I DSE")
            meet_requirements = False

    return meet_requirements

# 1. Decide if double buff should be enabled or not
# 2. Set #ports requred for the design accordingly
# 3. Calculate load and store time for both poly and TFs
# How to check if double buffering can be avoided:
# Checking stratergy is this function will calculate the minimum number of ports required
# to have off-chip memory access within OFF_CHIP_ACC_TO_COMP_THRESHOLD of compute time and
# see if user have provided enough ports. If yes, then we can go WITHOUT double buffering.
# Later during DSE, it will determine other resource including how to utilize all given ports
def calc_other_design_params(iterativeConfigsVar):
    NUM_DRAM_PORTS = iterativeConfigsVar.DSEParamsVar.NUM_DRAM_PORTS
    DRAM_PORT_WIDTH = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH
    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS
    DRAM_WORD_SIZE = iterativeConfigsVar.DSEParamsVar.DRAM_WORD_SIZE

    NUM_BU = iterativeConfigsVar.NUM_BU
    COMPUTE_LATECY_CYCLES = iterativeConfigsVar.COMPUTE_LATECY_CYCLES


    #### Check double buffer requirments ####
    
    # The maximum allowed off-chip memory access time in cycles
    max_off_chip_access_cycles = math.floor(COMPUTE_LATECY_CYCLES*OFF_CHIP_ACC_TO_COMP_THRESHOLD)

    # max_off_chip_access_cycles contains both load and store time.
    # Hence, calculate time for either for load or store
    max_poly_load_or_store_cycles = max_off_chip_access_cycles//2
    
    #### Poly ####
    # get the number of poly ports and port width required for a single parallel limb
    min_poly_ls_ports_per_para_limb, min_poly_dram_port_width_per_para_limb = calc_best_BW_for_poly_load_or_store(iterativeConfigsVar, NUM_BU, max_poly_load_or_store_cycles)

    # calculate total poly ports required for all parallel limbs
    poly_ls_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//min_poly_dram_port_width_per_para_limb)) * min_poly_ls_ports_per_para_limb

    #### TF ####
    # get the number of TF ports and port width required for a single parallel limb
    min_tf_ports_per_para_limb, min_tf_dram_port_width_per_para_limb = calc_best_BW_for_TF_load(iterativeConfigsVar, NUM_BU, max_off_chip_access_cycles) #TFs can take both poly store and load time to load data for the next iteration.

    # calculate total TF ports required for all parallel limbs
    tf_ports = math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//min_tf_dram_port_width_per_para_limb)) * min_tf_ports_per_para_limb

    # Total ports
    min_dram_ports_required = (poly_ls_ports+tf_ports)

    double_buf_en = True
    if( min_dram_ports_required <= NUM_DRAM_PORTS): # ports are adequate to avoid double buffering
        double_buf_en = False
        logging.getLogger("calc_other_design_params").trace(f"Minimum #ports required to avoid double buffering = {min_dram_ports_required}, received = {NUM_DRAM_PORTS}. Hence, double buffering is not enabled.")
    else:
        logging.getLogger("calc_other_design_params").trace(f"Minimum #ports required to avoid double buffering = {min_dram_ports_required}, received = {NUM_DRAM_PORTS}. Hence, double buffering is enabled.")

    iterativeConfigsVar.DOUBLE_BUF_EN = double_buf_en

    #### set final ports ####

    if(not(iterativeConfigsVar.DOUBLE_BUF_EN)): # if double buffering is not enabled, assign avaialble number of ports based on the minimum ratio as calculated above
        poly_port_ratio = poly_ls_ports/(poly_ls_ports+tf_ports)
        tf_port_ratio = 1-poly_port_ratio
        
        all_ports_for_poly = nearest_lower_power_of_two(math.floor(poly_port_ratio*NUM_DRAM_PORTS))
        all_ports_for_tf = nearest_lower_power_of_two(math.floor(tf_port_ratio*NUM_DRAM_PORTS))

        updated_poly_ls_ports_per_para_limb = all_ports_for_poly // math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//min_poly_dram_port_width_per_para_limb))
        updated_tf_ports_per_para_limb = all_ports_for_tf // math.ceil(PARA_LIMBS / (DRAM_PORT_WIDTH//min_tf_dram_port_width_per_para_limb))

        updated_poly_dram_port_width_per_para_limb = min_poly_dram_port_width_per_para_limb
        updated_tf_dram_port_width_per_para_limb = min_tf_dram_port_width_per_para_limb

        if(updated_poly_ls_ports_per_para_limb!=min_poly_ls_ports_per_para_limb): # new number of ports are given. careful adjustments are need to avoid extra parallelism(i.e., parallelism greater than available buffers), and fill one port 1st for each parallel limb
            poly_ls_ports_per_para_limb_update_ratio = updated_poly_ls_ports_per_para_limb // min_poly_ls_ports_per_para_limb
            updated_poly_dram_port_width_per_para_limb = min(min_poly_dram_port_width_per_para_limb * poly_ls_ports_per_para_limb_update_ratio, min(NUM_BU*DRAM_WORD_SIZE, DRAM_PORT_WIDTH))
            updated_poly_ls_ports_per_para_limb = min(NUM_BU*DRAM_WORD_SIZE // updated_poly_dram_port_width_per_para_limb, updated_poly_ls_ports_per_para_limb * (min_poly_dram_port_width_per_para_limb//updated_poly_dram_port_width_per_para_limb)) # scale down ports accordingly. Either select the scaled down number of ports or required maximum number of ports.
        
        if(updated_tf_ports_per_para_limb!=min_tf_ports_per_para_limb): # new number of ports are given. careful adjustments are need to avoid extra parallelism(i.e., parallelism greater than available buffers), and fill one port 1st for each parallel limb
            tf_ports_per_para_limb_update_ratio = updated_tf_ports_per_para_limb // min_tf_ports_per_para_limb
            updated_tf_dram_port_width_per_para_limb = min(min_tf_dram_port_width_per_para_limb * tf_ports_per_para_limb_update_ratio, min((NUM_BU//2)*DRAM_WORD_SIZE, DRAM_PORT_WIDTH))
            updated_tf_ports_per_para_limb = min(((NUM_BU//2)*DRAM_WORD_SIZE) // updated_tf_dram_port_width_per_para_limb, updated_tf_ports_per_para_limb * (min_tf_dram_port_width_per_para_limb//updated_tf_dram_port_width_per_para_limb)) # scale down ports accordingly. Either select the scaled down number of ports or required maximum number of ports.

        iterativeConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB = updated_poly_ls_ports_per_para_limb
        iterativeConfigsVar.TF_PORTS_PER_PARA_LIMB = updated_tf_ports_per_para_limb
        iterativeConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = updated_poly_dram_port_width_per_para_limb
        iterativeConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = updated_tf_dram_port_width_per_para_limb
    
    else: #if double buffering is enabled, we need to calculate optimum amount of ports and port width to support with double buffer with COMPUTE_LATECY_CYCLES cycle budget. Calculation is done here. Checking resources is done later
        iterativeConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB, iterativeConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = calc_best_BW_for_poly_load_or_store(iterativeConfigsVar, NUM_BU, COMPUTE_LATECY_CYCLES)
        iterativeConfigsVar.TF_PORTS_PER_PARA_LIMB, iterativeConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = calc_best_BW_for_TF_load(iterativeConfigsVar, NUM_BU, COMPUTE_LATECY_CYCLES)

    logging.getLogger("calc_other_design_params").trace(f"Per limb poly ports assigned in the design = {iterativeConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB}, per limb width = {iterativeConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB}")
    logging.getLogger("calc_other_design_params").trace(f"Per limb TF ports assigned in the design = {iterativeConfigsVar.TF_PORTS_PER_PARA_LIMB}, per limb width = {iterativeConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB}")

    #### Update Poly load store time ####
    iterativeConfigsVar.POLY_LOAD_OR_STORE_LATENCY_CYCLES = calc_poly_load_or_store_cycles(iterativeConfigsVar)

    #### Update Poly load store time ####
    iterativeConfigsVar.TF_LOAD_LATENCY_CYCLES = calc_tf_load_cycles(iterativeConfigsVar)

def dse_iterative(DSEParamsVar):
    
    logging.getLogger("dse_iterative").info("Start DSE in AutoNTT-I")

    # Create iterative design config object
    iterativeConfigsVar = iterativeConfigs(DSEParamsVar)

    # Config object to hold optimum design config
    iterativeConfigsVar_optimum = iterativeConfigs(DSEParamsVar)
    iterativeConfigsVar_optimum.EXPECTED_LATENCY_MS = float("inf")

    # Init latency
    latency_ms = float('inf')

    # get the largest number of BUs the iterative design can have
    iterativeConfigsVar.NUM_BU = get_max_BU_in_iter_arch(iterativeConfigsVar)
    logging.getLogger("dse_iterative").debug(f"Highest #BUs AutoNTT-I can have per parallel limb = {iterativeConfigsVar.NUM_BU}")

    # to track if any probable design found
    iterativeConfigsVar.ARCH_VALID = False

    # Check whether minimum DSE criterias are met
    meet_min_requirements = iterative_arch_min_requirements(iterativeConfigsVar)

    if(meet_min_requirements):
        logging.getLogger("dse_iterative").trace("==== Start AutoNTT-I search ====")
        
        # recursively search through next largest BU arrangement
        while(iterativeConfigsVar.NUM_BU>1):

            logging.getLogger("dse_iterative").trace(f"== num_BU = {iterativeConfigsVar.NUM_BU} ==")

            # Calc compute cycles
            calc_comp_latency_cycles(iterativeConfigsVar)
            
            # 1. Decide if double buff should be enabled or not
            # 2. Set #ports requred for the design accordingly
            # 3. Calculate load and store time for both poly and TFs
            calc_other_design_params(iterativeConfigsVar)

            # Calc latency and throughput
            calc_latency_throughput(iterativeConfigsVar)

            # check if latency and throughput numbers matches with expected targets
            latency_throughput_target_matched = verify_latency_throughput_targets(iterativeConfigsVar)
            if(not(latency_throughput_target_matched)): #means largest designs could not match given targets. No reason for further exploring
                break

            # check if latency is less than the previous value
            if( iterativeConfigsVar.EXPECTED_LATENCY_MS <= iterativeConfigsVar_optimum.EXPECTED_LATENCY_MS ):
                # calculate resources
                calc_resource_utilization(iterativeConfigsVar)

                # check if resources are adequate
                resources_matched = verify_resource_targets(iterativeConfigsVar)
                if(resources_matched):
                    # make the design valid design
                    iterativeConfigsVar.ARCH_VALID = True
                    # keep design record
                    iterativeConfigsVar_optimum = copy.deepcopy(iterativeConfigsVar)
            else: # previous valid design's latency is the minimum
                logging.getLogger("dse_iterative").trace(f"Exiting DSE as minimum latency design is found")
                break

            # Reduce number of BUs for next iteration
            iterativeConfigsVar.NUM_BU = iterativeConfigsVar.NUM_BU // 2
    
    if(iterativeConfigsVar_optimum.ARCH_VALID):
        logging.getLogger("dse_iterative").info(f"Valid design found with {iterativeConfigsVar_optimum.NUM_BU} BUs. Latency = {iterativeConfigsVar_optimum.EXPECTED_LATENCY_MS} ms, Throughput = {iterativeConfigsVar_optimum.EXPECTED_THROUGHPUT} NTT/s")
    else:
        logging.getLogger("dse_iterative").info(f"Valid design is not found.")

    return iterativeConfigsVar_optimum
