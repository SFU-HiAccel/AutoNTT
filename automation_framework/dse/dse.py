import logging
import sys

from dse.dse_compute import calc_dse_precompute
from dse.dse_compute import select_best_design

from dse.dse_iterative.dse_iterative_main import dse_iterative
from dse.dse_dataflow.dse_dataflow_main import dse_dataflow
from dse.dse_hybrid.dse_hybrid_main import dse_hybrid

def invoke_DSE(DSEParamsVar):

    # perform required precomputations to update variables
    calc_dse_precompute(DSEParamsVar)

    iterativeConfigsVar = None
    dataflowConfigsVar = None
    hybridConfigsVar = None
    bestArchConfigVar = None

    
    logging.getLogger("invoke_DSE").info(f"DSE is performed for AutoNTT-{DSEParamsVar.TARGET_ARCH_TYPE}")

    # Invoke DSE and select best
    if("I" in DSEParamsVar.TARGET_ARCH_TYPE): 
        #Invoke iterative
        iterativeConfigsVar = dse_iterative(DSEParamsVar)
    
    if("D" in DSEParamsVar.TARGET_ARCH_TYPE):
        #Invoke dataflow
        dataflowConfigsVar = dse_dataflow(DSEParamsVar)
    
    if("H" in DSEParamsVar.TARGET_ARCH_TYPE):
        #Invoke hybrid
        hybridConfigsVar = dse_hybrid(DSEParamsVar)
    
    #Select the best
    bestArchConfigVar = select_best_design(iterativeConfigsVar, dataflowConfigsVar, hybridConfigsVar)
    
    if(not(bestArchConfigVar.ARCH_VALID)):
        logging.getLogger("invoke_DSE").error("Valid design is not found during DSE for given constraints. Please rerun by relaxing some constraints.")
        sys.exit(1)
    
    return bestArchConfigVar