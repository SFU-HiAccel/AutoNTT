#include <cstdint>

#include <tapa.h>
#include "ntt.h"

// /********************************************************************************************
// * Polynomial load store tasks *
// ********************************************************************************************/

void fwd_load_inv_store_poly_1_limbs(tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_in_poly_L0_stream0,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_in_poly_L0_stream1,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_in_poly_L0_stream2,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_in_poly_L0_stream3,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_out_poly_L0_stream0,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_out_poly_L0_stream1,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_out_poly_L0_stream2,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_out_poly_L0_stream3,
                 bool direction,
                 VAR_TYPE_16 iter) {

  VAR_TYPE_16 totalDataCount = (N/V_TOTAL_DATA)*(SEQ_BUG_PER_PARA_LIMB_POLY_PORT);
  POLY_WIDE_DATA val;
  WORD smallData;

  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    LOAD_STORE_POLY_0:for (int i_req = 0, i_resp=0; i_resp < totalDataCount;) {
      #pragma HLS PIPELINE II=1

      if(direction){  //fwd load
        if( ( i_req < totalDataCount ) && (poly_mmap.read_addr.try_write(i_req)) ){
          i_req++;
        }

        if( !poly_mmap.read_data.empty() ){
          POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);

          VAR_TYPE_16 seq_group_idx = i_resp/(N/V_TOTAL_DATA);
          
          for(int j=0; j<(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT); j++){
            #pragma HLS UNROLL
            WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA)1)<<WORD_SIZE)-1));
            if( seq_group_idx==0 ){
              fwd_out_poly_L0_stream0[j].write(smallVal);
            }
            else if( seq_group_idx==1 ){
              fwd_out_poly_L0_stream1[j].write(smallVal);
            }
            else if( seq_group_idx==2 ){
              fwd_out_poly_L0_stream2[j].write(smallVal);
            }
            else{
              fwd_out_poly_L0_stream3[j].write(smallVal);
            }
            val >>= DRAM_WORD_SIZE;
          }

          i_resp++;
        }
      }
      else{ //inv store
        VAR_TYPE_16 seq_group_idx = i_req/(N/V_TOTAL_DATA);

        val = 0;
        
        bool inpStreamNotEmpty;
        if( seq_group_idx==0 ){
          inpStreamNotEmpty = ( !inv_in_poly_L0_stream0[0].empty() );
        }
        else if( seq_group_idx==1 ){
          inpStreamNotEmpty = ( !inv_in_poly_L0_stream1[0].empty() );
        }
        else if( seq_group_idx==2 ){
          inpStreamNotEmpty = ( !inv_in_poly_L0_stream2[0].empty() );
        }
        else{
          inpStreamNotEmpty = ( !inv_in_poly_L0_stream3[0].empty() );
        }

        for(int j=1; j<(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT); j++){
          if( seq_group_idx==0 ){
             inpStreamNotEmpty &= ( !inv_in_poly_L0_stream0[j].empty() );
          }
          else if( seq_group_idx==1 ){
             inpStreamNotEmpty &= ( !inv_in_poly_L0_stream1[j].empty() );
          }
          else if( seq_group_idx==2 ){
             inpStreamNotEmpty &= ( !inv_in_poly_L0_stream2[j].empty() );
          }
          else{
             inpStreamNotEmpty &= ( !inv_in_poly_L0_stream3[j].empty() );
          }
        }

        if( ( i_req < (totalDataCount) ) && ( inpStreamNotEmpty ) ){
          
          //read FIFOs
          for(int j=(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT)-1; j>=0; j--){
            #pragma HLS UNROLL
            val <<= DRAM_WORD_SIZE;
            if( seq_group_idx==0 ){
              smallData = inv_in_poly_L0_stream0[j].read();
            }
            else if( seq_group_idx==1 ){
              smallData = inv_in_poly_L0_stream1[j].read();
            }
            else if( seq_group_idx==2 ){
              smallData = inv_in_poly_L0_stream2[j].read();
            }
            else{
              smallData = inv_in_poly_L0_stream3[j].read();
            }
            val |= (POLY_WIDE_DATA)(smallData);
          }
          
          //write mem
          poly_mmap.write_addr.write(i_req);
          poly_mmap.write_data.write(val);
          i_req++;
        }

        if( !poly_mmap.write_resp.empty() ){
          i_resp += unsigned(poly_mmap.write_resp.read(nullptr)) + 1;
        }
      }
    }
  }
  #ifndef __SYNTHESIS__
  if(direction){
    printf("[fwd_load_inv_store_poly]: Polynomial loading done\n");
  }
  else{
    printf("[fwd_load_inv_store_poly]: Polynomial storing done\n");
  }
  #endif
}


void fwd_store_inv_load_poly_1_limbs(tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_in_poly_L0_stream0,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_in_poly_L0_stream1,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_in_poly_L0_stream2,
                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& fwd_in_poly_L0_stream3,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_out_poly_L0_stream0,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_out_poly_L0_stream1,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_out_poly_L0_stream2,
                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& inv_out_poly_L0_stream3,
                 bool direction,
                 VAR_TYPE_16 iter) {

  VAR_TYPE_16 totalDataCount = (N/V_TOTAL_DATA)*(SEQ_BUG_PER_PARA_LIMB_POLY_PORT);
  POLY_WIDE_DATA val;
  WORD smallData;

  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    LOAD_STORE_POLY_0:for (int i_req = 0, i_resp=0; i_resp < totalDataCount;) {
      #pragma HLS PIPELINE II=1

      if(!direction){  //inv load
        if( ( i_req < totalDataCount ) && (poly_mmap.read_addr.try_write(i_req)) ){
          i_req++;
        }

        if( !poly_mmap.read_data.empty() ){
          POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);

          VAR_TYPE_16 seq_group_idx = i_resp/(N/V_TOTAL_DATA);
          
          for(int j=0; j<(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT); j++){
            #pragma HLS UNROLL
            WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA)1)<<WORD_SIZE)-1));
            if( seq_group_idx==0 ){
              inv_out_poly_L0_stream0[j].write(smallVal);
            }
            else if( seq_group_idx==1 ){
              inv_out_poly_L0_stream1[j].write(smallVal);
            }
            else if( seq_group_idx==2 ){
              inv_out_poly_L0_stream2[j].write(smallVal);
            }
            else{
              inv_out_poly_L0_stream3[j].write(smallVal);
            }
            val >>= DRAM_WORD_SIZE;
          }

          i_resp++;
        }
      }
      else{ //fwd store
        VAR_TYPE_16 seq_group_idx = i_req/(N/V_TOTAL_DATA);

        val = 0;
        
        bool inpStreamNotEmpty;
        if( seq_group_idx==0 ){
          inpStreamNotEmpty = ( !fwd_in_poly_L0_stream0[0].empty() );
        }
        else if( seq_group_idx==1 ){
          inpStreamNotEmpty = ( !fwd_in_poly_L0_stream1[0].empty() );
        }
        else if( seq_group_idx==2 ){
          inpStreamNotEmpty = ( !fwd_in_poly_L0_stream2[0].empty() );
        }
        else{
          inpStreamNotEmpty = ( !fwd_in_poly_L0_stream3[0].empty() );
        }

        for(int j=1; j<(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT); j++){
          if( seq_group_idx==0 ){
             inpStreamNotEmpty &= ( !fwd_in_poly_L0_stream0[j].empty() );
          }
          else if( seq_group_idx==1 ){
             inpStreamNotEmpty &= ( !fwd_in_poly_L0_stream1[j].empty() );
          }
          else if( seq_group_idx==2 ){
             inpStreamNotEmpty &= ( !fwd_in_poly_L0_stream2[j].empty() );
          }
          else{
             inpStreamNotEmpty &= ( !fwd_in_poly_L0_stream3[j].empty() );
          }
        }

        if( ( i_req < (totalDataCount) ) && ( inpStreamNotEmpty ) ){
          
          //read FIFOs
          for(int j=(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT)-1; j>=0; j--){
            #pragma HLS UNROLL
            val <<= DRAM_WORD_SIZE;
            if( seq_group_idx==0 ){
              smallData = fwd_in_poly_L0_stream0[j].read();
            }
            else if( seq_group_idx==1 ){
              smallData = fwd_in_poly_L0_stream1[j].read();
            }
            else if( seq_group_idx==2 ){
              smallData = fwd_in_poly_L0_stream2[j].read();
            }
            else{
              smallData = fwd_in_poly_L0_stream3[j].read();
            }
            val |= (POLY_WIDE_DATA)(smallData);
          }
          
          //write mem
          poly_mmap.write_addr.write(i_req);
          poly_mmap.write_data.write(val);
          i_req++;
        }

        if( !poly_mmap.write_resp.empty() ){
          i_resp += unsigned(poly_mmap.write_resp.read(nullptr)) + 1;
        }
      }
    }
  }
  #ifndef __SYNTHESIS__
  if(direction){
    printf("[fwd_store_inv_load_poly]: Polynomial storing done\n");
  }
  else{
    printf("[fwd_store_inv_load_poly]: Polynomial loading done\n");
  }
  #endif
}


// /********************************************************************************************
// * TF load tasks *
// ********************************************************************************************/

void Mmap2Stream_tf_0_1_limbs(tapa::async_mmap<TF_WIDE_DATA>& tf_mmap,
                 tapa::ostreams<DWORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2>& tf_stream_L0_0,
                 bool direction,
                 VAR_TYPE_16 iter) {

  
  VAR_TYPE_16 fwd_total_depth = 1245;
  VAR_TYPE_16 inv_total_depth = 1317;

  VAR_TYPE_16 total_depth;
  if(direction){
    total_depth = fwd_total_depth;
  }
  else{
    total_depth = inv_total_depth;
  }
  
  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    LOAD_TF:for (int i_req = 0, i_resp=0; i_resp < (total_depth);) {
      #pragma HLS PIPELINE II=1

      if( ( i_req < (total_depth) ) && (tf_mmap.read_addr.try_write(i_req)) ){
        i_req++;
      }

      if( !tf_mmap.read_data.empty() ){
        TF_WIDE_DATA val = tf_mmap.read_data.read();
        
        for(VAR_TYPE_8 j=0; j<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2; j++){
          DWORD smallVal = (DWORD)(val & ((((TF_WIDE_DATA)1)<<(2*WORD_SIZE))-1));
          tf_stream_L0_0[j].write(smallVal);
          val >>= (2*DRAM_WORD_SIZE);
        }
        
        i_resp++;
      }

    }
  }

  #ifndef __SYNTHESIS__
  printf("[Mmap2Stream_tf]: TF loading done\n");
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
    tapa::istream<WORD>& inv_inVal0,
    tapa::istream<WORD>& inv_inVal1, 
    tapa::istream<WORD>& tf_inVal,
    tapa::ostream<WORD>& fwd_outVal0,
    tapa::ostream<WORD>& fwd_outVal1,
    tapa::ostream<WORD>& inv_outVal0,
    tapa::ostream<WORD>& inv_outVal1,
    WORD q,
    WORD twoInverse,
    WORD_PLUS3 factor,
    bool direction,
    VAR_TYPE_16 iter,
    VAR_TYPE_16 BUG_id,
    VAR_TYPE_16 layer_id
    ){

  VAR_TYPE_32 totalIterDataCount = 0;
  VAR_TYPE_16 singleIterDataCount = 0;
  VAR_TYPE_32 totalIterDataLimit = (N/V_TOTAL_DATA) * ( (VAR_TYPE_32)(logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) * (iter+1);
  VAR_TYPE_16 singleIterDataLimit = (N/V_TOTAL_DATA) * ( (VAR_TYPE_16)(logN+(H_BUG_SIZE-1))/H_BUG_SIZE );
  VAR_TYPE_16 nonCompleteStageLimit = ( (logN%H_BUG_SIZE) >= (layer_id+1) ) ? 1 : 0;
  VAR_TYPE_16 fwd_singleIterCompLimit = (N/V_TOTAL_DATA) * ( ((VAR_TYPE_16)logN/H_BUG_SIZE) + nonCompleteStageLimit );
  VAR_TYPE_16 inv_singleIterCompLimit = singleIterDataLimit - fwd_singleIterCompLimit;

  WORD left;
  WORD right;
  WORD tfVal;
  WORD updatedLeft;
  WORD updatedRight;

  BU_COMP:for (;totalIterDataCount<totalIterDataLimit; ) {
    #pragma HLS PIPELINE II=1
    if( ( ( ( (!fwd_inVal0.empty()) && (!fwd_inVal1.empty()) ) || ( (!inv_inVal0.empty()) && (!inv_inVal1.empty()) ) )  && ( !tf_inVal.empty() ) ) ){
      
      if(direction){
        left = fwd_inVal0.read();
        right = fwd_inVal1.read();
      }
      else{
        left = inv_inVal0.read();
        right = inv_inVal1.read();
      }
      tfVal = tf_inVal.read();
      
      WORD reducedProduct = barrett_reduce(right, tfVal, q, factor);
      WORD_PLUS1 intemAdd = reducedProduct + left;
      if(intemAdd>=q){
        updatedLeft = intemAdd - q;
      }
      else{
        updatedLeft = intemAdd;
      }
      
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

      if( ( (direction) && (singleIterDataCount >= fwd_singleIterCompLimit) ) || ( (!direction) && (singleIterDataCount < inv_singleIterCompLimit) ) ){
        updatedLeft = left;
        updatedRight = right;
      }

      if(direction){
        fwd_outVal0.write(updatedLeft);
        fwd_outVal1.write(updatedRight);
      }
      else{
        inv_outVal0.write(updatedLeft);
        inv_outVal1.write(updatedRight);
      }
      
      totalIterDataCount++;
      singleIterDataCount = (singleIterDataCount==(singleIterDataLimit-1)) ? (0) : (singleIterDataCount+1);
    }
  }

}

// /********************************************************************************************
// * Shuffler tasks *
// ********************************************************************************************/

void shuffler(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal,
                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal,
                   tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal,
                   tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal,
                    bool direction,
                   VAR_TYPE_16 BUG_id,
                   VAR_TYPE_16 iter){
  
  WORD poly_buf[2*V_BUG_SIZE][2*SINGLE_LIMB_BUF_SIZE];
  #pragma HLS bind_storage variable=poly_buf type=RAM_S2P impl=BRAM latency=1
  #pragma HLS array_partition variable=poly_buf type=complete dim=1

  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_16 shuffleLimit = (VAR_TYPE_32)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;

  VAR_TYPE_16 max_data_offset = (V_BUG_SIZE*2);
  
  //==== Auto generated variables start ====//
  VAR_TYPE_8 shIn_log_shift_freq_table[shuffleLimit] = {0, 2, 5, 8};
  VAR_TYPE_8 shIn_log_mini_shift_reset_freq_table[shuffleLimit] = {0, 0, 0, 2};
  VAR_TYPE_8 shIn_log_mini_shift_amount_table[shuffleLimit] = {0, 0, 0, 0};
  VAR_TYPE_8 shIn_log_shift_jump_table[shuffleLimit] = {1, 0, 0, 2};

  VAR_TYPE_16 shBuf_log_shift_freq_table[shuffleLimit] = {0, 2, 5, 8};
  VAR_TYPE_16 shBuf_log_mini_shift_reset_freq_table[shuffleLimit] = {0, 0, 0, 2};
  VAR_TYPE_16 shBuf_log_mini_shift_amount_table[shuffleLimit] = {0, 0, 0, 0};
  VAR_TYPE_16 shBuf_log_max_buf_offset_table[shuffleLimit] = {3, 3, 3, 3};
  VAR_TYPE_16 shBuf_shift_counts_table[shuffleLimit] = {1, 0, 0, 0};
  VAR_TYPE_16 shBuf_poly_group_line_offset_num_line_table[shuffleLimit] = {8, 8, 8, 8};
  VAR_TYPE_16 shBuf_log_poly_group_total_num_line_table[shuffleLimit] = {2, 5, 8, 9};
  VAR_TYPE_16 shBuf_log_out_data_cycles_per_bufGrp_table[shuffleLimit] = {2, 5, 8, 9};
  VAR_TYPE_16 shBuf_total_lines_in_group_mask_table[shuffleLimit] = {7, 31, 255, 511};

  VAR_TYPE_8 shOut_log_shift_freq_table[shuffleLimit] = {0, 2, 5, 8};
  VAR_TYPE_8 shOut_log_mini_shift_reset_freq_table[shuffleLimit] = {0, 0, 0, 2};
  VAR_TYPE_8 shOut_log_mini_shift_amount_table[shuffleLimit] = {0, 0, 0, 0};
  VAR_TYPE_8 shOut_shift_counts_table[shuffleLimit] = {1, 0, 0, 0};

  #pragma HLS array_partition variable=shIn_log_shift_freq_table type=complete dim=1
  #pragma HLS array_partition variable=shIn_log_mini_shift_reset_freq_table type=complete dim=1
  #pragma HLS array_partition variable=shIn_log_mini_shift_amount_table type=complete dim=1
  #pragma HLS array_partition variable=shIn_log_shift_jump_table type=complete dim=1

  #pragma HLS array_partition variable=shBuf_log_shift_freq_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_log_mini_shift_reset_freq_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_log_mini_shift_amount_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_log_max_buf_offset_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_shift_counts_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_poly_group_line_offset_num_line_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_log_poly_group_total_num_line_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_log_out_data_cycles_per_bufGrp_table type=complete dim=1
  #pragma HLS array_partition variable=shBuf_total_lines_in_group_mask_table type=complete dim=1

  #pragma HLS array_partition variable=shOut_log_shift_freq_table type=complete dim=1
  #pragma HLS array_partition variable=shOut_log_mini_shift_reset_freq_table type=complete dim=1
  #pragma HLS array_partition variable=shOut_log_mini_shift_amount_table type=complete dim=1
  #pragma HLS array_partition variable=shOut_shift_counts_table type=complete dim=1
  //==== Auto generated variables end ====//

  VAR_TYPE_16 non_seq_idx[2*V_BUG_SIZE];
  WORD inValRegArr[2*V_BUG_SIZE];
  WORD shInBuf_RegArr[2*V_BUG_SIZE];
  WORD shBufShOut_RegArr[2*V_BUG_SIZE];
  WORD outValRegArr[2*V_BUG_SIZE];
  bool val_send_success[2*V_BUG_SIZE];
  VAR_TYPE_16 receiveCount[2];
  VAR_TYPE_16 sendCount[2];
  VAR_TYPE_8 shIn_mini_shift = 0;
  VAR_TYPE_8 shIn_major_shift = 0;
  VAR_TYPE_8 shIn_shift_amount = 0;
  VAR_TYPE_8 shOut_shift_amount = 0;
  VAR_TYPE_8 shOut_adjusted_shift_amount = 0;

  ITER_LOOP:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    
    for(VAR_TYPE_16 i=0; i<2; i++){
      #pragma HLS UNROLL
      receiveCount[i] = 0;
      sendCount[i] = 0;
    }

    for(VAR_TYPE_16 i=0; i<2*V_BUG_SIZE; i++){
      val_send_success[i] = false;
    }
    bool all_val_send_success = true;
    VAR_TYPE_16 seq_idx;

    VAR_TYPE_16 write_shuffler_id = 0;
    VAR_TYPE_16 read_shuffler_id = 0;
    VAR_TYPE_16 inv_write_shuffler_id = shuffleLimit - 1;
    VAR_TYPE_16 inv_read_shuffler_id = shuffleLimit - 1;
    VAR_TYPE_16 comp_write_shuffler_id = 0;
    VAR_TYPE_16 comp_read_shuffler_id = 0;

    VAR_TYPE_16 shuffleCount = 0;

    BUF_COMP:for(; shuffleCount<shuffleLimit ;){
      #pragma HLS PIPELINE II=1

      if(direction){
        comp_read_shuffler_id = read_shuffler_id;
        comp_write_shuffler_id = write_shuffler_id;
      }
      else{
        comp_read_shuffler_id = inv_read_shuffler_id;
        comp_write_shuffler_id = inv_write_shuffler_id;
      }

      VAR_TYPE_16 log_shift_freq;
      VAR_TYPE_16 log_mini_shift_reset_freq;
      VAR_TYPE_16 log_mini_shift_amount;
      VAR_TYPE_16 log_max_buf_offset;
      VAR_TYPE_16 shift_counts;
      VAR_TYPE_16 poly_group_line_offset_num_line;
      VAR_TYPE_16 log_poly_group_total_num_line;
      VAR_TYPE_16 log_out_data_cycles_per_bufGrp;
      VAR_TYPE_16 total_lines_in_group_mask;

      VAR_TYPE_16 seq_addr_shuffler_id;
      VAR_TYPE_16 non_seq_addr_shuffler_id;

      VAR_TYPE_16 seq_addr_count;
      VAR_TYPE_16 non_seq_addr_count;

      if( direction ){
        seq_addr_shuffler_id = comp_write_shuffler_id;
        non_seq_addr_shuffler_id = comp_read_shuffler_id;
      }
      else{
        seq_addr_shuffler_id = comp_read_shuffler_id;
        non_seq_addr_shuffler_id = comp_write_shuffler_id;
      }

      log_shift_freq = shBuf_log_shift_freq_table[non_seq_addr_shuffler_id];
      log_mini_shift_reset_freq = shBuf_log_mini_shift_reset_freq_table[non_seq_addr_shuffler_id];
      log_mini_shift_amount = shBuf_log_mini_shift_amount_table[non_seq_addr_shuffler_id];
      log_max_buf_offset = shBuf_log_max_buf_offset_table[non_seq_addr_shuffler_id];
      shift_counts = shBuf_shift_counts_table[non_seq_addr_shuffler_id];
      poly_group_line_offset_num_line = shBuf_poly_group_line_offset_num_line_table[non_seq_addr_shuffler_id];
      log_poly_group_total_num_line = shBuf_log_poly_group_total_num_line_table[non_seq_addr_shuffler_id];
      log_out_data_cycles_per_bufGrp = shBuf_log_out_data_cycles_per_bufGrp_table[non_seq_addr_shuffler_id];
      total_lines_in_group_mask = shBuf_total_lines_in_group_mask_table[non_seq_addr_shuffler_id];

      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){
        #pragma HLS UNROLL
        if( (direction) && ( !val_send_success[local_buf_id] ) && (!all_val_send_success) && ( fwd_outVal[local_buf_id].try_write(outValRegArr[local_buf_id]) ) ){
          val_send_success[local_buf_id] = true;
        }
        else if( (!direction) && ( !val_send_success[local_buf_id] ) && (!all_val_send_success) && ( inv_outVal[local_buf_id].try_write(outValRegArr[local_buf_id]) ) ){
          val_send_success[local_buf_id] = true;
        }
      }

      bool all_stream_send_success = val_send_success[0];
      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){
        #pragma HLS UNROLL
        all_stream_send_success &= val_send_success[local_buf_id];
      }

      if(all_stream_send_success && (!all_val_send_success)){
        sendCount[comp_read_shuffler_id%2]++;
        all_val_send_success = true;
      }

      if( direction ){
        seq_addr_count = receiveCount[comp_write_shuffler_id%2];
        non_seq_addr_count = sendCount[comp_read_shuffler_id%2];
      }
      else{
        seq_addr_count = sendCount[comp_read_shuffler_id%2];
        non_seq_addr_count = receiveCount[comp_write_shuffler_id%2];
      }

      VAR_TYPE_16 read_idx_poly_group_line_offset = ( ( non_seq_addr_count >> log_out_data_cycles_per_bufGrp) << (log_poly_group_total_num_line) ) & SINGLE_LIMB_BUF_SIZE_MASK;
      VAR_TYPE_16 cycle_start_idx_buffer_id = ( ( non_seq_addr_count >> (log_shift_freq - log_mini_shift_reset_freq) ) << (shift_counts + log_mini_shift_amount ) ) & ( (1<<log_max_buf_offset)-1 );
      VAR_TYPE_16 read_idx_iter_offset = ( non_seq_addr_count & ((1<<(log_shift_freq - log_mini_shift_reset_freq)) - 1) ) << log_mini_shift_reset_freq;
      VAR_TYPE_16 index_offset_based_on_strat_buffer = (poly_group_line_offset_num_line - cycle_start_idx_buffer_id);

      seq_idx = (seq_addr_shuffler_id%2)*(SINGLE_LIMB_BUF_SIZE) +  seq_addr_count;

      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){
        #pragma HLS UNROLL
        non_seq_idx[local_buf_id] = (non_seq_addr_shuffler_id%2)*(SINGLE_LIMB_BUF_SIZE) + \
                (read_idx_poly_group_line_offset) + \
                ( ( ( ( ( (local_buf_id + index_offset_based_on_strat_buffer) % (V_BUG_SIZE*2) ) >> (shift_counts + log_mini_shift_reset_freq + log_mini_shift_amount)) << log_shift_freq ) + \
                ( ( ( ( local_buf_id + index_offset_based_on_strat_buffer ) % (V_BUG_SIZE*2)) & ( ( 1 << (log_mini_shift_reset_freq + log_mini_shift_amount) ) -1 ) ) >> (log_mini_shift_amount) ) ) & total_lines_in_group_mask ) + \
                (read_idx_iter_offset);
      }

      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){
        #pragma HLS UNROLL
        if(direction){
          shBufShOut_RegArr[local_buf_id] = poly_buf[local_buf_id][non_seq_idx[local_buf_id]];
        }
        else{
          shBufShOut_RegArr[local_buf_id] = poly_buf[local_buf_id][seq_idx];
        }
      }

      VAR_TYPE_16 shOut_log_shift_freq = shOut_log_shift_freq_table[non_seq_addr_shuffler_id];
      VAR_TYPE_16 shOut_log_mini_shift_reset_freq = shOut_log_mini_shift_reset_freq_table[non_seq_addr_shuffler_id];
      VAR_TYPE_16 shOut_log_mini_shift_amount = shOut_log_mini_shift_amount_table[non_seq_addr_shuffler_id];
      VAR_TYPE_16 shOut_shift_counts = shOut_shift_counts_table[non_seq_addr_shuffler_id];

      VAR_TYPE_8 shIn_log_shift_freq = shIn_log_shift_freq_table[seq_addr_shuffler_id];
      VAR_TYPE_8 shIn_log_mini_shift_reset_freq = shIn_log_mini_shift_reset_freq_table[seq_addr_shuffler_id];
      VAR_TYPE_8 shIn_log_shift_jump = shIn_log_shift_jump_table[seq_addr_shuffler_id];
      VAR_TYPE_8 shIn_log_mini_shift_amount = shIn_log_mini_shift_amount_table[seq_addr_shuffler_id];

      //Out shuffle
      shOut_shift_amount = ( ( non_seq_addr_count & ( (1<<(shOut_log_shift_freq-shOut_log_mini_shift_reset_freq)) - 1 ) ) == 0) ? ( ( max_data_offset - (((non_seq_addr_count >> (shOut_log_shift_freq-shOut_log_mini_shift_reset_freq)) << (shOut_shift_counts + shOut_log_mini_shift_amount)) % (max_data_offset)) ) % (max_data_offset) ) : (shOut_shift_amount);

      //shuffle In process
      shIn_major_shift = ( ( seq_addr_count & ( (1<<shIn_log_shift_freq) - 1 ) ) == 0) ? (((seq_addr_count >> shIn_log_shift_freq) << shIn_log_shift_jump) % (max_data_offset)) : (shIn_major_shift);
      shIn_mini_shift = ( ( seq_addr_count & ( (1<<shIn_log_mini_shift_reset_freq) - 1 ) ) == 0 ) ? (0) : ( ( seq_addr_count & ( (1<<shIn_log_mini_shift_reset_freq) - 1 ) ) << shIn_log_mini_shift_amount );

      if(direction){
        shOut_adjusted_shift_amount = shOut_shift_amount;
        shIn_shift_amount = shIn_major_shift + shIn_mini_shift;
      }
      else{
        shOut_adjusted_shift_amount = (max_data_offset - (shIn_major_shift + shIn_mini_shift))%max_data_offset;
        shIn_shift_amount = ( max_data_offset - shOut_shift_amount ) % max_data_offset;
      }

      for(VAR_TYPE_16 j=0; j<V_BUG_SIZE*2; j++){
        #pragma HLS UNROLL
        outValRegArr[(j+shOut_adjusted_shift_amount)%max_data_offset] = shBufShOut_RegArr[j];
      }   

      if( all_val_send_success && ( (receiveCount[comp_read_shuffler_id%2] >> log_poly_group_total_num_line) > (sendCount[comp_read_shuffler_id%2] >> log_poly_group_total_num_line) ) ){
        all_val_send_success = false;
        for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){
          #pragma HLS UNROLL
          val_send_success[local_buf_id] = false;
        }
      }

      if(sendCount[comp_read_shuffler_id%2]==dataCount){
        sendCount[comp_read_shuffler_id%2] = 0;
        receiveCount[comp_read_shuffler_id%2] = 0;
        read_shuffler_id++;
        inv_read_shuffler_id--;
        shuffleCount++;
      }

      //receive
      bool inFifoNotEmpty = ( !fwd_inVal[0].empty() ) || ( !inv_inVal[0].empty() ) ;

      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){
        #pragma HLS UNROLL
        inFifoNotEmpty &= ( !fwd_inVal[local_buf_id].empty() ) || ( !inv_inVal[local_buf_id].empty() ) ;
      }

      if(inFifoNotEmpty){
        for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
          #pragma HLS UNROLL
          if(direction){
            inValRegArr[j] = fwd_inVal[j].read();
          }
          else{
            inValRegArr[j] = inv_inVal[j].read();
          }
        }

        //one cycle only shift
        for(VAR_TYPE_16 j=0; j<V_BUG_SIZE*2; j++){
          #pragma HLS UNROLL
          shInBuf_RegArr[(j+shIn_shift_amount)%max_data_offset] = inValRegArr[j];
        }

        for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){
          #pragma HLS UNROLL
            if(direction){
              poly_buf[local_buf_id][seq_idx] = shInBuf_RegArr[local_buf_id];
            }
            else{
              poly_buf[local_buf_id][non_seq_idx[local_buf_id]] = shInBuf_RegArr[local_buf_id];
            }
        }
        receiveCount[comp_write_shuffler_id%2]++;
      }

      if( receiveCount[comp_write_shuffler_id%2] == dataCount ){ //received all the data in this iteration
        write_shuffler_id++;
        inv_write_shuffler_id = (inv_write_shuffler_id==0) ? (0) : inv_write_shuffler_id-1;
      }
    }
  }
}

void shuffler_out_split(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal,
                        tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal_inter_0,
                        tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal_intra,
                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal_inter_0,
                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal_intra,
                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal,
                        bool direction,
                        VAR_TYPE_16 iter,
                        VAR_TYPE_16 task_id){
  
  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_8 shuffleLimit = (VAR_TYPE_8)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;
  VAR_TYPE_8 max_data_offset = (V_BUG_SIZE*2);

  WORD inValRegArr[2*V_BUG_SIZE];
  WORD outValRegArr[2*V_BUG_SIZE];

  bool inpStreamNotEmpty;
  VAR_TYPE_8 comp_shuffler_id;
  VAR_TYPE_8 shift_amount = 0;
  VAR_TYPE_8 adjusted_shift_amount = 0;

  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    for(VAR_TYPE_8 shuffler_id=0, inv_shuffler_id=shuffleLimit-1; shuffler_id<shuffleLimit; shuffler_id++, inv_shuffler_id--){
      OUT_SHUF_COMP:for(VAR_TYPE_16 i=0; i<dataCount;){
        #pragma HLS PIPELINE II = 1

        if(direction){
          comp_shuffler_id = shuffler_id;
        }
        else{
          comp_shuffler_id = inv_shuffler_id;
        }

        //read data from in stream
        inpStreamNotEmpty = ( !fwd_inVal[0].empty() ) || ( !inv_inVal_inter_0[0].empty() ) || ( !inv_inVal_intra[0].empty() );
        for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){
          inpStreamNotEmpty &= ( !fwd_inVal[j].empty() ) || ( !inv_inVal_inter_0[j].empty() ) || ( !inv_inVal_intra[j].empty() );
        }

        if(inpStreamNotEmpty){

          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
            #pragma HLS UNROLL
            if(direction){
              inValRegArr[j] = fwd_inVal[j].read();
            }
            else{
              if(comp_shuffler_id==0){
                inValRegArr[j] = inv_inVal_inter_0[j].read();
              }
              else{
                inValRegArr[j] = inv_inVal_intra[j].read();
              }
            }
          }

          //forward
          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
            #pragma HLS UNROLL
            outValRegArr[j] = inValRegArr[j];
          }

          //write data to out stream
          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
            #pragma HLS UNROLL
            if(direction){
              if(comp_shuffler_id==0){
                fwd_outVal_inter_0[j].write(outValRegArr[j]);
              }
              else{
                fwd_outVal_intra[j].write(outValRegArr[j]);
              }
            }
            else{
              inv_outVal[j].write(outValRegArr[j]);
            }
          }
          i++;
        }
      }
    }
  }
}


void shuffler_out_shuff(
                  tapa::istream<WORD>& fwd_inVal_inter0_0,
                  tapa::istream<WORD>& fwd_inVal_inter0_1,
                  tapa::istream<WORD>& fwd_inVal_inter0_2,
                  tapa::istream<WORD>& fwd_inVal_inter0_3,
                  tapa::istream<WORD>& fwd_inVal_inter0_4,
                  tapa::istream<WORD>& fwd_inVal_inter0_5,
                  tapa::istream<WORD>& fwd_inVal_inter0_6,
                  tapa::istream<WORD>& fwd_inVal_inter0_7,
                  tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal_intra,
                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal_intra,
                  tapa::ostream<WORD>& inv_outVal_inter0_0,
                  tapa::ostream<WORD>& inv_outVal_inter0_1,
                  tapa::ostream<WORD>& inv_outVal_inter0_2,
                  tapa::ostream<WORD>& inv_outVal_inter0_3,
                  tapa::ostream<WORD>& inv_outVal_inter0_4,
                  tapa::ostream<WORD>& inv_outVal_inter0_5,
                  tapa::ostream<WORD>& inv_outVal_inter0_6,
                  tapa::ostream<WORD>& inv_outVal_inter0_7,
                    bool direction,
                   VAR_TYPE_16 iter
                    ){
  
  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_8 shuffleLimit = ( (VAR_TYPE_32)(logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;

  WORD inValRegArr[V_TOTAL_DATA];
  WORD outValRegArr[V_TOTAL_DATA];

  bool inpStreamNotEmpty;
  VAR_TYPE_8 comp_shuffler_id = 0;

  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    for(VAR_TYPE_8 shuffler_id=0, inv_shuffler_id=shuffleLimit-1; shuffler_id<shuffleLimit; shuffler_id++, inv_shuffler_id--){

      if(direction){
        comp_shuffler_id = shuffler_id;
      }
      else{
        comp_shuffler_id = inv_shuffler_id;
      }

      OUT_SHUF_COMP:for(VAR_TYPE_16 i=0; i<dataCount;){
        #pragma HLS PIPELINE II = 1

        //read data from in stream
        if(direction && (comp_shuffler_id==0)){
          inpStreamNotEmpty = !fwd_inVal_inter0_0.empty();
          inpStreamNotEmpty &= !fwd_inVal_inter0_1.empty();
          inpStreamNotEmpty &= !fwd_inVal_inter0_2.empty();
          inpStreamNotEmpty &= !fwd_inVal_inter0_3.empty();
          inpStreamNotEmpty &= !fwd_inVal_inter0_4.empty();
          inpStreamNotEmpty &= !fwd_inVal_inter0_5.empty();
          inpStreamNotEmpty &= !fwd_inVal_inter0_6.empty();
          inpStreamNotEmpty &= !fwd_inVal_inter0_7.empty();

          if(inpStreamNotEmpty){
            inValRegArr[0] = fwd_inVal_inter0_0.read();
            inValRegArr[1] = fwd_inVal_inter0_1.read();
            inValRegArr[2] = fwd_inVal_inter0_2.read();
            inValRegArr[3] = fwd_inVal_inter0_3.read();
            inValRegArr[4] = fwd_inVal_inter0_4.read();
            inValRegArr[5] = fwd_inVal_inter0_5.read();
            inValRegArr[6] = fwd_inVal_inter0_6.read();
            inValRegArr[7] = fwd_inVal_inter0_7.read();
          }

        }
        else if( (direction) ){
          inpStreamNotEmpty = !fwd_inVal_intra[0].empty();

          for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){
            inpStreamNotEmpty &= !fwd_inVal_intra[j].empty();
          }

          if(inpStreamNotEmpty){
            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
              inValRegArr[j] = fwd_inVal_intra[j].read();
            }
          }
        }
        else{
          inpStreamNotEmpty = !inv_inVal[0].empty();

          for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){
            inpStreamNotEmpty &= !inv_inVal[j].empty();
          }

          if(inpStreamNotEmpty){
            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
              inValRegArr[j] = inv_inVal[j].read();
            }
          }
        }

        if(inpStreamNotEmpty){

          //Handle partial BUG
          if( (direction) && (comp_shuffler_id==(shuffleLimit-1)) ){
            outValRegArr[0] = inValRegArr[0];
            outValRegArr[2] = inValRegArr[1];
            outValRegArr[4] = inValRegArr[2];
            outValRegArr[6] = inValRegArr[3];
            outValRegArr[1] = inValRegArr[4];
            outValRegArr[3] = inValRegArr[5];
            outValRegArr[5] = inValRegArr[6];
            outValRegArr[7] = inValRegArr[7];
          }
          else if( (!direction) && (comp_shuffler_id==(shuffleLimit-1)) ){
            outValRegArr[0] = inValRegArr[0];
            outValRegArr[1] = inValRegArr[2];
            outValRegArr[2] = inValRegArr[4];
            outValRegArr[3] = inValRegArr[6];
            outValRegArr[4] = inValRegArr[1];
            outValRegArr[5] = inValRegArr[3];
            outValRegArr[6] = inValRegArr[5];
            outValRegArr[7] = inValRegArr[7];
          }
          else{
            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
              outValRegArr[j] = inValRegArr[j];
            }
          }

          //write data to out stream
          if(direction){
            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
              #pragma HLS UNROLL
              fwd_outVal[j].write(outValRegArr[j]);
            }
          }
          else{
            if(comp_shuffler_id==0){
              inv_outVal_inter0_0.write(outValRegArr[0]);
              inv_outVal_inter0_1.write(outValRegArr[1]);
              inv_outVal_inter0_2.write(outValRegArr[2]);
              inv_outVal_inter0_3.write(outValRegArr[3]);
              inv_outVal_inter0_4.write(outValRegArr[4]);
              inv_outVal_inter0_5.write(outValRegArr[5]);
              inv_outVal_inter0_6.write(outValRegArr[6]);
              inv_outVal_inter0_7.write(outValRegArr[7]);
            }
            else{
              for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
                #pragma HLS UNROLL
                inv_outVal_intra[j].write(outValRegArr[j]);
              }
            }
          }
          i++;
        }
      }
    }
  }
}


// /********************************************************************************************
// * TF buffer tasks *
// ********************************************************************************************/

void TFBuf_loadTF_wiFW(
           tapa::istream<DWORD>& loadTFStream,
           tapa::ostream<DWORD>& loadTFToNext,
           WORD TFArr[N/2],
           VAR_TYPE_16 tf_load_counter, 
           VAR_TYPE_16 this_buf_limit){

  #pragma HLS inline off

  //load
  TF_LOAD:for(VAR_TYPE_16 i=0; i<tf_load_counter;){
    #pragma HLS PIPELINE II = 1

    bool inpStreamNotEmpty = !loadTFStream.empty();

    if(inpStreamNotEmpty){
      if(i<this_buf_limit){
        DWORD val = loadTFStream.read();   
        TFArr[2*i] = (WORD)(val & ((((DWORD)1) << WORD_SIZE) - 1));
        TFArr[2*i+1] = (WORD)(val >> WORD_SIZE);
      }
      else{
        loadTFToNext.write((loadTFStream.read()));
      }
      i++;
    }
  }
}

void TFBuf_loadTF_woFW(
           tapa::istream<DWORD>& loadTFStream,
           WORD TFArr[N/2],
           VAR_TYPE_16 tf_load_counter){
  
  #pragma HLS inline off

  //load
  TF_LOAD:for(VAR_TYPE_16 i=0; i<tf_load_counter;){
    #pragma HLS PIPELINE II = 1

    bool inpStreamNotEmpty = !loadTFStream.empty();

    if(inpStreamNotEmpty){
      DWORD val = loadTFStream.read();   
      TFArr[2*i] = (WORD)(val & ((((DWORD)1) << WORD_SIZE) - 1));
      TFArr[2*i+1] = (WORD)(val >> WORD_SIZE);
      i++;
    }
  }
}

void TFBuf_comp(
           tapa::ostream<WORD>& tfToBu_0,
           tapa::ostream<WORD>& tfToBu_1,
           WORD TFArr[N/2],
           const VAR_TYPE_16 fwd_log_stageWiseTFs[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )],
           const VAR_TYPE_16 inv_log_stageWiseTFs[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )],
           const VAR_TYPE_16 fwd_stageWiseOffset[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )],
           const VAR_TYPE_16 inv_stageWiseOffset[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )],
           const VAR_TYPE_16 fwd_log_num_val_accessed_by_consec_BUs_arr[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )],
           const VAR_TYPE_16 inv_log_num_val_accessed_by_consec_BUs_arr[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )],
           VAR_TYPE_8 unit_id_0,
           VAR_TYPE_8 unit_id_1,
           VAR_TYPE_16 dataCount,
           VAR_TYPE_8 dataFlowIterLimit,
           bool direction){
  
  #pragma HLS inline off

  TF_DF_ITER:for(VAR_TYPE_8 dataFlowIter = 0; dataFlowIter<dataFlowIterLimit; dataFlowIter++){
      
    VAR_TYPE_16 log_num_TFs;
    VAR_TYPE_16 tf_offset;
    VAR_TYPE_16 log_num_val_accessed_by_consec_BUs;
    VAR_TYPE_16 log_countLimit;

    if(direction){
      log_num_TFs = fwd_log_stageWiseTFs[dataFlowIter];
      tf_offset = fwd_stageWiseOffset[dataFlowIter];
      log_num_val_accessed_by_consec_BUs = fwd_log_num_val_accessed_by_consec_BUs_arr[dataFlowIter];
      log_countLimit = log_num_TFs - log_num_val_accessed_by_consec_BUs;
    }
    else{
      log_num_TFs = inv_log_stageWiseTFs[dataFlowIter];
      tf_offset = inv_stageWiseOffset[dataFlowIter];
      log_num_val_accessed_by_consec_BUs = inv_log_num_val_accessed_by_consec_BUs_arr[dataFlowIter];
      log_countLimit = (logN - log_V_TOTAL_DATA) - (log_num_TFs - log_num_val_accessed_by_consec_BUs);
    }

    TF_COMP:for(VAR_TYPE_16 inpCount=0; inpCount<dataCount; inpCount++){
      #pragma HLS PIPELINE II = 1
      
      VAR_TYPE_16 tf_idx_0;
      VAR_TYPE_16 tf_idx_1;
      if(direction){
        tf_idx_0 = tf_offset + (inpCount & ( (1<<log_countLimit)-1 ) ) + ( (unit_id_0 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 )) << (log_countLimit) );
        tf_idx_1 = tf_offset + (inpCount & ( (1<<log_countLimit)-1 ) ) + ( (unit_id_1 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 )) << (log_countLimit) );
      }
      else{
        tf_idx_0 = tf_offset + ( (inpCount >> (log_countLimit) ) << log_num_val_accessed_by_consec_BUs ) + (unit_id_0 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 ));
        tf_idx_1 = tf_offset + ( (inpCount >> (log_countLimit) ) << log_num_val_accessed_by_consec_BUs ) + (unit_id_1 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 ));
      }
    
      WORD tfVal_0 = TFArr[tf_idx_0];
      WORD tfVal_1 = TFArr[tf_idx_1];

      tfToBu_0.write(tfVal_0);
      tfToBu_1.write(tfVal_1);

    }

  }
}

void TFBuf_wiFW_0(
           tapa::istream<DWORD>& loadTFStream,
           tapa::ostream<DWORD>& loadTFToNext,
           tapa::ostream<WORD>& tfToBu_0,
           tapa::ostream<WORD>& tfToBu_1,
           bool direction,
           VAR_TYPE_8 BUG_id,
           VAR_TYPE_8 TFGen_offset, 
           VAR_TYPE_8 unit_id,
           VAR_TYPE_16 iter){
  
  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_8 dataFlowIterLimit = (VAR_TYPE_8)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE );

  //==== Auto generated variables start ====//
  const VAR_TYPE_16 TFArr_size = 1318;
  const VAR_TYPE_16 fwd_tf_load_counter = 1245;
  const VAR_TYPE_16 inv_tf_load_counter = 1317;
  const VAR_TYPE_16 fwd_this_buf_limit = 659;
  const VAR_TYPE_16 inv_this_buf_limit = 659;

  const VAR_TYPE_16 fwd_log_stageWiseTFs[dataFlowIterLimit] = {0, 2, 5, 8, 10};
  const VAR_TYPE_16 inv_log_stageWiseTFs[dataFlowIterLimit] = {0, 2, 5, 8, 10};
  const VAR_TYPE_16 fwd_stageWiseOffset[dataFlowIterLimit] = {0, 1, 5, 37, 293};
  const VAR_TYPE_16 inv_stageWiseOffset[dataFlowIterLimit] = {0, 1, 5, 37, 293};
  const VAR_TYPE_16 fwd_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = {0, 0, 0, 0, 1};
  const VAR_TYPE_16 inv_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = {0, 1, 1, 1, 1};
  //==== Auto generated variables end ====//
  
  const VAR_TYPE_16 tf_load_counter = (direction) ? (fwd_tf_load_counter) : (inv_tf_load_counter);
  const VAR_TYPE_16 this_buf_limit = (direction) ? (fwd_this_buf_limit) : (inv_this_buf_limit);

  WORD TFArr[2][TFArr_size];
  #pragma HLS bind_storage variable=TFArr type=RAM_T2P impl=uram latency=1
  #pragma HLS array_partition variable=TFArr type=complete dim=1

  VAR_TYPE_8 unit_id_0 = 2*unit_id;
  VAR_TYPE_8 unit_id_1 = 2*unit_id+1;

  TF_ITER:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    TFBuf_loadTF_wiFW(loadTFStream, loadTFToNext, TFArr[iterCount%2], tf_load_counter, this_buf_limit);
    TFBuf_comp(tfToBu_0, tfToBu_1, TFArr[(iterCount+1)%2], fwd_log_stageWiseTFs, inv_log_stageWiseTFs, fwd_stageWiseOffset, inv_stageWiseOffset, fwd_log_num_val_accessed_by_consec_BUs_arr, inv_log_num_val_accessed_by_consec_BUs_arr, unit_id_0, unit_id_1, dataCount, dataFlowIterLimit, direction);
  }
}    

void TFBuf_wiFW_1(
           tapa::istream<DWORD>& loadTFStream,
           tapa::ostream<DWORD>& loadTFToNext,
           tapa::ostream<WORD>& tfToBu_0,
           tapa::ostream<WORD>& tfToBu_1,
           bool direction,
           VAR_TYPE_8 BUG_id,
           VAR_TYPE_8 TFGen_offset, 
           VAR_TYPE_8 unit_id,
           VAR_TYPE_16 iter){
  
  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_8 dataFlowIterLimit = (VAR_TYPE_8)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE );

  //==== Auto generated variables start ====//
  const VAR_TYPE_16 TFArr_size = 658;
  const VAR_TYPE_16 fwd_tf_load_counter = 586;
  const VAR_TYPE_16 inv_tf_load_counter = 658;
  const VAR_TYPE_16 fwd_this_buf_limit = 293;
  const VAR_TYPE_16 inv_this_buf_limit = 329;

  const VAR_TYPE_16 fwd_log_stageWiseTFs[dataFlowIterLimit] = {1, 3, 6, 9, 1};
  const VAR_TYPE_16 inv_log_stageWiseTFs[dataFlowIterLimit] = {1, 1, 4, 7, 9};
  const VAR_TYPE_16 fwd_stageWiseOffset[dataFlowIterLimit] = {0, 2, 10, 74, 586};
  const VAR_TYPE_16 inv_stageWiseOffset[dataFlowIterLimit] = {0, 0, 2, 18, 146};
  const VAR_TYPE_16 fwd_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = {1, 1, 1, 1, 0};
  const VAR_TYPE_16 inv_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = {0, 0, 0, 0, 0};
  //==== Auto generated variables end ====//
  
  const VAR_TYPE_16 tf_load_counter = (direction) ? (fwd_tf_load_counter) : (inv_tf_load_counter);
  const VAR_TYPE_16 this_buf_limit = (direction) ? (fwd_this_buf_limit) : (inv_this_buf_limit);

  WORD TFArr[2][TFArr_size];
  #pragma HLS bind_storage variable=TFArr type=RAM_T2P impl=uram latency=1
  #pragma HLS array_partition variable=TFArr type=complete dim=1

  VAR_TYPE_8 unit_id_0 = 2*unit_id;
  VAR_TYPE_8 unit_id_1 = 2*unit_id+1;

  TF_ITER:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    TFBuf_loadTF_wiFW(loadTFStream, loadTFToNext, TFArr[iterCount%2], tf_load_counter, this_buf_limit);
    TFBuf_comp(tfToBu_0, tfToBu_1, TFArr[(iterCount+1)%2], fwd_log_stageWiseTFs, inv_log_stageWiseTFs, fwd_stageWiseOffset, inv_stageWiseOffset, fwd_log_num_val_accessed_by_consec_BUs_arr, inv_log_num_val_accessed_by_consec_BUs_arr, unit_id_0, unit_id_1, dataCount, dataFlowIterLimit, direction);
  }
}    

void TFBuf_woFW_2(
           tapa::istream<DWORD>& loadTFStream,
           tapa::ostream<WORD>& tfToBu_0,
           tapa::ostream<WORD>& tfToBu_1,
           bool direction,
           VAR_TYPE_8 BUG_id,
           VAR_TYPE_8 TFGen_offset, 
           VAR_TYPE_8 unit_id,
           VAR_TYPE_16 iter){
  
  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_8 dataFlowIterLimit = (VAR_TYPE_8)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE );

  //==== Auto generated variables start ====//
  const VAR_TYPE_16 TFArr_size = 658;
  const VAR_TYPE_16 fwd_tf_load_counter = 293;
  const VAR_TYPE_16 inv_tf_load_counter = 329;
  const VAR_TYPE_16 fwd_this_buf_limit = 293;
  const VAR_TYPE_16 inv_this_buf_limit = 329;

  const VAR_TYPE_16 fwd_log_stageWiseTFs[dataFlowIterLimit] = {1, 3, 6, 9, 1};
  const VAR_TYPE_16 inv_log_stageWiseTFs[dataFlowIterLimit] = {1, 1, 4, 7, 9};
  const VAR_TYPE_16 fwd_stageWiseOffset[dataFlowIterLimit] = {0, 2, 10, 74, 586};
  const VAR_TYPE_16 inv_stageWiseOffset[dataFlowIterLimit] = {0, 0, 2, 18, 146};
  const VAR_TYPE_16 fwd_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = {1, 1, 1, 1, 0};
  const VAR_TYPE_16 inv_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = {0, 0, 0, 0, 0};
  //==== Auto generated variables end ====//
  
  const VAR_TYPE_16 tf_load_counter = (direction) ? (fwd_tf_load_counter) : (inv_tf_load_counter);
  const VAR_TYPE_16 this_buf_limit = (direction) ? (fwd_this_buf_limit) : (inv_this_buf_limit);

  WORD TFArr[2][TFArr_size];
  #pragma HLS bind_storage variable=TFArr type=RAM_T2P impl=uram latency=1
  #pragma HLS array_partition variable=TFArr type=complete dim=1

  VAR_TYPE_8 unit_id_0 = 2*unit_id;
  VAR_TYPE_8 unit_id_1 = 2*unit_id+1;

  //comp
  TF_ITER:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    TFBuf_loadTF_woFW(loadTFStream, TFArr[iterCount%2], tf_load_counter);
    TFBuf_comp(tfToBu_0, tfToBu_1, TFArr[(iterCount+1)%2], fwd_log_stageWiseTFs, inv_log_stageWiseTFs, fwd_stageWiseOffset, inv_stageWiseOffset, fwd_log_num_val_accessed_by_consec_BUs_arr, inv_log_num_val_accessed_by_consec_BUs_arr, unit_id_0, unit_id_1, dataCount, dataFlowIterLimit, direction);
  }
}


// /********************************************************************************************
// * Input/Output selector tasks *
// ********************************************************************************************/

void input_selector(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_valFromLoad,
                   tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_valFromShuf,
                   tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_valFromBU,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_valToBU,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_valToShuf,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_valToStore,
                  bool direction,
                  VAR_TYPE_16 iter,
                  VAR_TYPE_16 task_id){


  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_8 dataFlowIterLimit = (VAR_TYPE_32)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE );
  
  WORD val;

  bool inpStreamNotEmpty;
  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    for(VAR_TYPE_8 dataFlowIter=0; dataFlowIter<dataFlowIterLimit; dataFlowIter++){
      for(VAR_TYPE_16 i=0; i<dataCount;){
        #pragma HLS PIPELINE II = 1
        if(direction){
          if(dataFlowIter==0){
            inpStreamNotEmpty = !fwd_valFromLoad[0].empty();
          }
          else{
            inpStreamNotEmpty = !fwd_valFromShuf[0].empty();
          }
          for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){
            #pragma HLS UNROLL
            if(dataFlowIter==0){
              inpStreamNotEmpty &= !fwd_valFromLoad[j].empty();
            }
            else{
              inpStreamNotEmpty &= !fwd_valFromShuf[j].empty();
            }
          }
          if( inpStreamNotEmpty ){
            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
              #pragma HLS UNROLL
              if(dataFlowIter==0){
                val = fwd_valFromLoad[j].read();
              }
              else{
                val = fwd_valFromShuf[j].read();
              }
              fwd_valToBU[j].write(val);
            }
            i++;
          }
        }
        else{
          inpStreamNotEmpty = !inv_valFromBU[0].empty();
          for(VAR_TYPE_32 j=1; j<2*V_BUG_SIZE; j++){
            inpStreamNotEmpty &= !inv_valFromBU[j].empty();
          }
          if(inpStreamNotEmpty){
            for(VAR_TYPE_32 j=0; j<2*V_BUG_SIZE; j++){
              if( dataFlowIter == (dataFlowIterLimit-1) ){
                inv_valToStore[j].write(inv_valFromBU[j].read());
              }
              else{
                inv_valToShuf[j].write(inv_valFromBU[j].read());
              }
            }
            i++;
          }
        }
      }
    }
  }
}
void output_slector(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_valFromBU,
                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_valFromLoad,
                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_valFromShuf,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_valToShuf,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_valToStore,
                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_valToBU,
                  bool direction,
                  VAR_TYPE_16 iter,
                  VAR_TYPE_16 task_id){


  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));
  const VAR_TYPE_8 dataFlowIterLimit = (VAR_TYPE_32)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE );
  WORD val;

  bool inpStreamNotEmpty;
  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){
    for(VAR_TYPE_8 dataFlowIter=0; dataFlowIter<dataFlowIterLimit; dataFlowIter++){
      for(VAR_TYPE_16 i=0; i<dataCount;){
        #pragma HLS PIPELINE II = 1
        if(direction){
          inpStreamNotEmpty = !fwd_valFromBU[0].empty();
          for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){
            inpStreamNotEmpty &= !fwd_valFromBU[j].empty();
          }
          if(inpStreamNotEmpty){
            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
              #pragma HLS UNROLL
              val = fwd_valFromBU[j].read();
              if( dataFlowIter == (dataFlowIterLimit-1) ){
                fwd_valToStore[j].write(val);
              }
              else{
                fwd_valToShuf[j].write(val);
              }
            }
            i++;
          }
        }
        else{
          if(dataFlowIter==0){
            inpStreamNotEmpty = !inv_valFromLoad[0].empty();
            for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){
              inpStreamNotEmpty &= !inv_valFromLoad[j].empty();
            }
          }
          else{
            inpStreamNotEmpty = !inv_valFromShuf[0].empty();
            for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){
              inpStreamNotEmpty &= !inv_valFromShuf[j].empty();
            }
          }
          if( inpStreamNotEmpty ){
            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){
              if(dataFlowIter==0){
                WORD temp_val = inv_valFromLoad[j].read();
                inv_valToBU[j].write(temp_val);
              }
              else{
                inv_valToBU[j].write(inv_valFromShuf[j].read());
              }
            }
            i++;
          }
        }
      }
    }
  }
}

// /********************************************************************************************
// * Dual interface FIFO tasks *
// ********************************************************************************************/

void dual_interface_FIFO_receive(
                  tapa::istream<WORD>& fwd_inVal,
                  tapa::istream<WORD>& inv_inVal,
                  tapa::ostream<WORD>& common_outVal,
                  bool direction){
  
  bool inpStreamNotEmpty;
  for(;;){
    
    inpStreamNotEmpty = ( !fwd_inVal.empty() ) || ( !inv_inVal.empty() );

    if(inpStreamNotEmpty){
      if(direction){
        common_outVal.write(fwd_inVal.read());
      }
      else{
        common_outVal.write(inv_inVal.read());
      }
    }
  }
}

void dual_interface_FIFO_send(
                  tapa::istream<WORD>& common_inVal,
                  tapa::ostream<WORD>& fwd_outVal,
                  tapa::ostream<WORD>& inv_outVal,
                  bool direction){
  
  bool inpStreamNotEmpty;
  for(;;){
    
    inpStreamNotEmpty = !common_inVal.empty();

    if(inpStreamNotEmpty){
      if(direction){
        fwd_outVal.write(common_inVal.read());
      }
      else{
        inv_outVal.write(common_inVal.read());
      }
    }
  }
}

// /********************************************************************************************
// * Top kernel *
// ********************************************************************************************/

void NTT_kernel(
    tapa::mmap<POLY_WIDE_DATA> polyVectorInOut_G0,
    tapa::mmap<TF_WIDE_DATA> TFArr_G0,
    tapa::mmap<POLY_WIDE_DATA> polyVectorInOut_G1,
    WORD q0,
    WORD twoInverse0,
    WORD_PLUS3 factor0,
    bool direction,
    VAR_TYPE_16 iter
    )
{

    /* Limb0 */
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_load_to_DIF_L0_BUG0_0("fwd_poly_load_to_DIF_L0_BUG0_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_load_to_DIF_L0_BUG0_1("fwd_poly_load_to_DIF_L0_BUG0_1_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_DIF_to_store_L0_BUG0_0("inv_poly_DIF_to_store_L0_BUG0_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_DIF_to_store_L0_BUG0_1("inv_poly_DIF_to_store_L0_BUG0_1_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_load_to_DIF_L0_BUG1_0("fwd_poly_load_to_DIF_L0_BUG1_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_load_to_DIF_L0_BUG1_1("fwd_poly_load_to_DIF_L0_BUG1_1_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_DIF_to_store_L0_BUG1_0("inv_poly_DIF_to_store_L0_BUG1_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_DIF_to_store_L0_BUG1_1("inv_poly_DIF_to_store_L0_BUG1_1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE, LS_FIFO_BUF_SIZE> poly_inFIFO_L0_BUG0("poly_inFIFO_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE, LS_FIFO_BUF_SIZE> poly_inFIFO_L0_BUG1("poly_inFIFO_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_DIF_to_inSel_L0_BUG0("fwd_poly_DIF_to_inSel_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_DIF_to_inSel_L0_BUG1("fwd_poly_DIF_to_inSel_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_inSel_to_DIF_L0_BUG0("inv_poly_inSel_to_DIF_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_inSel_to_DIF_L0_BUG1("inv_poly_inSel_to_DIF_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_inSel_to_BUG_L0_BUG0("fwd_poly_inSel_to_BUG_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_inSel_to_BUG_L0_BUG1("fwd_poly_inSel_to_BUG_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_BUG_to_inSel_L0_BUG0("inv_poly_BUG_to_inSel_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_BUG_to_inSel_L0_BUG1("inv_poly_BUG_to_inSel_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_H0_to_H1_L0_BUG0("fwd_poly_H0_to_H1_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_H0_to_H1_L0_BUG1("fwd_poly_H0_to_H1_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_H1_to_H0_L0_BUG0("inv_poly_H1_to_H0_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_H1_to_H0_L0_BUG1("inv_poly_H1_to_H0_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_H1_to_H2_L0_BUG0("fwd_poly_H1_to_H2_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_H1_to_H2_L0_BUG1("fwd_poly_H1_to_H2_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_H2_to_H1_L0_BUG0("inv_poly_H2_to_H1_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_H2_to_H1_L0_BUG1("inv_poly_H2_to_H1_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_BUG_to_outSel_L0_BUG0("fwd_poly_BUG_to_outSel_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_BUG_to_outSel_L0_BUG1("fwd_poly_BUG_to_outSel_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_outSel_to_BUG_L0_BUG0("inv_poly_outSel_to_BUG_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_outSel_to_BUG_L0_BUG1("inv_poly_outSel_to_BUG_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_outSel_to_shuf_L0_BUG0("fwd_poly_outSel_to_shuf_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_outSel_to_shuf_L0_BUG1("fwd_poly_outSel_to_shuf_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shuf_to_outSel_L0_BUG0("inv_poly_shuf_to_outSel_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shuf_to_outSel_L0_BUG1("inv_poly_shuf_to_outSel_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shuf_to_shufOutSplit_L0_BUG0("fwd_poly_shuf_to_shufOutSplit_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shuf_to_shufOutSplit_L0_BUG1("fwd_poly_shuf_to_shufOutSplit_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shufOutSplit_to_shuf_L0_BUG0("inv_poly_shufOutSplit_to_shuf_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shufOutSplit_to_shuf_L0_BUG1("inv_poly_shufOutSplit_to_shuf_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0("fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1("fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0("inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1("inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG0("fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG1("fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG0("inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG1("inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shufOutShuff_to_inSel_L0_BUG0("fwd_poly_shufOutShuff_to_inSel_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_shufOutShuff_to_inSel_L0_BUG1("fwd_poly_shufOutShuff_to_inSel_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_inSel_to_shufOutShuff_L0_BUG0("inv_poly_inSel_to_shufOutShuff_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_inSel_to_shufOutShuff_L0_BUG1("inv_poly_inSel_to_shufOutShuff_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_outSel_to_DIF_L0_BUG0("fwd_poly_outSel_to_DIF_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> fwd_poly_outSel_to_DIF_L0_BUG1("fwd_poly_outSel_to_DIF_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_DIF_to_outSel_L0_BUG0("inv_poly_DIF_to_outSel_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE> inv_poly_DIF_to_outSel_L0_BUG1("inv_poly_DIF_to_outSel_L0_BUG1_stream");

    tapa::streams<WORD, 2*V_BUG_SIZE, LS_FIFO_BUF_SIZE> poly_outFIFO_L0_BUG0("poly_outFIFO_L0_BUG0_stream");
    tapa::streams<WORD, 2*V_BUG_SIZE, LS_FIFO_BUF_SIZE> poly_outFIFO_L0_BUG1("poly_outFIFO_L0_BUG1_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_DIF_to_store_L0_BUG0_0("fwd_poly_DIF_to_store_L0_BUG0_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_DIF_to_store_L0_BUG0_1("fwd_poly_DIF_to_store_L0_BUG0_1_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_load_to_DIF_L0_BUG0_0("inv_poly_load_to_DIF_L0_BUG0_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_load_to_DIF_L0_BUG0_1("inv_poly_load_to_DIF_L0_BUG0_1_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_DIF_to_store_L0_BUG1_0("fwd_poly_DIF_to_store_L0_BUG1_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> fwd_poly_DIF_to_store_L0_BUG1_1("fwd_poly_DIF_to_store_L0_BUG1_1_stream");

    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_load_to_DIF_L0_BUG1_0("inv_poly_load_to_DIF_L0_BUG1_0_stream");
    tapa::streams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT> inv_poly_load_to_DIF_L0_BUG1_1("inv_poly_load_to_DIF_L0_BUG1_1_stream");

    tapa::streams<DWORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2> tf_load_to_TFBuf_L0_G0_0("tf_load_to_TFBuf_L0_G0_0_stream");
    tapa::streams<DWORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2> tf_load_to_TFBuf_L0_G0_1("tf_load_to_TFBuf_L0_G0_1_stream");
    tapa::streams<DWORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2> tf_load_to_TFBuf_L0_G0_2("tf_load_to_TFBuf_L0_G0_2_stream");

    tapa::streams<WORD, V_BUG_SIZE> tf_TFBuf_to_BUG_L0_BUG0_H0("tf_TFBuf_to_BUG_L0_BUG0_H0_stream");
    tapa::streams<WORD, V_BUG_SIZE> tf_TFBuf_to_BUG_L0_BUG0_H1("tf_TFBuf_to_BUG_L0_BUG0_H1_stream");
    tapa::streams<WORD, V_BUG_SIZE> tf_TFBuf_to_BUG_L0_BUG0_H2("tf_TFBuf_to_BUG_L0_BUG0_H2_stream");

    tapa::streams<WORD, V_BUG_SIZE> tf_TFBuf_to_BUG_L0_BUG1_H0("tf_TFBuf_to_BUG_L0_BUG1_H0_stream");
    tapa::streams<WORD, V_BUG_SIZE> tf_TFBuf_to_BUG_L0_BUG1_H1("tf_TFBuf_to_BUG_L0_BUG1_H1_stream");
    tapa::streams<WORD, V_BUG_SIZE> tf_TFBuf_to_BUG_L0_BUG1_H2("tf_TFBuf_to_BUG_L0_BUG1_H2_stream");

    tapa::task()
        //polynomial loading/storing tasks: FWD loading and INV storing
        .invoke(fwd_load_inv_store_poly_1_limbs, polyVectorInOut_G0, inv_poly_DIF_to_store_L0_BUG0_0, inv_poly_DIF_to_store_L0_BUG0_1, inv_poly_DIF_to_store_L0_BUG1_0, inv_poly_DIF_to_store_L0_BUG1_1, fwd_poly_load_to_DIF_L0_BUG0_0, fwd_poly_load_to_DIF_L0_BUG0_1, fwd_poly_load_to_DIF_L0_BUG1_0, fwd_poly_load_to_DIF_L0_BUG1_1, direction, iter)

        //polynomial loading/storing tasks: FWD storing and INV loading
        .invoke(fwd_store_inv_load_poly_1_limbs, polyVectorInOut_G1, fwd_poly_DIF_to_store_L0_BUG0_0, fwd_poly_DIF_to_store_L0_BUG0_1, fwd_poly_DIF_to_store_L0_BUG1_0, fwd_poly_DIF_to_store_L0_BUG1_1, inv_poly_load_to_DIF_L0_BUG0_0, inv_poly_load_to_DIF_L0_BUG0_1, inv_poly_load_to_DIF_L0_BUG1_0, inv_poly_load_to_DIF_L0_BUG1_1, direction, iter)

        //TF loading tasks
        .invoke(Mmap2Stream_tf_0_1_limbs, TFArr_G0, tf_load_to_TFBuf_L0_G0_0, direction, iter)

        /* Limb0 */
        //Dual Interface FIFO (DIF) tasks from FWD in side
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_0[0], inv_poly_inSel_to_DIF_L0_BUG0[0], poly_inFIFO_L0_BUG0[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_0[1], inv_poly_inSel_to_DIF_L0_BUG0[1], poly_inFIFO_L0_BUG0[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_0[2], inv_poly_inSel_to_DIF_L0_BUG0[2], poly_inFIFO_L0_BUG0[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_0[3], inv_poly_inSel_to_DIF_L0_BUG0[3], poly_inFIFO_L0_BUG0[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_1[0], inv_poly_inSel_to_DIF_L0_BUG0[4], poly_inFIFO_L0_BUG0[4], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_1[1], inv_poly_inSel_to_DIF_L0_BUG0[5], poly_inFIFO_L0_BUG0[5], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_1[2], inv_poly_inSel_to_DIF_L0_BUG0[6], poly_inFIFO_L0_BUG0[6], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG0_1[3], inv_poly_inSel_to_DIF_L0_BUG0[7], poly_inFIFO_L0_BUG0[7], direction)

        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[0], fwd_poly_DIF_to_inSel_L0_BUG0[0], inv_poly_DIF_to_store_L0_BUG0_0[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[1], fwd_poly_DIF_to_inSel_L0_BUG0[1], inv_poly_DIF_to_store_L0_BUG0_0[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[2], fwd_poly_DIF_to_inSel_L0_BUG0[2], inv_poly_DIF_to_store_L0_BUG0_0[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[3], fwd_poly_DIF_to_inSel_L0_BUG0[3], inv_poly_DIF_to_store_L0_BUG0_0[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[4], fwd_poly_DIF_to_inSel_L0_BUG0[4], inv_poly_DIF_to_store_L0_BUG0_1[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[5], fwd_poly_DIF_to_inSel_L0_BUG0[5], inv_poly_DIF_to_store_L0_BUG0_1[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[6], fwd_poly_DIF_to_inSel_L0_BUG0[6], inv_poly_DIF_to_store_L0_BUG0_1[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG0[7], fwd_poly_DIF_to_inSel_L0_BUG0[7], inv_poly_DIF_to_store_L0_BUG0_1[3], direction)

        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_0[0], inv_poly_inSel_to_DIF_L0_BUG1[0], poly_inFIFO_L0_BUG1[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_0[1], inv_poly_inSel_to_DIF_L0_BUG1[1], poly_inFIFO_L0_BUG1[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_0[2], inv_poly_inSel_to_DIF_L0_BUG1[2], poly_inFIFO_L0_BUG1[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_0[3], inv_poly_inSel_to_DIF_L0_BUG1[3], poly_inFIFO_L0_BUG1[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_1[0], inv_poly_inSel_to_DIF_L0_BUG1[4], poly_inFIFO_L0_BUG1[4], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_1[1], inv_poly_inSel_to_DIF_L0_BUG1[5], poly_inFIFO_L0_BUG1[5], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_1[2], inv_poly_inSel_to_DIF_L0_BUG1[6], poly_inFIFO_L0_BUG1[6], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L0_BUG1_1[3], inv_poly_inSel_to_DIF_L0_BUG1[7], poly_inFIFO_L0_BUG1[7], direction)

        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[0], fwd_poly_DIF_to_inSel_L0_BUG1[0], inv_poly_DIF_to_store_L0_BUG1_0[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[1], fwd_poly_DIF_to_inSel_L0_BUG1[1], inv_poly_DIF_to_store_L0_BUG1_0[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[2], fwd_poly_DIF_to_inSel_L0_BUG1[2], inv_poly_DIF_to_store_L0_BUG1_0[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[3], fwd_poly_DIF_to_inSel_L0_BUG1[3], inv_poly_DIF_to_store_L0_BUG1_0[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[4], fwd_poly_DIF_to_inSel_L0_BUG1[4], inv_poly_DIF_to_store_L0_BUG1_1[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[5], fwd_poly_DIF_to_inSel_L0_BUG1[5], inv_poly_DIF_to_store_L0_BUG1_1[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[6], fwd_poly_DIF_to_inSel_L0_BUG1[6], inv_poly_DIF_to_store_L0_BUG1_1[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L0_BUG1[7], fwd_poly_DIF_to_inSel_L0_BUG1[7], inv_poly_DIF_to_store_L0_BUG1_1[3], direction)


        //input_selector tasks
        .invoke(input_selector, fwd_poly_DIF_to_inSel_L0_BUG0, fwd_poly_shufOutShuff_to_inSel_L0_BUG0, inv_poly_BUG_to_inSel_L0_BUG0, fwd_poly_inSel_to_BUG_L0_BUG0, inv_poly_inSel_to_shufOutShuff_L0_BUG0, inv_poly_inSel_to_DIF_L0_BUG0, direction, iter, 0)
        .invoke(input_selector, fwd_poly_DIF_to_inSel_L0_BUG1, fwd_poly_shufOutShuff_to_inSel_L0_BUG1, inv_poly_BUG_to_inSel_L0_BUG1, fwd_poly_inSel_to_BUG_L0_BUG1, inv_poly_inSel_to_shufOutShuff_L0_BUG1, inv_poly_inSel_to_DIF_L0_BUG1, direction, iter, 1)

        //TF buffer tasks
        //TF buffers for BUG0 - Layer0
        .invoke(TFBuf_wiFW_0, tf_load_to_TFBuf_L0_G0_0[0], tf_load_to_TFBuf_L0_G0_1[0], tf_TFBuf_to_BUG_L0_BUG0_H0[0], tf_TFBuf_to_BUG_L0_BUG0_H0[1], direction, 0, 0, 0, iter)
        .invoke(TFBuf_wiFW_0, tf_load_to_TFBuf_L0_G0_0[1], tf_load_to_TFBuf_L0_G0_1[1], tf_TFBuf_to_BUG_L0_BUG0_H0[2], tf_TFBuf_to_BUG_L0_BUG0_H0[3], direction, 0, 0, 1, iter)

        //TF buffers for BUG0 - Layer1
        .invoke(TFBuf_wiFW_1, tf_load_to_TFBuf_L0_G0_1[0], tf_load_to_TFBuf_L0_G0_2[0], tf_TFBuf_to_BUG_L0_BUG0_H1[0], tf_TFBuf_to_BUG_L0_BUG0_H1[1], direction, 0, 1, 0, iter)
        .invoke(TFBuf_wiFW_1, tf_load_to_TFBuf_L0_G0_1[1], tf_load_to_TFBuf_L0_G0_2[1], tf_TFBuf_to_BUG_L0_BUG0_H1[2], tf_TFBuf_to_BUG_L0_BUG0_H1[3], direction, 0, 1, 1, iter)

        //TF buffers for BUG0 - Layer2
        .invoke(TFBuf_woFW_2, tf_load_to_TFBuf_L0_G0_2[0], tf_TFBuf_to_BUG_L0_BUG0_H2[0], tf_TFBuf_to_BUG_L0_BUG0_H2[1], direction, 0, 2, 0, iter)
        .invoke(TFBuf_woFW_2, tf_load_to_TFBuf_L0_G0_2[1], tf_TFBuf_to_BUG_L0_BUG0_H2[2], tf_TFBuf_to_BUG_L0_BUG0_H2[3], direction, 0, 2, 1, iter)

        //TF buffers for BUG1 - Layer0
        .invoke(TFBuf_wiFW_0, tf_load_to_TFBuf_L0_G0_0[2], tf_load_to_TFBuf_L0_G0_1[2], tf_TFBuf_to_BUG_L0_BUG1_H0[0], tf_TFBuf_to_BUG_L0_BUG1_H0[1], direction, 1, 0, 0, iter)
        .invoke(TFBuf_wiFW_0, tf_load_to_TFBuf_L0_G0_0[3], tf_load_to_TFBuf_L0_G0_1[3], tf_TFBuf_to_BUG_L0_BUG1_H0[2], tf_TFBuf_to_BUG_L0_BUG1_H0[3], direction, 1, 0, 1, iter)

        //TF buffers for BUG1 - Layer1
        .invoke(TFBuf_wiFW_1, tf_load_to_TFBuf_L0_G0_1[2], tf_load_to_TFBuf_L0_G0_2[2], tf_TFBuf_to_BUG_L0_BUG1_H1[0], tf_TFBuf_to_BUG_L0_BUG1_H1[1], direction, 1, 1, 0, iter)
        .invoke(TFBuf_wiFW_1, tf_load_to_TFBuf_L0_G0_1[3], tf_load_to_TFBuf_L0_G0_2[3], tf_TFBuf_to_BUG_L0_BUG1_H1[2], tf_TFBuf_to_BUG_L0_BUG1_H1[3], direction, 1, 1, 1, iter)

        //TF buffers for BUG1 - Layer2
        .invoke(TFBuf_woFW_2, tf_load_to_TFBuf_L0_G0_2[2], tf_TFBuf_to_BUG_L0_BUG1_H2[0], tf_TFBuf_to_BUG_L0_BUG1_H2[1], direction, 1, 2, 0, iter)
        .invoke(TFBuf_woFW_2, tf_load_to_TFBuf_L0_G0_2[3], tf_TFBuf_to_BUG_L0_BUG1_H2[2], tf_TFBuf_to_BUG_L0_BUG1_H2[3], direction, 1, 2, 1, iter)


        //BUGs
        //BUG0
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG0[0], fwd_poly_inSel_to_BUG_L0_BUG0[1], inv_poly_H1_to_H0_L0_BUG0[0], inv_poly_H1_to_H0_L0_BUG0[1], tf_TFBuf_to_BUG_L0_BUG0_H0[0], fwd_poly_H0_to_H1_L0_BUG0[0], fwd_poly_H0_to_H1_L0_BUG0[1], inv_poly_BUG_to_inSel_L0_BUG0[0], inv_poly_BUG_to_inSel_L0_BUG0[1], q0, twoInverse0, factor0, direction, iter, 0, 0)
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG0[2], fwd_poly_inSel_to_BUG_L0_BUG0[3], inv_poly_H1_to_H0_L0_BUG0[2], inv_poly_H1_to_H0_L0_BUG0[3], tf_TFBuf_to_BUG_L0_BUG0_H0[1], fwd_poly_H0_to_H1_L0_BUG0[2], fwd_poly_H0_to_H1_L0_BUG0[3], inv_poly_BUG_to_inSel_L0_BUG0[2], inv_poly_BUG_to_inSel_L0_BUG0[3], q0, twoInverse0, factor0, direction, iter, 0, 0)
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG0[4], fwd_poly_inSel_to_BUG_L0_BUG0[5], inv_poly_H1_to_H0_L0_BUG0[4], inv_poly_H1_to_H0_L0_BUG0[5], tf_TFBuf_to_BUG_L0_BUG0_H0[2], fwd_poly_H0_to_H1_L0_BUG0[4], fwd_poly_H0_to_H1_L0_BUG0[5], inv_poly_BUG_to_inSel_L0_BUG0[4], inv_poly_BUG_to_inSel_L0_BUG0[5], q0, twoInverse0, factor0, direction, iter, 0, 0)
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG0[6], fwd_poly_inSel_to_BUG_L0_BUG0[7], inv_poly_H1_to_H0_L0_BUG0[6], inv_poly_H1_to_H0_L0_BUG0[7], tf_TFBuf_to_BUG_L0_BUG0_H0[3], fwd_poly_H0_to_H1_L0_BUG0[6], fwd_poly_H0_to_H1_L0_BUG0[7], inv_poly_BUG_to_inSel_L0_BUG0[6], inv_poly_BUG_to_inSel_L0_BUG0[7], q0, twoInverse0, factor0, direction, iter, 0, 0)

        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG0[0], fwd_poly_H0_to_H1_L0_BUG0[2], inv_poly_H2_to_H1_L0_BUG0[0], inv_poly_H2_to_H1_L0_BUG0[2], tf_TFBuf_to_BUG_L0_BUG0_H1[0], fwd_poly_H1_to_H2_L0_BUG0[0], fwd_poly_H1_to_H2_L0_BUG0[2], inv_poly_H1_to_H0_L0_BUG0[0], inv_poly_H1_to_H0_L0_BUG0[2], q0, twoInverse0, factor0, direction, iter, 0, 1)
        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG0[1], fwd_poly_H0_to_H1_L0_BUG0[3], inv_poly_H2_to_H1_L0_BUG0[1], inv_poly_H2_to_H1_L0_BUG0[3], tf_TFBuf_to_BUG_L0_BUG0_H1[1], fwd_poly_H1_to_H2_L0_BUG0[1], fwd_poly_H1_to_H2_L0_BUG0[3], inv_poly_H1_to_H0_L0_BUG0[1], inv_poly_H1_to_H0_L0_BUG0[3], q0, twoInverse0, factor0, direction, iter, 0, 1)
        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG0[4], fwd_poly_H0_to_H1_L0_BUG0[6], inv_poly_H2_to_H1_L0_BUG0[4], inv_poly_H2_to_H1_L0_BUG0[6], tf_TFBuf_to_BUG_L0_BUG0_H1[2], fwd_poly_H1_to_H2_L0_BUG0[4], fwd_poly_H1_to_H2_L0_BUG0[6], inv_poly_H1_to_H0_L0_BUG0[4], inv_poly_H1_to_H0_L0_BUG0[6], q0, twoInverse0, factor0, direction, iter, 0, 1)
        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG0[5], fwd_poly_H0_to_H1_L0_BUG0[7], inv_poly_H2_to_H1_L0_BUG0[5], inv_poly_H2_to_H1_L0_BUG0[7], tf_TFBuf_to_BUG_L0_BUG0_H1[3], fwd_poly_H1_to_H2_L0_BUG0[5], fwd_poly_H1_to_H2_L0_BUG0[7], inv_poly_H1_to_H0_L0_BUG0[5], inv_poly_H1_to_H0_L0_BUG0[7], q0, twoInverse0, factor0, direction, iter, 0, 1)

        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG0[0], fwd_poly_H1_to_H2_L0_BUG0[4], inv_poly_outSel_to_BUG_L0_BUG0[0], inv_poly_outSel_to_BUG_L0_BUG0[4], tf_TFBuf_to_BUG_L0_BUG0_H2[0], fwd_poly_BUG_to_outSel_L0_BUG0[0], fwd_poly_BUG_to_outSel_L0_BUG0[4], inv_poly_H2_to_H1_L0_BUG0[0], inv_poly_H2_to_H1_L0_BUG0[4], q0, twoInverse0, factor0, direction, iter, 0, 2)
        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG0[1], fwd_poly_H1_to_H2_L0_BUG0[5], inv_poly_outSel_to_BUG_L0_BUG0[1], inv_poly_outSel_to_BUG_L0_BUG0[5], tf_TFBuf_to_BUG_L0_BUG0_H2[1], fwd_poly_BUG_to_outSel_L0_BUG0[1], fwd_poly_BUG_to_outSel_L0_BUG0[5], inv_poly_H2_to_H1_L0_BUG0[1], inv_poly_H2_to_H1_L0_BUG0[5], q0, twoInverse0, factor0, direction, iter, 0, 2)
        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG0[2], fwd_poly_H1_to_H2_L0_BUG0[6], inv_poly_outSel_to_BUG_L0_BUG0[2], inv_poly_outSel_to_BUG_L0_BUG0[6], tf_TFBuf_to_BUG_L0_BUG0_H2[2], fwd_poly_BUG_to_outSel_L0_BUG0[2], fwd_poly_BUG_to_outSel_L0_BUG0[6], inv_poly_H2_to_H1_L0_BUG0[2], inv_poly_H2_to_H1_L0_BUG0[6], q0, twoInverse0, factor0, direction, iter, 0, 2)
        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG0[3], fwd_poly_H1_to_H2_L0_BUG0[7], inv_poly_outSel_to_BUG_L0_BUG0[3], inv_poly_outSel_to_BUG_L0_BUG0[7], tf_TFBuf_to_BUG_L0_BUG0_H2[3], fwd_poly_BUG_to_outSel_L0_BUG0[3], fwd_poly_BUG_to_outSel_L0_BUG0[7], inv_poly_H2_to_H1_L0_BUG0[3], inv_poly_H2_to_H1_L0_BUG0[7], q0, twoInverse0, factor0, direction, iter, 0, 2)

        //BUG1
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG1[0], fwd_poly_inSel_to_BUG_L0_BUG1[1], inv_poly_H1_to_H0_L0_BUG1[0], inv_poly_H1_to_H0_L0_BUG1[1], tf_TFBuf_to_BUG_L0_BUG1_H0[0], fwd_poly_H0_to_H1_L0_BUG1[0], fwd_poly_H0_to_H1_L0_BUG1[1], inv_poly_BUG_to_inSel_L0_BUG1[0], inv_poly_BUG_to_inSel_L0_BUG1[1], q0, twoInverse0, factor0, direction, iter, 1, 0)
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG1[2], fwd_poly_inSel_to_BUG_L0_BUG1[3], inv_poly_H1_to_H0_L0_BUG1[2], inv_poly_H1_to_H0_L0_BUG1[3], tf_TFBuf_to_BUG_L0_BUG1_H0[1], fwd_poly_H0_to_H1_L0_BUG1[2], fwd_poly_H0_to_H1_L0_BUG1[3], inv_poly_BUG_to_inSel_L0_BUG1[2], inv_poly_BUG_to_inSel_L0_BUG1[3], q0, twoInverse0, factor0, direction, iter, 1, 0)
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG1[4], fwd_poly_inSel_to_BUG_L0_BUG1[5], inv_poly_H1_to_H0_L0_BUG1[4], inv_poly_H1_to_H0_L0_BUG1[5], tf_TFBuf_to_BUG_L0_BUG1_H0[2], fwd_poly_H0_to_H1_L0_BUG1[4], fwd_poly_H0_to_H1_L0_BUG1[5], inv_poly_BUG_to_inSel_L0_BUG1[4], inv_poly_BUG_to_inSel_L0_BUG1[5], q0, twoInverse0, factor0, direction, iter, 1, 0)
        .invoke(BU, fwd_poly_inSel_to_BUG_L0_BUG1[6], fwd_poly_inSel_to_BUG_L0_BUG1[7], inv_poly_H1_to_H0_L0_BUG1[6], inv_poly_H1_to_H0_L0_BUG1[7], tf_TFBuf_to_BUG_L0_BUG1_H0[3], fwd_poly_H0_to_H1_L0_BUG1[6], fwd_poly_H0_to_H1_L0_BUG1[7], inv_poly_BUG_to_inSel_L0_BUG1[6], inv_poly_BUG_to_inSel_L0_BUG1[7], q0, twoInverse0, factor0, direction, iter, 1, 0)

        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG1[0], fwd_poly_H0_to_H1_L0_BUG1[2], inv_poly_H2_to_H1_L0_BUG1[0], inv_poly_H2_to_H1_L0_BUG1[2], tf_TFBuf_to_BUG_L0_BUG1_H1[0], fwd_poly_H1_to_H2_L0_BUG1[0], fwd_poly_H1_to_H2_L0_BUG1[2], inv_poly_H1_to_H0_L0_BUG1[0], inv_poly_H1_to_H0_L0_BUG1[2], q0, twoInverse0, factor0, direction, iter, 1, 1)
        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG1[1], fwd_poly_H0_to_H1_L0_BUG1[3], inv_poly_H2_to_H1_L0_BUG1[1], inv_poly_H2_to_H1_L0_BUG1[3], tf_TFBuf_to_BUG_L0_BUG1_H1[1], fwd_poly_H1_to_H2_L0_BUG1[1], fwd_poly_H1_to_H2_L0_BUG1[3], inv_poly_H1_to_H0_L0_BUG1[1], inv_poly_H1_to_H0_L0_BUG1[3], q0, twoInverse0, factor0, direction, iter, 1, 1)
        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG1[4], fwd_poly_H0_to_H1_L0_BUG1[6], inv_poly_H2_to_H1_L0_BUG1[4], inv_poly_H2_to_H1_L0_BUG1[6], tf_TFBuf_to_BUG_L0_BUG1_H1[2], fwd_poly_H1_to_H2_L0_BUG1[4], fwd_poly_H1_to_H2_L0_BUG1[6], inv_poly_H1_to_H0_L0_BUG1[4], inv_poly_H1_to_H0_L0_BUG1[6], q0, twoInverse0, factor0, direction, iter, 1, 1)
        .invoke(BU, fwd_poly_H0_to_H1_L0_BUG1[5], fwd_poly_H0_to_H1_L0_BUG1[7], inv_poly_H2_to_H1_L0_BUG1[5], inv_poly_H2_to_H1_L0_BUG1[7], tf_TFBuf_to_BUG_L0_BUG1_H1[3], fwd_poly_H1_to_H2_L0_BUG1[5], fwd_poly_H1_to_H2_L0_BUG1[7], inv_poly_H1_to_H0_L0_BUG1[5], inv_poly_H1_to_H0_L0_BUG1[7], q0, twoInverse0, factor0, direction, iter, 1, 1)

        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG1[0], fwd_poly_H1_to_H2_L0_BUG1[4], inv_poly_outSel_to_BUG_L0_BUG1[0], inv_poly_outSel_to_BUG_L0_BUG1[4], tf_TFBuf_to_BUG_L0_BUG1_H2[0], fwd_poly_BUG_to_outSel_L0_BUG1[0], fwd_poly_BUG_to_outSel_L0_BUG1[4], inv_poly_H2_to_H1_L0_BUG1[0], inv_poly_H2_to_H1_L0_BUG1[4], q0, twoInverse0, factor0, direction, iter, 1, 2)
        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG1[1], fwd_poly_H1_to_H2_L0_BUG1[5], inv_poly_outSel_to_BUG_L0_BUG1[1], inv_poly_outSel_to_BUG_L0_BUG1[5], tf_TFBuf_to_BUG_L0_BUG1_H2[1], fwd_poly_BUG_to_outSel_L0_BUG1[1], fwd_poly_BUG_to_outSel_L0_BUG1[5], inv_poly_H2_to_H1_L0_BUG1[1], inv_poly_H2_to_H1_L0_BUG1[5], q0, twoInverse0, factor0, direction, iter, 1, 2)
        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG1[2], fwd_poly_H1_to_H2_L0_BUG1[6], inv_poly_outSel_to_BUG_L0_BUG1[2], inv_poly_outSel_to_BUG_L0_BUG1[6], tf_TFBuf_to_BUG_L0_BUG1_H2[2], fwd_poly_BUG_to_outSel_L0_BUG1[2], fwd_poly_BUG_to_outSel_L0_BUG1[6], inv_poly_H2_to_H1_L0_BUG1[2], inv_poly_H2_to_H1_L0_BUG1[6], q0, twoInverse0, factor0, direction, iter, 1, 2)
        .invoke(BU, fwd_poly_H1_to_H2_L0_BUG1[3], fwd_poly_H1_to_H2_L0_BUG1[7], inv_poly_outSel_to_BUG_L0_BUG1[3], inv_poly_outSel_to_BUG_L0_BUG1[7], tf_TFBuf_to_BUG_L0_BUG1_H2[3], fwd_poly_BUG_to_outSel_L0_BUG1[3], fwd_poly_BUG_to_outSel_L0_BUG1[7], inv_poly_H2_to_H1_L0_BUG1[3], inv_poly_H2_to_H1_L0_BUG1[7], q0, twoInverse0, factor0, direction, iter, 1, 2)


        //output_selector tasks
        .invoke(output_slector, fwd_poly_BUG_to_outSel_L0_BUG0, inv_poly_DIF_to_outSel_L0_BUG0, inv_poly_shuf_to_outSel_L0_BUG0, fwd_poly_outSel_to_shuf_L0_BUG0, fwd_poly_outSel_to_DIF_L0_BUG0, inv_poly_outSel_to_BUG_L0_BUG0, direction, iter, 0)
        .invoke(output_slector, fwd_poly_BUG_to_outSel_L0_BUG1, inv_poly_DIF_to_outSel_L0_BUG1, inv_poly_shuf_to_outSel_L0_BUG1, fwd_poly_outSel_to_shuf_L0_BUG1, fwd_poly_outSel_to_DIF_L0_BUG1, inv_poly_outSel_to_BUG_L0_BUG1, direction, iter, 1)

        //Dual Interface FIFO (DIF) tasks from FWD out side
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[0], inv_poly_load_to_DIF_L0_BUG0_0[0], poly_outFIFO_L0_BUG0[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[1], inv_poly_load_to_DIF_L0_BUG0_0[1], poly_outFIFO_L0_BUG0[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[2], inv_poly_load_to_DIF_L0_BUG0_0[2], poly_outFIFO_L0_BUG0[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[3], inv_poly_load_to_DIF_L0_BUG0_0[3], poly_outFIFO_L0_BUG0[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[4], inv_poly_load_to_DIF_L0_BUG0_1[0], poly_outFIFO_L0_BUG0[4], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[5], inv_poly_load_to_DIF_L0_BUG0_1[1], poly_outFIFO_L0_BUG0[5], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[6], inv_poly_load_to_DIF_L0_BUG0_1[2], poly_outFIFO_L0_BUG0[6], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG0[7], inv_poly_load_to_DIF_L0_BUG0_1[3], poly_outFIFO_L0_BUG0[7], direction)

        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[0], fwd_poly_DIF_to_store_L0_BUG0_0[0], inv_poly_DIF_to_outSel_L0_BUG0[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[1], fwd_poly_DIF_to_store_L0_BUG0_0[1], inv_poly_DIF_to_outSel_L0_BUG0[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[2], fwd_poly_DIF_to_store_L0_BUG0_0[2], inv_poly_DIF_to_outSel_L0_BUG0[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[3], fwd_poly_DIF_to_store_L0_BUG0_0[3], inv_poly_DIF_to_outSel_L0_BUG0[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[4], fwd_poly_DIF_to_store_L0_BUG0_1[0], inv_poly_DIF_to_outSel_L0_BUG0[4], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[5], fwd_poly_DIF_to_store_L0_BUG0_1[1], inv_poly_DIF_to_outSel_L0_BUG0[5], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[6], fwd_poly_DIF_to_store_L0_BUG0_1[2], inv_poly_DIF_to_outSel_L0_BUG0[6], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG0[7], fwd_poly_DIF_to_store_L0_BUG0_1[3], inv_poly_DIF_to_outSel_L0_BUG0[7], direction)

        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[0], inv_poly_load_to_DIF_L0_BUG1_0[0], poly_outFIFO_L0_BUG1[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[1], inv_poly_load_to_DIF_L0_BUG1_0[1], poly_outFIFO_L0_BUG1[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[2], inv_poly_load_to_DIF_L0_BUG1_0[2], poly_outFIFO_L0_BUG1[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[3], inv_poly_load_to_DIF_L0_BUG1_0[3], poly_outFIFO_L0_BUG1[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[4], inv_poly_load_to_DIF_L0_BUG1_1[0], poly_outFIFO_L0_BUG1[4], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[5], inv_poly_load_to_DIF_L0_BUG1_1[1], poly_outFIFO_L0_BUG1[5], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[6], inv_poly_load_to_DIF_L0_BUG1_1[2], poly_outFIFO_L0_BUG1[6], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L0_BUG1[7], inv_poly_load_to_DIF_L0_BUG1_1[3], poly_outFIFO_L0_BUG1[7], direction)

        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[0], fwd_poly_DIF_to_store_L0_BUG1_0[0], inv_poly_DIF_to_outSel_L0_BUG1[0], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[1], fwd_poly_DIF_to_store_L0_BUG1_0[1], inv_poly_DIF_to_outSel_L0_BUG1[1], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[2], fwd_poly_DIF_to_store_L0_BUG1_0[2], inv_poly_DIF_to_outSel_L0_BUG1[2], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[3], fwd_poly_DIF_to_store_L0_BUG1_0[3], inv_poly_DIF_to_outSel_L0_BUG1[3], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[4], fwd_poly_DIF_to_store_L0_BUG1_1[0], inv_poly_DIF_to_outSel_L0_BUG1[4], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[5], fwd_poly_DIF_to_store_L0_BUG1_1[1], inv_poly_DIF_to_outSel_L0_BUG1[5], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[6], fwd_poly_DIF_to_store_L0_BUG1_1[2], inv_poly_DIF_to_outSel_L0_BUG1[6], direction)
        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L0_BUG1[7], fwd_poly_DIF_to_store_L0_BUG1_1[3], inv_poly_DIF_to_outSel_L0_BUG1[7], direction)


        //shuffler tasks
        .invoke(shuffler, fwd_poly_outSel_to_shuf_L0_BUG0, inv_poly_shufOutSplit_to_shuf_L0_BUG0, fwd_poly_shuf_to_shufOutSplit_L0_BUG0, inv_poly_shuf_to_outSel_L0_BUG0, direction, 0, iter)
        .invoke(shuffler, fwd_poly_outSel_to_shuf_L0_BUG1, inv_poly_shufOutSplit_to_shuf_L0_BUG1, fwd_poly_shuf_to_shufOutSplit_L0_BUG1, inv_poly_shuf_to_outSel_L0_BUG1, direction, 1, iter)

        .invoke(shuffler_out_split, fwd_poly_shuf_to_shufOutSplit_L0_BUG0, inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0, inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG0, fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0, fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG0, inv_poly_shufOutSplit_to_shuf_L0_BUG0, direction, iter, 0)
        .invoke(shuffler_out_split, fwd_poly_shuf_to_shufOutSplit_L0_BUG1, inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1, inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG1, fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1, fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG1, inv_poly_shufOutSplit_to_shuf_L0_BUG1, direction, iter, 1)


        .invoke(shuffler_out_shuff, \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[0], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[0], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[2], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[2], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[4], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[4], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[6], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[6], \
            fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG0, \
            inv_poly_inSel_to_shufOutShuff_L0_BUG0, \
            fwd_poly_shufOutShuff_to_inSel_L0_BUG0, \
            inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG0, \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[0], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[0], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[2], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[2], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[4], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[4], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[6], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[6], \
            direction, iter
        )

        .invoke(shuffler_out_shuff, \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[1], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[1], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[3], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[3], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[5], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[5], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG0[7], \
            fwd_poly_shufOutSplit_to_shufOutShuff_inter0_L0_BUG1[7], \
            fwd_poly_shufOutSplit_to_shufOutShuff_intra_L0_BUG1, \
            inv_poly_inSel_to_shufOutShuff_L0_BUG1, \
            fwd_poly_shufOutShuff_to_inSel_L0_BUG1, \
            inv_poly_shufOutShuff_to_shufOutSplit_intra_L0_BUG1, \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[1], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[1], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[3], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[3], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[5], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[5], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG0[7], \
            inv_poly_shufOutShuff_to_shufOutSplit_inter0_L0_BUG1[7], \
            direction, iter
        )


    ;
}
