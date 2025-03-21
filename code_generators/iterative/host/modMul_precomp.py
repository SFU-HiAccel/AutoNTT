from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM, CUSTOM_REDUCTION

from code_generators.modmul.barrett import gen_barrett_host_func_def
from code_generators.modmul.montgomery import gen_montgomery_host_func_def
from code_generators.modmul.wlm import gen_wlm_host_func_def
from code_generators.modmul.custom import gen_custom_red_host_func_def

def gen_modmul_preComp_functions(designParamsVar):
    line = ""

    # precomputation function generation
    if(designParamsVar.REDUCTION_TYPE==BARRETT):
        line += gen_barrett_host_func_def()
    elif(designParamsVar.REDUCTION_TYPE==MONTGOMERY):
        line += gen_montgomery_host_func_def()
    elif(designParamsVar.REDUCTION_TYPE==WLM):
        line += gen_wlm_host_func_def()
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        line += gen_custom_red_host_func_def(designParamsVar)

    return line