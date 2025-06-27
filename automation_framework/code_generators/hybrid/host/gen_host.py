from code_generators.common.helper_functions import gen_function_banner

from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

from code_generators.hybrid.header_files.include_headers import include_host_headers

from code_generators.hybrid.kernel_top.header import gen_top_header

from code_generators.hybrid.host.support_host_functions import gen_supporting_host_functions
from code_generators.hybrid.host.host_NTT_compute import gen_host_NTT_compute_functions
from code_generators.hybrid.host.poly_data_arrange import gen_poly_data_rearrange_functions
from code_generators.hybrid.host.TF_data_arrange import gen_TF_data_rearrange_functions
from code_generators.hybrid.host.modMul_precomp import gen_modmul_preComp_functions
from code_generators.hybrid.host.main import gen_main

####
# This task is to generate BU based on the different modulo reduction method
####
def gen_ntt_hybrid_host_code(designParamsVar):
    
    code = ""

    # include header files
    code += include_host_headers()
    code += "\n"

    # include kernel header definition
    code += gen_top_header(designParamsVar)
    code += ";" + "\n"
    code += "\n"

    # generate supporting functions
    banner_title = "Supporting functions"
    code += gen_function_banner(banner_title)
    code += gen_supporting_host_functions(designParamsVar)
    code += "\n"

    # generate host NTT functions
    banner_title = "Cooley-Tukey based NTT computations"
    code += gen_function_banner(banner_title)
    code += gen_host_NTT_compute_functions()
    code += "\n"

    # generate polynomial rearrangement functions
    banner_title = "Polynomial rearrangements"
    code += gen_function_banner(banner_title)
    code += gen_poly_data_rearrange_functions()
    code += "\n"

    # generate TF rearrangement functions
    banner_title = "TF rearrangements"
    code += gen_function_banner(banner_title)
    code += gen_TF_data_rearrange_functions(designParamsVar)
    code += "\n"

    # generate modulo multiplication related functions
    banner_title = "Modulo multiplication precomputations"
    code += gen_function_banner(banner_title)
    code += gen_modmul_preComp_functions(designParamsVar)
    code += "\n"

    # generate main
    banner_title = "main"
    code += gen_function_banner(banner_title)
    code += gen_main(designParamsVar)
    code += "\n"

    return code