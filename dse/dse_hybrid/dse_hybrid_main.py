import logging
import math
import copy

from dse.dse_config import hybridConfigs
from dse.dse_config import OFF_CHIP_ACC_TO_COMP_THRESHOLD

from dse.dse_hybrid.hybrid_models import set_next_largest_design
from dse.dse_hybrid.hybrid_models import calc_comp_latency_cycles
from dse.dse_hybrid.hybrid_models import calc_best_BW_for_poly_load_or_store
from dse.dse_hybrid.hybrid_models import calc_best_BW_for_TF_load
from dse.dse_hybrid.hybrid_models import calc_latency_throughput
from dse.dse_hybrid.hybrid_models import calc_resource_utilization

from dse.common.helper_functions import verify_latency_throughput_targets
from dse.common.helper_functions import nearest_lower_power_of_two
from dse.common.helper_functions import verify_resource_targets

from dse.dse_config import BRAM_DEPTH
from dse.dse_config import URAM_DEPTH


# Adding this function to check minimum requirements for AutoNTT-I DSE
def hybrid_arch_min_requirements(hybridConfigsVar):
    num_BU_in_hybrid_arch = hybridConfigsVar.NUM_BU

    meet_requirements = True
    
    # Check minimum BU budget
    if(num_BU_in_hybrid_arch<4):
        logging.getLogger("hybrid_arch_min_requirements").warning(f"AutoNTT-H needs resources for at least 4 BUs. Got only for {num_BU_in_hybrid_arch}. Hence, not running AutoNTT-H DSE")
        meet_requirements = False

    # Check minimum number of DRAM ports
    if(hybridConfigsVar.DSEParamsVar.NUM_DRAM_PORTS<3):
        logging.getLogger("hybrid_arch_min_requirements").warning(f"AutoNTT-H needs at least 3 DRAM ports for polynomials and TFs. Got only {hybridConfigsVar.DSEParamsVar.NUM_DRAM_PORTS}. Hence, not running AutoNTT-H DSE")
        meet_requirements = False
    else: # this is a sanity check to check if the minimum #ports are given
        num_of_DRAM_WORDs_per_port = hybridConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH//hybridConfigsVar.DSEParamsVar.DRAM_WORD_SIZE
        min_num_of_ports_for_each = math.ceil(hybridConfigsVar.DSEParamsVar.PARA_LIMBS / num_of_DRAM_WORDs_per_port) # number of minimum ports required for poly(assuming load and store being done using different ports) and TFs
        min_num_of_ports_required = min_num_of_ports_for_each*3
        logging.getLogger("hybrid_arch_min_requirements").debug(f"Parallel limbs = {hybridConfigsVar.DSEParamsVar.PARA_LIMBS}, #ports per each communication(poly load/poly store/TF) = {min_num_of_ports_for_each}, required #ports = {min_num_of_ports_required}, received #ports = {hybridConfigsVar.DSEParamsVar.NUM_DRAM_PORTS}")
        if(min_num_of_ports_required > hybridConfigsVar.DSEParamsVar.NUM_DRAM_PORTS):
            logging.getLogger("hybrid_arch_min_requirements").warning(f"AutoNTT-H needs at least {min_num_of_ports_required} DRAM ports to support {hybridConfigsVar.DSEParamsVar.PARA_LIMBS} parallel limbs. Got only {hybridConfigsVar.DSEParamsVar.NUM_DRAM_PORTS}. Hence, not running AutoNTT-H DSE")
            meet_requirements = False

    return meet_requirements

# 1. Set #ports requred for the design accordingly
def calc_other_design_params(hybridConfigsVar):
    POLY_SIZE = hybridConfigsVar.DSEParamsVar.POLY_SIZE
    COMPUTE_LATECY_CYCLES = hybridConfigsVar.COMPUTE_LATECY_CYCLES
    V_TOTAL_DATA = hybridConfigsVar.V_TOTAL_DATA

    #### set final ports ####
    hybridConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB, hybridConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = calc_best_BW_for_poly_load_or_store(hybridConfigsVar, COMPUTE_LATECY_CYCLES)
    hybridConfigsVar.TF_PORTS_PER_PARA_LIMB, hybridConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = calc_best_BW_for_TF_load(hybridConfigsVar, COMPUTE_LATECY_CYCLES)

    logging.getLogger("calc_other_design_params").trace(f"Per limb poly ports assigned in the design = {hybridConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB}, per limb width = {hybridConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB}")
    logging.getLogger("calc_other_design_params").trace(f"Per limb TF ports assigned in the design = {hybridConfigsVar.TF_PORTS_PER_PARA_LIMB}, per limb width = {hybridConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB}")

    #### set FIFO buffer sizes ####
    # These FIFOs act as double buffers for polynomial loading and storing.
    # While compute is going on, input side load new data to these FIFOs.
    # Output side read from these FIFOs and complete store.
    exact_needed_fifo_size = POLY_SIZE//V_TOTAL_DATA

    if(exact_needed_fifo_size>BRAM_DEPTH): # Forcing FIFO size to be greater than 4096 to map into URAMs
        hybridConfigsVar.LS_FIFO_BUF_SIZE = max(URAM_DEPTH, exact_needed_fifo_size)
        logging.getLogger("calc_other_design_params").trace(f"Load store FIFO size required = {exact_needed_fifo_size}, Set to = {hybridConfigsVar.LS_FIFO_BUF_SIZE} to map into URAMs")
    else: # Forcing FIFO size to 1024 to map into BRAMs
        hybridConfigsVar.LS_FIFO_BUF_SIZE = BRAM_DEPTH
        logging.getLogger("calc_other_design_params").trace(f"Load store FIFO size required = {exact_needed_fifo_size}, Set to = {hybridConfigsVar.LS_FIFO_BUF_SIZE} to map into BRAMs")

def dse_hybrid(DSEParamsVar):
    
    logging.getLogger("dse_hybrid").info("Start DSE in AutoNTT-H")

    # Create iterative design config object
    hybridConfigsVar = hybridConfigs(DSEParamsVar)

    # Set the number of BUs per single parallel design
    hybridConfigsVar.NUM_BU = DSEParamsVar.NUM_BU_BUDGET // DSEParamsVar.PARA_LIMBS

    # Config object to hold optimum design config
    hybridConfigsVar_optimum = hybridConfigs(DSEParamsVar)
    hybridConfigsVar_optimum.EXPECTED_LATENCY_MS = float("inf")

    # to track if any probable design found
    hybridConfigsVar.ARCH_VALID = False

    # Check whether minimum DSE criterias are met
    meet_min_requirements = hybrid_arch_min_requirements(hybridConfigsVar)

    if(meet_min_requirements):
        logging.getLogger("dse_hybrid").trace("==== Start AutoNTT-H search ====")
        
        # recursively search through next largest BU arrangement until total BU is equal to 4, which is the smallest BUG(2x2)
        while(True):

            # Set the next largest design
            set_next_largest_design(hybridConfigsVar)

            if(hybridConfigsVar.NUM_BU < 4): # NUM_BU reached less than minimum
                break

            logging.getLogger("dse_hybrid").trace(f"== Design = ({ hybridConfigsVar.V_BUG_SIZE } x { hybridConfigsVar.H_BUG_SIZE } BUG) x { hybridConfigsVar.BUG_CONCAT_FACTOR }, Total BUs = { hybridConfigsVar.NUM_BU } ==")

            # Calc compute cycles
            calc_comp_latency_cycles(hybridConfigsVar)
            
            # 1. Set #ports requred for the design accordingly
            calc_other_design_params(hybridConfigsVar)

            # Calc latency and throughput
            calc_latency_throughput(hybridConfigsVar)

            # check if latency and throughput numbers matches with expected targets
            latency_throughput_target_matched = verify_latency_throughput_targets(hybridConfigsVar)
            
            if(latency_throughput_target_matched):

                # check if latency is less than the previous value
                if( hybridConfigsVar.EXPECTED_LATENCY_MS <= hybridConfigsVar_optimum.EXPECTED_LATENCY_MS ):
                    # calculate resources
                    calc_resource_utilization(hybridConfigsVar)

                    # # check if resources are adequate
                    resources_matched = verify_resource_targets(hybridConfigsVar)
                    if(resources_matched):
                        # make the design valid design
                        hybridConfigsVar.ARCH_VALID = True
                        # keep design record
                        hybridConfigsVar_optimum = copy.deepcopy(hybridConfigsVar)
                else: # previous valid design's latency is the minimum
                    logging.getLogger("dse_hybrid").trace(f"Exiting DSE as minimum latency design is found")
                    break

    
    if(hybridConfigsVar_optimum.ARCH_VALID):
        logging.getLogger("dse_hybrid").info(f"Valid design found with ({ hybridConfigsVar_optimum.V_BUG_SIZE } x {hybridConfigsVar_optimum.H_BUG_SIZE} BUG) x {hybridConfigsVar_optimum.BUG_CONCAT_FACTOR} conifguration. Total BUs = { hybridConfigsVar_optimum.NUM_BU }, Latency = {hybridConfigsVar_optimum.EXPECTED_LATENCY_MS} ms, Throughput = {hybridConfigsVar_optimum.EXPECTED_THROUGHPUT} NTT/s")
    else:
        logging.getLogger("dse_hybrid").info(f"Valid design is not found.")
    
    return hybridConfigsVar_optimum
