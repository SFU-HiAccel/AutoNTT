#ifndef _H_GEMM_H_
#define _H_GEMM_H_
#define __gmp_const const
#include <cstdint>
#include "ap_int.h"  

#define VAR_TYPE_32 uint32_t
#define VAR_TYPE_64 uint64_t
#define VAR_TYPE_8 uint8_t
#define VAR_TYPE_16 uint16_t

//Polynomial size related
const uint8_t logN=13;
const uint32_t N=(1U<<logN);

//Number of BU related
const uint8_t logBU=2;
const uint16_t NUM_BU=(1<<logBU);
const uint16_t HALF_BU=(logBU==0)?1:(NUM_BU>>1);
const uint8_t loglogBU=4; //this is basically log(logBU) value. This is required to reduce resources during TF groups accessing. Currently setting it to max value = 4

//data sizes
const VAR_TYPE_8 WORD_SIZE=48;
const VAR_TYPE_8 DWORD_SIZE=(2*WORD_SIZE);
const VAR_TYPE_8 DRAM_WORD_SIZE=(WORD_SIZE>32)?64:32;

//data types
#define WORD ap_uint<WORD_SIZE>
#define DRAM_WORD ap_uint<DRAM_WORD_SIZE>
#define WORD_PLUS1 ap_uint<WORD_SIZE+1>
#define WORD_PLUS2 ap_uint<WORD_SIZE+2>
#define WORD_PLUS3 ap_uint<WORD_SIZE+3>
#define DWORD ap_uint<WORD_SIZE*2>
#define DWORD_PLUS1 ap_uint<WORD_SIZE*2+1>
#define DWORD_PLUS3 ap_uint<WORD_SIZE*2+3>
#define TWORD ap_uint<WORD_SIZE*3>
#define TWORD_PLUS1 ap_uint<WORD_SIZE*3+1>
#define DDWORD ap_uint<WORD_SIZE*4>

//Following data types are used to reduce resources with specific POLY_SIZE and NUM_BU
const VAR_TYPE_8 BETA_WORD_SIZE=(logN - logBU);
const VAR_TYPE_8 TF_GROUP_WORD_SIZE=(loglogBU + BETA_WORD_SIZE); //number of maximum groups x beta
#define BETA_WORD ap_uint<BETA_WORD_SIZE>   //this size is used to reduce resources related to data counters. 
#define TF_GROUP_WORD ap_uint<TF_GROUP_WORD_SIZE>


const WORD WORD_SIZE_MASK=(WORD)(((WORD_PLUS1)1<<WORD_SIZE)-1);
const WORD_PLUS2 WORD_SIZE_PLUS2_MASK=(WORD_PLUS2)((WORD_PLUS3(1)<<(WORD_SIZE+2)) - 1);

//FIFO related
#ifndef BU_BUF_FIFO_DEPTH
/*
For csim it is required a higher FIFO size to avoid hang. 
This is due to, TAPA makes each task run in a random schedule and circular dependency in polyBuf and BU cause some tasks to hang.
Hardware does not need this higher FIFO depth.
*/
#define BU_BUF_FIFO_DEPTH 3
#endif

//Parallel limbs
const uint8_t PARA_LIMBS = 1;

//Double buffer related
const bool DOUBLE_BUF_EN = true;

//HBM related
const uint16_t DEFAULT_DRAM_PORT_WIDTH = 512;

//Poly
const uint16_t POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = 64;
const uint16_t POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);
#define POLY_WIDE_DATA_PER_PARA_LIMB ap_uint<POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB>

const uint16_t POLY_LS_PORTS_PER_PARA_LIMB=1;
const uint16_t NUM_BUF_PER_PARA_LIMB_POLY_PORT=(NUM_BU/POLY_LS_PORTS_PER_PARA_LIMB);
const uint16_t NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT=(NUM_BUF_PER_PARA_LIMB_POLY_PORT/POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT);

const uint16_t PARA_LIMB_PORTS_PER_POLY_PORT = (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB);
const uint16_t POLY_LS_PORTS = ((PARA_LIMBS + PARA_LIMB_PORTS_PER_POLY_PORT-1)/PARA_LIMB_PORTS_PER_POLY_PORT)*POLY_LS_PORTS_PER_PARA_LIMB; //ceil divsion
#define POLY_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>

//TFs
const uint16_t TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = 64;
const uint16_t TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = (TF_DRAM_PORT_WIDTH_PER_PARA_LIMB/DRAM_WORD_SIZE);
#define TF_WIDE_DATA_PER_PARA_LIMB ap_uint<TF_DRAM_PORT_WIDTH_PER_PARA_LIMB>

const uint16_t TF_PORTS_PER_PARA_LIMB=1;
const uint16_t NUM_BUF_PER_PARA_LIMB_TF_PORT=(NUM_BU/(2*TF_PORTS_PER_PARA_LIMB));
const uint16_t NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT=(NUM_BUF_PER_PARA_LIMB_TF_PORT/TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT);

const uint16_t PER_LIMB_PORTS_PER_TF_PORT = (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB > PARA_LIMBS) ? (PARA_LIMBS) : (DEFAULT_DRAM_PORT_WIDTH/TF_DRAM_PORT_WIDTH_PER_PARA_LIMB);
const uint16_t TF_PORTS = ((PARA_LIMBS+PER_LIMB_PORTS_PER_TF_PORT-1)/PER_LIMB_PORTS_PER_TF_PORT)*TF_PORTS_PER_PARA_LIMB; //ceil divsion
#define TF_WIDE_DATA ap_uint<DEFAULT_DRAM_PORT_WIDTH>

//TF Groups
const VAR_TYPE_16 FWD_NUM_TF_GRPS_PER_BUF[NUM_BU/2] = {2, 3};
const VAR_TYPE_16 INV_NUM_TF_GRPS_PER_BUF[NUM_BU/2] = {2, 4};

//Masks for TF calculations
const VAR_TYPE_32 fwd_mask_arr[logN] = {0, 1, 3, 7, 15, 31, 63, 127, 255, 511, 1023, 2047, 4095};
const VAR_TYPE_32 inv_mask_arr[logN] = {4096, 6144, 7168, 7680, 7936, 8064, 8128, 8160, 8176, 8184, 8188, 8190, 8191};

#endif
