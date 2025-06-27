#include <cstdint>

#include <tapa.h>
#include "ntt.h"

// /********************************************************************************************
// * Polynomial load store tasks *
// ********************************************************************************************/

void Mmap2Stream_poly_1_limbs(
                 tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& poly_stream_L0,
                 VAR_TYPE_16 port_idx,
                 VAR_TYPE_16 iter) {

  LOAD_ITER: for(VAR_TYPE_16 iterCount=0; iterCount<(iter+2); iterCount++){
    LOAD_POLY_0:for (int i_req = 0, i_resp=0; i_resp < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT;) {
      #pragma HLS PIPELINE II=1

      if( (i_req < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT) && (poly_mmap.read_addr.try_write(i_req)) ){
        i_req++;
      }

      if( !poly_mmap.read_data.empty() ){
        POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);

        for(int j=0; j<POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){
          #pragma HLS UNROLL
          WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA)1)<<WORD_SIZE)-1));
          poly_stream_L0[j].write(smallVal);
          val >>= DRAM_WORD_SIZE;
        }

        i_resp++;
      }

    }
  }
  #ifndef __SYNTHESIS__
  printf("[Mmap2Stream_poly %d]: Polynomial loading done\n", (int)port_idx);
  #endif
}

void Stream2Mmap_poly_1_limbs(
                    tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap,
                    tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& poly_stream_L0,
                    VAR_TYPE_16 port_idx,
                    VAR_TYPE_16 iter) {

  bool sendDataSuccess = true;
  POLY_WIDE_DATA val;

  STORE_ITER:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+2); iterCount++){
    STORE_POLY_0:for (int i_req = 0, i_resp = 0; i_resp < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT;) {
      #pragma HLS PIPELINE II=1

      bool inp_not_empty = (!poly_stream_L0[0].empty());
      for(int j=1; j<POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){
        #pragma HLS UNROLL
        inp_not_empty &= !poly_stream_L0[j].empty();
      }

      if( sendDataSuccess && inp_not_empty ){
        val = 0;
        
        for(int j=POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1; j>=0; j--){
          #pragma HLS UNROLL
          val <<= DRAM_WORD_SIZE;
          WORD smallData = poly_stream_L0[j].read();
          val |= (POLY_WIDE_DATA)(smallData);
        }
        
        sendDataSuccess = false;
      }

      if( ( i_req < ((N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)) && (poly_mmap.write_addr.try_write(i_req)) ){
        i_req++;
      }

      if( (!sendDataSuccess) && (poly_mmap.write_data.try_write(val)) ){
        sendDataSuccess = true;
      }

      if( !poly_mmap.write_resp.empty() ){
        i_resp += unsigned(poly_mmap.write_resp.read(nullptr)) + 1;
      }

    }
  }
  #ifndef __SYNTHESIS__
  printf("[Stream2Mmap_poly %d]: Polynomial storing done\n", (int)port_idx);
  #endif
}


// /********************************************************************************************
// * TF load tasks *
// ********************************************************************************************/

void Mmap2Stream_tf_1_limbs(
                 tapa::async_mmap<TF_WIDE_DATA>& tf_mmap,
                 tapa::ostreams<WORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& tf_stream_L0,
                 bool direction, VAR_TYPE_16 iter, VAR_TYPE_16 port_idx) {
                  
  VAR_TYPE_16 beta = (N)/(2*NUM_BU);

  VAR_TYPE_16 loopCounter = 0;

  COMP_LIMIT:for(VAR_TYPE_16 s=0; s<NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT; s++){
    VAR_TYPE_16 new_bufIdx = port_idx*NUM_BUF_PER_PARA_LIMB_TF_PORT + s*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1;
    if(direction){
      loopCounter += FWD_NUM_TF_GRPS_PER_BUF[new_bufIdx]*beta;
    }
    else{
      loopCounter += (VAR_TYPE_16)(INV_NUM_TF_GRPS_PER_BUF[new_bufIdx] - (VAR_TYPE_16)2 + 2*beta);
    }
  }

  LOAD_ITER: for(VAR_TYPE_16 iterCount=0; iterCount<(iter+2); iterCount++){
    LOAD_TF:for (int i_req = 0, i_resp=0; i_resp < loopCounter;) {
      #pragma HLS PIPELINE II=1
      
      if( (i_req < loopCounter) && (tf_mmap.read_addr.try_write(i_req)) ){
        i_req++;
      }

      if( !tf_mmap.read_data.empty() ){
        TF_WIDE_DATA comb_tfVal = tf_mmap.read_data.read();
        
        for(int j=0; j<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){
          #pragma HLS UNROLL
          tf_stream_L0[j].write(comb_tfVal & ((((TF_WIDE_DATA)1)<<WORD_SIZE)-1));
          comb_tfVal >>= DRAM_WORD_SIZE;
        }
        
        i_resp++;
      }

    }
  }
  #ifndef __SYNTHESIS__
  printf("[Mmap2Stream_tf %d]: TF loading done\n", (int)port_idx);
  #endif
}

// /********************************************************************************************
// * Function to multiply with two inverse *
// ********************************************************************************************/

void multiplyTwoInverse(WORD *val, WORD *twoInverse){
  #pragma HLS inline
  *val = (*val>>1) + (*val & 1)*(*twoInverse);
}

// /********************************************************************************************
// * Modulo multiplication functions *
// ********************************************************************************************/

ap_uint<96> hardcoded_fullMul_0(ap_uint<48> u, ap_uint<48> v){
  #pragma HLS inline

  ap_uint<17> u_0 = u & ((1<<17)-1);
  u = u >> 17;
  ap_uint<17> u_1 = u & ((1<<17)-1);
  u = u >> 17;
  ap_uint<14> u_2 = u & ((1<<14)-1);

  ap_uint<27> v_0 = v & ((1<<27)-1);
  v = v >> 27;
  ap_uint<21> v_1 = v & ((1<<21)-1);
  
  ap_uint<44> mul_0 = ((ap_uint<44>)(u_0) * v_0); //<<0
  #pragma HLS bind_op variable=mul_0 op=mul impl=dsp
  ap_uint<44> mul_1 = ((ap_uint<44>)(u_1) * v_0); //<<17
  #pragma HLS bind_op variable=mul_1 op=mul impl=dsp
  ap_uint<41> mul_2 = ((ap_uint<41>)(u_2) * v_0); //<<34
  #pragma HLS bind_op variable=mul_2 op=mul impl=dsp

  ap_uint<38> mul_3 = ((ap_uint<38>)(u_0) * v_1); //<<27
  #pragma HLS bind_op variable=mul_3 op=mul impl=dsp
  ap_uint<38> mul_4 = ((ap_uint<38>)(u_1) * v_1); //<<44
  #pragma HLS bind_op variable=mul_4 op=mul impl=dsp
  ap_uint<35> mul_5 = ((ap_uint<35>)(u_2) * v_1); //<<61
  #pragma HLS bind_op variable=mul_5 op=mul impl=dsp

  
  ap_uint<96> res = ( (((ap_uint<96>)mul_0)<<0) + (((ap_uint<96>)mul_1)<<17) + (((ap_uint<96>)mul_2)<<34) + (((ap_uint<96>)mul_3)<<27) + (((ap_uint<96>)mul_4)<<44) + (((ap_uint<96>)mul_5)<<61) );
  return res;
}

ap_uint<49> hardcoded_fullMul_1(ap_uint<51> u, ap_uint<48> v){
  #pragma HLS inline

  ap_uint<17> u_0 = u & ((1<<17)-1);
  u = u >> 17;
  ap_uint<17> u_1 = u & ((1<<17)-1);
  u = u >> 17;
  ap_uint<17> u_2 = u & ((1<<17)-1);

  ap_uint<27> v_0 = v & ((1<<27)-1);
  v = v >> 27;
  ap_uint<21> v_1 = v & ((1<<21)-1);
  
  ap_uint<44> mul_0 = ((ap_uint<44>)(u_0) * v_0); //<<0
  #pragma HLS bind_op variable=mul_0 op=mul impl=dsp
  ap_uint<44> mul_1 = ((ap_uint<44>)(u_1) * v_0); //<<17
  #pragma HLS bind_op variable=mul_1 op=mul impl=dsp
  ap_uint<44> mul_2 = ((ap_uint<44>)(u_2) * v_0); //<<34
  #pragma HLS bind_op variable=mul_2 op=mul impl=dsp

  ap_uint<38> mul_3 = ((ap_uint<38>)(u_0) * v_1); //<<27
  #pragma HLS bind_op variable=mul_3 op=mul impl=dsp
  ap_uint<38> mul_4 = ((ap_uint<38>)(u_1) * v_1); //<<44
  #pragma HLS bind_op variable=mul_4 op=mul impl=dsp
  ap_uint<38> mul_5 = ((ap_uint<38>)(u_2) * v_1); //<<61
  #pragma HLS bind_op variable=mul_5 op=mul impl=dsp

  
  ap_uint<49> res = ( (((ap_uint<99>)mul_0)<<0) + (((ap_uint<99>)mul_1)<<17) + (((ap_uint<99>)mul_2)<<34) + (((ap_uint<99>)mul_3)<<27) + (((ap_uint<99>)mul_4)<<44) + (((ap_uint<99>)mul_5)<<61) ) >> (WORD_SIZE+2);
  return res;
}

ap_uint<50> hardcoded_lowerHalfMul_2(ap_uint<49> u, ap_uint<48> v){
  #pragma HLS inline

  ap_uint<17> u_0 = u & ((1<<17)-1);
  u = u >> 17;
  ap_uint<17> u_1 = u & ((1<<17)-1);
  u = u >> 17;
  ap_uint<15> u_2 = u & ((1<<15)-1);

  ap_uint<27> v_0 = v & ((1<<27)-1);
  v = v >> 27;
  ap_uint<21> v_1 = v & ((1<<21)-1);
  
  ap_uint<44> mul_0 = ((ap_uint<44>)(u_0) * v_0); //<<0
  #pragma HLS bind_op variable=mul_0 op=mul impl=dsp
  ap_uint<44> mul_1 = ((ap_uint<44>)(u_1) * v_0); //<<17
  #pragma HLS bind_op variable=mul_1 op=mul impl=dsp
  ap_uint<42> mul_2 = ((ap_uint<42>)(u_2) * v_0); //<<34
  #pragma HLS bind_op variable=mul_2 op=mul impl=dsp

  ap_uint<38> mul_3 = ((ap_uint<38>)(u_0) * v_1); //<<27
  #pragma HLS bind_op variable=mul_3 op=mul impl=dsp
  ap_uint<38> mul_4 = ((ap_uint<38>)(u_1) * v_1); //<<44
  #pragma HLS bind_op variable=mul_4 op=mul impl=dsp

  
  ap_uint<50> res = ( (((ap_uint<50>)mul_0)<<0) + (((ap_uint<50>)mul_1)<<17) + (((ap_uint<50>)mul_2)<<34) + (((ap_uint<50>)mul_3)<<27) + (((ap_uint<50>)mul_4)<<44) ) & WORD_SIZE_PLUS2_MASK;
  return res;
}

WORD barrett_reduce(WORD u, WORD v, WORD mod, WORD_PLUS3 factor)
{
  #pragma HLS inline

  DWORD U = hardcoded_fullMul_0(u,v);
  WORD_PLUS2 Y = (U) & WORD_SIZE_PLUS2_MASK;

  WORD V = U >> WORD_SIZE;
  WORD_PLUS1 W_1 = hardcoded_fullMul_1(factor, V);

  WORD_PLUS2 X_1 = hardcoded_lowerHalfMul_2(W_1, mod);

  WORD_PLUS1 Z;
  if(X_1<=Y){
    Z = Y - X_1;
  }
  else{
    Z = (WORD_PLUS3(1)<<(WORD_SIZE+2)) - X_1 + Y;
  }

  if(Z >= (3*mod)){
    Z = Z - 3*mod;
  }
  else if(Z >= (2*mod)){
    Z = Z - 2*mod;
  }
  else if(Z >= mod){
    Z = Z - mod;
  }

	return (WORD)Z;
}

// /********************************************************************************************
// * Butterfly Unit(BU) *
// ********************************************************************************************/

void BU(
    tapa::istream<WORD>& fwd_inVal0,
    tapa::istream<WORD>& fwd_inVal1, 
    tapa::istreams<WORD,2>& inv_inVals,
    tapa::istream<WORD>& inTf,
    tapa::ostreams<WORD,2 >& fwd_outVal,
    tapa::ostream<WORD>& inv_outVal0,
    tapa::ostream<WORD>& inv_outVal1,
    WORD q,
    WORD twoInverse,
    WORD_PLUS3 factor,
    bool direction,
    VAR_TYPE_16 iter,
    int BUIdx
    ){
  
  int i=0;
  VAR_TYPE_32 numBUIter = ((N*logN)/(2*NUM_BU)) * (iter+2);

  WORD left;
  WORD right;

  BU_COMP:for (;i<numBUIter; ) {
    #pragma HLS PIPELINE II=1
    if((((!fwd_inVal0.empty()) && (!fwd_inVal1.empty())) || ((!inv_inVals[0].empty()) && (!inv_inVals[1].empty())))  && (!inTf.empty())){
      if(direction){
        left = fwd_inVal0.read();
        right = fwd_inVal1.read();
      } else {
        left = inv_inVals[0].read();
        right = inv_inVals[1].read();
      }
      WORD tfVal = inTf.read();

      WORD reducedProduct = barrett_reduce(right, tfVal, q, factor);
      WORD_PLUS1 intemAdd = reducedProduct + left;
      WORD updatedLeft;
      if(intemAdd>=q){
        updatedLeft = intemAdd - q;
      }
      else{
        updatedLeft = intemAdd;
      }
      
      WORD updatedRight;
      if(left >= reducedProduct){
        updatedRight = left - reducedProduct;
      }
      else{
        updatedRight = q - (reducedProduct - left); 
      }

      if(!direction){ //Multiply with 2 inverse here. Equation=> (a>>1) + a[0]((mod+1)/2)
        multiplyTwoInverse(&updatedLeft, &twoInverse);
        multiplyTwoInverse(&updatedRight, &twoInverse);
      }
      
      if(direction){
        fwd_outVal[0].write(updatedLeft);
        fwd_outVal[1].write(updatedRight);
      } else {
        inv_outVal0.write(updatedLeft);
        inv_outVal1.write(updatedRight);
      }
      i++;
    }
  }
}

// /********************************************************************************************
// * TF buffer tasks *
// ********************************************************************************************/

void BufModule_loadTF_wiFW(tapa::istream<WORD>&    inTfFromLoad,
                           tapa::ostream<WORD>&    outTfToNextBuf,
                           WORD                    TFArr[N/2],
                           VAR_TYPE_16             loadTFLoopCounter,
                           VAR_TYPE_16             thisBufTFEnd,
                           VAR_TYPE_16             forwardingStart){

  #pragma HLS inline off

  VAR_TYPE_16 loadTFCounter = 0;

  BUF_LOAD_TF:for(VAR_TYPE_16 i=0; i<loadTFLoopCounter; i++){
    #pragma HLS PIPELINE II=1
    WORD readVal = inTfFromLoad.read();
    if(i<thisBufTFEnd){
      TFArr[loadTFCounter] = readVal;
      loadTFCounter++;
    }
    else if(i>=forwardingStart){
      outTfToNextBuf.write(readVal); 
    }
  }
}

void BufModule_loadTF_woFW(tapa::istream<WORD>&    inTfFromLoad,
                           WORD                    TFArr[N/2],
                           VAR_TYPE_16             loadTFLoopCounter,
                           VAR_TYPE_16             thisBufTFEnd){

  #pragma HLS inline off

  VAR_TYPE_16 loadCounter = 0;
  VAR_TYPE_16 loadTFCounter = 0;

  BUF_LOAD_TF:for(VAR_TYPE_16 i=0; i<loadTFLoopCounter; i++){
    #pragma HLS PIPELINE II=1
    WORD readVal = inTfFromLoad.read();
    if(i<thisBufTFEnd){
      TFArr[loadTFCounter] = readVal;
      loadTFCounter++;
    }
  }
}

void TFSend(tapa::ostreams<WORD,2>& tfToBUs,
            WORD                    TFArr[N/2],
            const TF_GROUP_WORD     FWD_TF_GROUP_IDX0[logN],
            const TF_GROUP_WORD     FWD_TF_GROUP_IDX1[logN],
            const TF_GROUP_WORD     INV_TF_GROUP_IDX0[logN],
            const TF_GROUP_WORD     INV_TF_GROUP_IDX1[logN],
            bool                    direction,
            VAR_TYPE_32             beta){

  #pragma HLS inline off

  TF_GROUP_WORD tfIdx_0;
  TF_GROUP_WORD tfIdx_1;
  WORD tfVal_0;
  WORD tfVal_1;

  BETA_WORD sendCount_0 = 0;
  BETA_WORD countMask = 0;
  TF_GROUP_WORD tfGroup_access0 = 0;
  TF_GROUP_WORD tfGroup_access1 = 0;

  BUF_COMP:for (VAR_TYPE_8 buffTrack=0; (buffTrack<logN); buffTrack++) {
    BUF_STAGE:for(sendCount_0 = 0 ;  sendCount_0 < beta; sendCount_0++){
      #pragma HLS PIPELINE II=1
      tfGroup_access0 = (direction) ? FWD_TF_GROUP_IDX0[buffTrack] : INV_TF_GROUP_IDX0[buffTrack];
      tfGroup_access1 = (direction) ? FWD_TF_GROUP_IDX1[buffTrack] : INV_TF_GROUP_IDX1[buffTrack];
      countMask = (direction) ? fwd_mask_arr[buffTrack] : inv_mask_arr[buffTrack];

      tfIdx_0 = ((tfGroup_access0)) + (sendCount_0 & (countMask));
      tfIdx_1 = ((tfGroup_access1)) + (sendCount_0 & (countMask));
    
      tfVal_0 = TFArr[tfIdx_0];
      tfVal_1 = TFArr[tfIdx_1];

      tfToBUs[0].write(tfVal_0);
      tfToBUs[1].write(tfVal_1);
    }
  }
}

void TFModule_wiFW_0(tapa::istream<WORD>&    inTfFromLoad,
                    tapa::ostream<WORD>&     outTfToNextBuf,
                    tapa::ostreams<WORD,2>&  tfToBUs,
                    bool                     direction,
                    VAR_TYPE_8               iter,
                    VAR_TYPE_32              BufIdx
                    ) {

    //==== Auto generated variables start ====//
    const BETA_WORD BETA = 1024; 
    const VAR_TYPE_32 TF_ARR_SIZE = 2048;
    const VAR_TYPE_32 FWD_LOAD_TF_LOOP_COUNTER = 5120;
    const VAR_TYPE_32 INV_LOAD_TF_LOOP_COUNTER = 4098;
    const VAR_TYPE_32 THIS_BUF_TF_END_FWD = 2048;
    const VAR_TYPE_32 THIS_BUF_TF_END_INV = 2048;
    const VAR_TYPE_32 TF_FORWARDING_START_FWD = 2048; 
    const VAR_TYPE_32 TF_FORWARDING_START_INV = 2048;
    const TF_GROUP_WORD FWD_TF_GROUP_IDX0[logN] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    const TF_GROUP_WORD FWD_TF_GROUP_IDX1[logN] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1024};
    const TF_GROUP_WORD INV_TF_GROUP_IDX0[logN] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    const TF_GROUP_WORD INV_TF_GROUP_IDX1[logN] = {0, 1024, 1024, 1024, 1024, 1024, 1024, 1024, 1024, 1024, 1024, 1024, 1024};
    //==== Auto generated variables end ====//
    
    WORD TFArr[2][TF_ARR_SIZE];
    #pragma HLS array_partition variable=TFArr type=complete  dim=1
    #pragma HLS bind_storage variable = TFArr type = RAM_2P impl = uram latency=1

    const BETA_WORD beta = BETA;
    
    const VAR_TYPE_32 loadTFLoopCounter = (direction) ? FWD_LOAD_TF_LOOP_COUNTER : INV_LOAD_TF_LOOP_COUNTER;
    const VAR_TYPE_32 thisBufTFEnd = (direction) ? THIS_BUF_TF_END_FWD : THIS_BUF_TF_END_INV;
    const VAR_TYPE_32 forwardingStart = (direction) ? TF_FORWARDING_START_FWD : TF_FORWARDING_START_INV;

    TF_GROUP_WORD tfIdx_0;
    TF_GROUP_WORD tfIdx_1;
    WORD tfVal_0;
    WORD tfVal_1;

    BETA_WORD sendCount_0 = 0;
    BETA_WORD countMask = 0;
    TF_GROUP_WORD tfGroup_access0 = 0;
    TF_GROUP_WORD tfGroup_access1 = 0;

    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){
      TFSend(tfToBUs, TFArr[iterCount%2], FWD_TF_GROUP_IDX0, FWD_TF_GROUP_IDX1, INV_TF_GROUP_IDX0, INV_TF_GROUP_IDX1, direction, beta);
      BufModule_loadTF_wiFW(inTfFromLoad, outTfToNextBuf, TFArr[(iterCount+1)%2], loadTFLoopCounter, thisBufTFEnd, forwardingStart);
    }
}

void TFModule_woFW_1(tapa::istream<WORD>&    inTfFromLoad,
                    tapa::ostreams<WORD,2>&  tfToBUs,
                    bool                     direction,
                    VAR_TYPE_8               iter,
                    VAR_TYPE_32              BufIdx
                    ) {

    //==== Auto generated variables start ====//
    const BETA_WORD BETA = 1024;
    const VAR_TYPE_32 TF_ARR_SIZE = 3072;
    const VAR_TYPE_32 FWD_LOAD_TF_LOOP_COUNTER = 3072;
    const VAR_TYPE_32 INV_LOAD_TF_LOOP_COUNTER = 2050; 
    const VAR_TYPE_32 THIS_BUF_TF_END_FWD = 3072;
    const VAR_TYPE_32 THIS_BUF_TF_END_INV = 2050;
    const TF_GROUP_WORD FWD_TF_GROUP_IDX0[logN] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1024, 1024};
    const TF_GROUP_WORD FWD_TF_GROUP_IDX1[logN] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1024, 2048};
    const TF_GROUP_WORD INV_TF_GROUP_IDX0[logN] = {0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1};
    const TF_GROUP_WORD INV_TF_GROUP_IDX1[logN] = {0, 1025, 1026, 1026, 1026, 1026, 1026, 1026, 1026, 1026, 1026, 1026, 1026};
    //==== Auto generated variables end ====//
    
    WORD TFArr[2][TF_ARR_SIZE];
    #pragma HLS array_partition variable=TFArr type=complete  dim=1
    #pragma HLS bind_storage variable = TFArr type = RAM_2P impl = uram latency=1

    const BETA_WORD beta = BETA;
    
    const VAR_TYPE_32 loadTFLoopCounter = (direction) ? FWD_LOAD_TF_LOOP_COUNTER : INV_LOAD_TF_LOOP_COUNTER;
    const VAR_TYPE_32 thisBufTFEnd = (direction) ? THIS_BUF_TF_END_FWD : THIS_BUF_TF_END_INV;

    TF_GROUP_WORD tfIdx_0;
    TF_GROUP_WORD tfIdx_1;
    WORD tfVal_0;
    WORD tfVal_1;

    BETA_WORD sendCount_0 = 0;
    BETA_WORD countMask = 0;
    TF_GROUP_WORD tfGroup_access0 = 0;
    TF_GROUP_WORD tfGroup_access1 = 0;

    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){
      TFSend(tfToBUs, TFArr[iterCount%2], FWD_TF_GROUP_IDX0, FWD_TF_GROUP_IDX1, INV_TF_GROUP_IDX0, INV_TF_GROUP_IDX1, direction, beta);
      BufModule_loadTF_woFW(inTfFromLoad, TFArr[(iterCount+1)%2], loadTFLoopCounter, thisBufTFEnd);
    }
}



// /********************************************************************************************
// * Polynomial buffer tasks *
// ********************************************************************************************/

void BufModule_comp_stage_polySend(tapa::ostreams<WORD,2>& fwd_PolyToBUs,
                                tapa::ostreams<WORD,2>& inv_PolyToBUs,
                                bool                    direction,
                                WORD                    polyBuf0[N/NUM_BU],
                                VAR_TYPE_32             beta){

  #pragma HLS inline off

  BETA_WORD sendCount_0 = 0;

  BETA_WORD inLeftIdx;
  BETA_WORD inRightIdx;
  WORD inVal0;
  WORD inVal1;

  //compute data
  BUF_STAGE:for(; ( sendCount_0<beta ); sendCount_0++){
    #pragma HLS PIPELINE II=1
    if(direction){
      inLeftIdx = sendCount_0;
      inRightIdx = beta+sendCount_0;
    }
    else{
      inLeftIdx = 2*sendCount_0;
      inRightIdx = 2*sendCount_0 + (BETA_WORD)1;
    }

    inVal0 = polyBuf0[inLeftIdx];
    inVal1 = polyBuf0[inRightIdx];

    if( direction ){
      fwd_PolyToBUs[0].write(inVal0);
      fwd_PolyToBUs[1].write(inVal1);
    }
    else{
      inv_PolyToBUs[0].write(inVal0);
      inv_PolyToBUs[1].write(inVal1);
    }
  }
}


void BufModule_comp_stage_polyReceive(tapa::istreams<WORD,2>& fwd_polyFromBUs,
                                tapa::istreams<WORD,2>& inv_polyFromBUs,
                                bool                    direction,
                                WORD                    polyBuf0[N/NUM_BU],
                                VAR_TYPE_32             beta){

  #pragma HLS inline off

  BETA_WORD outLeftIdx;
  BETA_WORD outRightIdx;
  WORD outVal0;
  WORD outVal1;

  BETA_WORD receiveCount_0 = 0;

  //compute data
  BUF_STAGE:for(; ( receiveCount_0 < beta ); receiveCount_0++){
    #pragma HLS PIPELINE II=1
    #pragma HLS dependence variable=polyBuf0 intra WAW false

    if(direction){
      outLeftIdx = 2*receiveCount_0;
      outRightIdx = (2*receiveCount_0) + 1;
    }
    else{
      outLeftIdx = receiveCount_0;
      outRightIdx = receiveCount_0 + beta;
    }

    if(direction){
        outVal0 = fwd_polyFromBUs[0].read();
        outVal1 = fwd_polyFromBUs[1].read();
        polyBuf0[outLeftIdx] = outVal0;
        polyBuf0[outRightIdx] = outVal1;
    }
    else{
        outVal0 = inv_polyFromBUs[0].read();
        outVal1 = inv_polyFromBUs[1].read();
        polyBuf0[outLeftIdx] = outVal0;
        polyBuf0[outRightIdx] = outVal1;
    }
  }
}

void BufModule_comp(tapa::istreams<WORD,2>& fwd_polyFromBUs,
                                tapa::istreams<WORD,2>& inv_polyFromBUs,
                                tapa::ostreams<WORD,2>& fwd_PolyToBUs,
                                tapa::ostreams<WORD,2>& inv_PolyToBUs,
                                bool                    direction,
                                VAR_TYPE_32             iter,
                                WORD                    polyBuf0[N/NUM_BU],
                                WORD                    polyBuf1[N/NUM_BU],
                                VAR_TYPE_32             beta){
  #pragma HLS inline off
  VAR_TYPE_8 buffTrack = 0;

  //compute data
  BUF_COMP:for (; (buffTrack<logN); buffTrack++) {
    if(buffTrack%2){
      BufModule_comp_stage_polySend(fwd_PolyToBUs, inv_PolyToBUs, direction, polyBuf1, beta);
      BufModule_comp_stage_polyReceive(fwd_polyFromBUs, inv_polyFromBUs, direction, polyBuf0, beta);
    }
    else{
      BufModule_comp_stage_polySend(fwd_PolyToBUs, inv_PolyToBUs, direction, polyBuf0, beta);
      BufModule_comp_stage_polyReceive(fwd_polyFromBUs, inv_polyFromBUs, direction, polyBuf1, beta);
    }
  }
}
void BufModule_poly_load_store_wiFW(tapa::istream<WORD>&    inpPolyFromLoad,
                           tapa::ostream<WORD>&    outPolyToNextBuf,
                           WORD                    polyBuf[N/NUM_BU],
                           VAR_TYPE_32             loadStoreDataLoopCounter,
                           VAR_TYPE_32             loadStoreThisBufDataEnd,
                           tapa::istream<WORD>&    inpPolyFromNextBuf,
                           tapa::ostream<WORD>&    outPolyToStore,
                           VAR_TYPE_32             BufIdx){

  #pragma HLS inline off

  VAR_TYPE_32 loadCounter = 0;
  VAR_TYPE_32 storeCounter = 0;
  WORD loadReadData;
  bool loadReadValid=false;
  VAR_TYPE_32 loadThreshold;

  WORD storeReadData;
  bool storeReadValid=false;

  //Load data
  BUF_LOAD_STORE_POLY:for(; ((loadCounter<loadStoreDataLoopCounter)); ){
    #pragma HLS PIPELINE II=1

    if( storeReadValid && (outPolyToStore.try_write(storeReadData)) ){
      storeCounter++;
      storeReadValid = false;
    }
    
    if( (storeCounter<loadStoreThisBufDataEnd) ){
      storeReadData = polyBuf[storeCounter];
      storeReadValid = true;
    }
    else if ( (!storeReadValid) && (storeCounter<loadStoreDataLoopCounter) && inpPolyFromNextBuf.try_read(storeReadData) ){
      storeReadValid = true;
    }

    if( (!loadReadValid) && (loadCounter<storeCounter) && (inpPolyFromLoad.try_read(loadReadData)) ){
      loadReadValid = true;
    }

    if( loadReadValid && (loadCounter<loadStoreThisBufDataEnd) ){
      polyBuf[loadCounter] = loadReadData;
      loadReadValid = false;
      loadCounter++;
    }
    else if( loadReadValid && (outPolyToNextBuf.try_write(loadReadData)) ){
      loadReadValid = false;
      loadCounter++;
    }
  }
}

void BufModule_poly_load_store_woFW(tapa::istream<WORD>&    inpPolyFromLoad,
                           WORD                    polyBuf[N/NUM_BU],
                           VAR_TYPE_32             loadStoreDataLoopCounter,
                           VAR_TYPE_32             loadStoreThisBufDataEnd,
                           tapa::ostream<WORD>&    outPolyToStore,
                           VAR_TYPE_32             BufIdx){
  
  #pragma HLS inline off

  VAR_TYPE_32 loadCounter = 0;
  VAR_TYPE_32 storeCounter=0;
  WORD loadReadData;

  WORD storeReadData;
  bool storeReadValid=false;

  //Load data
  BUF_LOAD_POLY:for(; ((loadCounter<loadStoreDataLoopCounter)); ){
    #pragma HLS PIPELINE II=1

    if( storeReadValid && (outPolyToStore.try_write(storeReadData)) ){
      storeCounter++;
    }

    if( (storeCounter<loadStoreThisBufDataEnd) ){
      storeReadData = polyBuf[storeCounter];
      storeReadValid = true;
    }
    else{
      storeReadValid = false;
    }
    
    if( (loadCounter<storeCounter) && (inpPolyFromLoad.try_read(loadReadData)) ){
      polyBuf[loadCounter] = loadReadData;
      loadCounter++;
    }
  }
}


void BufModule_wiFW_0(tapa::istream<WORD>&    inpPolyFromLoad,
                      tapa::ostream<WORD>&    outPolyToNextBuf,
                      tapa::istreams<WORD,2>& fwd_polyFromBUs,
                      tapa::istreams<WORD,2>& inv_polyFromBUs,
                      tapa::ostreams<WORD,2>& fwd_PolyToBUs,
                      tapa::ostreams<WORD,2>& inv_PolyToBUs,
                      tapa::istream<WORD>&    inpPolyFromNextBuf,
                      tapa::ostream<WORD>&    outPolyToStore,
                      bool                    direction,
                      VAR_TYPE_8              iter,
                      VAR_TYPE_32             BufIdx
                    ) {

    //==== Auto generated variables start ====//
    const BETA_WORD BETA = 1024; 
    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = 8192; 
    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = 2048;
    //==== Auto generated variables end ====//
    
    WORD polyBuf[3][N/NUM_BU];
    #pragma HLS array_partition variable=polyBuf type=complete  dim=1
    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1

    const BETA_WORD beta = BETA;

    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; 
    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;

    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){
      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%3], polyBuf[(iterCount+2)%3], beta);
      BufModule_poly_load_store_wiFW(inpPolyFromLoad, outPolyToNextBuf, polyBuf[(iterCount+1)%3], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, inpPolyFromNextBuf, outPolyToStore, BufIdx);
    }
}

void BufModule_wiFW_1(tapa::istream<WORD>&    inpPolyFromLoad,
                      tapa::ostream<WORD>&    outPolyToNextBuf,
                      tapa::istreams<WORD,2>& fwd_polyFromBUs,
                      tapa::istreams<WORD,2>& inv_polyFromBUs,
                      tapa::ostreams<WORD,2>& fwd_PolyToBUs,
                      tapa::ostreams<WORD,2>& inv_PolyToBUs,
                      tapa::istream<WORD>&    inpPolyFromNextBuf,
                      tapa::ostream<WORD>&    outPolyToStore,
                      bool                    direction,
                      VAR_TYPE_8              iter,
                      VAR_TYPE_32             BufIdx
                    ) {

    //==== Auto generated variables start ====//
    const BETA_WORD BETA = 1024; 
    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = 6144; 
    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = 2048;
    //==== Auto generated variables end ====//
    
    WORD polyBuf[3][N/NUM_BU];
    #pragma HLS array_partition variable=polyBuf type=complete  dim=1
    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1

    const BETA_WORD beta = BETA;

    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; 
    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;

    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){
      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%3], polyBuf[(iterCount+2)%3], beta);
      BufModule_poly_load_store_wiFW(inpPolyFromLoad, outPolyToNextBuf, polyBuf[(iterCount+1)%3], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, inpPolyFromNextBuf, outPolyToStore, BufIdx);
    }
}

void BufModule_wiFW_2(tapa::istream<WORD>&    inpPolyFromLoad,
                      tapa::ostream<WORD>&    outPolyToNextBuf,
                      tapa::istreams<WORD,2>& fwd_polyFromBUs,
                      tapa::istreams<WORD,2>& inv_polyFromBUs,
                      tapa::ostreams<WORD,2>& fwd_PolyToBUs,
                      tapa::ostreams<WORD,2>& inv_PolyToBUs,
                      tapa::istream<WORD>&    inpPolyFromNextBuf,
                      tapa::ostream<WORD>&    outPolyToStore,
                      bool                    direction,
                      VAR_TYPE_8              iter,
                      VAR_TYPE_32             BufIdx
                    ) {

    //==== Auto generated variables start ====//
    const BETA_WORD BETA = 1024; 
    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = 4096; 
    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = 2048;
    //==== Auto generated variables end ====//
    
    WORD polyBuf[3][N/NUM_BU];
    #pragma HLS array_partition variable=polyBuf type=complete  dim=1
    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1

    const BETA_WORD beta = BETA;

    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; 
    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;

    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){
      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%3], polyBuf[(iterCount+2)%3], beta);
      BufModule_poly_load_store_wiFW(inpPolyFromLoad, outPolyToNextBuf, polyBuf[(iterCount+1)%3], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, inpPolyFromNextBuf, outPolyToStore, BufIdx);
    }
}

void BufModule_woFW_3(tapa::istream<WORD>&    inpPolyFromLoad,
                      tapa::istreams<WORD,2>& fwd_polyFromBUs,
                      tapa::istreams<WORD,2>& inv_polyFromBUs,
                      tapa::ostreams<WORD,2>& fwd_PolyToBUs,
                      tapa::ostreams<WORD,2>& inv_PolyToBUs,
                      tapa::ostream<WORD>&    outPolyToStore,
                      bool                    direction,
                      VAR_TYPE_8              iter,
                      VAR_TYPE_32             BufIdx
                    ) {

    //==== Auto generated variables start ====//
    const BETA_WORD BETA = 1024; 
    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = 2048; 
    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = 2048;
    //==== Auto generated variables end ====//
    
    WORD polyBuf[3][N/NUM_BU];
    #pragma HLS array_partition variable=polyBuf type=complete  dim=1
    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1

    const BETA_WORD beta = BETA;

    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; 
    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;

    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){
      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%3], polyBuf[(iterCount+2)%3], beta);
      BufModule_poly_load_store_woFW(inpPolyFromLoad, polyBuf[(iterCount+1)%3], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, outPolyToStore, BufIdx);
    }
}



// /********************************************************************************************
// * Top kernel *
// ********************************************************************************************/

void NTT_kernel(
    tapa::mmap<POLY_WIDE_DATA> polyVectorIn_G0,
    tapa::mmap<TF_WIDE_DATA> TFArr_G0,
    tapa::mmap<POLY_WIDE_DATA> polyVectorOut_G0,
    WORD q0,
    WORD twoInverse0,
    WORD_PLUS3 factor0,
    bool direction,
    VAR_TYPE_16 iter
    )
{

    /* Limb0 */
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyLoad_to_polyBuf_L0_G0_0("polyLoad_to_polyBuf_L0_G0_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyLoad_to_polyBuf_L0_G0_1("polyLoad_to_polyBuf_L0_G0_1_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyLoad_to_polyBuf_L0_G0_2("polyLoad_to_polyBuf_L0_G0_2_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyLoad_to_polyBuf_L0_G0_3("polyLoad_to_polyBuf_L0_G0_3_stream");

    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_polyBuf_to_BU_L0_0("fwd_polyBuf_to_BU_L0_0_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_polyBuf_to_BU_L0_1("fwd_polyBuf_to_BU_L0_1_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_polyBuf_to_BU_L0_2("fwd_polyBuf_to_BU_L0_2_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_polyBuf_to_BU_L0_3("fwd_polyBuf_to_BU_L0_3_stream");

    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_polyBuf_to_BU_L0_0("inv_polyBuf_to_BU_L0_0_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_polyBuf_to_BU_L0_1("inv_polyBuf_to_BU_L0_1_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_polyBuf_to_BU_L0_2("inv_polyBuf_to_BU_L0_2_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_polyBuf_to_BU_L0_3("inv_polyBuf_to_BU_L0_3_stream");

    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_BU_to_polyBuf_L0_0("fwd_BU_to_polyBuf_L0_0_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_BU_to_polyBuf_L0_1("fwd_BU_to_polyBuf_L0_1_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_BU_to_polyBuf_L0_2("fwd_BU_to_polyBuf_L0_2_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> fwd_BU_to_polyBuf_L0_3("fwd_BU_to_polyBuf_L0_3_stream");

    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_BU_to_polyBuf_L0_0("inv_BU_to_polyBuf_L0_0_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_BU_to_polyBuf_L0_1("inv_BU_to_polyBuf_L0_1_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_BU_to_polyBuf_L0_2("inv_BU_to_polyBuf_L0_2_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> inv_BU_to_polyBuf_L0_3("inv_BU_to_polyBuf_L0_3_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyBuf_to_polyStore_L0_G0_0("polyBuf_to_polyStore_L0_G0_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyBuf_to_polyStore_L0_G0_1("polyBuf_to_polyStore_L0_G0_1_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyBuf_to_polyStore_L0_G0_2("polyBuf_to_polyStore_L0_G0_2_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> polyBuf_to_polyStore_L0_G0_3("polyBuf_to_polyStore_L0_G0_3_stream");

    tapa::streams<WORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT> tfLoad_to_TFBuf_L0_G0_0("tfLoad_to_TFBuf_L0_G0_0_stream");
    tapa::streams<WORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT> tfLoad_to_TFBuf_L0_G0_1("tfLoad_to_TFBuf_L0_G0_1_stream");

    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> tfBuf_to_BU_L0_0("tfBuf_to_BU_L0_0_stream");
    tapa::streams<WORD, 2, BU_BUF_FIFO_DEPTH> tfBuf_to_BU_L0_1("tfBuf_to_BU_L0_1_stream");

    tapa::task()
        //polynomial loading tasks (Mmap2Stream_poly)
        .invoke(Mmap2Stream_poly_1_limbs, polyVectorIn_G0, polyLoad_to_polyBuf_L0_G0_0, 0, iter)

        //TF loading tasks (Mmap2Stream_tf)
        .invoke(Mmap2Stream_tf_1_limbs, TFArr_G0, tfLoad_to_TFBuf_L0_G0_0, direction, iter, 0)

        /* Limb0 */
        //TF buffer tasks
        .invoke(TFModule_wiFW_0, tfLoad_to_TFBuf_L0_G0_0[0], tfLoad_to_TFBuf_L0_G0_1[0], tfBuf_to_BU_L0_0, direction, iter, 0)
        .invoke(TFModule_woFW_1, tfLoad_to_TFBuf_L0_G0_1[0], tfBuf_to_BU_L0_1, direction, iter, 1)

        //polynomial buffer tasks
        .invoke(BufModule_wiFW_0, polyLoad_to_polyBuf_L0_G0_0[0], polyLoad_to_polyBuf_L0_G0_1[0], fwd_BU_to_polyBuf_L0_0, inv_BU_to_polyBuf_L0_0, fwd_polyBuf_to_BU_L0_0, inv_polyBuf_to_BU_L0_0, polyBuf_to_polyStore_L0_G0_1[0], polyBuf_to_polyStore_L0_G0_0[0], direction, iter, 0)
        .invoke(BufModule_wiFW_1, polyLoad_to_polyBuf_L0_G0_1[0], polyLoad_to_polyBuf_L0_G0_2[0], fwd_BU_to_polyBuf_L0_1, inv_BU_to_polyBuf_L0_1, fwd_polyBuf_to_BU_L0_1, inv_polyBuf_to_BU_L0_1, polyBuf_to_polyStore_L0_G0_2[0], polyBuf_to_polyStore_L0_G0_1[0], direction, iter, 1)
        .invoke(BufModule_wiFW_2, polyLoad_to_polyBuf_L0_G0_2[0], polyLoad_to_polyBuf_L0_G0_3[0], fwd_BU_to_polyBuf_L0_2, inv_BU_to_polyBuf_L0_2, fwd_polyBuf_to_BU_L0_2, inv_polyBuf_to_BU_L0_2, polyBuf_to_polyStore_L0_G0_3[0], polyBuf_to_polyStore_L0_G0_2[0], direction, iter, 2)
        .invoke(BufModule_woFW_3, polyLoad_to_polyBuf_L0_G0_3[0], fwd_BU_to_polyBuf_L0_3, inv_BU_to_polyBuf_L0_3, fwd_polyBuf_to_BU_L0_3, inv_polyBuf_to_BU_L0_3, polyBuf_to_polyStore_L0_G0_3[0], direction, iter, 3)

        //BU tasks
        .invoke(BU, fwd_polyBuf_to_BU_L0_0[0], fwd_polyBuf_to_BU_L0_2[0], inv_polyBuf_to_BU_L0_0, tfBuf_to_BU_L0_0[0], fwd_BU_to_polyBuf_L0_0, inv_BU_to_polyBuf_L0_0[0], inv_BU_to_polyBuf_L0_2[0], q0, twoInverse0, factor0, direction, iter, 0)
        .invoke(BU, fwd_polyBuf_to_BU_L0_0[1], fwd_polyBuf_to_BU_L0_2[1], inv_polyBuf_to_BU_L0_1, tfBuf_to_BU_L0_1[0], fwd_BU_to_polyBuf_L0_1, inv_BU_to_polyBuf_L0_0[1], inv_BU_to_polyBuf_L0_2[1], q0, twoInverse0, factor0, direction, iter, 1)
        .invoke(BU, fwd_polyBuf_to_BU_L0_1[0], fwd_polyBuf_to_BU_L0_3[0], inv_polyBuf_to_BU_L0_2, tfBuf_to_BU_L0_0[1], fwd_BU_to_polyBuf_L0_2, inv_BU_to_polyBuf_L0_1[0], inv_BU_to_polyBuf_L0_3[0], q0, twoInverse0, factor0, direction, iter, 2)
        .invoke(BU, fwd_polyBuf_to_BU_L0_1[1], fwd_polyBuf_to_BU_L0_3[1], inv_polyBuf_to_BU_L0_3, tfBuf_to_BU_L0_1[1], fwd_BU_to_polyBuf_L0_3, inv_BU_to_polyBuf_L0_1[1], inv_BU_to_polyBuf_L0_3[1], q0, twoInverse0, factor0, direction, iter, 3)

        //polynomial storing tasks (Stream2Mmap_poly)
        .invoke(Stream2Mmap_poly_1_limbs, polyVectorOut_G0, polyBuf_to_polyStore_L0_G0_0, 0, iter)

    ;
}
