from code_generators.modmul.config import WLM, CUSTOM_REDUCTION

from code_generators.modmul.wlm import gen_wlm_header_file_definitions
from code_generators.modmul.custom import gen_custom_red_header_file_definitions

def gen_ntt_header_file(designParamsVar):

    logN = designParamsVar.logN
    WORD_SIZE = designParamsVar.WORD_SIZE
    V_BUG_SIZE = designParamsVar.V_BUG_SIZE
    H_BUG_SIZE = designParamsVar.H_BUG_SIZE
    logV_BUG_SIZE = designParamsVar.logV_BUG_SIZE
    BUG_CONCAT_FACTOR = designParamsVar.BUG_CONCAT_FACTOR
    logBUG_CONCAT_FACTOR = designParamsVar.logBUG_CONCAT_FACTOR
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = designParamsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = designParamsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    TF_PORTS_PER_PARA_LIMB = designParamsVar.TF_PORTS_PER_PARA_LIMB
    LS_FIFO_BUF_SIZE = designParamsVar.LS_FIFO_BUF_SIZE
    PARA_LIMBS = designParamsVar.PARA_LIMBS
    DEFAULT_DRAM_PORT_WIDTH =  designParamsVar.DEFAULT_DRAM_PORT_WIDTH


    line = ""
    line += "#ifndef _H_GEMM_H_" + "\n"
    line += "#define _H_GEMM_H_" + "\n"
    line += "#define __gmp_const const" + "\n"
    line += "#include <cstdint>" + "\n"
    line += "#include \"ap_int.h\"  " + "\n"
    line += "" + "\n"

    line += "// inbuilt data types" + "\n"
    line += "#define VAR_TYPE_32 uint32_t" + "\n"
    line += "#define VAR_TYPE_64 uint64_t" + "\n"
    line += "#define VAR_TYPE_8 uint8_t" + "\n"
    line += "#define VAR_TYPE_16 uint16_t" + "\n"
    line += "" + "\n"

    line += "// Polynomial size related" + "\n"
    line += "const uint8_t logN=" + str(logN) + ";" + "\n"
    line += "const uint32_t N=(1U<<logN);" + "\n"
    line += "" + "\n"

    line += "// data sizes" + "\n"
    line += "const VAR_TYPE_8 WORD_SIZE=" + str(WORD_SIZE) + ";" + "\n"
    line += "const VAR_TYPE_8 DWORD_SIZE=(2*WORD_SIZE);" + "\n"
    line += "const VAR_TYPE_8 DRAM_WORD_SIZE=(WORD_SIZE>32)?64:32;" + "\n"
    line += "" + "\n"

    line += "// custom data types" + "\n"
    line += "#define WORD ap_uint<WORD_SIZE>" + "\n"
    line += "#define DRAM_WORD ap_uint<DRAM_WORD_SIZE>" + "\n"
    line += "#define WORD_PLUS1 ap_uint<WORD_SIZE+1>" + "\n"
    line += "#define WORD_PLUS2 ap_uint<WORD_SIZE+2>" + "\n"
    line += "#define WORD_PLUS3 ap_uint<WORD_SIZE+3>" + "\n"
    line += "#define DWORD ap_uint<WORD_SIZE*2>" + "\n"
    line += "#define DWORD_PLUS1 ap_uint<WORD_SIZE*2+1>" + "\n"
    line += "#define DWORD_PLUS3 ap_uint<WORD_SIZE*2+3>" + "\n"
    line += "#define TWORD ap_uint<WORD_SIZE*3>  // TWORD" + "\n"
    line += "#define TWORD_PLUS1 ap_uint<WORD_SIZE*3+1>  // TWORD_PLUS1" + "\n"
    line += "#define DDWORD ap_uint<WORD_SIZE*4>" + "\n"

    if(designParamsVar.REDUCTION_TYPE==WLM):
        line += gen_wlm_header_file_definitions(designParamsVar.WLM_WORD_SIZE)
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        line += gen_custom_red_header_file_definitions(designParamsVar)

    line += "" + "\n"
    line += "// predefined vals" + "\n"
    line += "const WORD WORD_SIZE_MASK=(WORD)(((WORD_PLUS1)1<<WORD_SIZE)-1);" + "\n"
    line += "const WORD_PLUS2 WORD_SIZE_PLUS2_MASK=(WORD_PLUS2)((WORD_PLUS3(1)<<(WORD_SIZE+2)) - 1);" + "\n"
    line += "" + "\n"

    line += "// FIFO related" + "\n"
    line += "#define BU_BUF_FIFO_DEPTH 3" + "\n"
    line += "" + "\n"

    line += "// BUG and architecture config" + "\n"
    line += "const uint16_t V_BUG_SIZE = " + str(V_BUG_SIZE) + ";" + "\n"
    line += "const uint16_t H_BUG_SIZE = " + str(H_BUG_SIZE) + ";" + "\n"
    line += "const uint16_t logV_BUG_SIZE = " + str(logV_BUG_SIZE) + ";" + "\n"
    line += "const uint16_t BUG_CONCAT_FACTOR = " + str(BUG_CONCAT_FACTOR) + ";" + "\n"
    line += "const uint16_t logBUG_CONCAT_FACTOR = " + str(logBUG_CONCAT_FACTOR) + ";" + "\n"
    line += "const uint16_t V_TOTAL_DATA = V_BUG_SIZE*BUG_CONCAT_FACTOR*2;" + "\n"
    line += "const uint16_t log_V_TOTAL_DATA = (logV_BUG_SIZE+logBUG_CONCAT_FACTOR+1);" + "\n"
    line += "" + "\n"

    line += "const uint16_t SINGLE_LIMB_BUF_SIZE = (N/V_TOTAL_DATA);" + "\n"
    line += "const uint16_t SINGLE_LIMB_BUF_SIZE_MASK = ( (1<<(logN-log_V_TOTAL_DATA)) - 1 );" + "\n"
    line += "const uint16_t TWO_SINGLE_LIMB_BUF_SIZE_MASK = ( (1<<(logN-log_V_TOTAL_DATA+1)) - 1 );" + "\n"
    line += "" + "\n"

    line += "//Parallel limbs" + "\n"
    line += "const uint8_t PARA_LIMBS = " + str(PARA_LIMBS) + ";" + "\n"
    line += "" + "\n"
    line += "//HBM related" + "\n"
    line += "const uint16_t DEFAULT_DRAM_PORT_WIDTH = " + str(DEFAULT_DRAM_PORT_WIDTH) + ";" + "\n"
    line += "" + "\n"


    line += "// POLY DRAM related" + "\n"
    line += "const uint16_t POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = " + str(POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint16_t POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);" + "\n"
    line += "#define POLY_WIDE_DATA_PER_PARA_LIMB ap_uint<DRAM_WORD_SIZE*POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>" + "\n"
    line += "const uint8_t POLY_LS_PORTS_PER_PARA_LIMB=" + str(POLY_LS_PORTS_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint8_t BUG_PER_PARA_LIMB_POLY_PORT = (2*V_BUG_SIZE>POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT) ? (V_TOTAL_DATA/(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT*POLY_LS_PORTS_PER_PARA_LIMB)) : (BUG_CONCAT_FACTOR/POLY_LS_PORTS_PER_PARA_LIMB);" + "\n"
    line += "const uint8_t BUG_PER_PARA_LIMB_POLY_WIDE_DATA = (2*V_BUG_SIZE>POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT) ? (1) : (POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/(2*V_BUG_SIZE));" + "\n"
    line += "const uint8_t SEQ_BUG_PER_PARA_LIMB_POLY_PORT = (BUG_PER_PARA_LIMB_POLY_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA);" + "\n"
    line += "" + "\n"
    line += "const uint16_t PARA_LIMB_PORTS_PER_POLY_PORT = (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB);" + "\n"
    line += "const uint16_t POLY_LS_PORTS = ((PARA_LIMBS + PARA_LIMB_PORTS_PER_POLY_PORT-1)/PARA_LIMB_PORTS_PER_POLY_PORT) * POLY_LS_PORTS_PER_PARA_LIMB; //ceil divsion" + "\n"
    line += "#define POLY_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>" + "\n"
    line += "" + "\n"

    line += "// TF DRAM related" + "\n"
    line += "const uint16_t TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = " + str(TF_DRAM_PORT_WIDTH_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint16_t TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (TF_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);" + "\n"
    line += "#define TF_WIDE_DATA_PER_PARA_LIMB ap_uint<DRAM_WORD_SIZE*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT>" + "\n"
    line += "" + "\n"
    line += "const uint8_t TF_PORTS_PER_PARA_LIMB=" + str(TF_PORTS_PER_PARA_LIMB) + ";" + "\n"
    line += "const uint8_t TF_LOAD_V_SEGS_PER_PARA_LIMB=( ( (V_BUG_SIZE/2) * BUG_CONCAT_FACTOR * 2 ) / TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT );   //i.e., vertically how many TFBuffers the design has and each can take 2 values at a time" + "\n"
    line += "const uint8_t TF_LOAD_H_SEGS_PER_PARA_LIMB=TF_PORTS_PER_PARA_LIMB/TF_LOAD_V_SEGS_PER_PARA_LIMB;   //i.e., How many segments total H_BUG_SIZE layers are bokern into" + "\n"
    line += "" + "\n"
    line += "const uint16_t PARA_LIMB_PORTS_PER_TF_PORT = (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB);" + "\n"
    line += "const uint16_t TF_PORTS = ((PARA_LIMBS+PARA_LIMB_PORTS_PER_TF_PORT-1)/PARA_LIMB_PORTS_PER_TF_PORT) * TF_PORTS_PER_PARA_LIMB; //ceil divsion" + "\n"
    line += "#define TF_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>" + "\n"
    line += "" + "\n"

    line += "// in/out FIFO size. Ideally this is equal to N/V_TOTAL_DATA. In order to force the FIFO into SRAM, larger sizes are used." + "\n"
    line += "const uint16_t LS_FIFO_BUF_SIZE=" + str(LS_FIFO_BUF_SIZE) + ";" + "\n"
    line += "" + "\n"

    line += "#endif" + "\n"
    line += "" + "\n"

    return line