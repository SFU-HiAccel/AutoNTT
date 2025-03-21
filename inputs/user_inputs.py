import argparse
import json
import os
import logging

from code_generators.modmul.config import NAIVE_RED, BARRETT, MONTGOMERY, WLM, CUSTOM_REDUCTION
from code_generators.common.helper_functions import calc_log2

from inputs.log_setup import setup_logger

from dse.dse_config import HBM_PORT_BW, DDR_PORT_BW
from dse.dse_config import DEFAULT_DRAM_PORT_WIDTH

# Validate polynomial input
def validate_N(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"poly_size/N must be an integer, got '{value}'")

    if n < 2**10 or n > 2**18:
        raise argparse.ArgumentTypeError(f"poly_size/N must be between 2^10 (1024) and 2^18 (262144), got {n}")
    
    if n & (n - 1) != 0:
        raise argparse.ArgumentTypeError(f"poly_size/N must be a power of two, got {n}")

    return n


# Validate modulus size input
def validate_log_q(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"mod_size/log_q must be an integer, got '{value}'")

    if n < 1 or n > 64:
        raise argparse.ArgumentTypeError(f"mod_size/log_q must be a positive number less than or equal to 64, got {n}")

    return n

# Validate FPGA resource input
def validate_resource_json(file_path):
    if not os.path.isfile(file_path):
        raise argparse.ArgumentTypeError(f"File not found: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError(f"Invalid JSON in file '{file_path}': {e}")
    
    # Validate expected keys
    expected_keys = ["LUT", "FF", "DSP", "BRAM", "URAM", "offchip_BW", "offchip_type"]
    for key in expected_keys:
        if key not in data:
            raise argparse.ArgumentTypeError(f"Missing expected key '{key}' in resource file")

    return data  # Return parsed JSON if needed, or file_path if you want to re-read later

def validate_platform_file(parser, input_args):
    # If custom reduction algorithm is used, a valid platform file is a must
    if input_args.custom_mod_kernel:
        if not(input_args.platform):
            parser.error("[ERROR] A platform file must be provided to support custom reduction")
    
    # Chcek if the platform file is available
    platform_path = os.path.join("/opt/xilinx/platforms", input_args.platform)
    if not os.path.exists(platform_path):
        parser.error(f"[ERROR] Platform '{input_args.platform}' not found at: {platform_path}")

# Validate arch input
def validate_arch_type(value):
    valid_types = {'I', 'D', 'H'}
    value = value.strip().upper()

    if not value:
        raise argparse.ArgumentTypeError("Architecture type cannot be empty. Choose from I, D, H.")

    value_set = set(value)

    invalid_chars = value_set - valid_types
    if invalid_chars:
        raise argparse.ArgumentTypeError(
            f"Invalid architecture type(s): {', '.join(invalid_chars)}. "
            f"Allowed types: I (Iterative), D (Dataflow), H (Hybrid)."
        )

    return value


# Validate number of parallel limbs
def validate_parallel_limbs(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"parallel_limbs/pl must be an integer, got '{value}'")

    if n < 1:
        raise argparse.ArgumentTypeError(f"parallel_limbs/pl must be a positive number, got {n}")

    return n

# Set WLM word size to a default value
def validate_and_set_WLM_word_size(parser, input_args):
    if input_args.modmul_type == "WLM":
        if input_args.WLM_word_size is None:
            input_args.WLM_word_size = input_args.log_q//2
            logging.getLogger("validate_and_set_WLM_word_size").info(f"WLM_WORD_SIZE is not provided. Defaulting to = {input_args.WLM_word_size}")
        elif ((input_args.WLM_word_size < 1) or ( input_args.WLM_word_size >= input_args.log_q )):
            raise parser.error(
                f"wlm_word_size must be a positive number less than log_q=({input_args.log_q}), got {input_args.WLM_word_size}"
            )

# Set DRAM port bandwidth to a default value
def validate_and_set_DRAM_port_BW(parser, input_args):

    if(input_args.dram_port_bw is None):
        if(input_args.resource_json["offchip_type"]=="HBM"):
            input_args.dram_port_bw = HBM_PORT_BW
        elif(input_args.resource_json["offchip_type"]=="DDR"):
            input_args.dram_port_bw = DDR_PORT_BW
        logging.getLogger("validate_and_set_DRAM_port_BW").info(f"HBM_PORT_BW is not provided. Defaulting to {input_args.dram_port_bw} GB/s")
    elif(input_args.dram_port_bw <= 0):
        raise parser.error(
                f"DRAM port BW must be a postive number, got {input_args.dram_port_bw}"
            )

# Validate polynomial input
def validate_dram_port_width(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"DRAM port width must be an integer, got '{value}'")

    if n > 1024:
        raise argparse.ArgumentTypeError(f"DRAM port width must be less than or equal to 1024, got {n}")
    
    if n & (n - 1) != 0:
        raise argparse.ArgumentTypeError(f"DRAM port width must be a power of two, got {n}")

    return n

def extract_kernel_code_sections(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()

    defs = []
    call = []
    current_section = None

    for line in lines:
        if "=== BEGIN DEFS ===" in line:
            current_section = "defs"
            continue
        elif "=== END DEFS ===" in line:
            current_section = None
            continue
        elif "=== BEGIN CALL ===" in line:
            current_section = "call"
            continue
        elif "=== END CALL ===" in line:
            current_section = None
            continue

        if current_section == "defs":
            defs.append(line)
        elif current_section == "call":
            call.append(line)

    return "".join(defs), "".join(call)


def is_section_nonempty(section_str):
    lines = section_str.strip().splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("//"):
            return True
    return False

def extract_host_code_sections(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()

    modgen_defs = []
    reduct_defs = []
    modgen_call = []
    reduct_call = []
    current_section = None

    for line in lines:
        if "=== BEGIN MOD_GEN DEFS ===" in line:
            current_section = "modgen_defs"
            continue
        elif "=== END MOD_GEN DEFS ===" in line:
            current_section = None
            continue
        if "=== BEGIN REDUCTION DEFS ===" in line:
            current_section = "reduct_defs"
            continue
        elif "=== END REDUCTION DEFS ===" in line:
            current_section = None
            continue
        elif "=== BEGIN MOD_GEN CALL ===" in line:
            current_section = "modgen_call"
            continue
        elif "=== END MOD_GEN CALL ===" in line:
            current_section = None
            continue
        elif "=== BEGIN REDUCTION CALL ===" in line:
            current_section = "reduct_call"
            continue
        elif "=== END REDUCTION CALL ===" in line:
            current_section = None
            continue

        if current_section == "modgen_defs":
            modgen_defs.append(line)
        elif current_section == "reduct_defs":
            reduct_defs.append(line)
        elif current_section == "modgen_call":
            modgen_call.append(line)
        elif current_section == "reduct_call":
            reduct_call.append(line)

    modgen_defs_section = "".join(modgen_defs)
    reduct_defs_section = "".join(reduct_defs)
    modgen_call_section = "".join(modgen_call)
    reduct_call_section = "".join(reduct_call)

    if not(is_section_nonempty(modgen_defs_section)):
        modgen_defs_section = ""

    if not(is_section_nonempty(reduct_defs_section)):
        reduct_defs_section = ""

    if not(is_section_nonempty(modgen_call_section)):
        modgen_call_section = ""

    if not(is_section_nonempty(reduct_call_section)):
        reduct_call_section = ""

    return modgen_defs_section, reduct_defs_section, modgen_call_section, reduct_call_section

# Validate custom modulo reduction content
# Validations
# 1. kernel code file must be passed. Others are optional
# 2. kerenel code content cannot be empty.
# 3. kernel code must contain function definition and function call
# 4. function call must contain "WORD reducedProduct = " to match the template
# Process
# 1. Read the content and return a dictionary
def validate_and_return_custom_reduction(parser, input_args):
    
    # Default content
    kernel_defs = ""
    kernel_call = ""
    host_mod_gen_defs = ""
    host_reduction_defs = ""
    host_mod_gen_call = ""
    host_reduction_call = ""
    header_code = ""
    interface_args = []

    if input_args.modmul_type == "C": # if reduction algo is custom
        #### Necessary inputs in custom reduction ####

        # Read and validate kernel code
        if input_args.custom_mod_kernel:
            try:
                kernel_defs, kernel_call = extract_kernel_code_sections(input_args.custom_mod_kernel)
            except Exception as e:
                parser.error(f"Failed to read or parse kernel code file: {e}")

            if not kernel_defs.strip():
                parser.error("Kernel code must contain a function definition section marked with // === BEGIN DEFS ===")

            if not kernel_call.strip():
                parser.error("Kernel code must contain a function call section marked with // === BEGIN CALL ===")

            if "WORD reducedProduct =" not in kernel_call:
                parser.error("Kernel function call must include 'WORD reducedProduct = ...'")
        else:
            parser.error("For custom reduction algorithm passing the kernel code using --custom_mod_kernel is a must.")


        #### Optional inputs in custom reduction ####

        # Parse host code (optional)
        if input_args.custom_mod_host:
            if not input_args.custom_mod_kernel:
                parser.error(f"Custom reduction host code cannot be passed without a kernel code")
            try:
                host_mod_gen_defs, host_reduction_defs, host_mod_gen_call, host_reduction_call = extract_host_code_sections(input_args.custom_mod_host)
            except Exception as e:
                parser.error(f"Failed to read or parse host code file: {e}")

        # Parse header file content (optional)
        if input_args.custom_mod_header:
            if not input_args.custom_mod_kernel:
                parser.error(f"Custom reduction header file content cannot be passed without a kernel code")
            try:
                with open(input_args.custom_mod_header, "r") as f:
                    header_code = f.read().strip()
            except Exception as e:
                parser.error(f"Failed to read optional file {input_args.custom_mod_header}: {e}")
        
        # Parse interface arguments
        if input_args.custom_mod_interface:
            if not input_args.custom_mod_kernel:
                parser.error(f"Custom reduction interface variables cannot be passed without a kernel code")
            try:
                with open(input_args.custom_mod_interface, "r") as f:
                    interface_code = f.read().strip()
            except Exception as e:
                parser.error(f"Failed to read interface file: {e}")

            if not interface_code:
                parser.error("Interface file is empty.")

            # Split on commas and clean each argument
            try:
                interface_args = [arg.strip() for arg in interface_code.split(",") if arg.strip()]
            except Exception as e:
                parser.error(f"Failed to parse interface arguments: {e}")

    else:
        if input_args.custom_mod_kernel:
            logging.getLogger("validate_and_return_custom_reduction").warning("--custom_mod_kernel has been set without setting reduction method as custom(C). Ignoring")
        if input_args.custom_mod_host:
            logging.getLogger("validate_and_return_custom_reduction").warning("--custom_mod_host has been set without setting reduction method as custom(C). Ignoring")
        if input_args.custom_mod_header:
            logging.getLogger("validate_and_return_custom_reduction").warning("--custom_mod_header has been set without setting reduction method as custom(C). Ignoring")
        if input_args.custom_mod_interface:
            logging.getLogger("validate_and_return_custom_reduction").warning("--custom_mod_interface has been set without setting reduction method as custom(C). Ignoring")

    # Return everything in a structured dictionary
    return {
        "kernel_defs": kernel_defs,
        "kernel_call": kernel_call,
        "host_mod_gen_defs": host_mod_gen_defs,
        "host_reduction_defs": host_reduction_defs,
        "host_mod_gen_call": host_mod_gen_call,
        "host_reduction_call": host_reduction_call,
        "header_code": header_code,
        "interface_code": interface_args
    }


def get_user_inputs(DSEParamsVar):

    parser = argparse.ArgumentParser(
        description="AutoNTT: Automatic Architecture Design and Exploration for Number Theoretic Transform Acceleration on FPGAs"
    )

    # === Mandatory Arguments ===
    # Group: Algo parameters
    algo_group = parser.add_argument_group("Mandatory: FHE parameters")
    algo_group.add_argument("--poly_size", "-N", required=True, dest="N", type=validate_N, action="store", help="Specify the polynomial size (must be power of 2 between 2^10-2^18)")
    algo_group.add_argument("--mod_size", "-log_q", required=True, dest="log_q", type=validate_log_q, action="store", help="Specify the bit length of modulus (must be a positive number less than or equal to 64)")

    # Group: Device parameters
    device_group = parser.add_argument_group("Mandatory: FPGA Device parameters")
    device_group.add_argument("--resources", "-r", required=True, dest="resource_json", type=validate_resource_json, action="store", help="Provide device resources in a JSON file")
    device_group.add_argument("--platform", "-p", required=False, dest="platform", type=str, action="store", help="Pass the target platform", default="xilinx_u280_gen3x16_xdma_1_202211_1")

    # === Optional Arguments ===
    # Group: Performance parameters
    perf_group = parser.add_argument_group("Optional: Performance targets")
    perf_group.add_argument("--latency_target", "-lt", required=False, dest="latency_target", type=float, action="store", help="Provide target latency in milliseconds", default=float('inf'))
    perf_group.add_argument("--throughput_target", "-tt", required=False, dest="throughput_target", type=int, action="store", help="Provide target throughput in #NTT/sec", default=0)

    # Group: Architecture specific
    arch_group = parser.add_argument_group("Optional: Architecture specific")
    arch_group.add_argument("--arch_type", "-a", required=False, dest="arch", type=validate_arch_type, action="store", help="Specify a target architecture types if needed. Architecture types: I=Iterative, D=Dataflow, H=Hybrid", default="IDH")

    # Group: Parallel limbs
    perf_group = parser.add_argument_group("Optional: Parallel limbs")
    perf_group.add_argument("--parallel_limbs", "-pl", required=False, dest="num_parallel_limbs", type=validate_parallel_limbs, action="store", help="Specify number of parallel limbs in the design", default=1)

    # Group: Modulo multiplication specific
    modmul_group = parser.add_argument_group("Optional: Modulo multiplication specific")
    modmul_group.add_argument("--modmul_type", "-mm", required=False, dest="modmul_type", type=str, action="store", choices=["B", "M", "WLM", "C", "N"], help="Modulo multiplication methods: B=Barrett, M=Montgomery, WLM=Word Level Montgomery, N=Naive, C=Custom", default="B")
    modmul_group.add_argument("--wlm_word_size", "-wlm_ws", required=False, dest="WLM_word_size", type=int, action="store", help="Specify Word Level Montgomery word size.")
    modmul_group.add_argument("--custom_mod_kernel", "-cm_kernel", required=False, dest="custom_mod_kernel", type=str, action="store", help="Pass the kernel code content of the custom modulo reduction")
    modmul_group.add_argument("--custom_mod_host", "-cm_host", required=False, dest="custom_mod_host", type=str, action="store", help="Pass the host code content of the custom modulo reduction")
    modmul_group.add_argument("--custom_mod_header", "-cm_header", required=False, dest="custom_mod_header", type=str, action="store", help="Pass the header file content of the custom modulo reduction")
    modmul_group.add_argument("--custom_mod_interface", "-cm_interface", required=False, dest="custom_mod_interface", type=str, action="store", help="Pass the interface variable definitions")

    # Group: DRAM parameter overwrite
    dram_param_group = parser.add_argument_group("Optional: DRAM parameters")
    dram_param_group.add_argument("--dram_port_bw", "-p_bw", required=False, dest="dram_port_bw", type=float, action="store", help="Specify BW per DRAM port. Defaults: HBM = 13.18GB/s, DDR = 13.73GB/s")
    dram_param_group.add_argument("--dram_port_width", "-p_w", required=False, dest="dram_port_width", type=validate_dram_port_width, action="store", help=f"Specify DRAM port width in terms of bits. Defaults = {DEFAULT_DRAM_PORT_WIDTH}", default=DEFAULT_DRAM_PORT_WIDTH)
    

    # Group: Misc parameters
    misc_group = parser.add_argument_group("Optional: Misc parameters")
    misc_group.add_argument("--verbose", "-v", required=False, dest="verbosity", type=int, action="store", choices=[0, 1, 2], help="Verbosity level: 0=INFO, 1=DEBUG, 2=TRACE", default=0)

    input_args = parser.parse_args()

    # Setup logger
    setup_logger(input_args.verbosity)

    # Check whether the platform file is valid
    validate_platform_file(parser, input_args)

    # Conditional assignment of wlm_word_size
    validate_and_set_WLM_word_size(parser, input_args)

    # Conditional assignment of dram port bandwidth
    validate_and_set_DRAM_port_BW(parser, input_args)
    
    # Conditional assignment for custom reduction methods
    custom_reduction_content = validate_and_return_custom_reduction(parser, input_args)

    # Assign input values to variables in class object
    DSEParamsVar.WORD_SIZE = input_args.log_q
    
    DSEParamsVar.POLY_SIZE = input_args.N
    DSEParamsVar.logN = calc_log2(input_args.N)

    DSEParamsVar.DEVICE_RESOURCES = input_args.resource_json
    DSEParamsVar.PLATFORM_FILE = input_args.platform

    DSEParamsVar.TARGET_LATENCY_MS = input_args.latency_target
    DSEParamsVar.TARGET_THROUGHPUT = input_args.throughput_target

    DSEParamsVar.TARGET_ARCH_TYPE = input_args.arch

    DSEParamsVar.PARA_LIMBS = input_args.num_parallel_limbs

    if(input_args.modmul_type=="B"):
        DSEParamsVar.REDUCTION_TYPE = BARRETT
    elif(input_args.modmul_type=="M"):
        DSEParamsVar.REDUCTION_TYPE = MONTGOMERY
    elif(input_args.modmul_type=="WLM"):
        DSEParamsVar.REDUCTION_TYPE = WLM
    elif(input_args.modmul_type=="C"):
        DSEParamsVar.REDUCTION_TYPE = CUSTOM_REDUCTION
    elif(input_args.modmul_type=="N"):
        DSEParamsVar.REDUCTION_TYPE = NAIVE_RED

    DSEParamsVar.WLM_WORD_SIZE = input_args.WLM_word_size
    DSEParamsVar.CUSTOM_REDUCTION_CONTENT = custom_reduction_content

    DSEParamsVar.DRAM_BW_PER_PORT = input_args.dram_port_bw
    DSEParamsVar.DRAM_PORT_WIDTH = input_args.dram_port_width

    logging.getLogger("get_user_inputs").info("Finished validating input arguments")
