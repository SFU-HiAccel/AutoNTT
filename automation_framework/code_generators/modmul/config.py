from dse.dse_config import DSP_DATA_WIDTHS

#If any word size <= threshold -> map to LUTs 
MAP_TO_LUT_THRESHOLD = 1  #

#Case0 DSP match
DSP_WIDTH0_CASE0 = DSP_DATA_WIDTHS[0]-1
DSP_WIDTH1_CASE0 = DSP_DATA_WIDTHS[1]

#Case1 DSP match
DSP_WIDTH0_CASE1 = DSP_DATA_WIDTHS[0]
DSP_WIDTH1_CASE1 = DSP_DATA_WIDTHS[1]-1

###### Reduction Types ######
NAIVE_RED=0
BARRETT=1
MONTGOMERY=2
WLM=3
CUSTOM_REDUCTION=4

reduction_mode_names = {
    0: "NAIVE_RED",
    1: "BARRETT",
    2: "MONTGOMERY",
    3: "WLM",
    4: "CUSTOM_REDUCTION"
}
#########################

from code_generators.modmul.barrett import gen_barrett
from code_generators.modmul.montgomery import gen_montgomery
from code_generators.modmul.wlm import gen_wlm
from code_generators.modmul.naive import gen_naive
from code_generators.modmul.custom import gen_custom_red

def modmul_header_args(designParamsVar, prefix, suffix):
    reduction_arg_str = ""
    if(designParamsVar.REDUCTION_TYPE==BARRETT):
        reduction_arg_str += str(prefix) + "WORD_PLUS3 factor" + str(suffix)
    elif(designParamsVar.REDUCTION_TYPE==MONTGOMERY):
        reduction_arg_str += str(prefix) + "WORD k" + str(suffix)
    elif(designParamsVar.REDUCTION_TYPE==WLM):
        reduction_arg_str += str(prefix) + "WLM_MULTIPLIER_WORD multiplier" + str(suffix)
    elif(designParamsVar.REDUCTION_TYPE==NAIVE_RED):
        reduction_arg_str += ""
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        interface_args = designParamsVar.CUSTOM_REDUCTION_CONTENT["interface_code"]
        for item in interface_args:
            reduction_arg_str += str(prefix) + item + str(suffix)
    return reduction_arg_str

def modmul_funcCall_args(designParamsVar, prefix, suffix):
    reduction_arg_str = ""
    if(designParamsVar.REDUCTION_TYPE==BARRETT):
        reduction_arg_str += str(prefix) + "factor" + str(suffix)
    elif(designParamsVar.REDUCTION_TYPE==MONTGOMERY):
        reduction_arg_str += str(prefix) + "k" + str(suffix)
    elif(designParamsVar.REDUCTION_TYPE==WLM):
        reduction_arg_str += str(prefix) + "multiplier" + str(suffix)
    elif(designParamsVar.REDUCTION_TYPE==NAIVE_RED):
        reduction_arg_str += ""
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        interface_args = designParamsVar.CUSTOM_REDUCTION_CONTENT["interface_code"]
        interface_arg_name_arr = [item.strip().split()[-1] for item in interface_args]
        for item in interface_arg_name_arr:
            reduction_arg_str += str(prefix) + item + str(suffix)
    return reduction_arg_str

def modmul_kernel_funcCall(designParamsVar):
    line = ""
    
    if(designParamsVar.REDUCTION_TYPE==BARRETT):
        line += "      WORD reducedProduct = barrett_reduce(right, tfVal, q, factor);" + "\n"
    elif(designParamsVar.REDUCTION_TYPE==MONTGOMERY):
        line += "      WORD reducedProduct = montgomery_reduce(right, tfVal, q, k);" + "\n"
    elif(designParamsVar.REDUCTION_TYPE==WLM):
        line += "      WORD reducedProduct = wlm_reduce(right, tfVal, q, multiplier);" + "\n"
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        funcCall = designParamsVar.CUSTOM_REDUCTION_CONTENT["kernel_call"]
        line += "      " + funcCall + "\n"
    elif(designParamsVar.REDUCTION_TYPE==NAIVE_RED):
        line += "      WORD reducedProduct = naive_reduce(right, tfVal, q);" + "\n"
    
    return line

####
# This task is to generate modulo multiplier code
# TODO: Stop taking DSP number as well
####
def gen_modmul(designParamsVar):
    reduction_code = ""
    reduction_dsp_count = 0
    if(designParamsVar.REDUCTION_TYPE==BARRETT):
        reduction_code, reduction_dsp_count = gen_barrett(designParamsVar.WORD_SIZE)
    elif(designParamsVar.REDUCTION_TYPE==MONTGOMERY):
        reduction_code, reduction_dsp_count = gen_montgomery(designParamsVar.WORD_SIZE)
    elif(designParamsVar.REDUCTION_TYPE==WLM):
        reduction_code, reduction_dsp_count = gen_wlm(designParamsVar.WORD_SIZE, designParamsVar.WLM_WORD_SIZE)
    elif(designParamsVar.REDUCTION_TYPE==NAIVE_RED):
        reduction_code, reduction_dsp_count = gen_naive(designParamsVar.WORD_SIZE)
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        reduction_code = gen_custom_red(designParamsVar)
        reduction_dsp_count = 0
    return reduction_code, reduction_dsp_count