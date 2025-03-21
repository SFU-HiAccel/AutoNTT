import logging
import copy
import subprocess
import re
import os
import sys
import glob
import shutil
from types import SimpleNamespace

from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM
from code_generators.modmul.config import gen_modmul
from dse.common.helper_functions import evaluate_polynomial

from code_generators.iterative.codeGen_iterative import gen_custom_iterative

# Depth table
# This is created based on linear interpolation.
# Data has been collected from 28-64 bit widths with stride of 4 and m and c values has been calculated based on linear interpolation
# update this
BU_pipe_depth_table = {
    BARRETT: [-1.4727, 0.4701, -0.0033],
    MONTGOMERY: [4.1879, 0.2515, -0.0019],
    WLM: [8.7788, -0.0479, 0.0017],
    NAIVE_RED: [5.9758, 2.0788],
}

BU_resource_model_table = {
    BARRETT: {
    "LUT": [-181.79, 39.484],
    "FF": [-419.57, 29.702]
    },
    MONTGOMERY: {
    "LUT": [-189.24, 40.592],
    "FF": [-140.3, 21.715]
    },
    WLM: {
    "LUT": [106.35, 26.711],
    "FF": [-313.56, 25.462]
    },
    NAIVE_RED: {
    "LUT": [-12173, 562.07],
    "FF": [-11872, 546.22]
    }
}

def calc_BU_pipe_depth(DSEParamsVar):
    REDUCTION_TYPE = DSEParamsVar.REDUCTION_TYPE
    WORD_SIZE = DSEParamsVar.WORD_SIZE

    BU_pipe_depth_poly_mod_args = BU_pipe_depth_table[REDUCTION_TYPE]
    BU_pipe_depth = round(evaluate_polynomial(WORD_SIZE, BU_pipe_depth_poly_mod_args))
    # if (REDUCTION_TYPE in [BARRETT, MONTGOMERY, NAIVE_RED]): # go with equation
    # else: # try example design and extract data

    logging.getLogger("calc_BU_pipe_depth").trace(f"BU pipeline depth = {BU_pipe_depth}")

    return BU_pipe_depth

def calc_BU_DSPs(DSEParamsVar):
    reduction_code, num_of_dsps_per_BU = gen_modmul(DSEParamsVar)
    # if (REDUCTION_TYPE in [BARRETT, MONTGOMERY, NAIVE_RED]): # go with equation
    # else: # try example design and extract data
    return num_of_dsps_per_BU

def calc_BU_LUTs(DSEParamsVar):
    REDUCTION_TYPE = DSEParamsVar.REDUCTION_TYPE
    WORD_SIZE = DSEParamsVar.WORD_SIZE

    BU_LUTs_poly_mod_args = BU_resource_model_table[REDUCTION_TYPE]["LUT"]
    BU_LUTs = round(evaluate_polynomial(WORD_SIZE, BU_LUTs_poly_mod_args))
    # if (REDUCTION_TYPE in [BARRETT, MONTGOMERY, NAIVE_RED]): # go with equation
    # else: # try example design and extract data

    return BU_LUTs

def calc_BU_FFs(DSEParamsVar):
    REDUCTION_TYPE = DSEParamsVar.REDUCTION_TYPE
    WORD_SIZE = DSEParamsVar.WORD_SIZE

    BU_FFs_poly_mod_args = BU_resource_model_table[REDUCTION_TYPE]["FF"]
    BU_FFs = round(evaluate_polynomial(WORD_SIZE, BU_FFs_poly_mod_args))
    # if (REDUCTION_TYPE in [BARRETT, MONTGOMERY, NAIVE_RED]): # go with equation
    # else: # try example design and extract data

    return BU_FFs



def extract_depth_from_log(log_path):
    with open(log_path, "r") as f:
        for line in f:
            if "Pipelining result" in line and "BU_COMP" in line:
                match = re.search(r"Depth\s*=\s*(\d+)", line)
                if match:
                    return int(match.group(1))
    raise ValueError("Depth not found in log.")

def extract_resource_from_log(file_path):
    with open(file_path, "r") as f:
        for line in f:
            if "TASK_VERTEX_BU_0" in line:
                # Use regex to extract values
                match = re.search(r'DSP:\s*(\d+)\s+FF:\s*(\d+)\s+LUT:\s*([\d.]+)', line)
                if match:
                    dsp = int(match.group(1))
                    ff = float(match.group(2))
                    lut = float(match.group(3))
                    return dsp, ff, lut
                else:
                    raise ValueError("Could not parse resource line")
    
    raise FileNotFoundError("TASK_VERTEX_BU_0 not found in log")


def get_custom_reduction_BU_attributes(DSEParamsVar):

    temp_dir = "temp_design"
    BU_log_path = temp_dir + "/NTT_kernel." + DSEParamsVar.PLATFORM_FILE + ".hw.xo.tapa/log/BU.log"
    autobridge_log_pattern = temp_dir + "/NTT_kernel." + DSEParamsVar.PLATFORM_FILE + ".hw.xo.tapa/autobridge/autobridge-*.log"

    # Create a temporary namespace to generate a small iterative design
    DSEParamsVar_copy = copy.deepcopy(DSEParamsVar)
    DSEParamsVar_copy.PARA_LIMBS = 1
    params = SimpleNamespace(
        ARCH_IDENTITY = "I",
        DSEParamsVar=DSEParamsVar_copy,
        NUM_BU = 2,
        DOUBLE_BUF_EN = False,
        POLY_LS_PORTS_PER_PARA_LIMB = 1,
        TF_PORTS_PER_PARA_LIMB = 1,
        POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = DSEParamsVar.DRAM_WORD_SIZE,
        TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = DSEParamsVar.DRAM_WORD_SIZE
        )
    
    # generate custom small iterative architecture design (can change the arch if needed)
    logging.getLogger("get_custom_reduction_BU_attributes").info(f"Creating a temporary design to extract BU details with the custom reduction algorithm")
    gen_custom_iterative(params, temp_dir)

    logging.getLogger("get_custom_reduction_BU_attributes").info(f"Start compiling process to extract the details")
    # try csim first to make sure accuracy
    try:
        original_dir = os.getcwd()  # Save current directory
        os.chdir(temp_dir)     # Change to temp_design

        # Only show shell output if TRACE level is enabled
        show_output = logging.getLogger("get_custom_reduction_BU_attributes").isEnabledFor(5)  # 5 = TRACE
        subprocess.run(["make", "csim"], 
                        check=True,
                        stdout=None if show_output else subprocess.DEVNULL,
                        stderr=None if show_output else subprocess.DEVNULL,)

        os.chdir(original_dir)     # Return to original directory

    except subprocess.CalledProcessError:
        os.chdir(original_dir)     # Make sure we return even if make fails
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"C simulation failed with given custom reduction method. Please check a temporary design in {temp_dir} to verify the accuracy.")
        sys.exit(1)

    except Exception as e:
        os.chdir(original_dir)     # Handle other errors
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"Unexpected error {e} in C simulation. Please check a temporary design in {temp_dir} to verify.")
        sys.exit(1)

    
    # try autobridge run to collect data
    try:
        original_dir = os.getcwd()  # Save current directory
        os.chdir(temp_dir)     # Change to temp_design

        subprocess.run(["make", "tapa_wi_autobridge"], 
                        check=True,
                        stdout=None if show_output else subprocess.DEVNULL,
                        stderr=None if show_output else subprocess.DEVNULL,)

        os.chdir(original_dir)     # Return to original directory

    except subprocess.CalledProcessError:
        os.chdir(original_dir)     # Make sure we return even if make fails
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"TAPA/Autobridge run failed with given custom reduction method. Please check a temporary design in {temp_dir} to verify the accuracy.")
        sys.exit(1)

    except Exception as e:
        os.chdir(original_dir)     # Handle other errors
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"Unexpected error {e} in TAPA/Autobridge run. Please check a temporary design in {temp_dir} to verify.")
        sys.exit(1)

    # extract BU pipeline depth
    if not os.path.exists(BU_log_path):
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"Synthesis log for BU is not found in {BU_log_path} path. Please check a temporary design in {temp_dir} to verify.")
        sys.exit(1)
    
    try:
        BU_pipe_depth = extract_depth_from_log(BU_log_path)
    except Exception as e:
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"Error {e} while searching for pipeline depth in file {BU_log_path}. Please check a temporary design in {temp_dir} to verify.")
        sys.exit(1)

    # extract resources from autobridge log
    log_files = glob.glob(autobridge_log_pattern)
    if not log_files:
        print(f"[ERROR] No log files found matching: {autobridge_log_pattern}")
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"No log files found matching: {autobridge_log_pattern}")
        sys.exit(1)

    autobridge_log_path = log_files[0]
    try:
        num_of_dsps_per_BU, BU_FFs, BU_LUTs = extract_resource_from_log(autobridge_log_path)
        
    except Exception as e:
        print(f"[ERROR] Failed to extract resources: {e}")
        logging.getLogger("get_custom_reduction_BU_attributes").error(f"Error {e} while searching for resources in file {autobridge_log_path}. Please check a temporary design in {temp_dir} to verify.")
        sys.exit(1)

    # remove temporary dir
    shutil.rmtree(temp_dir)
    logging.getLogger("get_custom_reduction_BU_attributes").info(f"Finish BU details extraction")

    return BU_pipe_depth, num_of_dsps_per_BU, BU_LUTs, BU_FFs

    