import math
import logging

from dse.dse_config import LUT_FF_MODEL_ADJUST_PERCENTAGE

def linear_model_val(lin_model, val):
    m = lin_model["m"]
    c = lin_model["c"]
    result = m*val + c
    return result 


# Evaluate a polynomial at a given x value.
# Parameters:
# - x: the value at which to evaluate the polynomial.
# - coefficients: list of coefficients [a0, a1, ..., an] representing
#                 a0 + a1*x + a2*x^2 + ... + an*x^n
# Returns:
# - Result of the polynomial evaluated at x.
def evaluate_polynomial(x, coefficients):
    result = 0
    power = 0
    for coeff in (coefficients):
        result += coeff * (x ** power)
        power += 1

    return result


def verify_latency_throughput_targets(archConfigsVar):

    targets_matched = True

    if(archConfigsVar.EXPECTED_LATENCY_MS > archConfigsVar.DSEParamsVar.TARGET_LATENCY_MS):
        targets_matched = False
        logging.getLogger("verify_latency_throughput_targets").trace(f"Target latency is not met. Target = {archConfigsVar.TARGET_LATENCY_MS} ms, Received = {archConfigsVar.EXPECTED_LATENCY_MS} ms")
    
    if(archConfigsVar.EXPECTED_THROUGHPUT < archConfigsVar.DSEParamsVar.TARGET_THROUGHPUT):
        targets_matched = False
        logging.getLogger("verify_latency_throughput_targets").trace(f"Target throughput is not met. Target = {archConfigsVar.TARGET_THROUGHPUT} NTT/s, Received = {archConfigsVar.EXPECTED_THROUGHPUT} NTT/s")

    return targets_matched

def verify_resource_targets(archConfigsVar):
    targets_matched = True

    given_DSP = archConfigsVar.DSEParamsVar.DEVICE_RESOURCES["DSP"]
    given_BRAM = archConfigsVar.DSEParamsVar.DEVICE_RESOURCES["BRAM"]
    given_URAM = archConfigsVar.DSEParamsVar.DEVICE_RESOURCES["URAM"]
    given_LUT = archConfigsVar.DSEParamsVar.DEVICE_RESOURCES["LUT"]
    given_FF = archConfigsVar.DSEParamsVar.DEVICE_RESOURCES["FF"]
    given_offchip_ports = archConfigsVar.DSEParamsVar.NUM_DRAM_PORTS

    exp_DSP = archConfigsVar.DESIGN_RESOURCES["DSP"]
    exp_BRAM = archConfigsVar.DESIGN_RESOURCES["BRAM"]
    exp_URAM = archConfigsVar.DESIGN_RESOURCES["URAM"]
    exp_LUT = archConfigsVar.DESIGN_RESOURCES["LUT"]
    exp_FF = archConfigsVar.DESIGN_RESOURCES["FF"]
    exp_offchip_ports = archConfigsVar.DESIGN_RESOURCES["offchip_ports"]

    logging.getLogger("verify_resource_targets").trace(f"Given resources:: LUT = {given_LUT}, FF = {given_FF}, DSP = {given_DSP}, BRAM = {given_BRAM}, URAM = {given_URAM}, DRAM ports = {given_offchip_ports}")
    logging.getLogger("verify_resource_targets").trace(f"Expected resources:: LUT = {exp_LUT}, FF = {exp_FF}, DSP = {exp_DSP}, BRAM = {exp_BRAM}, URAM = {exp_URAM}, DRAM ports = {exp_offchip_ports}")

    # Checing resource that should match exactly
    exact_match_resources_keys = ["DSP", "BRAM", "URAM"]

    for key in exact_match_resources_keys:
        if(archConfigsVar.DSEParamsVar.DEVICE_RESOURCES[key] < archConfigsVar.DESIGN_RESOURCES[key]):
            targets_matched = False
    
    # Checing resource that should match with an adjustment
    threshold_match_resources_keys = ["LUT", "FF"]

    for key in threshold_match_resources_keys:
        adjusted_resource = round(archConfigsVar.DESIGN_RESOURCES[key] * (100-LUT_FF_MODEL_ADJUST_PERCENTAGE)/100) #in case of overshoot we reduce resources by LUT_FF_MODEL_ADJUST_PERCENTAGE%
        if(archConfigsVar.DSEParamsVar.DEVICE_RESOURCES[key] < adjusted_resource):
            targets_matched = False

    # checking off chip ports
    if(archConfigsVar.DSEParamsVar.NUM_DRAM_PORTS < archConfigsVar.DESIGN_RESOURCES["offchip_ports"]):
        targets_matched = False
    

    if(targets_matched):
        logging.getLogger("verify_resource_targets").trace(f"Resources fit within given range.")
    else:
        logging.getLogger("verify_resource_targets").trace(f"Resources do not fit within given range.")

    return targets_matched

# returns largest two to power number < num 
def nearest_lower_power_of_two(num):
    if(num<1):
        return 0
    else:
        return 1 << (num.bit_length()-1)
        
# returns log(n)
def calc_log2(n):
    if n <= 0 or (n & (n - 1)) != 0:
        raise ValueError(f"{n} is not a power of 2.")
    return int(math.log2(n))