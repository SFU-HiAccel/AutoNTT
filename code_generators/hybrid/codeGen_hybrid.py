import sys
import math

from code_generators.common.helper_functions import gen_function_banner
from code_generators.common.helper_functions import calc_log2
from code_generators.common.helper_functions import gen_arch_out_name
from code_generators.common.helper_functions import write_design_files

from code_generators.common.supporting_file_gen import gen_Makefile

from code_generators.hybrid.header_files.include_headers import include_kernel_headers
from code_generators.hybrid.header_files.ntt_header_file import gen_ntt_header_file

from code_generators.hybrid.poly_load_store.poly_load_store import gen_fwd_load_inv_store_poly
from code_generators.hybrid.poly_load_store.poly_load_store import gen_fwd_store_inv_load_poly

from code_generators.modmul.config import modmul_header_args
from code_generators.modmul.config import gen_modmul
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

from code_generators.hybrid.BU.gen_BU import gen_BU
from code_generators.hybrid.BU.gen_twoInverseMul import gen_twoInverseMul

from code_generators.hybrid.shuffler.config import gen_shuffler_control
from code_generators.hybrid.shuffler.config import gen_shuffler

from code_generators.hybrid.TFs.TF_load import gen_tf_load
from code_generators.hybrid.TFs.TF_buffers import gen_tf_buf_config
from code_generators.hybrid.TFs.TF_buffers import gen_TF_buffers

from code_generators.hybrid.flow_controllers.in_out_selector import gen_in_out_selector
from code_generators.hybrid.flow_controllers.dual_interface_FIFO import gen_dual_interface_FIFO

from code_generators.hybrid.kernel_top.header import gen_top_header
from code_generators.hybrid.kernel_top.FIFO import gen_FIFOs
from code_generators.hybrid.kernel_top.task_invokes import gen_task_invokes

from code_generators.hybrid.host.gen_host import gen_ntt_hybrid_host_code

from code_generators.hybrid.dram_connectivity.gen_connectivity import HBM, DDR
from code_generators.hybrid.dram_connectivity.gen_connectivity import gen_ntt_connectivity_code
        
from code_generators.code_gen_config import hybridDesignParams

def generateWrapperTasksWithSpecifiedParams(designParamsVar):
    code = ""

    #generate poly load and store tasks
    banner_title = "Polynomial load store tasks"
    code += gen_function_banner(banner_title)
    code += gen_fwd_load_inv_store_poly(designParamsVar)
    code += "\n"
    code += gen_fwd_store_inv_load_poly(designParamsVar)
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

    #generate shuffler
    banner_title = "Shuffler tasks"
    code += gen_function_banner(banner_title)
    code += gen_shuffler(designParamsVar)
    code += "\n"

    #generate TF buffer tasks
    banner_title = "TF buffer tasks"
    code += gen_function_banner(banner_title)
    code += gen_TF_buffers(designParamsVar)
    code += "\n"

    #generate input and output selector tasks
    banner_title = "Input/Output selector tasks"
    code += gen_function_banner(banner_title)
    code += gen_in_out_selector(designParamsVar)
    code += "\n"

    #generate dual interface FIFO tasks
    banner_title = "Dual interface FIFO tasks"
    code += gen_function_banner(banner_title)
    code += gen_dual_interface_FIFO(designParamsVar)
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

    # Generate FIFO declarations
    code += gen_FIFOs(designParamsVar)
    
    # Generate task invocations
    code += gen_task_invokes(designParamsVar)

    code += "}" + "\n"
    
    return code

def generate_ntt_kernel_hybrid(designParamsVar):
    code = ""
    
    # include header files
    code += include_kernel_headers()
    code += "\n"
    
    # generate task definitions
    code += generateWrapperTasksWithSpecifiedParams(designParamsVar)

    # generate top task
    code += generateTopKernel(designParamsVar)

    return code

def generate_ntt_header_hybrid(designParamsVar):
    code = ""
    
    # include header files
    code += gen_ntt_header_file(designParamsVar)

    return code


def generate_ntt_host_hybrid(designParamsVar):
    code = ""
    
    # generate host code
    code += gen_ntt_hybrid_host_code(designParamsVar)
    
    return code

def generate_ntt_connectivity(designParamsVar):
    code = ""
    
    # generate connectivity file
    code += gen_ntt_connectivity_code(designParamsVar)
    
    return code

def config_design_params(hybridConfigsVar, designParamsVar):
    ######Only chnage this######
    POLY_SIZE = hybridConfigsVar.DSEParamsVar.POLY_SIZE
    WORD_SIZE = hybridConfigsVar.DSEParamsVar.WORD_SIZE
    REDUCTION_TYPE = hybridConfigsVar.DSEParamsVar.REDUCTION_TYPE
    WLM_WORD_SIZE = hybridConfigsVar.DSEParamsVar.WLM_WORD_SIZE
    CUSTOM_REDUCTION_CONTENT = hybridConfigsVar.DSEParamsVar.CUSTOM_REDUCTION_CONTENT

    V_BUG_SIZE = hybridConfigsVar.V_BUG_SIZE
    H_BUG_SIZE = hybridConfigsVar.H_BUG_SIZE
    BUG_CONCAT_FACTOR = hybridConfigsVar.BUG_CONCAT_FACTOR

    PLATFORM_FILE = hybridConfigsVar.DSEParamsVar.PLATFORM_FILE

    DRAM_TYPE = hybridConfigsVar.DSEParamsVar.DEVICE_RESOURCES["offchip_type"]
    DEFAULT_DRAM_PORT_WIDTH = hybridConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    PARA_LIMBS = hybridConfigsVar.DSEParamsVar.PARA_LIMBS

    POLY_LS_PORTS_PER_PARA_LIMB = hybridConfigsVar.POLY_LS_PORTS_PER_PARA_LIMB
    TF_PORTS_PER_PARA_LIMB = hybridConfigsVar.TF_PORTS_PER_PARA_LIMB
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = hybridConfigsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = hybridConfigsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB

    LS_FIFO_BUF_SIZE = hybridConfigsVar.LS_FIFO_BUF_SIZE
    ############################
    logN=calc_log2(POLY_SIZE)
    logV_BUG_SIZE = calc_log2(V_BUG_SIZE)
    logBUG_CONCAT_FACTOR = calc_log2(BUG_CONCAT_FACTOR)

    DRAM_WORD_SIZE = 64 if(WORD_SIZE>32) else 32
    V_TOTAL_DATA = V_BUG_SIZE*BUG_CONCAT_FACTOR*2
    log_V_TOTAL_DATA = (logV_BUG_SIZE+logBUG_CONCAT_FACTOR+1)

    # HBM related
    # Poly
    POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB//DRAM_WORD_SIZE)
    BUG_PER_PARA_LIMB_POLY_PORT = (V_TOTAL_DATA//(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT*POLY_LS_PORTS_PER_PARA_LIMB)) if(2*V_BUG_SIZE>POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT) else (BUG_CONCAT_FACTOR//POLY_LS_PORTS_PER_PARA_LIMB)
    BUG_PER_PARA_LIMB_POLY_WIDE_DATA = (1) if (2*V_BUG_SIZE>POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT) else (POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT//(2*V_BUG_SIZE))
    SEQ_BUG_PER_PARA_LIMB_POLY_PORT = (BUG_PER_PARA_LIMB_POLY_PORT//BUG_PER_PARA_LIMB_POLY_WIDE_DATA)

    PARA_LIMB_PORTS_PER_POLY_PORT = (PARA_LIMBS) if (DEFAULT_DRAM_PORT_WIDTH // POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) else (DEFAULT_DRAM_PORT_WIDTH // POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)
    POLY_LS_PORTS = ((PARA_LIMBS + PARA_LIMB_PORTS_PER_POLY_PORT-1) // PARA_LIMB_PORTS_PER_POLY_PORT) * POLY_LS_PORTS_PER_PARA_LIMB #ceil divsion

    # TFs
    TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (TF_DRAM_PORT_WIDTH_PER_PARA_LIMB//DRAM_WORD_SIZE)
    TF_LOAD_V_SEGS_PER_PARA_LIMB=( ( (V_BUG_SIZE//2) * BUG_CONCAT_FACTOR * 2 ) // TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT )
    TF_LOAD_H_SEGS_PER_PARA_LIMB=TF_PORTS_PER_PARA_LIMB//TF_LOAD_V_SEGS_PER_PARA_LIMB

    PARA_LIMB_PORTS_PER_TF_PORT = (PARA_LIMBS) if (DEFAULT_DRAM_PORT_WIDTH // TF_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) else (DEFAULT_DRAM_PORT_WIDTH// TF_DRAM_PORT_WIDTH_PER_PARA_LIMB)
    TF_PORTS = ((PARA_LIMBS+PARA_LIMB_PORTS_PER_TF_PORT-1) // PARA_LIMB_PORTS_PER_TF_PORT) * TF_PORTS_PER_PARA_LIMB #ceil divsion

    ####
    # In the case of log(vector size)>H_BUG_SIZE it require inter BUG communications
    # The number of inter BUG communications can be more than once based on the vector size and H_BUG_SIZE
    ####
    NUM_INTER_BUG_COM = ( math.ceil(math.log2(V_TOTAL_DATA)/H_BUG_SIZE) - 1 ) # -1 since number of shufflers are one less than rounds


    # update varaibles
    designParamsVar.WORD_SIZE = WORD_SIZE

    designParamsVar.REDUCTION_TYPE = REDUCTION_TYPE
    designParamsVar.WLM_WORD_SIZE = WLM_WORD_SIZE
    designParamsVar.CUSTOM_REDUCTION_CONTENT = CUSTOM_REDUCTION_CONTENT

    designParamsVar.logN = logN
    designParamsVar.POLY_SIZE = POLY_SIZE

    designParamsVar.V_BUG_SIZE = V_BUG_SIZE
    designParamsVar.H_BUG_SIZE = H_BUG_SIZE
    designParamsVar.logV_BUG_SIZE = logV_BUG_SIZE
    designParamsVar.BUG_CONCAT_FACTOR = BUG_CONCAT_FACTOR
    designParamsVar.logBUG_CONCAT_FACTOR = logBUG_CONCAT_FACTOR
    designParamsVar.V_TOTAL_DATA = V_TOTAL_DATA
    designParamsVar.log_V_TOTAL_DATA = log_V_TOTAL_DATA
    designParamsVar.NUM_INTER_BUG_COM = NUM_INTER_BUG_COM

    designParamsVar.PLATFORM_FILE = PLATFORM_FILE

    designParamsVar.DRAM_TYPE = DRAM_TYPE
    designParamsVar.DEFAULT_DRAM_PORT_WIDTH = DEFAULT_DRAM_PORT_WIDTH

    designParamsVar.PARA_LIMBS = PARA_LIMBS

    designParamsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB
    designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB = POLY_LS_PORTS_PER_PARA_LIMB
    designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    designParamsVar.BUG_PER_PARA_LIMB_POLY_PORT = BUG_PER_PARA_LIMB_POLY_PORT
    designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA = BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    designParamsVar.SEQ_BUG_PER_PARA_LIMB_POLY_PORT = SEQ_BUG_PER_PARA_LIMB_POLY_PORT
    designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT = PARA_LIMB_PORTS_PER_POLY_PORT
    designParamsVar.POLY_LS_PORTS = POLY_LS_PORTS

    designParamsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = TF_DRAM_PORT_WIDTH_PER_PARA_LIMB
    designParamsVar.TF_PORTS_PER_PARA_LIMB = TF_PORTS_PER_PARA_LIMB
    designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    designParamsVar.TF_LOAD_V_SEGS_PER_PARA_LIMB = TF_LOAD_V_SEGS_PER_PARA_LIMB
    designParamsVar.TF_LOAD_H_SEGS_PER_PARA_LIMB = TF_LOAD_H_SEGS_PER_PARA_LIMB
    designParamsVar.PARA_LIMB_PORTS_PER_TF_PORT = PARA_LIMB_PORTS_PER_TF_PORT
    designParamsVar.TF_PORTS = TF_PORTS

    designParamsVar.LS_FIFO_BUF_SIZE = LS_FIFO_BUF_SIZE

    # Update shuffler characteristics
    designParamsVar.IS_SPLIT_SHUFFLER, designParamsVar.IS_SPLIT_BUFFER, designParamsVar.IS_INTER_BUG_CONNECTIONS = gen_shuffler_control(designParamsVar)

    # Update TF buffer configs
    designParamsVar.TFBuffersParamsVar = gen_tf_buf_config(designParamsVar)

def gen_code(designParamsVar):
    # Generate Tasks
   
    kernel_code = generate_ntt_kernel_hybrid(designParamsVar)
    host_code = generate_ntt_host_hybrid(designParamsVar)
    header_file_code = generate_ntt_header_hybrid(designParamsVar)
    connectivity_code = generate_ntt_connectivity(designParamsVar)
    
    return kernel_code, host_code, header_file_code, connectivity_code

def gen_hybrid(hybridConfigsVar):

    # create design parameter class
    designParamsVar = hybridDesignParams()

    # update design parameters
    config_design_params(hybridConfigsVar, designParamsVar)

    # generate code
    kernel_code, host_code, header_file_code, connectivity_code = gen_code(designParamsVar)

    # generate output directory name
    output_dir_name = gen_arch_out_name(designParamsVar)

    # generate Makefile
    makefile_content = gen_Makefile(designParamsVar)

    # write to files
    write_design_files(output_dir_name, kernel_code, host_code, header_file_code, connectivity_code, makefile_content)