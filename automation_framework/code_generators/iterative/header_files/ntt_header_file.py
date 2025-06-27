from code_generators.common.helper_functions import num_arr_to_cppArrStr

from code_generators.modmul.config import WLM, CUSTOM_REDUCTION
from code_generators.modmul.wlm import gen_wlm_header_file_definitions
from code_generators.modmul.custom import gen_custom_red_header_file_definitions

# this function generates the mask array for the given polynomial size
def genMaskArrays(logN):
    fwd_mask_arr = []
    for i in range(logN):
        mask = (1<<i)-1
        fwd_mask_arr.append(mask)
    
    inv_mask_arr = []
    mask = 0
    for i in range(logN):
        mask += (1<<(logN-i-1))
        inv_mask_arr.append(mask)
    
    return fwd_mask_arr, inv_mask_arr

def gen_ntt_header_file(designParamsVar):

    logN = designParamsVar.logN
    
    logBU = designParamsVar.logBU

    WORD_SIZE = designParamsVar.WORD_SIZE
    
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = designParamsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = designParamsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    TF_PORTS_PER_PARA_LIMB = designParamsVar.TF_PORTS_PER_PARA_LIMB

    FWD_sizeArr = designParamsVar.FWD_sizeArr
    INV_sizeArr = designParamsVar.INV_sizeArr

    line = ""

    line += "#ifndef _H_GEMM_H_" + "\n"
    line += "#define _H_GEMM_H_" + "\n"
    line += "#define __gmp_const const" + "\n"
    line += "#include <cstdint>" + "\n"
    line += "#include \"ap_int.h\"  " + "\n"
    line += "" + "\n"
    line += "#define VAR_TYPE_32 uint32_t" + "\n"
    line += "#define VAR_TYPE_64 uint64_t" + "\n"
    line += "#define VAR_TYPE_8 uint8_t" + "\n"
    line += "#define VAR_TYPE_16 uint16_t" + "\n"
    line += "" + "\n"

    line += "//Polynomial size related" + "\n"
    line += "const uint8_t logN=" + str(logN) + ";" + "\n"
    line += "const uint32_t N=(1U<<logN);" + "\n"
    line += "" + "\n"

    line += "//Number of BU related" + "\n"
    line += "const uint8_t logBU=" + str(logBU) + ";" + "\n"
    line += "const uint16_t NUM_BU=(1<<logBU);" + "\n"
    line += "const uint16_t HALF_BU=(logBU==0)?1:(NUM_BU>>1);" + "\n"
    line += "const uint8_t loglogBU=4; //this is basically log(logBU) value. This is required to reduce resources during TF groups accessing. Currently setting it to max value = 4" + "\n"
    line += "" + "\n"

    line += "//data sizes" + "\n"
    line += "const VAR_TYPE_8 WORD_SIZE=" + str(WORD_SIZE) + ";" + "\n"
    line += "const VAR_TYPE_8 DWORD_SIZE=(2*WORD_SIZE);" + "\n"
    line += "const VAR_TYPE_8 DRAM_WORD_SIZE=(WORD_SIZE>32)?64:32;" + "\n"
    line += "" + "\n"

    line += "//data types" + "\n"
    line += "#define WORD ap_uint<WORD_SIZE>" + "\n"
    line += "#define DRAM_WORD ap_uint<DRAM_WORD_SIZE>" + "\n"
    line += "#define WORD_PLUS1 ap_uint<WORD_SIZE+1>" + "\n"
    line += "#define WORD_PLUS2 ap_uint<WORD_SIZE+2>" + "\n"
    line += "#define WORD_PLUS3 ap_uint<WORD_SIZE+3>" + "\n"
    line += "#define DWORD ap_uint<WORD_SIZE*2>" + "\n"
    line += "#define DWORD_PLUS1 ap_uint<WORD_SIZE*2+1>" + "\n"
    line += "#define DWORD_PLUS3 ap_uint<WORD_SIZE*2+3>" + "\n"
    line += "#define TWORD ap_uint<WORD_SIZE*3>" + "\n"
    line += "#define TWORD_PLUS1 ap_uint<WORD_SIZE*3+1>" + "\n"
    line += "#define DDWORD ap_uint<WORD_SIZE*4>" + "\n"
    line += "" + "\n"

    line += "//Following data types are used to reduce resources with specific POLY_SIZE and NUM_BU" + "\n"
    line += "const VAR_TYPE_8 BETA_WORD_SIZE=(logN - logBU);" + "\n"
    line += "const VAR_TYPE_8 TF_GROUP_WORD_SIZE=(loglogBU + BETA_WORD_SIZE); //number of maximum groups x beta" + "\n"
    line += "#define BETA_WORD ap_uint<BETA_WORD_SIZE>   //this size is used to reduce resources related to data counters. " + "\n"
    line += "#define TF_GROUP_WORD ap_uint<TF_GROUP_WORD_SIZE>" + "\n"
    line += "" + "\n"

    if(designParamsVar.REDUCTION_TYPE==WLM):
        line += gen_wlm_header_file_definitions(designParamsVar.WLM_WORD_SIZE)
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        line += gen_custom_red_header_file_definitions(designParamsVar)
    
    line += "" + "\n"
    line += "const WORD WORD_SIZE_MASK=(WORD)(((WORD_PLUS1)1<<WORD_SIZE)-1);" + "\n"
    line += "const WORD_PLUS2 WORD_SIZE_PLUS2_MASK=(WORD_PLUS2)((WORD_PLUS3(1)<<(WORD_SIZE+2)) - 1);" + "\n"
    line += "" + "\n"

    line += "//FIFO related" + "\n"
    line += "#ifndef BU_BUF_FIFO_DEPTH" + "\n"
    line += "/*" + "\n"
    line += "For csim it is required a higher FIFO size to avoid hang. " + "\n"
    line += "This is due to, TAPA makes each task run in a random schedule and circular dependency in polyBuf and BU cause some tasks to hang." + "\n"
    line += "Hardware does not need this higher FIFO depth." + "\n"
    line += "*/" + "\n"
    line += "#define BU_BUF_FIFO_DEPTH 3" + "\n"
    line += "#endif" + "\n"
    line += "" + "\n"

    line += "//Parallel limbs" + "\n"
    line += "const uint8_t PARA_LIMBS = " + str(designParamsVar.PARA_LIMBS) + ";" + "\n"
    line += "" + "\n"

    line += "//Double buffer related" + "\n"
    if(designParamsVar.DOUBLE_BUF_EN):
        line += "const bool DOUBLE_BUF_EN = true;" + "\n"
    else:
        line += "const bool DOUBLE_BUF_EN = false;" + "\n"
    line += "" + "\n"

    line += "//HBM related" + "\n"
    line += "const uint16_t DEFAULT_DRAM_PORT_WIDTH = " + str(designParamsVar.DEFAULT_DRAM_PORT_WIDTH) + ";" + "\n"
    line += "" + "\n"

    line += "//Poly" + "\n"
    line += "const uint16_t POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = " + str(designParamsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint16_t POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);" + "\n"
    line += "#define POLY_WIDE_DATA_PER_PARA_LIMB ap_uint<POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB>" + "\n"
    line += "" + "\n"
    line += "const uint16_t POLY_LS_PORTS_PER_PARA_LIMB=" + str(designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint16_t NUM_BUF_PER_PARA_LIMB_POLY_PORT=(NUM_BU/POLY_LS_PORTS_PER_PARA_LIMB);" + "\n"
    line += "const uint16_t NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT=(NUM_BUF_PER_PARA_LIMB_POLY_PORT/POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT);" + "\n"
    line += "" + "\n"
    line += "const uint16_t PARA_LIMB_PORTS_PER_POLY_PORT = (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB);" + "\n"
    line += "const uint16_t POLY_LS_PORTS = ((PARA_LIMBS + PARA_LIMB_PORTS_PER_POLY_PORT-1)/PARA_LIMB_PORTS_PER_POLY_PORT)*POLY_LS_PORTS_PER_PARA_LIMB; //ceil divsion" + "\n"
    line += "#define POLY_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>" + "\n"
    line += "" + "\n"

    line += "//TFs" + "\n"
    line += "const uint16_t TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = " + str(designParamsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint16_t TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (TF_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);" + "\n"
    line += "#define TF_WIDE_DATA_PER_PARA_LIMB ap_uint<TF_DRAM_PORT_WIDTH_PER_PARA_LIMB>" + "\n"
    line += "" + "\n"
    line += "const uint16_t TF_PORTS_PER_PARA_LIMB=" + str(designParamsVar.TF_PORTS_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint16_t NUM_BUF_PER_PARA_LIMB_TF_PORT=(NUM_BU/(2*TF_PORTS_PER_PARA_LIMB));" + "\n"
    line += "const uint16_t NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT=(NUM_BUF_PER_PARA_LIMB_TF_PORT/TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT);" + "\n"
    line += "" + "\n"
    line += "const uint16_t PER_LIMB_PORTS_PER_TF_PORT = (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB);" + "\n"
    line += "const uint16_t TF_PORTS = ((PARA_LIMBS+PER_LIMB_PORTS_PER_TF_PORT-1)/PER_LIMB_PORTS_PER_TF_PORT)*TF_PORTS_PER_PARA_LIMB; //ceil divsion" + "\n"
    line += "#define TF_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>" + "\n"
    line += "" + "\n"

    line += "//TF Groups" + "\n"
    line += "const VAR_TYPE_16 FWD_NUM_TF_GRPS_PER_BUF[NUM_BU/2] = " + num_arr_to_cppArrStr(FWD_sizeArr) + ";" + "\n"
    line += "const VAR_TYPE_16 INV_NUM_TF_GRPS_PER_BUF[NUM_BU/2] = " + num_arr_to_cppArrStr(INV_sizeArr) + ";" + "\n"
    line += "" + "\n"

    line += "//Masks for TF calculations" + "\n"
    fwd_mask_arr, inv_mask_arr = genMaskArrays(logN)

    line += "const VAR_TYPE_32 fwd_mask_arr[logN] = " + num_arr_to_cppArrStr(fwd_mask_arr) + ";" + "\n"
    line += "const VAR_TYPE_32 inv_mask_arr[logN] = " + num_arr_to_cppArrStr(inv_mask_arr) +";" + "\n"
    line += "" + "\n"
    line += "#endif" + "\n"

    return line