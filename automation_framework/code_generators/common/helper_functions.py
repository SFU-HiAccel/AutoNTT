import math
import os
import logging

from code_generators.modmul.config import reduction_mode_names

def num_arr_to_cppArrStr(arr_in):
    str_arr_in =  [str(x) for x in arr_in]
    str_out = "{" + ", ".join(str_arr_in) + "}"
    return str_out

def binary_arr_to_cppArrStr(arr_in):
    str_arr_in =  [ 'true' if (x) else 'false' for x in arr_in]
    str_out = "{" + ", ".join(str_arr_in) + "}"
    return str_out

def gen_function_banner(banner_name):
    line = ""
    line += "// /********************************************************************************************" + "\n"
    line += "// * " + banner_name + " *" + "\n"
    line += "// ********************************************************************************************/" + "\n"
    line += "\n"

    return line

def calc_log2(n):
    if n <= 0 or (n & (n - 1)) != 0:
        raise ValueError(f"{n} is not a power of 2.")
    return int(math.log2(n))

def gen_arch_out_name(bestArchConfigVar):
    
    
    POLY_SIZE = bestArchConfigVar.POLY_SIZE
    WORD_SIZE = bestArchConfigVar.WORD_SIZE
    REDUCTION_TYPE = bestArchConfigVar.REDUCTION_TYPE
    
    reduction_name = reduction_mode_names[REDUCTION_TYPE]
    
    common_output_dir = "tool_outputs/"

    name = ""
    if(bestArchConfigVar.ARCH_IDENTITY == "I"):
        NUM_BU = bestArchConfigVar.NUM_BU
        name = common_output_dir + f"AutoNTT_I__N_{POLY_SIZE}__q_{WORD_SIZE}__red_{reduction_name}__BUs_{NUM_BU}"
    elif(bestArchConfigVar.ARCH_IDENTITY == "D"):
        logN = bestArchConfigVar.logN
        V_BUG_SIZE = bestArchConfigVar.V_BU_NUM
        H_BUG_SIZE = bestArchConfigVar.H_BU_NUM
        name = common_output_dir + f"AutoNTT_D__N_{POLY_SIZE}__q_{WORD_SIZE}__red_{reduction_name}__BUG_{V_BUG_SIZE}x{H_BUG_SIZE}__BUs_{V_BUG_SIZE*logN}"
    elif(bestArchConfigVar.ARCH_IDENTITY == "H"):
        V_BUG_SIZE = bestArchConfigVar.V_BUG_SIZE
        H_BUG_SIZE = bestArchConfigVar.H_BUG_SIZE
        BUG_CONCAT_FACTOR = bestArchConfigVar.BUG_CONCAT_FACTOR
        name = common_output_dir + f"AutoNTT_H__N_{POLY_SIZE}__q_{WORD_SIZE}__red_{reduction_name}__config_{V_BUG_SIZE}x{H_BUG_SIZE}BUGx{BUG_CONCAT_FACTOR}__BUs_{V_BUG_SIZE*H_BUG_SIZE*BUG_CONCAT_FACTOR}"
    return name

def write_file(file_path, code):
    try:
        with open(file_path, "w") as f:
            f.write(code)
    except Exception as e:
        print(f"Failed to write the code to file {file_path}: {e}")

def write_design_files(output_dir_name, kernel_code, host_code, header_file_code, connectivity_code, makefile_content):
    # create the directory if not available
    os.makedirs(output_dir_name, exist_ok=True)

    #write kernel file
    file_name = f"ntt_kernel.cpp"
    file_path = os.path.join(output_dir_name, file_name)
    write_file(file_path, kernel_code)

    #write host file
    file_name = f"ntt_test.cpp"
    file_path = os.path.join(output_dir_name, file_name)
    write_file(file_path, host_code)

    #write header file
    file_name = f"ntt.h"
    file_path = os.path.join(output_dir_name, file_name)
    write_file(file_path, header_file_code)

    #write link_config.ini file
    file_name = f"link_config.ini"
    file_path = os.path.join(output_dir_name, file_name)
    write_file(file_path, connectivity_code)

    #write Makefile
    file_name = f"Makefile"
    file_path = os.path.join(output_dir_name, file_name)
    write_file(file_path, makefile_content)

    logging.getLogger("write_design_files").info(f"Output has been successfully written to the directory: {output_dir_name} ")