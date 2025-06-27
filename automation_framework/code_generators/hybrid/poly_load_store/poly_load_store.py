####################################
## load and store poly data
####################################

# In case of parallel limb support is needed and multiple limbs can be combined into a single port,
# there is a possibility that you would need a load/store function which does not need full capacity 
# of multiple limb support per port, but only smaller number of limbs. e.g., PARA_LIMBS=5, LIMBS_PER_PORT=2
# This function determines whether that condition occurs, and if yes only how many limb should be supported
# in that extra load/store task.
def gen_poly_load_store_configs(designParamsVar):
    PARA_LIMBS = designParamsVar.PARA_LIMBS
    
    DEFAULT_DRAM_PORT_WIDTH = designParamsVar.DEFAULT_DRAM_PORT_WIDTH
    POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = designParamsVar.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB

    is_full_load_store_needed = True
    is_partial_load_store_needed = False
    partial_load_store_size = 0

    if( PARA_LIMBS < (DEFAULT_DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)  ): # All parallel limbs can be fit into a single port and not full capacity of the port is needed
        is_full_load_store_needed = False
        is_partial_load_store_needed = True
        partial_load_store_size = PARA_LIMBS
    elif( ( PARA_LIMBS % (DEFAULT_DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB) ) != 0 ): # All parallel limbs can not be fit into a single port, and it requires a port without full capacity to support limb(s)
        is_full_load_store_needed = True
        is_partial_load_store_needed = True
        partial_load_store_size = ( PARA_LIMBS % (DEFAULT_DRAM_PORT_WIDTH//POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB) )
    
    return is_full_load_store_needed, is_partial_load_store_needed, partial_load_store_size

def gen_fwd_load_inv_store_poly_code(designParamsVar, para_num_limbs):
    BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.BUG_PER_PARA_LIMB_POLY_PORT
    BUG_PER_PARA_LIMB_POLY_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    SEQ_BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.SEQ_BUG_PER_PARA_LIMB_POLY_PORT

    #deciding unrolled loop counter string
    num_streams_per_BUG = ""
    if( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ):
        num_streams_per_BUG = "POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT"
    else:
        num_streams_per_BUG = "2*V_BUG_SIZE"
    
    line = ""
    line += "void fwd_load_inv_store_poly_" + str(para_num_limbs) + "_limbs(tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap," + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        for idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
            line += "                 tapa::istreams<WORD, " + num_streams_per_BUG + ">& inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(idx) + "," + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        for idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
            line += "                 tapa::ostreams<WORD, " + num_streams_per_BUG + ">& fwd_out_poly_L" + str(para_limb_idx) + "_stream" + str(idx) + "," + "\n"

    line += "                 bool direction," + "\n"
    line += "                 VAR_TYPE_16 iter) {" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_16 totalDataCount = (N/V_TOTAL_DATA)*(SEQ_BUG_PER_PARA_LIMB_POLY_PORT);" + "\n"
    line += "  POLY_WIDE_DATA val;" + "\n"
    line += "  WORD smallData;" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    LOAD_STORE_POLY_0:for (int i_req = 0, i_resp=0; i_resp < totalDataCount;) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      if(direction){  //fwd load" + "\n"
    line += "        if( ( i_req < totalDataCount ) && (poly_mmap.read_addr.try_write(i_req)) ){" + "\n"
    line += "          i_req++;" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if( !poly_mmap.read_data.empty() ){" + "\n"
    line += "          POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);" + "\n"
    line += "" + "\n"
    line += "          VAR_TYPE_16 seq_group_idx = i_resp/(N/V_TOTAL_DATA);" + "\n"
    line += "          " + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
            line += "          for(int j=0; j<(" + num_streams_per_BUG + "); j++){" + "\n"
            line += "            #pragma HLS UNROLL" + "\n"
            line += "            WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA)1)<<WORD_SIZE)-1));" + "\n"
            
            #handling seq BUGs.
            if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
                line += "            fwd_out_poly_L" + str(para_limb_idx) + "_stream" + str(0*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"    
            elif (SEQ_BUG_PER_PARA_LIMB_POLY_PORT==2):    ##may be we can remove this case and let it handle by else.
                line += "            if( seq_group_idx==0 ){" + "\n"
                line += "              fwd_out_poly_L" + str(para_limb_idx) + "_stream" + str(0*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
                line += "            else{" + "\n"
                line += "              fwd_out_poly_L" + str(para_limb_idx) + "_stream" + str(1*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
            else:
                line += "            if( seq_group_idx==0 ){" + "\n"
                line += "              fwd_out_poly_L" + str(para_limb_idx) + "_stream" + str(0*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
                for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
                    line += "            else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
                    line += "              fwd_out_poly_L" + str(para_limb_idx) + "_stream" + str((seq_idx+1)*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                    line += "            }" + "\n"
                line += "            else{" + "\n"
                line += "              fwd_out_poly_L" + str(para_limb_idx) + "_stream" + str((SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
            line += "            val >>= DRAM_WORD_SIZE;" + "\n"
            line += "          }" + "\n"
            line += "\n"

    line += "          i_resp++;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "      else{ //inv store" + "\n"
    line += "        VAR_TYPE_16 seq_group_idx = i_req/(N/V_TOTAL_DATA);" + "\n"
    line += "" + "\n"
    line += "        val = 0;" + "\n"
    line += "        " + "\n"
    line += "        bool inpStreamNotEmpty;" + "\n"
    if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !inv_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            else:
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
    elif (SEQ_BUG_PER_PARA_LIMB_POLY_PORT==2):
        line += "        if( seq_group_idx==0 ){" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !inv_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            else:
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
        line += "        else{" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + "[0].empty() )"
            else:
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + "[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA + para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
    else:
        line += "        if( seq_group_idx==0 ){" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !inv_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            else:
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
        for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
            line += "        else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
            line += "          inpStreamNotEmpty = "
            for para_limb_idx in range(para_num_limbs):
                if(para_limb_idx==0):
                    line += "( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1)) + "[0].empty() )"
                else:
                    line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1)) + "[0].empty() )"
                for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                    line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1) + para_idx + 1) + "[0].empty() )"
            line += ";" + "\n"
            line += "        }" + "\n"
        line += "        else{" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + "[0].empty() )"
            else:
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + "[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + para_idx + 1 ) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
    line += "" + "\n"
    line += "        for(int j=1; j<(" + str(num_streams_per_BUG) + "); j++){" + "\n"
    if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
        for para_limb_idx in range(para_num_limbs):
            line += "          inpStreamNotEmpty &= ( !inv_in_poly_L" + str(para_limb_idx) + "_stream0[j].empty() );" + "\n"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " inpStreamNotEmpty &= ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str( para_idx + 1 ) + "[j].empty() );" + "\n"
    else:
        line += "          if( seq_group_idx==0 ){" + "\n"
        for para_limb_idx in range(para_num_limbs):
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
                line += "             inpStreamNotEmpty &= ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx) + "[j].empty() );" + "\n"
        line += "          }" + "\n"
        for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
            line += "          else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
            for para_limb_idx in range(para_num_limbs):
                for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
                    line += "             inpStreamNotEmpty &= ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1) + para_idx) + "[j].empty() );" + "\n"
            line += "          }" + "\n"
        line += "          else{" + "\n"
        for para_limb_idx in range(para_num_limbs):
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
                line += "             inpStreamNotEmpty &= ( !inv_in_poly_L" + str(para_limb_idx) + "_stream" + str( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + para_idx ) + "[j].empty() );" + "\n"
        line += "          }" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if( ( i_req < (totalDataCount) ) && ( inpStreamNotEmpty ) ){" + "\n"
    line += "          " + "\n"
    line += "          //read FIFOs" + "\n"

    for para_limb_idx in range(para_num_limbs-1, -1, -1):
        for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1, -1, -1):
            line += "          for(int j=(" + str(num_streams_per_BUG) + ")-1; j>=0; j--){" + "\n"
            line += "            #pragma HLS UNROLL" + "\n"
            line += "            val <<= DRAM_WORD_SIZE;" + "\n"
            if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
                line += "              smallData = inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx)  + "[j].read();" + "\n"
            else:
                line += "            if( seq_group_idx==0 ){" + "\n"
                line += "              smallData = inv_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx) + "[j].read();" + "\n"
                line += "            }" + "\n"
                for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
                    line += "            else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
                    line += "              smallData = inv_in_poly_L" + str(para_limb_idx) + "_stream" + str( (seq_idx+1) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + para_idx ) + "[j].read();" + "\n"
                    line += "            }" + "\n"
                line += "            else{" + "\n"
                line += "              smallData = inv_in_poly_L" + str(para_limb_idx) + "_stream" + str( (SEQ_BUG_PER_PARA_LIMB_POLY_PORT - 1) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + para_idx ) + "[j].read();" + "\n"
                line += "            }" + "\n"
                
            line += "            val |= (POLY_WIDE_DATA)(smallData);" + "\n"
            line += "          }" + "\n"
            line += "          " + "\n"

    line += "          //write mem" + "\n"
    line += "          poly_mmap.write_addr.write(i_req);" + "\n"
    line += "          poly_mmap.write_data.write(val);" + "\n"
    line += "          i_req++;" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if( !poly_mmap.write_resp.empty() ){" + "\n"
    line += "          i_resp += unsigned(poly_mmap.write_resp.read(nullptr)) + 1;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "  #ifndef __SYNTHESIS__" + "\n"
    line += "  if(direction){" + "\n"
    line += "    printf(\"[fwd_load_inv_store_poly]: Polynomial loading done\\n\");" + "\n"
    line += "  }" + "\n"
    line += "  else{" + "\n"
    line += "    printf(\"[fwd_load_inv_store_poly]: Polynomial storing done\\n\");" + "\n"
    line += "  }" + "\n"
    line += "  #endif" + "\n"
    line += "}" + "\n"

    return line


def gen_fwd_store_inv_load_poly_code(designParamsVar, para_num_limbs):
    BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.BUG_PER_PARA_LIMB_POLY_PORT
    BUG_PER_PARA_LIMB_POLY_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    SEQ_BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.SEQ_BUG_PER_PARA_LIMB_POLY_PORT

    #deciding unrolled loop counter string
    num_streams_per_BUG = ""
    if( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ):
        num_streams_per_BUG = "POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT"
    else:
        num_streams_per_BUG = "2*V_BUG_SIZE"
    
    line = ""
    line += "void fwd_store_inv_load_poly_" + str(para_num_limbs) + "_limbs(tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap," + "\n"
    for para_limb_idx in range(para_num_limbs):
        for idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
            line += "                 tapa::istreams<WORD, " + num_streams_per_BUG + ">& fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(idx) + "," + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        for idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
            line += "                 tapa::ostreams<WORD, " + num_streams_per_BUG + ">& inv_out_poly_L" + str(para_limb_idx) + "_stream" + str(idx) + "," + "\n"

    line += "                 bool direction," + "\n"
    line += "                 VAR_TYPE_16 iter) {" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_16 totalDataCount = (N/V_TOTAL_DATA)*(SEQ_BUG_PER_PARA_LIMB_POLY_PORT);" + "\n"
    line += "  POLY_WIDE_DATA val;" + "\n"
    line += "  WORD smallData;" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    LOAD_STORE_POLY_0:for (int i_req = 0, i_resp=0; i_resp < totalDataCount;) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      if(!direction){  //inv load" + "\n"
    line += "        if( ( i_req < totalDataCount ) && (poly_mmap.read_addr.try_write(i_req)) ){" + "\n"
    line += "          i_req++;" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if( !poly_mmap.read_data.empty() ){" + "\n"
    line += "          POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);" + "\n"
    line += "" + "\n"
    line += "          VAR_TYPE_16 seq_group_idx = i_resp/(N/V_TOTAL_DATA);" + "\n"
    line += "          " + "\n"

    for para_limb_idx in range(para_num_limbs):
        for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
            line += "          for(int j=0; j<(" + num_streams_per_BUG + "); j++){" + "\n"
            line += "            #pragma HLS UNROLL" + "\n"
            line += "            WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA)1)<<WORD_SIZE)-1));" + "\n"
            
            #handling seq BUGs.
            if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
                line += "            inv_out_poly_L" + str(para_limb_idx) + "_stream" + str(0*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"    
            elif (SEQ_BUG_PER_PARA_LIMB_POLY_PORT==2):    ##may be we can remove this case and let it handle by else.
                line += "            if( seq_group_idx==0 ){" + "\n"
                line += "              inv_out_poly_L" + str(para_limb_idx) + "_stream" + str(0*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
                line += "            else{" + "\n"
                line += "              inv_out_poly_L" + str(para_limb_idx) + "_stream" + str(1*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
            else:
                line += "            if( seq_group_idx==0 ){" + "\n"
                line += "              inv_out_poly_L" + str(para_limb_idx) + "_stream" + str(0*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
                for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
                    line += "            else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
                    line += "              inv_out_poly_L" + str(para_limb_idx) + "_stream" + str((seq_idx+1)*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                    line += "            }" + "\n"
                line += "            else{" + "\n"
                line += "              inv_out_poly_L" + str(para_limb_idx) + "_stream" + str((SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)*BUG_PER_PARA_LIMB_POLY_WIDE_DATA+para_idx) + "[j].write(smallVal);" + "\n"
                line += "            }" + "\n"
            line += "            val >>= DRAM_WORD_SIZE;" + "\n"
            line += "          }" + "\n"
            line += "\n"

    line += "          i_resp++;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "      else{ //fwd store" + "\n"
    line += "        VAR_TYPE_16 seq_group_idx = i_req/(N/V_TOTAL_DATA);" + "\n"
    line += "" + "\n"
    line += "        val = 0;" + "\n"
    line += "        " + "\n"
    line += "        bool inpStreamNotEmpty;" + "\n"
    if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !fwd_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            else:
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
    elif (SEQ_BUG_PER_PARA_LIMB_POLY_PORT==2):
        line += "        if( seq_group_idx==0 ){" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !fwd_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            else:
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
        line += "        else{" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + "[0].empty() )"
            else:
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + "[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !fwd_in_poly_stream_BUG" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA + para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
    else:
        line += "        if( seq_group_idx==0 ){" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !fwd_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            else:
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream0[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx + 1) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
        for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
            line += "        else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
            line += "          inpStreamNotEmpty = "
            for para_limb_idx in range(para_num_limbs):
                if(para_limb_idx==0):
                    line += "( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1)) + "[0].empty() )"
                else:
                    line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1)) + "[0].empty() )"
                for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                    line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1) + para_idx + 1) + "[0].empty() )"
            line += ";" + "\n"
            line += "        }" + "\n"
        line += "        else{" + "\n"
        line += "          inpStreamNotEmpty = "
        for para_limb_idx in range(para_num_limbs):
            if(para_limb_idx==0):
                line += "( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + "[0].empty() )"
            else:
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + "[0].empty() )"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " && ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + para_idx + 1 ) + "[0].empty() )"
        line += ";" + "\n"
        line += "        }" + "\n"
    line += "" + "\n"
    line += "        for(int j=1; j<(" + str(num_streams_per_BUG) + "); j++){" + "\n"
    if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
        for para_limb_idx in range(para_num_limbs):
            line += "          inpStreamNotEmpty &= ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream0[j].empty() );" + "\n"
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1):
                line += " inpStreamNotEmpty &= ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str( para_idx + 1 ) + "[j].empty() );" + "\n"
    else:
        line += "          if( seq_group_idx==0 ){" + "\n"
        for para_limb_idx in range(para_num_limbs):
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
                line += "             inpStreamNotEmpty &= ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx) + "[j].empty() );" + "\n"
        line += "          }" + "\n"
        for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
            line += "          else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
            for para_limb_idx in range(para_num_limbs):
                for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
                    line += "             inpStreamNotEmpty &= ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (seq_idx+1) + para_idx) + "[j].empty() );" + "\n"
            line += "          }" + "\n"
        line += "          else{" + "\n"
        for para_limb_idx in range(para_num_limbs):
            for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA):
                line += "             inpStreamNotEmpty &= ( !fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT-1)) + para_idx ) + "[j].empty() );" + "\n"
        line += "          }" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if( ( i_req < (totalDataCount) ) && ( inpStreamNotEmpty ) ){" + "\n"
    line += "          " + "\n"
    line += "          //read FIFOs" + "\n"

    for para_limb_idx in range(para_num_limbs-1, -1, -1):
        for para_idx in range(BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1, -1, -1):
            line += "          for(int j=(" + str(num_streams_per_BUG) + ")-1; j>=0; j--){" + "\n"
            line += "            #pragma HLS UNROLL" + "\n"
            line += "            val <<= DRAM_WORD_SIZE;" + "\n"
            if(SEQ_BUG_PER_PARA_LIMB_POLY_PORT==1):
                line += "              smallData = fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx)  + "[j].read();" + "\n"
            else:
                line += "            if( seq_group_idx==0 ){" + "\n"
                line += "              smallData = fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str(para_idx) + "[j].read();" + "\n"
                line += "            }" + "\n"
                for seq_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT-2):
                    line += "            else if( seq_group_idx==" + str(seq_idx+1) + " ){" + "\n"
                    line += "              smallData = fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str( (seq_idx+1) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + para_idx ) + "[j].read();" + "\n"
                    line += "            }" + "\n"
                line += "            else{" + "\n"
                line += "              smallData = fwd_in_poly_L" + str(para_limb_idx) + "_stream" + str( (SEQ_BUG_PER_PARA_LIMB_POLY_PORT - 1) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + para_idx ) + "[j].read();" + "\n"
                line += "            }" + "\n"
                
            line += "            val |= (POLY_WIDE_DATA)(smallData);" + "\n"
            line += "          }" + "\n"
            line += "          " + "\n"

    line += "          //write mem" + "\n"
    line += "          poly_mmap.write_addr.write(i_req);" + "\n"
    line += "          poly_mmap.write_data.write(val);" + "\n"
    line += "          i_req++;" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if( !poly_mmap.write_resp.empty() ){" + "\n"
    line += "          i_resp += unsigned(poly_mmap.write_resp.read(nullptr)) + 1;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "  #ifndef __SYNTHESIS__" + "\n"
    line += "  if(direction){" + "\n"
    line += "    printf(\"[fwd_store_inv_load_poly]: Polynomial storing done\\n\");" + "\n"
    line += "  }" + "\n"
    line += "  else{" + "\n"
    line += "    printf(\"[fwd_store_inv_load_poly]: Polynomial loading done\\n\");" + "\n"
    line += "  }" + "\n"
    line += "  #endif" + "\n"
    line += "}" + "\n"

    return line

def gen_fwd_load_inv_store_poly(designParamsVar):
    is_full_load_store_needed, is_partial_load_store_needed, partial_load_store_size = gen_poly_load_store_configs(designParamsVar)
    
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    line = ""

    if(is_full_load_store_needed):
        line += gen_fwd_load_inv_store_poly_code(designParamsVar, PARA_LIMB_PORTS_PER_POLY_PORT)
        line += "\n"
    if(is_partial_load_store_needed):
        line += gen_fwd_load_inv_store_poly_code(designParamsVar, partial_load_store_size)
        line += "\n"

    return line

def gen_fwd_store_inv_load_poly(designParamsVar):
    is_full_load_store_needed, is_partial_load_store_needed, partial_load_store_size = gen_poly_load_store_configs(designParamsVar)
    
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    line = ""

    if(is_full_load_store_needed):
        line += gen_fwd_store_inv_load_poly_code(designParamsVar, PARA_LIMB_PORTS_PER_POLY_PORT)
        line += "\n"
    if(is_partial_load_store_needed):
        line += gen_fwd_store_inv_load_poly_code(designParamsVar, partial_load_store_size)
        line += "\n"

    return line