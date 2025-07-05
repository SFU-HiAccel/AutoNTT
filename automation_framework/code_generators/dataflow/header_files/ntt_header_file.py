import math
from code_generators.modmul.config import WLM, CUSTOM_REDUCTION

from code_generators.modmul.wlm import gen_wlm_header_file_definitions
from code_generators.modmul.custom import gen_custom_red_header_file_definitions

def gen_ntt_header_file(designParamsVar):

    WORD_SIZE = designParamsVar.WORD_SIZE
    DRAM_WORD_SIZE = designParamsVar.DRAM_WORD_SIZE
    logN = designParamsVar.logN
    H_BU_NUM = designParamsVar.H_BU_NUM
    V_BU_NUM = designParamsVar.V_BU_NUM
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    mmap_count = designParamsVar.mmap_count
    tf_mmap_count = designParamsVar.tf_mmap_count
    multi_ports_tf_mmap_count = designParamsVar.multi_ports_tf_mmap_count
    arr_TFToTF_idx = designParamsVar.arr_TFToTF_idx
    PARA_LIMBS = designParamsVar.PARA_LIMBS
    DEFAULT_DRAM_PORT_WIDTH = designParamsVar.DEFAULT_DRAM_PORT_WIDTH
    TF_FIFO_DEPTH = designParamsVar.TF_FIFO_DEPTH

    line = f"""
#ifndef _H_GEMM_H_
#define _H_GEMM_H_
#define __gmp_const const

#include <cstdint>
#include "ap_int.h"  

#define VAR_TYPE_8 uint8_t
#define VAR_TYPE_16 uint16_t
#define VAR_TYPE_32 uint32_t
#define VAR_TYPE_64 uint64_t

const VAR_TYPE_32 WORD_SIZE={WORD_SIZE};

const VAR_TYPE_8 DRAM_WORD_SIZE=(WORD_SIZE>32)?64:32;

const uint32_t logN={logN};
const uint32_t N=(1U<<logN);
const uint32_t halfN=(N>>1);

//BUG config: horizontal and vertical
#define LAST_H_BU_NUM {LAST_H_BU_NUM}
#define H_BU_NUM {H_BU_NUM}
#define V_BU_NUM {V_BU_NUM}
#define CONCAT_FACTOR {CONCAT_FACTOR}
#define LOG_CONCAT_FACTOR {int(math.log2(CONCAT_FACTOR))}

#define WORD ap_uint<WORD_SIZE>
#define WORD_PLUS1 ap_uint<WORD_SIZE+1>
#define WORD_PLUS2 ap_uint<WORD_SIZE+2>
#define WORD_PLUS3 ap_uint<WORD_SIZE+3>
#define DWORD ap_uint<WORD_SIZE*2>
#define DWORD_PLUS1 ap_uint<WORD_SIZE*2+1>
#define DWORD_PLUS3 ap_uint<WORD_SIZE*2+3>
#define TWORD ap_uint<WORD_SIZE*3>
#define TWORD_PLUS1 ap_uint<WORD_SIZE*3+1>
#define DDWORD ap_uint<WORD_SIZE*4>

const WORD WORD_SIZE_MASK=(WORD)(((WORD_PLUS1)1<<WORD_SIZE)-1);
const WORD_PLUS2 WORD_SIZE_PLUS2_MASK=(WORD_PLUS2)((WORD_PLUS3(1)<<(WORD_SIZE+2)) - 1);

const VAR_TYPE_32 HBM_PORT_NUM={mmap_count};
const VAR_TYPE_32 HBM_PORT_SIZE={CONCAT_FACTOR // mmap_count};
const VAR_TYPE_32 TF_PORT_NUM={tf_mmap_count};
const VAR_TYPE_32 TF_PORT_SIZE={(CONCAT_FACTOR>>1) // tf_mmap_count};
const VAR_TYPE_32 DB_TF_PORT_NUM={multi_ports_tf_mmap_count};

"""
# LEN_{idx} determines how many ports are assigned to input the TF. 
# Each BUG, except for the last one, has its own set of ports. The last BUG has one port if there is only one layer, and two ports if there are multiple layers.
    for idx in range(len(arr_TFToTF_idx)):
        line += f"""const VAR_TYPE_32 LEN_{idx}={arr_TFToTF_idx[idx]};\n"""
    line += f"""#define HBM_PORT_WIDE_DATA ap_uint<{DRAM_WORD_SIZE * (CONCAT_FACTOR // mmap_count)}>
    
"""

    if(designParamsVar.REDUCTION_TYPE==WLM):
        line += gen_wlm_header_file_definitions(designParamsVar.WLM_WORD_SIZE)
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        line += gen_custom_red_header_file_definitions(designParamsVar)

# {TF_FIFO_DEPTH} is determined by the pipeline depth of the BU task.
    line += f"""
const VAR_TYPE_32 FIFO_DEPTH=2;
const VAR_TYPE_32 TF_FIFO_DEPTH={TF_FIFO_DEPTH};
const VAR_TYPE_32 LAST_CONCAT_FACTOR=(CONCAT_FACTOR>>(H_BU_NUM-LAST_H_BU_NUM));
const VAR_TYPE_32 BUF_SIZE=N/CONCAT_FACTOR;
#define HALF_CONCAT_FACTOR (CONCAT_FACTOR>>1)
#define TF_CONCAT_FACTOR (HALF_CONCAT_FACTOR * H_BU_NUM)

#define NUM_TFARR (V_BU_NUM >> 1)
#define LOG_HALF_CONCAT_FACTOR (LOG_CONCAT_FACTOR-1)

/* Extending to parallel limbs */

//Parallel limbs
const uint8_t PARA_LIMBS = {PARA_LIMBS};

//HBM related
const uint16_t DEFAULT_DRAM_PORT_WIDTH = {DEFAULT_DRAM_PORT_WIDTH};

// POLY DRAM related
const uint16_t POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = (DRAM_WORD_SIZE * HBM_PORT_SIZE);
const uint16_t POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);
#define POLY_WIDE_DATA_PER_PARA_LIMB ap_uint<DRAM_WORD_SIZE*POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>
const uint8_t POLY_LS_PORTS_PER_PARA_LIMB = HBM_PORT_NUM;
const uint16_t PARA_LIMB_PORTS_PER_POLY_PORT = (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB);
const uint16_t POLY_LS_PORTS = ((PARA_LIMBS + PARA_LIMB_PORTS_PER_POLY_PORT-1)/PARA_LIMB_PORTS_PER_POLY_PORT) * POLY_LS_PORTS_PER_PARA_LIMB; //ceil divsion
#define POLY_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>

// TF DRAM related
const uint16_t TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = (DRAM_WORD_SIZE * TF_PORT_SIZE);
const uint16_t TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (TF_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);
const uint16_t TF_WIDE_DATA_SIZE_PER_PARA_LIMB = DRAM_WORD_SIZE*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT;
#define TF_WIDE_DATA_PER_PARA_LIMB ap_uint<TF_WIDE_DATA_SIZE_PER_PARA_LIMB>
#define TF_WIDE_DATA_PER_PARA_LIMB_PLUS1 ap_uint<TF_WIDE_DATA_SIZE_PER_PARA_LIMB+1>
const uint8_t V_TF_PORTS_PER_PARA_LIMB = TF_PORT_NUM; //Vertical TF ports
const uint8_t H_TF_PORTS_PER_PARA_LIMB = DB_TF_PORT_NUM/TF_PORT_NUM; //Horizontal TF ports
const uint8_t TF_PORTS_PER_PARA_LIMB = V_TF_PORTS_PER_PARA_LIMB * H_TF_PORTS_PER_PARA_LIMB;
const uint16_t V_PARA_LIMB_PORTS_PER_TF_PORT = (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB);
const uint16_t V_TF_PORTS = ((PARA_LIMBS+V_PARA_LIMB_PORTS_PER_TF_PORT-1)/V_PARA_LIMB_PORTS_PER_TF_PORT)*V_TF_PORTS_PER_PARA_LIMB; //ceil divsion
const uint16_t TF_PORTS = V_TF_PORTS * H_TF_PORTS_PER_PARA_LIMB;
#define TF_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>
#define TF_WIDE_DATA_PLUS1 ap_uint<DEFAULT_DRAM_PORT_WIDTH+1>

#endif
"""

    return line