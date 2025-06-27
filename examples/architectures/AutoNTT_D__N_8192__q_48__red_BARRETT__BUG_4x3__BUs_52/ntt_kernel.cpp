#include <cstdint>

#include <tapa.h>
#include "ntt.h"

// /********************************************************************************************
// * Polynomial load store tasks *
// ********************************************************************************************/

void Mmap2Stream_poly_1_limbs(
            tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap,
            tapa::ostreams<WORD, HBM_PORT_SIZE>& fwd_poly_stream_L0,
            tapa::istreams<WORD, HBM_PORT_SIZE>& inv_poly_stream_L0,
            bool direction, VAR_TYPE_32 iter) {

    VAR_TYPE_32 loopIter = (N/CONCAT_FACTOR)*(iter+1);

    if (direction) {
        MMAP2S:for(VAR_TYPE_32 i_req = 0, i_resp = 0; i_resp < loopIter;) {
            #pragma HLS PIPELINE II = 1

            if ((i_req < loopIter) && 
                (poly_mmap.read_addr.try_write(i_req%(N/CONCAT_FACTOR)))) {
                ++i_req;
            }
            
            if((!poly_mmap.read_data.empty()) && direction) {
                POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);
                for(VAR_TYPE_8 j=0; j<HBM_PORT_SIZE; j++) {
                    #pragma HLS UNROLL
                    WORD v0 = (val & ((((WORD_PLUS1)1)<<WORD_SIZE)-1));
                    fwd_poly_stream_L0[j].write(v0);
                    val >>= DRAM_WORD_SIZE;
                }

                ++i_resp;
            } 
        }
    } else {
        STORE_POLY:for (int i_req = 0, i_resp = 0; i_resp < loopIter; ) {
            #pragma HLS PIPELINE II = 1

            bool inFIFONotEmpty = (!inv_poly_stream_L0[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < HBM_PORT_SIZE; i++) {
                #pragma HLS UNROLL
                inFIFONotEmpty &= ((!inv_poly_stream_L0[i].empty())) ;
            }

            POLY_WIDE_DATA val0 = 0;
            if((i_resp < loopIter) && inFIFONotEmpty &&
                (!poly_mmap.write_addr.full()) &&
                (!poly_mmap.write_data.full())){
                
                for(int j=HBM_PORT_SIZE-1; j>=0; --j){
                    #pragma HLS UNROLL
                    val0 <<= DRAM_WORD_SIZE;
                    WORD smallData0 = 0;
                    smallData0 = inv_poly_stream_L0[j].read(nullptr);
                    val0 |= (POLY_WIDE_DATA)(smallData0);
                }

                poly_mmap.write_addr.write(i_req%(N/CONCAT_FACTOR));
                poly_mmap.write_data.write(val0);
                i_req++;
            }


            // receive acks of write success
            if (!poly_mmap.write_resp.empty()) {
                i_resp += (unsigned(poly_mmap.write_resp.read(nullptr)) + 1);
            }
        }
    }
}

void Stream2Mmap_poly_1_limbs(
                    tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap,
                    tapa::istreams<WORD, HBM_PORT_SIZE>& fwd_poly_stream_L0,
                    tapa::ostreams<WORD, HBM_PORT_SIZE>& inv_poly_stream_L0,
                    bool direction, VAR_TYPE_32 iter){

    int loopIter = (N/CONCAT_FACTOR)*(iter+1);

    if(direction) {
        STORE_POLY:for (int i_req = 0, i_resp = 0; i_resp < loopIter; ) {
            #pragma HLS PIPELINE II = 1

            bool inFIFONotEmpty = (!fwd_poly_stream_L0[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < HBM_PORT_SIZE; i++) {
                #pragma HLS UNROLL
                inFIFONotEmpty &= ((!fwd_poly_stream_L0[i].empty())) ;
            }

            POLY_WIDE_DATA val0 = 0;
            if((i_resp < loopIter) && inFIFONotEmpty &&
                (!poly_mmap.write_addr.full()) &&
                (!poly_mmap.write_data.full())){

                for(int j=HBM_PORT_SIZE-1; j>=0; --j){
                    #pragma HLS UNROLL
                    val0 <<= DRAM_WORD_SIZE;
                    WORD smallData0 = 0;
                    smallData0 = fwd_poly_stream_L0[j].read(nullptr);
                    val0 |= (POLY_WIDE_DATA)(smallData0);
                }

                poly_mmap.write_addr.write(i_req%(N/CONCAT_FACTOR));
                poly_mmap.write_data.write(val0);
                i_req++;
            }


            // receive acks of write success
            if (!poly_mmap.write_resp.empty()) {
                i_resp += (unsigned(poly_mmap.write_resp.read(nullptr)) + 1);
            }
        }
    } else {

        MMAP2S:for(VAR_TYPE_32 i_req = 0, i_resp = 0; i_resp < loopIter;) {
            #pragma HLS PIPELINE II = 1

            if ((i_req < loopIter) && 
                (poly_mmap.read_addr.try_write(i_req%(N/CONCAT_FACTOR)))) {
                ++i_req;
            }
            
            if((!poly_mmap.read_data.empty()) ) {
                POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);

                for(VAR_TYPE_8 j=0; j<HBM_PORT_SIZE; j++){
                    #pragma HLS UNROLL
                    WORD v0 = (val & ((((WORD_PLUS1)1)<<WORD_SIZE)-1));
                    inv_poly_stream_L0[j].write(v0);
                    val >>= DRAM_WORD_SIZE;
                }

                ++i_resp;
            }
        }
    }
}


// /********************************************************************************************
// * TF load *
// ********************************************************************************************/

void Mmap2Stream_tf_1_limbs(
                tapa::async_mmap<TF_WIDE_DATA>& tf_mmap,
                tapa::ostream<TF_WIDE_DATA_PER_PARA_LIMB>& tf_stream_L0,
                VAR_TYPE_32 tfArr_length,
                VAR_TYPE_32 iter) {

    VAR_TYPE_32 loopIter;
    #pragma HLS bind_op variable=loopIter op=mul impl=fabric latency=0

    loopIter = tfArr_length*(iter+1);
    TF_WIDE_DATA readVal;
    TF_WIDE_DATA_PER_PARA_LIMB val;

    LOAD_TF:for (VAR_TYPE_32 i_req = 0, i_req_address = 0, i_resp = 0; i_resp < loopIter; ) {
        #pragma HLS PIPELINE II=1
        if ((i_req < loopIter) && 
            (tf_mmap.read_addr.try_write(i_req_address))) {
            i_req_address = (i_req_address == (tfArr_length - 1) ? (0) : (i_req_address + 1));
            ++i_req;
        }
        
        if((!tf_mmap.read_data.empty())) {
            readVal = tf_mmap.read_data.read(nullptr);

            val = readVal & ((((TF_WIDE_DATA_PLUS1)1)<<TF_WIDE_DATA_SIZE_PER_PARA_LIMB) - 1);
            tf_stream_L0.write(val);
            readVal >>= TF_WIDE_DATA_SIZE_PER_PARA_LIMB;

            ++i_resp;
        }
    }
}

void load_tf(
               tapa::istream<TF_WIDE_DATA_PER_PARA_LIMB>& tf_stream0,
               tapa::ostreams<WORD, V_BU_NUM>& tf_stream_out,
               bool direction, VAR_TYPE_32 tfArr_length, VAR_TYPE_32 iter) {

    LOAD_POLY:for (;;) {
        #pragma HLS PIPELINE II=1

        if ((!tf_stream0.empty())) {
            TF_WIDE_DATA_PER_PARA_LIMB val0 = tf_stream0.read();
            for(int j=TF_PORT_SIZE-1; j>=0; j--) {
                #pragma HLS UNROLL
                WORD v0 = (val0 & ((((WORD_PLUS1)1)<<WORD_SIZE)-1));
                tf_stream_out[TF_PORT_SIZE*0+j].write(v0);
                val0 >>= DRAM_WORD_SIZE;
            }
            
        }
    }      
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
    tapa::istream<WORD>& fwd_inVal0, tapa::istream<WORD>& fwd_inVal1, 
    tapa::ostream<WORD>& inv_outVal0, tapa::ostream<WORD>& inv_outVal1,
    tapa::istream<WORD>& fwd_inTf,
    tapa::istream<WORD>& inv_inTf,
    tapa::ostream<WORD>& fwd_outVal0, tapa::ostream<WORD>& fwd_outVal1,
    tapa::istream<WORD>& inv_inVal0, tapa::istream<WORD>& inv_inVal1, 
    WORD q,
    WORD twoInverse,
    WORD_PLUS3 factor,
    VAR_TYPE_32 iter) {

    WORD left = 0;
    WORD right = 0;
    WORD tfVal = 0;

    bool fwd_valid = false;
    bool inv_valid = false;

    BU_COMP:for (;;) {
        #pragma HLS PIPELINE II=1

        fwd_valid = (!(fwd_inVal0.empty() || fwd_inVal1.empty())) && (!fwd_inTf.empty());
        inv_valid = (!(inv_inVal0.empty() || inv_inVal1.empty())) && (!inv_inTf.empty());

        if (fwd_valid){
            left = fwd_inVal0.read();
            right = fwd_inVal1.read();
            tfVal = fwd_inTf.read();
        } else if (inv_valid) {
            left = inv_inVal0.read();
            right = inv_inVal1.read();
            tfVal = inv_inTf.read();
        }

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

        if(inv_valid){ //Multiply with 2 inverse here. Equation=> (a>>1) + a[0]((mod+1)/2)
            multiplyTwoInverse(&updatedLeft, &twoInverse);
            multiplyTwoInverse(&updatedRight, &twoInverse);
        }
        
        if(fwd_valid){
            fwd_outVal0.write(updatedLeft);
            fwd_outVal1.write(updatedRight);
        } else if(inv_valid){
            inv_outVal0.write(updatedLeft);
            inv_outVal1.write(updatedRight);
        }

    }
}

// /********************************************************************************************
// * Shuffler tasks *
// ********************************************************************************************/



void shuffler_1(tapa::istreams<WORD, 8>& fwd_in_strm,
            tapa::istreams<WORD, 8>& inv_in_strm,
            tapa::ostreams<WORD, 8>& fwd_out_strm,
            tapa::ostreams<WORD, 8>& inv_out_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{  
    int stride = 1 << log_stride;
    int iteration_size = stride << 3;
    int buffer_size = stride << 4;

    int start_index_i_base[8] = {0, 6, 4, 2, 7, 5, 3, 1};

    WORD buf_poly[CONCAT_FACTOR][16];  // wait 8, but double buffer = 16
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram
    #pragma HLS array_partition type=complete dim=1 variable=buf_poly

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {
            // NTT realted defination
            int ntt_actual_j = j_read&(buffer_size-1);

            int ntt_offset_i = (j_read>>log_stride)%CONCAT_FACTOR;  // change in last_shuffler

            bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
            }


            // iNTT realted defination
            int intt_actual_j = 0;

            // int intt_index = (j_read>>log_stride)%CONCAT_FACTOR;
            int intt_offset_i = start_index_i_base[ntt_offset_i];

            bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
            CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
            }

            LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                if (fwd_inFIFONotEmpty) {
                    int offset_plus_i = ntt_offset_i+i;  // change in last_shuffler
                    int actual_i = offset_plus_i%CONCAT_FACTOR;
                    buf_poly[actual_i][ntt_actual_j] = fwd_in_strm[i].read();
                } else if (inv_inFIFONotEmpty) {
                    int offset_plus_i = intt_offset_i+i;
                    int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                    // iteration_of_j + offset_of_j + offset_of_i
                    intt_actual_j = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + actual_strm_i*stride)&(buffer_size-1);
                    buf_poly[i][intt_actual_j] = inv_in_strm[actual_strm_i].read();
                }
            }

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {
                j_read++;
                j_read_all_iter++;
            }

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {
                j_read = 0;
            }
        }

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {
            writeEnable = true;
        }

        /* poly input */
    
        // NTT defination
        int ntt_actual_j = 0;

        int ntt_index = (j_write>>log_stride)%CONCAT_FACTOR;
        int ntt_offset_i = start_index_i_base[ntt_index];


        // iNTT defination
            int intt_actual_j = j_write&(buffer_size-1);

        // int intt_offset_i = (j_write>>log_stride)%CONCAT_FACTOR;
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
            #pragma HLS UNROLL

            if (direction && writeEnable) {
                int offset_plus_i = ntt_offset_i+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                ntt_actual_j = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + actual_strm_i*stride)&(buffer_size-1);
                fwd_out_strm[actual_strm_i].write(buf_poly[i][ntt_actual_j]);
            } else if ((!direction) && writeEnable) {
                // int offset_plus_i = intt_offset_i+i;
                int offset_plus_i = ntt_index+i;
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                inv_out_strm[i].write(buf_poly[actual_i][intt_actual_j]);
            }
        }

        if (writeEnable) {
            j_write++;
            j_write_all_iter++;
        }

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {
            j_write = 0;
        }

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {
            writeEnable = false;
        }
    }
}




void shuffler_2(tapa::istreams<WORD, 8>& fwd_in_strm,
            tapa::istreams<WORD, 8>& inv_in_strm,
            tapa::ostreams<WORD, 8>& fwd_out_strm,
            tapa::ostreams<WORD, 8>& inv_out_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{  
    int stride = 1 << log_stride;
    int iteration_size = stride << 3;
    int buffer_size = stride << 4;

    int start_index_i_base[8] = {0, 6, 4, 2, 7, 5, 3, 1};

    WORD buf_poly[CONCAT_FACTOR][128];  // wait 64, but double buffer = 128
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram
    #pragma HLS array_partition type=complete dim=1 variable=buf_poly

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {
            // NTT realted defination
            int ntt_actual_j = j_read&(buffer_size-1);

            int ntt_offset_i = (j_read>>log_stride)%CONCAT_FACTOR;  // change in last_shuffler

            bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
            }


            // iNTT realted defination
            int intt_actual_j = 0;

            // int intt_index = (j_read>>log_stride)%CONCAT_FACTOR;
            int intt_offset_i = start_index_i_base[ntt_offset_i];

            bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
            CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
            }

            LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                if (fwd_inFIFONotEmpty) {
                    int offset_plus_i = ntt_offset_i+i;  // change in last_shuffler
                    int actual_i = offset_plus_i%CONCAT_FACTOR;
                    buf_poly[actual_i][ntt_actual_j] = fwd_in_strm[i].read();
                } else if (inv_inFIFONotEmpty) {
                    int offset_plus_i = intt_offset_i+i;
                    int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                    // iteration_of_j + offset_of_j + offset_of_i
                    intt_actual_j = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + actual_strm_i*stride)&(buffer_size-1);
                    buf_poly[i][intt_actual_j] = inv_in_strm[actual_strm_i].read();
                }
            }

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {
                j_read++;
                j_read_all_iter++;
            }

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {
                j_read = 0;
            }
        }

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {
            writeEnable = true;
        }

        /* poly input */
    
        // NTT defination
        int ntt_actual_j = 0;

        int ntt_index = (j_write>>log_stride)%CONCAT_FACTOR;
        int ntt_offset_i = start_index_i_base[ntt_index];


        // iNTT defination
            int intt_actual_j = j_write&(buffer_size-1);

        // int intt_offset_i = (j_write>>log_stride)%CONCAT_FACTOR;
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
            #pragma HLS UNROLL

            if (direction && writeEnable) {
                int offset_plus_i = ntt_offset_i+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                ntt_actual_j = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + actual_strm_i*stride)&(buffer_size-1);
                fwd_out_strm[actual_strm_i].write(buf_poly[i][ntt_actual_j]);
            } else if ((!direction) && writeEnable) {
                // int offset_plus_i = intt_offset_i+i;
                int offset_plus_i = ntt_index+i;
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                inv_out_strm[i].write(buf_poly[actual_i][intt_actual_j]);
            }
        }

        if (writeEnable) {
            j_write++;
            j_write_all_iter++;
        }

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {
            j_write = 0;
        }

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {
            writeEnable = false;
        }
    }
}




void shuffler_3(tapa::istreams<WORD, 8>& fwd_in_strm,
            tapa::istreams<WORD, 8>& inv_in_strm,
            tapa::ostreams<WORD, 8>& fwd_out_strm,
            tapa::ostreams<WORD, 8>& inv_out_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{  
    int stride = 1 << log_stride;
    int iteration_size = stride << 3;
    int buffer_size = stride << 4;

    int start_index_i_base[8] = {0, 6, 4, 2, 7, 5, 3, 1};

    WORD buf_poly[CONCAT_FACTOR][1024];  // wait 512, but double buffer = 1024
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram
    #pragma HLS array_partition type=complete dim=1 variable=buf_poly

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {
            // NTT realted defination
            int ntt_actual_j = j_read&(buffer_size-1);

            int ntt_offset_i = (j_read>>log_stride)%CONCAT_FACTOR;  // change in last_shuffler

            bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
            }


            // iNTT realted defination
            int intt_actual_j = 0;

            // int intt_index = (j_read>>log_stride)%CONCAT_FACTOR;
            int intt_offset_i = start_index_i_base[ntt_offset_i];

            bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
            CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
            }

            LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                if (fwd_inFIFONotEmpty) {
                    int offset_plus_i = ntt_offset_i+i;  // change in last_shuffler
                    int actual_i = offset_plus_i%CONCAT_FACTOR;
                    buf_poly[actual_i][ntt_actual_j] = fwd_in_strm[i].read();
                } else if (inv_inFIFONotEmpty) {
                    int offset_plus_i = intt_offset_i+i;
                    int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                    // iteration_of_j + offset_of_j + offset_of_i
                    intt_actual_j = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + actual_strm_i*stride)&(buffer_size-1);
                    buf_poly[i][intt_actual_j] = inv_in_strm[actual_strm_i].read();
                }
            }

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {
                j_read++;
                j_read_all_iter++;
            }

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {
                j_read = 0;
            }
        }

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {
            writeEnable = true;
        }

        /* poly input */
    
        // NTT defination
        int ntt_actual_j = 0;

        int ntt_index = (j_write>>log_stride)%CONCAT_FACTOR;
        int ntt_offset_i = start_index_i_base[ntt_index];


        // iNTT defination
            int intt_actual_j = j_write&(buffer_size-1);

        // int intt_offset_i = (j_write>>log_stride)%CONCAT_FACTOR;
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
            #pragma HLS UNROLL

            if (direction && writeEnable) {
                int offset_plus_i = ntt_offset_i+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                ntt_actual_j = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + actual_strm_i*stride)&(buffer_size-1);
                fwd_out_strm[actual_strm_i].write(buf_poly[i][ntt_actual_j]);
            } else if ((!direction) && writeEnable) {
                // int offset_plus_i = intt_offset_i+i;
                int offset_plus_i = ntt_index+i;
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                inv_out_strm[i].write(buf_poly[actual_i][intt_actual_j]);
            }
        }

        if (writeEnable) {
            j_write++;
            j_write_all_iter++;
        }

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {
            j_write = 0;
        }

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {
            writeEnable = false;
        }
    }
}




void shuffler_4(tapa::istreams<WORD, 8>& fwd_in_strm,
            tapa::istreams<WORD, 8>& inv_in_strm,
            tapa::ostreams<WORD, 8>& fwd_out_strm,
            tapa::ostreams<WORD, 8>& inv_out_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{  
    int stride = 1 << log_stride;
    int iteration_size = stride << 1;
    int buffer_size = stride << 2;

    int start_index_i_base[2] = {0, 7};
    int offset_1[2] = {0, 1};
    int offset_2[8] = {0, 4, 1, 5, 2, 6, 3, 7};
    int offset_3[8] = {0, 1, 0, 1, 0, 1, 0, 1};

    WORD buf_poly[CONCAT_FACTOR][1024];  // wait 1024 = N / CONCAT_FACTOR
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram
    #pragma HLS array_partition type=complete dim=1 variable=buf_poly

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {
            // iNTT realted defination
            int intt_actual_j = 0;

            int intt_index = (j_read>>log_stride)%LAST_CONCAT_FACTOR;
            int intt_offset_i = start_index_i_base[intt_index];

            bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
            CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
            }


            // NTT realted defination
            int ntt_actual_j = j_read&(iteration_size-1);  // get j index in buf_poly[][]
            int ntt_offset_i = offset_1[intt_index];  // get the first i index in buf_poly[][]

            bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
            }


            LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
                #pragma HLS UNROLL
                if (fwd_inFIFONotEmpty) {
                    int offset_plus_i = ntt_offset_i+offset_2[i];
                    int actual_i = offset_plus_i%CONCAT_FACTOR;
                    buf_poly[actual_i][ntt_actual_j] = fwd_in_strm[i].read();
                } else if (inv_inFIFONotEmpty) {
                    int offset_plus_i = intt_offset_i+i;
                    int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                    // iteration_of_j + offset_of_j + offset_of_i
                    intt_actual_j = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + offset_3[actual_strm_i]*stride)&(iteration_size-1);  //change in last_shuffler
                    buf_poly[i][intt_actual_j] = inv_in_strm[actual_strm_i].read();
                }
            }

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {
                j_read++;
                j_read_all_iter++;
            }

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {
                j_read = 0;
            }
        }

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {
            writeEnable = true;
        }

        /* poly input */
    
        // NTT defination
        int ntt_actual_j = 0;

        int ntt_index = (j_write>>log_stride)%LAST_CONCAT_FACTOR;
        int ntt_offset_i = start_index_i_base[ntt_index];

        // iNTT defination
        int intt_actual_j = j_write&(iteration_size-1); 
        int intt_offset_i = offset_1[ntt_index];
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {
            #pragma HLS UNROLL

            if (direction && writeEnable) {
                int offset_plus_i = ntt_offset_i+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                ntt_actual_j = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + offset_3[actual_strm_i]*stride)&(iteration_size-1);
                fwd_out_strm[actual_strm_i].write(buf_poly[i][ntt_actual_j]);
            } else if ((!direction) && writeEnable) {
                int offset_plus_i = intt_offset_i+offset_2[i];
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                inv_out_strm[i].write(buf_poly[actual_i][intt_actual_j]);
            }
        }

        if (writeEnable) {
            j_write++;
            j_write_all_iter++;
        }

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {
            j_write = 0;
        }

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {
            writeEnable = false;
        }
    }
}



// /********************************************************************************************
// * TF buffers *
// ********************************************************************************************/

void tf_load_forward_0(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD *TFArr) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 3, current_tfArr_length = 1;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
               TFArr[j / 4] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_0(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD *TFArr) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_inv_temp[1];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_inv_temp when fwd_flag == inv_flag and X < H_BU_NUM and tfarr_dimension == 1
        ASSIGN_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            fwd_inv_temp[idx] = TFArr[idx];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_inv_temp[j % 1]);
            } else if (!direction) {
                inv_tfToBUs[j].write(fwd_inv_temp[j / 4]);
            }

        }
    }
}

void TFGen0(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[1];
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[1];
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_0(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_0(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_0(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_0(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_1(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD *TFArr) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 2, current_tfArr_length = 1;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if ((tf_counter < current_tfArr_length) && direction) {
                TFArr[j / 2] = read_val;
            } else if ((tf_counter < current_tfArr_length) && (!direction)) {
                TFArr[j % 2 + (j / 4) * 2] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_1(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD *TFArr) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[2];
    WORD inv_temp[1];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X < H_BU_NUM and tfarr_dimension == 1
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            fwd_temp[idx] = TFArr[idx];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and LAST_H_BU_NUM <= X < H_BU_NUM and tfarr_dimension == 1
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            int offset = i_per_iter / 512;
            inv_temp[idx] = TFArr[idx * 2 + offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 2]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 4]);
            }

        }
    }
}

void TFGen1(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2];
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2];
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_1(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_1(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_1(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_1(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_2(tapa::istreams<WORD, 4>& tfToTfs, bool direction, 
                    WORD TFArr[][2]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 1, current_tfArr_length = 1;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            }
        }
    }
}


void tf_comp_2(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][2]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[4];
    WORD inv_temp[2];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X < H_BU_NUM and tfarr_dimension == 2
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 4; ++idx) {
            #pragma HLS UNROLL
            int tfarr_row = idx / 2;
            int tfarr_col = idx % 2;
            fwd_temp[idx] = TFArr[tfarr_row][tfarr_col];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 512;
            int index = i_per_iter_div_reuse / 2 + idx * 1;
            int offset = i_per_iter_div_reuse % 2;
            inv_temp[idx] = TFArr[index][offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 4]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 2]);
            }

        }
    }
}

void TFGen2(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][2];
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_0 factor=2 dim=2
    WORD TFArr_1[2][2];
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_1 factor=2 dim=2

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_2(tfToTfs, direction, TFArr_0);
                tf_comp_2(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_2(tfToTfs, direction, TFArr_1);
                tf_comp_2(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_3(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD TFArr[][4]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 14, current_tfArr_length = 2;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_3(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][4]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[1];
    WORD inv_temp[4];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            int index = (i_per_iter % 4) / 2 + idx * 2;
            int offset = (i_per_iter % 2) + ((i_per_iter / 4) % 2) * 2;
            fwd_temp[idx] = TFArr[index][offset];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 512;
            int base_offset = (i_per_iter_div_reuse % 8) * 2;
            inv_temp[idx * 2] = TFArr[idx][base_offset];
            inv_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 1]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 1]);
            }

        }
    }
}

void TFGen3(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][4];
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_0 factor=2 dim=2
    WORD TFArr_1[2][4];
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_1 factor=2 dim=2

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_3(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_3(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_3(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_3(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_4(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD TFArr[][8]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 12, current_tfArr_length = 4;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_4(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][8]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[2];
    WORD inv_temp[1];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int index = (i_per_iter % 2) / 2 + idx * 1;
            int offset = (i_per_iter % 2) + ((i_per_iter / 2) % 4) * 2;
            fwd_temp[idx] = TFArr[index][offset];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 64;
            int index = (i_per_iter_div_reuse % 4) / 2 + idx * 2;
            int offset = (i_per_iter_div_reuse % 2) + ((i_per_iter_div_reuse / 4) % 16) * 2;
            inv_temp[idx] = TFArr[index][offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 2]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 4]);
            }

        }
    }
}

void TFGen4(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][8];
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_0 factor=2 dim=2
    WORD TFArr_1[2][8];
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_1 factor=2 dim=2

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_4(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_4(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_4(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_4(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_5(tapa::istreams<WORD, 4>& tfToTfs, bool direction, 
                    WORD TFArr[][16]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 8, current_tfArr_length = 8;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            }
        }
    }
}


void tf_comp_5(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][16]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[4];
    WORD inv_temp[2];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int base_offset = (i_per_iter % 8) * 2;
            fwd_temp[idx * 2] = TFArr[idx][base_offset];
            fwd_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 64;
            int index = (i_per_iter_div_reuse % 2) / 2 + idx * 1;
            int offset = (i_per_iter_div_reuse % 2) + ((i_per_iter_div_reuse / 2) % 32) * 2;
            inv_temp[idx] = TFArr[index][offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 4]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 2]);
            }

        }
    }
}

void TFGen5(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][16];
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_0 factor=2 dim=2
    WORD TFArr_1[2][16];
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1
#pragma HLS array_partition type=cyclic variable=TFArr_1 factor=2 dim=2

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_5(tfToTfs, direction, TFArr_0);
                tf_comp_5(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_5(tfToTfs, direction, TFArr_1);
                tf_comp_5(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_6(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD TFArr[][32]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 112, current_tfArr_length = 16;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_6(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][32]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[1];
    WORD inv_temp[4];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            int index = (i_per_iter % 4) / 2 + idx * 2;
            int offset = (i_per_iter % 2) + ((i_per_iter / 4) % 16) * 2;
            fwd_temp[idx] = TFArr[index][offset];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 64;
            int base_offset = (i_per_iter_div_reuse % 64) * 2;
            inv_temp[idx * 2] = TFArr[idx][base_offset];
            inv_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 1]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 1]);
            }

        }
    }
}

void TFGen6(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][32];
#pragma HLS bind_storage variable=TFArr_0 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2][32];
#pragma HLS bind_storage variable=TFArr_1 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_6(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_6(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_6(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_6(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_7(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD TFArr[][64]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 96, current_tfArr_length = 32;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_7(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][64]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[2];
    WORD inv_temp[1];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int index = (i_per_iter % 2) / 2 + idx * 1;
            int offset = (i_per_iter % 2) + ((i_per_iter / 2) % 32) * 2;
            fwd_temp[idx] = TFArr[index][offset];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 8;
            int index = (i_per_iter_div_reuse % 4) / 2 + idx * 2;
            int offset = (i_per_iter_div_reuse % 2) + ((i_per_iter_div_reuse / 4) % 128) * 2;
            inv_temp[idx] = TFArr[index][offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 2]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 4]);
            }

        }
    }
}

void TFGen7(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][64];
#pragma HLS bind_storage variable=TFArr_0 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2][64];
#pragma HLS bind_storage variable=TFArr_1 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_7(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_7(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_7(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_7(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_8(tapa::istreams<WORD, 4>& tfToTfs, bool direction, 
                    WORD TFArr[][128]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 64, current_tfArr_length = 64;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            }
        }
    }
}


void tf_comp_8(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][128]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[4];
    WORD inv_temp[2];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int base_offset = (i_per_iter % 64) * 2;
            fwd_temp[idx * 2] = TFArr[idx][base_offset];
            fwd_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 8;
            int index = (i_per_iter_div_reuse % 2) / 2 + idx * 1;
            int offset = (i_per_iter_div_reuse % 2) + ((i_per_iter_div_reuse / 2) % 256) * 2;
            inv_temp[idx] = TFArr[index][offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 4]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 2]);
            }

        }
    }
}

void TFGen8(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][128];
#pragma HLS bind_storage variable=TFArr_0 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2][128];
#pragma HLS bind_storage variable=TFArr_1 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_8(tfToTfs, direction, TFArr_0);
                tf_comp_8(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_8(tfToTfs, direction, TFArr_1);
                tf_comp_8(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_9(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD TFArr[][256]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 896, current_tfArr_length = 128;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_9(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][256]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[1];
    WORD inv_temp[4];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            int index = (i_per_iter % 4) / 2 + idx * 2;
            int offset = (i_per_iter % 2) + ((i_per_iter / 4) % 128) * 2;
            fwd_temp[idx] = TFArr[index][offset];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 8;
            int base_offset = (i_per_iter_div_reuse % 512) * 2;
            inv_temp[idx * 2] = TFArr[idx][base_offset];
            inv_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 1]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 1]);
            }

        }
    }
}

void TFGen9(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][256];
#pragma HLS bind_storage variable=TFArr_0 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2][256];
#pragma HLS bind_storage variable=TFArr_1 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_9(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_9(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_9(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_9(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_10(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs, bool direction,
                    WORD TFArr[][512]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 768, current_tfArr_length = 256;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            } else {
                tfToNextTfs[j].write(read_val);
            }
        }
    }
}

void tf_comp_10(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][512]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[2];
    WORD inv_temp[1];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int index = (i_per_iter % 2) / 2 + idx * 1;
            int offset = (i_per_iter % 2) + ((i_per_iter / 2) % 256) * 2;
            fwd_temp[idx] = TFArr[index][offset];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 1; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 1;
            int index = (i_per_iter_div_reuse % 4) / 2 + idx * 2;
            int offset = (i_per_iter_div_reuse % 2) + ((i_per_iter_div_reuse / 4) % 1024) * 2;
            inv_temp[idx] = TFArr[index][offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 2]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 4]);
            }

        }
    }
}

void TFGen10(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& tfToNextTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][512];
#pragma HLS bind_storage variable=TFArr_0 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2][512];
#pragma HLS bind_storage variable=TFArr_1 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_10(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_10(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_10(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_10(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_11(tapa::istreams<WORD, 4>& tfToTfs, bool direction, 
                    WORD TFArr[][1024]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 512, current_tfArr_length = 512;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            }
        }
    }
}


void tf_comp_11(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][1024]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_temp[4];
    WORD inv_temp[2];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int base_offset = (i_per_iter % 512) * 2;
            fwd_temp[idx * 2] = TFArr[idx][base_offset];
            fwd_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }

        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / 1;
            int index = (i_per_iter_div_reuse % 2) / 2 + idx * 1;
            int offset = (i_per_iter_div_reuse % 2) + ((i_per_iter_div_reuse / 2) % 2048) * 2;
            inv_temp[idx] = TFArr[index][offset];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_temp[j % 4]);
            } else if (!direction) {
                inv_tfToBUs[j].write(inv_temp[j / 2]);
            }

        }
    }
}

void TFGen11(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][1024];
#pragma HLS bind_storage variable=TFArr_0 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2][1024];
#pragma HLS bind_storage variable=TFArr_1 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_11(tfToTfs, direction, TFArr_0);
                tf_comp_11(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_11(tfToTfs, direction, TFArr_1);
                tf_comp_11(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }


void tf_load_forward_12(tapa::istreams<WORD, 4>& tfToTfs, bool direction, 
                    WORD TFArr[][2048]) {
    #pragma HLS inline off

    VAR_TYPE_32 sum_tfArr_length = 1024, current_tfArr_length = 1024;
    VAR_TYPE_32 tf_counter = 0;

    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j){
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            }
        }
    }
}


void tf_comp_12(tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, 
                    WORD TFArr[][2048]) {
    #pragma HLS inline off

    VAR_TYPE_32 singleLoopIter = 1024;
    WORD fwd_inv_temp[4];

    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {
        #pragma HLS PIPELINE II=1

        // Assign values to fwd_inv_temp when fwd_flag == inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_TEMP:for(int idx = 0; idx < 2; ++idx) {
            #pragma HLS UNROLL
            int base_offset = (i_per_iter % 1024) * 2;
            fwd_inv_temp[idx * 2] = TFArr[idx][base_offset];
            fwd_inv_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }

        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < 4; ++j) {
            #pragma HLS UNROLL

            if (direction) {
                fwd_tfToBUs[j].write(fwd_inv_temp[j % 4]);
            } else if (!direction) {
                inv_tfToBUs[j].write(fwd_inv_temp[j / 1]);
            }

        }
    }
}

void TFGen12(tapa::istreams<WORD, 4>& tfToTfs,
                    tapa::ostreams<WORD, 4>& fwd_tfToBUs,
                    tapa::ostreams<WORD, 4>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {

    WORD TFArr_0[2][2048];
#pragma HLS bind_storage variable=TFArr_0 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_0 dim=1
    WORD TFArr_1[2][2048];
#pragma HLS bind_storage variable=TFArr_1 type=RAM_T2P impl=URAM
#pragma HLS array_partition type=complete variable=TFArr_1 dim=1

        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {
            if ((iteration_idx % 2) == 0) {
                tf_load_forward_12(tfToTfs, direction, TFArr_0);
                tf_comp_12(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            } else {
                tf_load_forward_12(tfToTfs, direction, TFArr_1);
                tf_comp_12(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }
        }
    }



// /********************************************************************************************
// * Top kernel *
// ********************************************************************************************/

void NTT_kernel(
    tapa::mmap<POLY_WIDE_DATA> polyVectorIn_G0,
    tapa::mmap<TF_WIDE_DATA> TFArr_G0,
    tapa::mmap<TF_WIDE_DATA> TFArr_G1,
    tapa::mmap<TF_WIDE_DATA> TFArr_G2,
    tapa::mmap<TF_WIDE_DATA> TFArr_G3,
    tapa::mmap<TF_WIDE_DATA> TFArr_G4,
    tapa::mmap<POLY_WIDE_DATA> polyVectorOut_G0,
    WORD q0,
    WORD twoInverse0,
    WORD_PLUS3 factor0,
    bool direction,
    VAR_TYPE_16 iter
    )
{

    /* Limb0 */
    // Forward and Inverse Shuffler streams
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_shuffler_to_BU_L0_0("fwd_shuffler_to_BU_L0_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_shuffler_to_BU_L0_0("inv_shuffler_to_BU_L0_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_shuffler_to_BU_L0_1("fwd_shuffler_to_BU_L0_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_shuffler_to_BU_L0_1("inv_shuffler_to_BU_L0_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_shuffler_to_BU_L0_2("fwd_shuffler_to_BU_L0_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_shuffler_to_BU_L0_2("inv_shuffler_to_BU_L0_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_shuffler_to_BU_L0_3("fwd_shuffler_to_BU_L0_3");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_shuffler_to_BU_L0_3("inv_shuffler_to_BU_L0_3");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_shuffler_to_BU_L0_4("fwd_shuffler_to_BU_L0_4");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_shuffler_to_BU_L0_4("inv_shuffler_to_BU_L0_4");


    // BU to Shuffler streams
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_BU_to_shuffler_L0_0("fwd_BU_to_shuffler_L0_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_BU_to_shuffler_L0_0("inv_BU_to_shuffler_L0_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_BU_to_shuffler_L0_1("fwd_BU_to_shuffler_L0_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_BU_to_shuffler_L0_1("inv_BU_to_shuffler_L0_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_BU_to_shuffler_L0_2("fwd_BU_to_shuffler_L0_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_BU_to_shuffler_L0_2("inv_BU_to_shuffler_L0_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_BU_to_shuffler_L0_3("fwd_BU_to_shuffler_L0_3");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_BU_to_shuffler_L0_3("inv_BU_to_shuffler_L0_3");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_BU_to_shuffler_L0_4("fwd_BU_to_shuffler_L0_4");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_BU_to_shuffler_L0_4("inv_BU_to_shuffler_L0_4");



    // Mid BU streams
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_0_0("fwd_midVals_L0_0_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_0_0("inv_midVals_L0_0_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_1_0("fwd_midVals_L0_1_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_1_0("inv_midVals_L0_1_0");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_0_1("fwd_midVals_L0_0_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_0_1("inv_midVals_L0_0_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_1_1("fwd_midVals_L0_1_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_1_1("inv_midVals_L0_1_1");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_0_2("fwd_midVals_L0_0_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_0_2("inv_midVals_L0_0_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_1_2("fwd_midVals_L0_1_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_1_2("inv_midVals_L0_1_2");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_0_3("fwd_midVals_L0_0_3");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_0_3("inv_midVals_L0_0_3");
    tapa::streams<WORD, 8, FIFO_DEPTH> fwd_midVals_L0_1_3("fwd_midVals_L0_1_3");
    tapa::streams<WORD, 8, FIFO_DEPTH> inv_midVals_L0_1_3("inv_midVals_L0_1_3");


    // TF streams
    tapa::stream<TF_WIDE_DATA_PER_PARA_LIMB, FIFO_DEPTH> tf_MM2S_to_loadTF_L0_0("tf_MM2S_to_loadTF_L0_0");
    tapa::stream<TF_WIDE_DATA_PER_PARA_LIMB, FIFO_DEPTH> tf_MM2S_to_loadTF_L0_1("tf_MM2S_to_loadTF_L0_1");
    tapa::stream<TF_WIDE_DATA_PER_PARA_LIMB, FIFO_DEPTH> tf_MM2S_to_loadTF_L0_2("tf_MM2S_to_loadTF_L0_2");
    tapa::stream<TF_WIDE_DATA_PER_PARA_LIMB, FIFO_DEPTH> tf_MM2S_to_loadTF_L0_3("tf_MM2S_to_loadTF_L0_3");
    tapa::stream<TF_WIDE_DATA_PER_PARA_LIMB, FIFO_DEPTH> tf_MM2S_to_loadTF_L0_4("tf_MM2S_to_loadTF_L0_4");


    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_0("tf_loadTF_to_TFGen_L0_0");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_1("tf_loadTF_to_TFGen_L0_1");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_2("tf_loadTF_to_TFGen_L0_2");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_3("tf_loadTF_to_TFGen_L0_3");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_4("tf_loadTF_to_TFGen_L0_4");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_5("tf_loadTF_to_TFGen_L0_5");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_6("tf_loadTF_to_TFGen_L0_6");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_7("tf_loadTF_to_TFGen_L0_7");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_8("tf_loadTF_to_TFGen_L0_8");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_9("tf_loadTF_to_TFGen_L0_9");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_10("tf_loadTF_to_TFGen_L0_10");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_11("tf_loadTF_to_TFGen_L0_11");
    tapa::streams<WORD, 4, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L0_12("tf_loadTF_to_TFGen_L0_12");

    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_0("tf_fwd_TFGen_to_BU_L0_0");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_1("tf_fwd_TFGen_to_BU_L0_1");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_2("tf_fwd_TFGen_to_BU_L0_2");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_3("tf_fwd_TFGen_to_BU_L0_3");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_4("tf_fwd_TFGen_to_BU_L0_4");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_5("tf_fwd_TFGen_to_BU_L0_5");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_6("tf_fwd_TFGen_to_BU_L0_6");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_7("tf_fwd_TFGen_to_BU_L0_7");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_8("tf_fwd_TFGen_to_BU_L0_8");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_9("tf_fwd_TFGen_to_BU_L0_9");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_10("tf_fwd_TFGen_to_BU_L0_10");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_11("tf_fwd_TFGen_to_BU_L0_11");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L0_12("tf_fwd_TFGen_to_BU_L0_12");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_0("tf_inv_TFGen_to_BU_L0_0");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_1("tf_inv_TFGen_to_BU_L0_1");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_2("tf_inv_TFGen_to_BU_L0_2");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_3("tf_inv_TFGen_to_BU_L0_3");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_4("tf_inv_TFGen_to_BU_L0_4");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_5("tf_inv_TFGen_to_BU_L0_5");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_6("tf_inv_TFGen_to_BU_L0_6");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_7("tf_inv_TFGen_to_BU_L0_7");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_8("tf_inv_TFGen_to_BU_L0_8");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_9("tf_inv_TFGen_to_BU_L0_9");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_10("tf_inv_TFGen_to_BU_L0_10");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_11("tf_inv_TFGen_to_BU_L0_11");
    tapa::streams<WORD, 4, FIFO_DEPTH> tf_inv_TFGen_to_BU_L0_12("tf_inv_TFGen_to_BU_L0_12");

    tapa::task()
        //polynomial loading/storing tasks: FWD loading and INV storing
        .invoke(Mmap2Stream_poly_1_limbs, polyVectorIn_G0, fwd_shuffler_to_BU_L0_0, inv_BU_to_shuffler_L0_4, direction, iter)

        //polynomial loading/storing tasks: FWD storing and INV loading
        .invoke(Stream2Mmap_poly_1_limbs, polyVectorOut_G0, fwd_BU_to_shuffler_L0_4, inv_shuffler_to_BU_L0_0, direction, iter)

        //TF loading tasks
        .invoke(Mmap2Stream_tf_1_limbs, TFArr_G0, tf_MM2S_to_loadTF_L0_0, 3, iter)
        .invoke(Mmap2Stream_tf_1_limbs, TFArr_G1, tf_MM2S_to_loadTF_L0_1, 14, iter)
        .invoke(Mmap2Stream_tf_1_limbs, TFArr_G2, tf_MM2S_to_loadTF_L0_2, 112, iter)
        .invoke(Mmap2Stream_tf_1_limbs, TFArr_G3, tf_MM2S_to_loadTF_L0_3, 896, iter)
        .invoke(Mmap2Stream_tf_1_limbs, TFArr_G4, tf_MM2S_to_loadTF_L0_4, 1024, iter)

        /* Limb0 */
        //TF split tasks
        .invoke<tapa::detach>(load_tf, tf_MM2S_to_loadTF_L0_0, tf_loadTF_to_TFGen_L0_0, direction, 3, iter)
        .invoke<tapa::detach>(load_tf, tf_MM2S_to_loadTF_L0_1, tf_loadTF_to_TFGen_L0_3, direction, 14, iter)
        .invoke<tapa::detach>(load_tf, tf_MM2S_to_loadTF_L0_2, tf_loadTF_to_TFGen_L0_6, direction, 112, iter)
        .invoke<tapa::detach>(load_tf, tf_MM2S_to_loadTF_L0_3, tf_loadTF_to_TFGen_L0_9, direction, 896, iter)
        .invoke<tapa::detach>(load_tf, tf_MM2S_to_loadTF_L0_4, tf_loadTF_to_TFGen_L0_12, direction, 1024, iter)

        //BUG 0
        .invoke(TFGen0, tf_loadTF_to_TFGen_L0_0, tf_loadTF_to_TFGen_L0_1, tf_fwd_TFGen_to_BU_L0_0, tf_inv_TFGen_to_BU_L0_0, 0, direction, iter)

        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_0[0], fwd_shuffler_to_BU_L0_0[1], inv_BU_to_shuffler_L0_4[0], inv_BU_to_shuffler_L0_4[1], tf_fwd_TFGen_to_BU_L0_0[0], tf_inv_TFGen_to_BU_L0_12[0], fwd_midVals_L0_0_0[0], fwd_midVals_L0_0_0[1], inv_midVals_L0_0_0[0], inv_midVals_L0_0_0[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_0[2], fwd_shuffler_to_BU_L0_0[3], inv_BU_to_shuffler_L0_4[2], inv_BU_to_shuffler_L0_4[3], tf_fwd_TFGen_to_BU_L0_0[1], tf_inv_TFGen_to_BU_L0_12[1], fwd_midVals_L0_0_0[2], fwd_midVals_L0_0_0[3], inv_midVals_L0_0_0[2], inv_midVals_L0_0_0[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_0[4], fwd_shuffler_to_BU_L0_0[5], inv_BU_to_shuffler_L0_4[4], inv_BU_to_shuffler_L0_4[5], tf_fwd_TFGen_to_BU_L0_0[2], tf_inv_TFGen_to_BU_L0_12[2], fwd_midVals_L0_0_0[4], fwd_midVals_L0_0_0[5], inv_midVals_L0_0_0[4], inv_midVals_L0_0_0[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_0[6], fwd_shuffler_to_BU_L0_0[7], inv_BU_to_shuffler_L0_4[6], inv_BU_to_shuffler_L0_4[7], tf_fwd_TFGen_to_BU_L0_0[3], tf_inv_TFGen_to_BU_L0_12[3], fwd_midVals_L0_0_0[6], fwd_midVals_L0_0_0[7], inv_midVals_L0_0_0[6], inv_midVals_L0_0_0[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen1, tf_loadTF_to_TFGen_L0_1, tf_loadTF_to_TFGen_L0_2, tf_fwd_TFGen_to_BU_L0_1, tf_inv_TFGen_to_BU_L0_1, 1, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_0[0], fwd_midVals_L0_0_0[2], inv_midVals_L0_0_0[0], inv_midVals_L0_0_0[2], tf_fwd_TFGen_to_BU_L0_1[0], tf_inv_TFGen_to_BU_L0_11[0], fwd_midVals_L0_1_0[0], fwd_midVals_L0_1_0[2], inv_midVals_L0_1_0[0], inv_midVals_L0_1_0[2], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_0[1], fwd_midVals_L0_0_0[3], inv_midVals_L0_0_0[1], inv_midVals_L0_0_0[3], tf_fwd_TFGen_to_BU_L0_1[1], tf_inv_TFGen_to_BU_L0_11[1], fwd_midVals_L0_1_0[1], fwd_midVals_L0_1_0[3], inv_midVals_L0_1_0[1], inv_midVals_L0_1_0[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_0[4], fwd_midVals_L0_0_0[6], inv_midVals_L0_0_0[4], inv_midVals_L0_0_0[6], tf_fwd_TFGen_to_BU_L0_1[2], tf_inv_TFGen_to_BU_L0_11[2], fwd_midVals_L0_1_0[4], fwd_midVals_L0_1_0[6], inv_midVals_L0_1_0[4], inv_midVals_L0_1_0[6], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_0[5], fwd_midVals_L0_0_0[7], inv_midVals_L0_0_0[5], inv_midVals_L0_0_0[7], tf_fwd_TFGen_to_BU_L0_1[3], tf_inv_TFGen_to_BU_L0_11[3], fwd_midVals_L0_1_0[5], fwd_midVals_L0_1_0[7], inv_midVals_L0_1_0[5], inv_midVals_L0_1_0[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen2, tf_loadTF_to_TFGen_L0_2, tf_fwd_TFGen_to_BU_L0_2, tf_inv_TFGen_to_BU_L0_2, 2, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_0[0], fwd_midVals_L0_1_0[4], inv_midVals_L0_1_0[0], inv_midVals_L0_1_0[4], tf_fwd_TFGen_to_BU_L0_2[0], tf_inv_TFGen_to_BU_L0_10[0], fwd_BU_to_shuffler_L0_0[0], fwd_BU_to_shuffler_L0_0[1], inv_shuffler_to_BU_L0_4[0], inv_shuffler_to_BU_L0_4[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_0[1], fwd_midVals_L0_1_0[5], inv_midVals_L0_1_0[1], inv_midVals_L0_1_0[5], tf_fwd_TFGen_to_BU_L0_2[1], tf_inv_TFGen_to_BU_L0_10[1], fwd_BU_to_shuffler_L0_0[2], fwd_BU_to_shuffler_L0_0[3], inv_shuffler_to_BU_L0_4[2], inv_shuffler_to_BU_L0_4[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_0[2], fwd_midVals_L0_1_0[6], inv_midVals_L0_1_0[2], inv_midVals_L0_1_0[6], tf_fwd_TFGen_to_BU_L0_2[2], tf_inv_TFGen_to_BU_L0_10[2], fwd_BU_to_shuffler_L0_0[4], fwd_BU_to_shuffler_L0_0[5], inv_shuffler_to_BU_L0_4[4], inv_shuffler_to_BU_L0_4[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_0[3], fwd_midVals_L0_1_0[7], inv_midVals_L0_1_0[3], inv_midVals_L0_1_0[7], tf_fwd_TFGen_to_BU_L0_2[3], tf_inv_TFGen_to_BU_L0_10[3], fwd_BU_to_shuffler_L0_0[6], fwd_BU_to_shuffler_L0_0[7], inv_shuffler_to_BU_L0_4[6], inv_shuffler_to_BU_L0_4[7], q0, twoInverse0, factor0, iter)

        .invoke(shuffler_1, fwd_BU_to_shuffler_L0_0, inv_BU_to_shuffler_L0_3, fwd_shuffler_to_BU_L0_1, inv_shuffler_to_BU_L0_4, 0, direction, iter)

        //BUG 1
        .invoke(TFGen3, tf_loadTF_to_TFGen_L0_3, tf_loadTF_to_TFGen_L0_4, tf_fwd_TFGen_to_BU_L0_3, tf_inv_TFGen_to_BU_L0_3, 3, direction, iter)

        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_1[0], fwd_shuffler_to_BU_L0_1[1], inv_BU_to_shuffler_L0_3[0], inv_BU_to_shuffler_L0_3[1], tf_fwd_TFGen_to_BU_L0_3[0], tf_inv_TFGen_to_BU_L0_9[0], fwd_midVals_L0_0_1[0], fwd_midVals_L0_0_1[1], inv_midVals_L0_0_1[0], inv_midVals_L0_0_1[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_1[2], fwd_shuffler_to_BU_L0_1[3], inv_BU_to_shuffler_L0_3[2], inv_BU_to_shuffler_L0_3[3], tf_fwd_TFGen_to_BU_L0_3[1], tf_inv_TFGen_to_BU_L0_9[1], fwd_midVals_L0_0_1[2], fwd_midVals_L0_0_1[3], inv_midVals_L0_0_1[2], inv_midVals_L0_0_1[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_1[4], fwd_shuffler_to_BU_L0_1[5], inv_BU_to_shuffler_L0_3[4], inv_BU_to_shuffler_L0_3[5], tf_fwd_TFGen_to_BU_L0_3[2], tf_inv_TFGen_to_BU_L0_9[2], fwd_midVals_L0_0_1[4], fwd_midVals_L0_0_1[5], inv_midVals_L0_0_1[4], inv_midVals_L0_0_1[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_1[6], fwd_shuffler_to_BU_L0_1[7], inv_BU_to_shuffler_L0_3[6], inv_BU_to_shuffler_L0_3[7], tf_fwd_TFGen_to_BU_L0_3[3], tf_inv_TFGen_to_BU_L0_9[3], fwd_midVals_L0_0_1[6], fwd_midVals_L0_0_1[7], inv_midVals_L0_0_1[6], inv_midVals_L0_0_1[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen4, tf_loadTF_to_TFGen_L0_4, tf_loadTF_to_TFGen_L0_5, tf_fwd_TFGen_to_BU_L0_4, tf_inv_TFGen_to_BU_L0_4, 4, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_1[0], fwd_midVals_L0_0_1[2], inv_midVals_L0_0_1[0], inv_midVals_L0_0_1[2], tf_fwd_TFGen_to_BU_L0_4[0], tf_inv_TFGen_to_BU_L0_8[0], fwd_midVals_L0_1_1[0], fwd_midVals_L0_1_1[2], inv_midVals_L0_1_1[0], inv_midVals_L0_1_1[2], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_1[1], fwd_midVals_L0_0_1[3], inv_midVals_L0_0_1[1], inv_midVals_L0_0_1[3], tf_fwd_TFGen_to_BU_L0_4[1], tf_inv_TFGen_to_BU_L0_8[1], fwd_midVals_L0_1_1[1], fwd_midVals_L0_1_1[3], inv_midVals_L0_1_1[1], inv_midVals_L0_1_1[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_1[4], fwd_midVals_L0_0_1[6], inv_midVals_L0_0_1[4], inv_midVals_L0_0_1[6], tf_fwd_TFGen_to_BU_L0_4[2], tf_inv_TFGen_to_BU_L0_8[2], fwd_midVals_L0_1_1[4], fwd_midVals_L0_1_1[6], inv_midVals_L0_1_1[4], inv_midVals_L0_1_1[6], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_1[5], fwd_midVals_L0_0_1[7], inv_midVals_L0_0_1[5], inv_midVals_L0_0_1[7], tf_fwd_TFGen_to_BU_L0_4[3], tf_inv_TFGen_to_BU_L0_8[3], fwd_midVals_L0_1_1[5], fwd_midVals_L0_1_1[7], inv_midVals_L0_1_1[5], inv_midVals_L0_1_1[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen5, tf_loadTF_to_TFGen_L0_5, tf_fwd_TFGen_to_BU_L0_5, tf_inv_TFGen_to_BU_L0_5, 5, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_1[0], fwd_midVals_L0_1_1[4], inv_midVals_L0_1_1[0], inv_midVals_L0_1_1[4], tf_fwd_TFGen_to_BU_L0_5[0], tf_inv_TFGen_to_BU_L0_7[0], fwd_BU_to_shuffler_L0_1[0], fwd_BU_to_shuffler_L0_1[1], inv_shuffler_to_BU_L0_3[0], inv_shuffler_to_BU_L0_3[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_1[1], fwd_midVals_L0_1_1[5], inv_midVals_L0_1_1[1], inv_midVals_L0_1_1[5], tf_fwd_TFGen_to_BU_L0_5[1], tf_inv_TFGen_to_BU_L0_7[1], fwd_BU_to_shuffler_L0_1[2], fwd_BU_to_shuffler_L0_1[3], inv_shuffler_to_BU_L0_3[2], inv_shuffler_to_BU_L0_3[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_1[2], fwd_midVals_L0_1_1[6], inv_midVals_L0_1_1[2], inv_midVals_L0_1_1[6], tf_fwd_TFGen_to_BU_L0_5[2], tf_inv_TFGen_to_BU_L0_7[2], fwd_BU_to_shuffler_L0_1[4], fwd_BU_to_shuffler_L0_1[5], inv_shuffler_to_BU_L0_3[4], inv_shuffler_to_BU_L0_3[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_1[3], fwd_midVals_L0_1_1[7], inv_midVals_L0_1_1[3], inv_midVals_L0_1_1[7], tf_fwd_TFGen_to_BU_L0_5[3], tf_inv_TFGen_to_BU_L0_7[3], fwd_BU_to_shuffler_L0_1[6], fwd_BU_to_shuffler_L0_1[7], inv_shuffler_to_BU_L0_3[6], inv_shuffler_to_BU_L0_3[7], q0, twoInverse0, factor0, iter)

        .invoke(shuffler_2, fwd_BU_to_shuffler_L0_1, inv_BU_to_shuffler_L0_2, fwd_shuffler_to_BU_L0_2, inv_shuffler_to_BU_L0_3, 3, direction, iter)

        //BUG 2
        .invoke(TFGen6, tf_loadTF_to_TFGen_L0_6, tf_loadTF_to_TFGen_L0_7, tf_fwd_TFGen_to_BU_L0_6, tf_inv_TFGen_to_BU_L0_6, 6, direction, iter)

        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_2[0], fwd_shuffler_to_BU_L0_2[1], inv_BU_to_shuffler_L0_2[0], inv_BU_to_shuffler_L0_2[1], tf_fwd_TFGen_to_BU_L0_6[0], tf_inv_TFGen_to_BU_L0_6[0], fwd_midVals_L0_0_2[0], fwd_midVals_L0_0_2[1], inv_midVals_L0_0_2[0], inv_midVals_L0_0_2[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_2[2], fwd_shuffler_to_BU_L0_2[3], inv_BU_to_shuffler_L0_2[2], inv_BU_to_shuffler_L0_2[3], tf_fwd_TFGen_to_BU_L0_6[1], tf_inv_TFGen_to_BU_L0_6[1], fwd_midVals_L0_0_2[2], fwd_midVals_L0_0_2[3], inv_midVals_L0_0_2[2], inv_midVals_L0_0_2[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_2[4], fwd_shuffler_to_BU_L0_2[5], inv_BU_to_shuffler_L0_2[4], inv_BU_to_shuffler_L0_2[5], tf_fwd_TFGen_to_BU_L0_6[2], tf_inv_TFGen_to_BU_L0_6[2], fwd_midVals_L0_0_2[4], fwd_midVals_L0_0_2[5], inv_midVals_L0_0_2[4], inv_midVals_L0_0_2[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_2[6], fwd_shuffler_to_BU_L0_2[7], inv_BU_to_shuffler_L0_2[6], inv_BU_to_shuffler_L0_2[7], tf_fwd_TFGen_to_BU_L0_6[3], tf_inv_TFGen_to_BU_L0_6[3], fwd_midVals_L0_0_2[6], fwd_midVals_L0_0_2[7], inv_midVals_L0_0_2[6], inv_midVals_L0_0_2[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen7, tf_loadTF_to_TFGen_L0_7, tf_loadTF_to_TFGen_L0_8, tf_fwd_TFGen_to_BU_L0_7, tf_inv_TFGen_to_BU_L0_7, 7, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_2[0], fwd_midVals_L0_0_2[2], inv_midVals_L0_0_2[0], inv_midVals_L0_0_2[2], tf_fwd_TFGen_to_BU_L0_7[0], tf_inv_TFGen_to_BU_L0_5[0], fwd_midVals_L0_1_2[0], fwd_midVals_L0_1_2[2], inv_midVals_L0_1_2[0], inv_midVals_L0_1_2[2], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_2[1], fwd_midVals_L0_0_2[3], inv_midVals_L0_0_2[1], inv_midVals_L0_0_2[3], tf_fwd_TFGen_to_BU_L0_7[1], tf_inv_TFGen_to_BU_L0_5[1], fwd_midVals_L0_1_2[1], fwd_midVals_L0_1_2[3], inv_midVals_L0_1_2[1], inv_midVals_L0_1_2[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_2[4], fwd_midVals_L0_0_2[6], inv_midVals_L0_0_2[4], inv_midVals_L0_0_2[6], tf_fwd_TFGen_to_BU_L0_7[2], tf_inv_TFGen_to_BU_L0_5[2], fwd_midVals_L0_1_2[4], fwd_midVals_L0_1_2[6], inv_midVals_L0_1_2[4], inv_midVals_L0_1_2[6], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_2[5], fwd_midVals_L0_0_2[7], inv_midVals_L0_0_2[5], inv_midVals_L0_0_2[7], tf_fwd_TFGen_to_BU_L0_7[3], tf_inv_TFGen_to_BU_L0_5[3], fwd_midVals_L0_1_2[5], fwd_midVals_L0_1_2[7], inv_midVals_L0_1_2[5], inv_midVals_L0_1_2[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen8, tf_loadTF_to_TFGen_L0_8, tf_fwd_TFGen_to_BU_L0_8, tf_inv_TFGen_to_BU_L0_8, 8, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_2[0], fwd_midVals_L0_1_2[4], inv_midVals_L0_1_2[0], inv_midVals_L0_1_2[4], tf_fwd_TFGen_to_BU_L0_8[0], tf_inv_TFGen_to_BU_L0_4[0], fwd_BU_to_shuffler_L0_2[0], fwd_BU_to_shuffler_L0_2[1], inv_shuffler_to_BU_L0_2[0], inv_shuffler_to_BU_L0_2[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_2[1], fwd_midVals_L0_1_2[5], inv_midVals_L0_1_2[1], inv_midVals_L0_1_2[5], tf_fwd_TFGen_to_BU_L0_8[1], tf_inv_TFGen_to_BU_L0_4[1], fwd_BU_to_shuffler_L0_2[2], fwd_BU_to_shuffler_L0_2[3], inv_shuffler_to_BU_L0_2[2], inv_shuffler_to_BU_L0_2[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_2[2], fwd_midVals_L0_1_2[6], inv_midVals_L0_1_2[2], inv_midVals_L0_1_2[6], tf_fwd_TFGen_to_BU_L0_8[2], tf_inv_TFGen_to_BU_L0_4[2], fwd_BU_to_shuffler_L0_2[4], fwd_BU_to_shuffler_L0_2[5], inv_shuffler_to_BU_L0_2[4], inv_shuffler_to_BU_L0_2[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_2[3], fwd_midVals_L0_1_2[7], inv_midVals_L0_1_2[3], inv_midVals_L0_1_2[7], tf_fwd_TFGen_to_BU_L0_8[3], tf_inv_TFGen_to_BU_L0_4[3], fwd_BU_to_shuffler_L0_2[6], fwd_BU_to_shuffler_L0_2[7], inv_shuffler_to_BU_L0_2[6], inv_shuffler_to_BU_L0_2[7], q0, twoInverse0, factor0, iter)

        .invoke(shuffler_3, fwd_BU_to_shuffler_L0_2, inv_BU_to_shuffler_L0_1, fwd_shuffler_to_BU_L0_3, inv_shuffler_to_BU_L0_2, 6, direction, iter)

        //BUG 3
        .invoke(TFGen9, tf_loadTF_to_TFGen_L0_9, tf_loadTF_to_TFGen_L0_10, tf_fwd_TFGen_to_BU_L0_9, tf_inv_TFGen_to_BU_L0_9, 9, direction, iter)

        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_3[0], fwd_shuffler_to_BU_L0_3[1], inv_BU_to_shuffler_L0_1[0], inv_BU_to_shuffler_L0_1[1], tf_fwd_TFGen_to_BU_L0_9[0], tf_inv_TFGen_to_BU_L0_3[0], fwd_midVals_L0_0_3[0], fwd_midVals_L0_0_3[1], inv_midVals_L0_0_3[0], inv_midVals_L0_0_3[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_3[2], fwd_shuffler_to_BU_L0_3[3], inv_BU_to_shuffler_L0_1[2], inv_BU_to_shuffler_L0_1[3], tf_fwd_TFGen_to_BU_L0_9[1], tf_inv_TFGen_to_BU_L0_3[1], fwd_midVals_L0_0_3[2], fwd_midVals_L0_0_3[3], inv_midVals_L0_0_3[2], inv_midVals_L0_0_3[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_3[4], fwd_shuffler_to_BU_L0_3[5], inv_BU_to_shuffler_L0_1[4], inv_BU_to_shuffler_L0_1[5], tf_fwd_TFGen_to_BU_L0_9[2], tf_inv_TFGen_to_BU_L0_3[2], fwd_midVals_L0_0_3[4], fwd_midVals_L0_0_3[5], inv_midVals_L0_0_3[4], inv_midVals_L0_0_3[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_3[6], fwd_shuffler_to_BU_L0_3[7], inv_BU_to_shuffler_L0_1[6], inv_BU_to_shuffler_L0_1[7], tf_fwd_TFGen_to_BU_L0_9[3], tf_inv_TFGen_to_BU_L0_3[3], fwd_midVals_L0_0_3[6], fwd_midVals_L0_0_3[7], inv_midVals_L0_0_3[6], inv_midVals_L0_0_3[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen10, tf_loadTF_to_TFGen_L0_10, tf_loadTF_to_TFGen_L0_11, tf_fwd_TFGen_to_BU_L0_10, tf_inv_TFGen_to_BU_L0_10, 10, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_3[0], fwd_midVals_L0_0_3[2], inv_midVals_L0_0_3[0], inv_midVals_L0_0_3[2], tf_fwd_TFGen_to_BU_L0_10[0], tf_inv_TFGen_to_BU_L0_2[0], fwd_midVals_L0_1_3[0], fwd_midVals_L0_1_3[2], inv_midVals_L0_1_3[0], inv_midVals_L0_1_3[2], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_3[1], fwd_midVals_L0_0_3[3], inv_midVals_L0_0_3[1], inv_midVals_L0_0_3[3], tf_fwd_TFGen_to_BU_L0_10[1], tf_inv_TFGen_to_BU_L0_2[1], fwd_midVals_L0_1_3[1], fwd_midVals_L0_1_3[3], inv_midVals_L0_1_3[1], inv_midVals_L0_1_3[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_3[4], fwd_midVals_L0_0_3[6], inv_midVals_L0_0_3[4], inv_midVals_L0_0_3[6], tf_fwd_TFGen_to_BU_L0_10[2], tf_inv_TFGen_to_BU_L0_2[2], fwd_midVals_L0_1_3[4], fwd_midVals_L0_1_3[6], inv_midVals_L0_1_3[4], inv_midVals_L0_1_3[6], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_0_3[5], fwd_midVals_L0_0_3[7], inv_midVals_L0_0_3[5], inv_midVals_L0_0_3[7], tf_fwd_TFGen_to_BU_L0_10[3], tf_inv_TFGen_to_BU_L0_2[3], fwd_midVals_L0_1_3[5], fwd_midVals_L0_1_3[7], inv_midVals_L0_1_3[5], inv_midVals_L0_1_3[7], q0, twoInverse0, factor0, iter)

        .invoke(TFGen11, tf_loadTF_to_TFGen_L0_11, tf_fwd_TFGen_to_BU_L0_11, tf_inv_TFGen_to_BU_L0_11, 11, direction, iter)

        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_3[0], fwd_midVals_L0_1_3[4], inv_midVals_L0_1_3[0], inv_midVals_L0_1_3[4], tf_fwd_TFGen_to_BU_L0_11[0], tf_inv_TFGen_to_BU_L0_1[0], fwd_BU_to_shuffler_L0_3[0], fwd_BU_to_shuffler_L0_3[1], inv_shuffler_to_BU_L0_1[0], inv_shuffler_to_BU_L0_1[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_3[1], fwd_midVals_L0_1_3[5], inv_midVals_L0_1_3[1], inv_midVals_L0_1_3[5], tf_fwd_TFGen_to_BU_L0_11[1], tf_inv_TFGen_to_BU_L0_1[1], fwd_BU_to_shuffler_L0_3[2], fwd_BU_to_shuffler_L0_3[3], inv_shuffler_to_BU_L0_1[2], inv_shuffler_to_BU_L0_1[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_3[2], fwd_midVals_L0_1_3[6], inv_midVals_L0_1_3[2], inv_midVals_L0_1_3[6], tf_fwd_TFGen_to_BU_L0_11[2], tf_inv_TFGen_to_BU_L0_1[2], fwd_BU_to_shuffler_L0_3[4], fwd_BU_to_shuffler_L0_3[5], inv_shuffler_to_BU_L0_1[4], inv_shuffler_to_BU_L0_1[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_midVals_L0_1_3[3], fwd_midVals_L0_1_3[7], inv_midVals_L0_1_3[3], inv_midVals_L0_1_3[7], tf_fwd_TFGen_to_BU_L0_11[3], tf_inv_TFGen_to_BU_L0_1[3], fwd_BU_to_shuffler_L0_3[6], fwd_BU_to_shuffler_L0_3[7], inv_shuffler_to_BU_L0_1[6], inv_shuffler_to_BU_L0_1[7], q0, twoInverse0, factor0, iter)

        .invoke(shuffler_4, fwd_BU_to_shuffler_L0_3, inv_BU_to_shuffler_L0_0, fwd_shuffler_to_BU_L0_4, inv_shuffler_to_BU_L0_1, 9, direction, iter)

        //BUG 4
        .invoke(TFGen12, tf_loadTF_to_TFGen_L0_12, tf_fwd_TFGen_to_BU_L0_12, tf_inv_TFGen_to_BU_L0_12, 12, direction, iter)

        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_4[0], fwd_shuffler_to_BU_L0_4[1], inv_BU_to_shuffler_L0_0[0], inv_BU_to_shuffler_L0_0[1], tf_fwd_TFGen_to_BU_L0_12[0], tf_inv_TFGen_to_BU_L0_0[0], fwd_BU_to_shuffler_L0_4[0], fwd_BU_to_shuffler_L0_4[1], inv_shuffler_to_BU_L0_0[0], inv_shuffler_to_BU_L0_0[1], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_4[2], fwd_shuffler_to_BU_L0_4[3], inv_BU_to_shuffler_L0_0[2], inv_BU_to_shuffler_L0_0[3], tf_fwd_TFGen_to_BU_L0_12[1], tf_inv_TFGen_to_BU_L0_0[1], fwd_BU_to_shuffler_L0_4[2], fwd_BU_to_shuffler_L0_4[3], inv_shuffler_to_BU_L0_0[2], inv_shuffler_to_BU_L0_0[3], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_4[4], fwd_shuffler_to_BU_L0_4[5], inv_BU_to_shuffler_L0_0[4], inv_BU_to_shuffler_L0_0[5], tf_fwd_TFGen_to_BU_L0_12[2], tf_inv_TFGen_to_BU_L0_0[2], fwd_BU_to_shuffler_L0_4[4], fwd_BU_to_shuffler_L0_4[5], inv_shuffler_to_BU_L0_0[4], inv_shuffler_to_BU_L0_0[5], q0, twoInverse0, factor0, iter)
        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L0_4[6], fwd_shuffler_to_BU_L0_4[7], inv_BU_to_shuffler_L0_0[6], inv_BU_to_shuffler_L0_0[7], tf_fwd_TFGen_to_BU_L0_12[3], tf_inv_TFGen_to_BU_L0_0[3], fwd_BU_to_shuffler_L0_4[6], fwd_BU_to_shuffler_L0_4[7], inv_shuffler_to_BU_L0_0[6], inv_shuffler_to_BU_L0_0[7], q0, twoInverse0, factor0, iter)


    ;
}
