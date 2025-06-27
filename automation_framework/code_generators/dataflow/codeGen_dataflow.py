import os
import math

from code_generators.common.helper_functions import gen_function_banner
from code_generators.common.helper_functions import gen_arch_out_name
from code_generators.common.helper_functions import write_design_files

from code_generators.common.supporting_file_gen import gen_Makefile

from code_generators.dataflow.header_files.include_headers import include_kernel_headers
from code_generators.dataflow.header_files.ntt_header_file import gen_ntt_header_file

from code_generators.dataflow.TFs.TF_common import gen_TF_load_config
from code_generators.dataflow.TFs.TF_load import gen_tf_load
from code_generators.dataflow.TFs.TF_load import calc_TF_load_port_num
from code_generators.dataflow.TFs.TF_buffers import generate_tfgen_functions
from code_generators.dataflow.poly_load_store.poly_load_store import gen_poly_load_store_tasks
from code_generators.dataflow.poly_load_store.poly_load_store import calc_poly_load_store_port_num

from code_generators.dataflow.shuffler.shuffler import generate_shufflergen_functions

from code_generators.dataflow.kernel_top.header import gen_top_header
from code_generators.dataflow.kernel_top.FIFO import gen_FIFOs
from code_generators.dataflow.kernel_top.task_invokes import gen_task_invokes

from code_generators.dataflow.BU.gen_BU import gen_BU
from code_generators.dataflow.BU.gen_twoInverseMul import gen_twoInverseMul

from code_generators.modmul.config import gen_modmul
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

from code_generators.dataflow.host.gen_host import gen_ntt_dataflow_host_code

from code_generators.dataflow.dram_connectivity.gen_connectivity import HBM, DDR
from code_generators.dataflow.dram_connectivity.gen_connectivity import gen_ntt_connectivity_code

from code_generators.code_gen_config import dataflowDesignParams

###################### generate header code ##########################

def generate_ntt_header_hybrid(designParamsVar):
    code = ""
    
    # include header files
    code += gen_ntt_header_file(designParamsVar)

    return code


###################### generate host code ##########################


def generate_ntt_host_hybrid(designParamsVar):
    code = ""
    
    # generate host code
    code += gen_ntt_dataflow_host_code(designParamsVar)
    
    return code

###################### generate kernel code ##########################


def generateWrapperTasksWithSpecifiedParams(designParamsVar):
    code = ""

    #generate poly load and store tasks
    banner_title = "Polynomial load store tasks"
    code += gen_function_banner(banner_title)
    code += gen_poly_load_store_tasks(designParamsVar)
    code += "\n"

    #generate tf load tasks
    banner_title = "TF load"
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
    code += generate_shufflergen_functions(designParamsVar)
    code += "\n"

    #generate tf load tasks
    banner_title = "TF buffers"
    code += gen_function_banner(banner_title)
    code += generate_tfgen_functions(designParamsVar)
    code += "\n"

    return code

def generateTopKernel(designParamsVar):
    code = ""

    banner_title = "Top kernel"
    code += gen_function_banner(banner_title)
    # code += kernel.generate_top_functions_detach(designParamsVar)

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

def generate_ntt_kernel_dataflow(designParamsVar):
    code = ""
    
    # include header files
    code += include_kernel_headers()
    code += "\n"
    
    # generate task definitions
    code += generateWrapperTasksWithSpecifiedParams(designParamsVar)

    # generate top task
    code += generateTopKernel(designParamsVar)

    return code

def generate_ntt_connectivity(designParamsVar):
    code = ""
    
    # generate connectivity file
    code += gen_ntt_connectivity_code(designParamsVar)
    
    return code

def config_design_params(dataflowConfigsVar, designParamsVar):
    #### Change only this ####
    logN = dataflowConfigsVar.DSEParamsVar.logN  # 10, 14, 17

    WORD_SIZE = dataflowConfigsVar.DSEParamsVar.WORD_SIZE  # 28, 32, 52

    REDUCTION_TYPE = dataflowConfigsVar.DSEParamsVar.REDUCTION_TYPE
    WLM_WORD_SIZE = dataflowConfigsVar.DSEParamsVar.WLM_WORD_SIZE
    CUSTOM_REDUCTION_CONTENT = dataflowConfigsVar.DSEParamsVar.CUSTOM_REDUCTION_CONTENT

    H_BU_NUM = dataflowConfigsVar.H_BUG_SIZE

    PLATFORM_FILE = dataflowConfigsVar.DSEParamsVar.PLATFORM_FILE

    DRAM_TYPE = dataflowConfigsVar.DSEParamsVar.DEVICE_RESOURCES["offchip_type"]
    DEFAULT_DRAM_PORT_WIDTH = dataflowConfigsVar.DSEParamsVar.DRAM_PORT_WIDTH

    PARA_LIMBS = dataflowConfigsVar.DSEParamsVar.PARA_LIMBS

    TF_FIFO_DEPTH = dataflowConfigsVar.TF_FIFO_DEPTH
    ##########################


    V_BU_NUM = (1 << (H_BU_NUM - 1))
    LAST_H_BU_NUM = logN % H_BU_NUM
    CONCAT_FACTOR = (V_BU_NUM << 1)
    LAST_CONCAT_FACTOR = (CONCAT_FACTOR >> (H_BU_NUM - LAST_H_BU_NUM))

    if LAST_H_BU_NUM != 0:
        PARTIAL_COUNT = logN // H_BU_NUM + 1
        partial_group = True
    else:
        PARTIAL_COUNT = logN // H_BU_NUM
        partial_group = False

    # DRAM WORD SIZE
    DRAM_WORD_SIZE = 64 if WORD_SIZE > 32 else 32

    # Update parameter class
    designParamsVar.logN = logN
    designParamsVar.POLY_SIZE = (1<<logN)

    designParamsVar.WORD_SIZE = WORD_SIZE
    designParamsVar.REDUCTION_TYPE = REDUCTION_TYPE
    designParamsVar.WLM_WORD_SIZE = WLM_WORD_SIZE
    designParamsVar.CUSTOM_REDUCTION_CONTENT = CUSTOM_REDUCTION_CONTENT

    designParamsVar.H_BU_NUM = H_BU_NUM
    designParamsVar.V_BU_NUM = V_BU_NUM
    designParamsVar.LAST_H_BU_NUM = LAST_H_BU_NUM
    designParamsVar.PARTIAL_COUNT = PARTIAL_COUNT
    designParamsVar.partial_group = partial_group

    designParamsVar.CONCAT_FACTOR = CONCAT_FACTOR
    designParamsVar.LAST_CONCAT_FACTOR = LAST_CONCAT_FACTOR

    designParamsVar.PLATFORM_FILE = PLATFORM_FILE
    designParamsVar.DRAM_WORD_SIZE = DRAM_WORD_SIZE

    designParamsVar.DRAM_TYPE = DRAM_TYPE
    designParamsVar.DEFAULT_DRAM_PORT_WIDTH = DEFAULT_DRAM_PORT_WIDTH

    designParamsVar.PARA_LIMBS = PARA_LIMBS

    designParamsVar.TF_FIFO_DEPTH = TF_FIFO_DEPTH

    # Polynomial DRAM ports
    HBM_PORT_SIZE, mmap_count = calc_poly_load_store_port_num(designParamsVar)

    # TF DRAM ports
    TF_PORT_SIZE, tf_mmap_count, multi_ports_tf_mmap_count = calc_TF_load_port_num(designParamsVar)

    # Extending DDR port calculation to support parallel limbs with usual notation
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = HBM_PORT_SIZE
    POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB // DRAM_WORD_SIZE

    POLY_LS_PORTS_PER_PARA_LIMB = mmap_count
    PARA_LIMB_PORTS_PER_POLY_PORT = (PARA_LIMBS) if ((DEFAULT_DRAM_PORT_WIDTH // POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB) > PARA_LIMBS) else (DEFAULT_DRAM_PORT_WIDTH // POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)
    POLY_LS_PORTS = math.ceil( PARA_LIMBS / PARA_LIMB_PORTS_PER_POLY_PORT ) * POLY_LS_PORTS_PER_PARA_LIMB

    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = TF_PORT_SIZE
    TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = TF_DRAM_PORT_WIDTH_PER_PARA_LIMB // DRAM_WORD_SIZE
    TF_WIDE_DATA_SIZE_PER_PARA_LIMB = DRAM_WORD_SIZE * TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT

    V_TF_PORTS_PER_PARA_LIMB = tf_mmap_count
    H_TF_PORTS_PER_PARA_LIMB = multi_ports_tf_mmap_count // tf_mmap_count
    TF_PORTS_PER_PARA_LIMB = V_TF_PORTS_PER_PARA_LIMB * H_TF_PORTS_PER_PARA_LIMB
    V_PARA_LIMB_PORTS_PER_TF_PORT = (PARA_LIMBS) if ((DEFAULT_DRAM_PORT_WIDTH // TF_DRAM_PORT_WIDTH_PER_PARA_LIMB) > PARA_LIMBS) else (DEFAULT_DRAM_PORT_WIDTH // TF_DRAM_PORT_WIDTH_PER_PARA_LIMB)
    V_TF_PORTS = math.ceil( PARA_LIMBS / V_PARA_LIMB_PORTS_PER_TF_PORT ) * V_TF_PORTS_PER_PARA_LIMB
    TF_PORTS = V_TF_PORTS * H_TF_PORTS_PER_PARA_LIMB


    designParamsVar.mmap_count = mmap_count
    designParamsVar.tf_mmap_count = tf_mmap_count
    designParamsVar.multi_ports_tf_mmap_count = multi_ports_tf_mmap_count


    designParamsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB
    designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB = POLY_LS_PORTS_PER_PARA_LIMB
    designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT = PARA_LIMB_PORTS_PER_POLY_PORT
    designParamsVar.POLY_LS_PORTS = POLY_LS_PORTS

    designParamsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = TF_DRAM_PORT_WIDTH_PER_PARA_LIMB
    designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    designParamsVar.TF_WIDE_DATA_SIZE_PER_PARA_LIMB = TF_WIDE_DATA_SIZE_PER_PARA_LIMB

    designParamsVar.V_TF_PORTS_PER_PARA_LIMB = V_TF_PORTS_PER_PARA_LIMB
    designParamsVar.H_TF_PORTS_PER_PARA_LIMB = H_TF_PORTS_PER_PARA_LIMB
    designParamsVar.TF_PORTS_PER_PARA_LIMB = TF_PORTS_PER_PARA_LIMB
    designParamsVar.V_PARA_LIMB_PORTS_PER_TF_PORT = V_PARA_LIMB_PORTS_PER_TF_PORT
    designParamsVar.V_TF_PORTS = V_TF_PORTS
    designParamsVar.TF_PORTS = TF_PORTS

    # Update TF load config
    gen_TF_load_config(designParamsVar)

def gen_code(designParamsVar):
    # Generate Tasks
   
    kernel_code = generate_ntt_kernel_dataflow(designParamsVar)
    host_code = generate_ntt_host_hybrid(designParamsVar)
    header_file_code = generate_ntt_header_hybrid(designParamsVar)
    connectivity_code = generate_ntt_connectivity(designParamsVar)
    
    return kernel_code, host_code, header_file_code, connectivity_code

def gen_dataflow(dataflowConfigsVar):

    # create design parameter class
    designParamsVar = dataflowDesignParams()

    # update design parameters
    config_design_params(dataflowConfigsVar, designParamsVar)

    # generate code
    kernel_code, host_code, header_file_code, connectivity_code = gen_code(designParamsVar)

    # generate output directory name
    output_dir_name = gen_arch_out_name(designParamsVar)

    # generate Makefile
    makefile_content = gen_Makefile(designParamsVar)

    # write to files
    write_design_files(output_dir_name, kernel_code, host_code, header_file_code, connectivity_code, makefile_content)