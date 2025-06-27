import logging
import math
import copy

from dse.dse_config import dataflowConfigs
from dse.dse_config import OFF_CHIP_ACC_TO_COMP_THRESHOLD

from dse.dse_dataflow.dataflow_models import get_max_BU_design_in_dataflow_arch
from dse.dse_dataflow.dataflow_models import set_next_largest_design
from dse.dse_dataflow.dataflow_models import calc_comp_latency_cycles
from dse.dse_dataflow.dataflow_models import calc_best_BW_for_poly_load_or_store
from dse.dse_dataflow.dataflow_models import calc_best_BW_for_TF_load
from dse.dse_dataflow.dataflow_models import calc_latency_throughput
from dse.dse_dataflow.dataflow_models import calc_resource_utilization

from dse.common.helper_functions import verify_latency_throughput_targets
from dse.common.helper_functions import nearest_lower_power_of_two
from dse.common.helper_functions import verify_resource_targets

from dse.dse_config import BRAM_DEPTH
from dse.dse_config import URAM_DEPTH


# Adding this function to check minimum requirements for AutoNTT-I DSE
def dataflow_arch_min_requirements(dataflowConfigsVar):
    NUM_BU = dataflowConfigsVar.NUM_BU
    logN = dataflowConfigsVar.DSEParamsVar.logN
    NUM_DRAM_PORTS = dataflowConfigsVar.DSEParamsVar.NUM_DRAM_PORTS

    meet_requirements = True
    
    # Check minimum BU budget
    if(NUM_BU < logN):
        logging.getLogger("dataflow_arch_min_requirements").warning(f"AutoNTT-D needs resources for at least logN={logN} BUs. Got only for {NUM_BU}. Hence, not running AutoNTT-D DSE")
        meet_requirements = False

    # Check minimum number of DRAM ports
    if(NUM_DRAM_PORTS<3):
        logging.getLogger("dataflow_arch_min_requirements").warning(f"AutoNTT-D needs at least 3 DRAM ports for polynomials and TFs. Got only {NUM_DRAM_PORTS}. Hence, not running AutoNTT-D DSE")
        meet_requirements = False

    return meet_requirements

# Set load store poly ports and TF ports
def calc_other_design_params(dataflowConfigsVar):


    #### set final ports ####
    dataflowConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB, dataflowConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = calc_best_BW_for_poly_load_or_store(dataflowConfigsVar)
    
    dataflowConfigsVar.TF_PORTS_PER_PARA_LIMB, dataflowConfigsVar.V_TF_PORTS_PER_PARA_LIMB, dataflowConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = calc_best_BW_for_TF_load(dataflowConfigsVar)
    dataflowConfigsVar.H_TF_PORTS_PER_PARA_LIMB = dataflowConfigsVar.TF_PORTS_PER_PARA_LIMB // dataflowConfigsVar.V_TF_PORTS_PER_PARA_LIMB

    logging.getLogger("calc_other_design_params").trace(f"Per limb poly ports assigned in the design = {dataflowConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB}, per limb width = {dataflowConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB}")
    logging.getLogger("calc_other_design_params").trace(f"Per limb TF ports assigned in the design = {dataflowConfigsVar.TF_PORTS_PER_PARA_LIMB}, per limb width = {dataflowConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB}")

    #### set TF FIFO buffer sizes ####
    # This is related to the TF loading FIFOs within a BUG.
    # As the TF loading within a BUG is done sequentially, layer by layer, they need to have the same pipeline depth as the BUG 
    # to ensure that TF loading can be done smoothly without stalls.
    # As BUs have a pipeline depth, we set pipeline depth of a BU as TF FIFO size.
    dataflowConfigsVar.TF_FIFO_DEPTH = dataflowConfigsVar.DSEParamsVar.BU_PIPELINE_DEPTH_CYCLES
    logging.getLogger("calc_other_design_params").trace(f"TF load FIFO depth is set to {dataflowConfigsVar.TF_FIFO_DEPTH}")


def dse_dataflow(DSEParamsVar):
    
    logging.getLogger("dse_dataflow").info("Start DSE in AutoNTT-D")

    # Create iterative design config object
    dataflowConfigsVar = dataflowConfigs(DSEParamsVar)

    # Set the number of BUs per single parallel design
    get_max_BU_design_in_dataflow_arch(dataflowConfigsVar)

    # Config object to hold optimum design config
    dataflowConfigsVar_optimum = dataflowConfigs(DSEParamsVar)
    dataflowConfigsVar_optimum.EXPECTED_LATENCY_MS = float("inf")

    # to track if any probable design found
    dataflowConfigsVar.ARCH_VALID = False

    # Check whether minimum DSE criterias are met
    meet_min_requirements = dataflow_arch_min_requirements(dataflowConfigsVar)

    if(meet_min_requirements):
        logging.getLogger("dse_dataflow").trace("==== Start AutoNTT-D search ====")
        
        # recursively search through next largest BU arrangement until total BU is equal to 4, which is the smallest BUG(2x2)
        while(dataflowConfigsVar.NUM_BU>0):

            logging.getLogger("dse_dataflow").trace(f"== Design = ({ dataflowConfigsVar.V_BUG_SIZE } x { dataflowConfigsVar.H_BUG_SIZE } BUG), Total BUs = { dataflowConfigsVar.NUM_BU } ==")

            # Calc compute cycles
            calc_comp_latency_cycles(dataflowConfigsVar)
            
            # 1. Set #ports requred for the design accordingly
            calc_other_design_params(dataflowConfigsVar)

            # Calc latency and throughput
            calc_latency_throughput(dataflowConfigsVar)

            # check if latency and throughput numbers matches with expected targets
            latency_throughput_target_matched = verify_latency_throughput_targets(dataflowConfigsVar)
            if(not(latency_throughput_target_matched)): #means largest designs could not match given targets. No reason for further exploring as next designs will be smaller
                break
            
            # check if latency is less than the previous value
            if( dataflowConfigsVar.EXPECTED_LATENCY_MS <= dataflowConfigsVar_optimum.EXPECTED_LATENCY_MS ):
                # calculate resources
                calc_resource_utilization(dataflowConfigsVar)

                # check if resources are adequate
                resources_matched = verify_resource_targets(dataflowConfigsVar)
                if(resources_matched):
                    # make the design valid design
                    dataflowConfigsVar.ARCH_VALID = True
                    # keep design record
                    dataflowConfigsVar_optimum = copy.deepcopy(dataflowConfigsVar)
            else: # previous valid design's latency is the minimum
                logging.getLogger("dse_dataflow").trace(f"Exiting DSE as minimum latency design is found")
                break

            # Set the next largest design
            set_next_largest_design(dataflowConfigsVar)

    
    if(dataflowConfigsVar_optimum.ARCH_VALID):
        logging.getLogger("dse_dataflow").info(f"Valid design found with ({ dataflowConfigsVar_optimum.V_BUG_SIZE } x {dataflowConfigsVar_optimum.H_BUG_SIZE} BUG). Total BUs = { dataflowConfigsVar_optimum.NUM_BU }, Latency = {dataflowConfigsVar_optimum.EXPECTED_LATENCY_MS} ms, Throughput = {dataflowConfigsVar_optimum.EXPECTED_THROUGHPUT} NTT/s")
    else:
        logging.getLogger("dse_dataflow").info(f"Valid design is not found.")
    
    return dataflowConfigsVar_optimum
