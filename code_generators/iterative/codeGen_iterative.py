from code_generators.common.helper_functions import gen_function_banner
from code_generators.common.helper_functions import calc_log2
from code_generators.common.helper_functions import gen_arch_out_name
from code_generators.common.helper_functions import write_design_files

from code_generators.common.supporting_file_gen import gen_Makefile

from code_generators.iterative.header_files.include_headers import include_kernel_headers
from code_generators.iterative.header_files.ntt_header_file import gen_ntt_header_file

from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM, CUSTOM_REDUCTION
from code_generators.modmul.config import gen_modmul

from code_generators.iterative.BU.gen_BU import gen_BU
from code_generators.iterative.BU.gen_twoInverseMul import gen_twoInverseMul

from code_generators.iterative.TFs.TF_common import fwd_bufWiseTFGroupSizeGen_halfPEsDistBufTogether
from code_generators.iterative.TFs.TF_common import inv_bufWiseTFGroupSizeGen_halfPEsDistBufTogether
from code_generators.iterative.TFs.TF_load import gen_tf_load
from code_generators.iterative.TFs.TF_buffers import gen_TF_buffers

from code_generators.iterative.poly.poly_load_store import gen_poly_load_store
from code_generators.iterative.poly.poly_buffers import gen_poly_buffers

from code_generators.iterative.kernel_top.header import gen_top_header
from code_generators.iterative.kernel_top.FIFO import gen_FIFOs
from code_generators.iterative.kernel_top.task_invokes import gen_task_invokes

from code_generators.iterative.host.gen_host import gen_ntt_iterative_host_code

from code_generators.iterative.dram_connectivity.gen_connectivity import gen_ntt_connectivity_code

from code_generators.code_gen_config import iterativeDesignParams
from code_generators.code_gen_config import iterativeBufParams

def generateWrapperTasksWithSpecifiedParams(designParamsVar):
    code = ""

    #generate poly load and store tasks
    banner_title = "Polynomial load store tasks"
    code += gen_function_banner(banner_title)
    code += gen_poly_load_store(designParamsVar)
    code += "\n"

    #generate tf load tasks
    banner_title = "TF load tasks"
    code += gen_function_banner(banner_title)
    code += gen_tf_load(designParamsVar)
    code += "\n"

    #generate function to multiply with two inverse(required for INV-NTT)
    banner_title = "Function to multiply with two inverse"
    code += gen_function_banner(banner_title)
    code += gen_twoInverseMul()
    code += "\n"

    #generate reduction functions
    banner_title = "Modulo multiplication functions"
    code += gen_function_banner(banner_title)
    reduction_code, reduction_dsp_count = gen_modmul(designParamsVar)
    code += reduction_code
    code += "\n"

    #generate BU
    banner_title = "Butterfly Unit(BU)"
    code += gen_function_banner(banner_title)
    code += gen_BU(designParamsVar)
    code += "\n"

    #generate TF buffer tasks
    banner_title = "TF buffer tasks"
    code += gen_function_banner(banner_title)
    code += gen_TF_buffers(designParamsVar)
    code += "\n"

    #generate TF buffer tasks
    banner_title = "Polynomial buffer tasks"
    code += gen_function_banner(banner_title)
    code += gen_poly_buffers(designParamsVar)
    code += "\n"

    return code

def generateTopKernel(designParamsVar):
    code = ""

    banner_title = "Top kernel"
    code += gen_function_banner(banner_title)

    # Generate header
    code += gen_top_header(designParamsVar)
    
    code += "{" + "\n"
    code += "\n"

    # # Generate FIFO declarations
    code += gen_FIFOs(designParamsVar)
    
    # # Generate task invocations
    code += gen_task_invokes(designParamsVar)

    code += "}" + "\n"
    
    return code

def generate_ntt_kernel_iterative(designParamsVar):
    code = ""
    
    # include header files
    code += include_kernel_headers()
    code += "\n"

    # generate task definitions
    code += generateWrapperTasksWithSpecifiedParams(designParamsVar)

    # generate top task
    code += generateTopKernel(designParamsVar)

    return code

def generate_ntt_header_iterative(designParamsVar):
    code = ""
    
    # include header files
    code += gen_ntt_header_file(designParamsVar)

    return code

def generate_ntt_host_iterative(designParamsVar):
    code = ""
    
    # generate host code
    code += gen_ntt_iterative_host_code(designParamsVar)
    
    return code

def generate_ntt_connectivity(designParamsVar):
    code = ""
    
    # generate connectivity file
    code += gen_ntt_connectivity_code(designParamsVar)

    return code
    
def config_design_params(iterativeConfigsVar, designParamsVar):
    ###### Only update this based on iterativeConfigsVar ######
    POLY_SIZE = iterativeConfigsVar.DSEParamsVar.POLY_SIZE
    WORD_SIZE = iterativeConfigsVar.DSEParamsVar.WORD_SIZE
    REDUCTION_TYPE = iterativeConfigsVar.DSEParamsVar.REDUCTION_TYPE
    WLM_WORD_SIZE = iterativeConfigsVar.DSEParamsVar.WLM_WORD_SIZE
    CUSTOM_REDUCTION_CONTENT = iterativeConfigsVar.DSEParamsVar.CUSTOM_REDUCTION_CONTENT

    NUM_BU = iterativeConfigsVar.NUM_BU

    PARA_LIMBS = iterativeConfigsVar.DSEParamsVar.PARA_LIMBS

    DOUBLE_BUF_EN = iterativeConfigsVar.DOUBLE_BUF_EN

    PLATFORM_FILE = iterativeConfigsVar.DSEParamsVar.PLATFORM_FILE

    DRAM_TYPE = iterativeConfigsVar.DSEParamsVar.DEVICE_RESOURCES["offchip_type"]
    DEFAULT_DRAM_PORT_WIDTH = iterativeConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    POLY_LS_PORTS_PER_PARA_LIMB = iterativeConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB
    TF_PORTS_PER_PARA_LIMB = iterativeConfigsVar.TF_PORTS_PER_PARA_LIMB
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = iterativeConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = iterativeConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB
    
    ############################
    logN=calc_log2(POLY_SIZE)

    logBU = calc_log2(NUM_BU)

    DRAM_WORD_SIZE = 64 if(WORD_SIZE>32) else 32

    #HBM related
    #Poly
    POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB//DRAM_WORD_SIZE)
    NUM_BUF_PER_PARA_LIMB_POLY_PORT = NUM_BU//POLY_LS_PORTS_PER_PARA_LIMB
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = NUM_BUF_PER_PARA_LIMB_POLY_PORT//POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT

    PARA_LIMB_PORTS_PER_POLY_PORT = (PARA_LIMBS) if (DEFAULT_DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) else (DEFAULT_DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)
    POLY_LS_PORTS = ((PARA_LIMBS + PARA_LIMB_PORTS_PER_POLY_PORT-1)//PARA_LIMB_PORTS_PER_POLY_PORT) * POLY_LS_PORTS_PER_PARA_LIMB #ceil divsion

    #TFs
    TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (TF_DRAM_PORT_WIDTH_PER_PARA_LIMB//DRAM_WORD_SIZE)
    NUM_BUF_PER_PARA_LIMB_TF_PORT = (NUM_BU//(2*TF_PORTS_PER_PARA_LIMB))
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = (NUM_BUF_PER_PARA_LIMB_TF_PORT//TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT)

    PARA_LIMB_PORTS_PER_TF_PORT = (PARA_LIMBS) if (DEFAULT_DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) else (DEFAULT_DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB)
    TF_PORTS = ((PARA_LIMBS+PARA_LIMB_PORTS_PER_TF_PORT-1)//PARA_LIMB_PORTS_PER_TF_PORT) * TF_PORTS_PER_PARA_LIMB #ceil divsion

    # update variables
    designParamsVar.WORD_SIZE = WORD_SIZE

    designParamsVar.REDUCTION_TYPE = REDUCTION_TYPE
    designParamsVar.WLM_WORD_SIZE = WLM_WORD_SIZE
    designParamsVar.CUSTOM_REDUCTION_CONTENT = CUSTOM_REDUCTION_CONTENT

    designParamsVar.logN = logN
    designParamsVar.POLY_SIZE = POLY_SIZE

    designParamsVar.logBU = logBU
    designParamsVar.NUM_BU = 1<<(designParamsVar.logBU)

    designParamsVar.PARA_LIMBS = PARA_LIMBS

    designParamsVar.bufParamsVar = iterativeBufParams()

    designParamsVar.DOUBLE_BUF_EN = DOUBLE_BUF_EN

    designParamsVar.PLATFORM_FILE = PLATFORM_FILE

    designParamsVar.DRAM_TYPE = DRAM_TYPE
    designParamsVar.DEFAULT_DRAM_PORT_WIDTH = DEFAULT_DRAM_PORT_WIDTH

    designParamsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB
    designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB = POLY_LS_PORTS_PER_PARA_LIMB
    designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    designParamsVar.NUM_BUF_PER_PARA_LIMB_POLY_PORT = NUM_BUF_PER_PARA_LIMB_POLY_PORT
    designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT
    designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT = PARA_LIMB_PORTS_PER_POLY_PORT
    designParamsVar.POLY_LS_PORTS = POLY_LS_PORTS

    designParamsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = TF_DRAM_PORT_WIDTH_PER_PARA_LIMB
    designParamsVar.TF_PORTS_PER_PARA_LIMB = TF_PORTS_PER_PARA_LIMB
    designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    designParamsVar.NUM_BUF_PER_PARA_LIMB_TF_PORT = NUM_BUF_PER_PARA_LIMB_TF_PORT
    designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT
    designParamsVar.PARA_LIMB_PORTS_PER_TF_PORT = PARA_LIMB_PORTS_PER_TF_PORT
    designParamsVar.TF_PORTS = TF_PORTS

    designParamsVar.beta = designParamsVar.POLY_SIZE//(2*designParamsVar.NUM_BU)
    designParamsVar.logBeta = designParamsVar.logN - designParamsVar.logBU - 1

    designParamsVar.FWD_sizeArr = fwd_bufWiseTFGroupSizeGen_halfPEsDistBufTogether(designParamsVar)
    designParamsVar.INV_sizeArr = inv_bufWiseTFGroupSizeGen_halfPEsDistBufTogether(designParamsVar)

def gen_code(designParamsVar):
    # Generate Tasks
   
    kernel_code = generate_ntt_kernel_iterative(designParamsVar)
    host_code = generate_ntt_host_iterative(designParamsVar)
    header_file_code = generate_ntt_header_iterative(designParamsVar)
    connectivity_code = generate_ntt_connectivity(designParamsVar)
    
    return kernel_code, host_code, header_file_code, connectivity_code

def gen_iterative(iterativeConfigsVar):

    # create design parameter class
    designParamsVar = iterativeDesignParams()

    # update design parameters
    config_design_params(iterativeConfigsVar, designParamsVar)

    # generate code
    kernel_code, host_code, header_file_code, connectivity_code = gen_code(designParamsVar)

    # generate output directory name
    output_dir_name = gen_arch_out_name(designParamsVar)

    # generate Makefile
    makefile_content = gen_Makefile(designParamsVar)

    # write to files
    write_design_files(output_dir_name, kernel_code, host_code, header_file_code, connectivity_code, makefile_content)

# This function is a replica of 'gen_iterative' only to be used during the custom reduction method details extraction
def gen_custom_iterative(iterativeConfigsVar, output_dir_name):

    # create design parameter class
    designParamsVar = iterativeDesignParams()

    # update design parameters
    config_design_params(iterativeConfigsVar, designParamsVar)

    # generate code
    kernel_code, host_code, header_file_code, connectivity_code = gen_code(designParamsVar)

    # generate Makefile
    makefile_content = gen_Makefile(designParamsVar)

    # write to files
    write_design_files(output_dir_name, kernel_code, host_code, header_file_code, connectivity_code, makefile_content)