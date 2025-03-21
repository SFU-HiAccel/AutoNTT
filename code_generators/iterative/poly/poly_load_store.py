
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


def gen_Mmap2Stream_poly_code(para_num_limbs, designParamsVar):
    line = ""
    line += "void Mmap2Stream_poly_" + str(para_num_limbs) + "_limbs(" + "\n"
    line += "                 tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap," + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& poly_stream_L" + str(para_limb_idx) + "," + "\n"
    line += "                 VAR_TYPE_16 port_idx," + "\n"
    line += "                 VAR_TYPE_16 iter) {" + "\n"
    line += "" + "\n"

    line += "  LOAD_ITER: for(VAR_TYPE_16 iterCount=0; iterCount<(iter+2); iterCount++){" + "\n"

    line += "    LOAD_POLY_0:for (int i_req = 0, i_resp=0; i_resp < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT;) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      if( (i_req < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT) && (poly_mmap.read_addr.try_write(i_req)) ){" + "\n"
    line += "        i_req++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( !poly_mmap.read_data.empty() ){" + "\n"
    line += "        POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);" + "\n"
    line += "" + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "        for(int j=0; j<POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){" + "\n"
        line += "          #pragma HLS UNROLL" + "\n"
        line += "          WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA)1)<<WORD_SIZE)-1));" + "\n"
        line += "          poly_stream_L" + str(para_limb_idx) + "[j].write(smallVal);" + "\n"
        line += "          val >>= DRAM_WORD_SIZE;" + "\n"
        line += "        }" + "\n"
        line += "" + "\n"
    line += "        i_resp++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "  #ifndef __SYNTHESIS__" + "\n"
    line += "  printf(\"[Mmap2Stream_poly %d]: Polynomial loading done\\n\", (int)port_idx);" + "\n"
    line += "  #endif" + "\n"
    line += "}" + "\n"

    return line

def gen_Stream2Mmap_poly_code(para_num_limbs, designParamsVar):
    line = ""

    line += "void Stream2Mmap_poly_" + str(para_num_limbs) + "_limbs(" + "\n"
    line += "                    tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap," + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        line += "                    tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& poly_stream_L" + str(para_limb_idx) + "," + "\n"

    line += "                    VAR_TYPE_16 port_idx," + "\n"
    line += "                    VAR_TYPE_16 iter) {" + "\n"
    line += "" + "\n"
    line += "  bool sendDataSuccess = true;" + "\n"
    line += "  POLY_WIDE_DATA val;" + "\n"
    line += "" + "\n"

    line += "  STORE_ITER:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+2); iterCount++){" + "\n"
    
    line += "    STORE_POLY_0:for (int i_req = 0, i_resp = 0; i_resp < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT;) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      bool inp_not_empty = (!poly_stream_L0[0].empty())"

    for para_limb_idx in range(1, para_num_limbs):
        line += " & (!poly_stream_L" + str(para_limb_idx) + "[0].empty())" + "\n"

    line += ";" + "\n"

    line += "      for(int j=1; j<POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){" + "\n"
    line += "        #pragma HLS UNROLL" + "\n"

    for para_limb_idx in range(0, para_num_limbs):
        line += "        inp_not_empty &= !poly_stream_L" + str(para_limb_idx) + "[j].empty();" + "\n"
    
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( sendDataSuccess && inp_not_empty ){" + "\n"
    line += "        val = 0;" + "\n"
    line += "        " + "\n"
    
    for para_limb_idx in range(para_num_limbs-1, -1, -1):
        line += "        for(int j=POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1; j>=0; j--){" + "\n"
        line += "          #pragma HLS UNROLL" + "\n"
        line += "          val <<= DRAM_WORD_SIZE;" + "\n"
        line += "          WORD smallData = poly_stream_L" + str(para_limb_idx) + "[j].read();" + "\n"
        line += "          val |= (POLY_WIDE_DATA)(smallData);" + "\n"
        line += "        }" + "\n"
        line += "        " + "\n"

    line += "        sendDataSuccess = false;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( ( i_req < ((N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)) && (poly_mmap.write_addr.try_write(i_req)) ){" + "\n"
    line += "        i_req++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( (!sendDataSuccess) && (poly_mmap.write_data.try_write(val)) ){" + "\n"
    line += "        sendDataSuccess = true;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( !poly_mmap.write_resp.empty() ){" + "\n"
    line += "        i_resp += unsigned(poly_mmap.write_resp.read(nullptr)) + 1;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "  #ifndef __SYNTHESIS__" + "\n"
    line += "  printf(\"[Stream2Mmap_poly %d]: Polynomial storing done\\n\", (int)port_idx);" + "\n"
    line += "  #endif" + "\n"
    line += "}" + "\n"

    return line

def gen_Mmap2Stream_and_Stream2Mmap_poly_code(para_num_limbs, designParamsVar):
    line = ""
    line += "void Mmap2Stream_and_Stream2Mmap_poly_" + str(para_num_limbs) + "_limbs(" + "\n"
    line += "                 tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap," + "\n"

    for para_limb_idx in range(para_num_limbs):
        line += "                 tapa::istreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& poly_stream_in_L" + str(para_limb_idx) + "," + "\n"

    for para_limb_idx in range(para_num_limbs):
        line += "                 tapa::ostreams<WORD, POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& poly_stream_out_L" + str(para_limb_idx) + "," + "\n"

    line += "                 VAR_TYPE_16 port_idx," + "\n"
    line += "                 VAR_TYPE_16 iter) {" + "\n"
    line += "" + "\n"

    line += "  int store_offset = (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT;" + "\n"
    line += "  bool sendDataSuccess = true;" + "\n"
    line += "  POLY_WIDE_DATA val;" + "\n"
    line += "" + "\n"

    line += "  LOAD_ITER: for(VAR_TYPE_16 iterCount=0; iterCount<iter; iterCount++){" + "\n"

    #### Load ####

    line += "    LOAD_POLY_0:for (int i_req = 0, i_resp=0; i_resp < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT;) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      if( (i_req < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT) && (poly_mmap.read_addr.try_write(i_req)) ){" + "\n"
    line += "        i_req++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( !poly_mmap.read_data.empty() ){" + "\n"
    line += "        val = poly_mmap.read_data.read(nullptr);" + "\n"
    line += "" + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "        for(int j=0; j<POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){" + "\n"
        line += "          #pragma HLS UNROLL" + "\n"
        line += "          WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA)1)<<WORD_SIZE)-1));" + "\n"
        line += "          poly_stream_out_L" + str(para_limb_idx) + "[j].write(smallVal);" + "\n"
        line += "          val >>= DRAM_WORD_SIZE;" + "\n"
        line += "        }" + "\n"
        line += "" + "\n"
    line += "        i_resp++;" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"

    #### Store ####
    line += "    STORE_POLY_0:for (int i_req = 0, i_resp = 0; i_resp < (N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT;) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      bool inp_not_empty = (!poly_stream_in_L0[0].empty())"

    for para_limb_idx in range(1, para_num_limbs):
        line += " & (!poly_stream_in_L" + str(para_limb_idx) + "[0].empty())" + "\n"

    line += ";" + "\n"

    line += "      for(int j=1; j<POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){" + "\n"
    line += "        #pragma HLS UNROLL" + "\n"

    for para_limb_idx in range(0, para_num_limbs):
        line += "        inp_not_empty &= !poly_stream_in_L" + str(para_limb_idx) + "[j].empty();" + "\n"
    
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( sendDataSuccess && inp_not_empty ){" + "\n"
    line += "        val = 0;" + "\n"
    line += "        " + "\n"
    
    for para_limb_idx in range(para_num_limbs-1, -1, -1):
        line += "        for(int j=POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1; j>=0; j--){" + "\n"
        line += "          #pragma HLS UNROLL" + "\n"
        line += "          val <<= DRAM_WORD_SIZE;" + "\n"
        line += "          WORD smallData = poly_stream_in_L" + str(para_limb_idx) + "[j].read();" + "\n"
        line += "          val |= (POLY_WIDE_DATA)(smallData);" + "\n"
        line += "        }" + "\n"
        line += "        " + "\n"

    line += "        sendDataSuccess = false;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( ( i_req < ((N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)) && (poly_mmap.write_addr.try_write(store_offset + i_req)) ){" + "\n"
    line += "        i_req++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( (!sendDataSuccess) && (poly_mmap.write_data.try_write(val)) ){" + "\n"
    line += "        sendDataSuccess = true;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( !poly_mmap.write_resp.empty() ){" + "\n"
    line += "        i_resp += unsigned(poly_mmap.write_resp.read(nullptr)) + 1;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"

    line += "  }" + "\n"
    line += "  #ifndef __SYNTHESIS__" + "\n"
    line += "  printf(\"[Mmap2Stream_and_Stream2Mmap_poly %d]: Polynomial loading and storing done\\n\", (int)port_idx);" + "\n"
    line += "  #endif" + "\n"
    line += "}" + "\n"

    return line

def gen_Mmap2Stream_poly(designParamsVar):

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_poly_load_store_configs(designParamsVar)
    
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    line = ""

    if(is_full_load_needed):
        line += gen_Mmap2Stream_poly_code(PARA_LIMB_PORTS_PER_POLY_PORT, designParamsVar)
        
    if(is_partial_load_needed):
        line += gen_Mmap2Stream_poly_code(partial_load_size, designParamsVar)
        
    return line

def gen_Stream2Mmap_poly(designParamsVar):
    is_full_store_needed, is_partial_store_needed, partial_store_size = gen_poly_load_store_configs(designParamsVar)
    
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    line = ""

    if(is_full_store_needed):
        line += gen_Stream2Mmap_poly_code(PARA_LIMB_PORTS_PER_POLY_PORT, designParamsVar)
        
    if(is_partial_store_needed):
        line += gen_Stream2Mmap_poly_code(partial_store_size, designParamsVar)

    return line

def gen_Mmap2Stream_and_Stream2Mmap_poly(designParamsVar):

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_poly_load_store_configs(designParamsVar)
    
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    line = ""

    if(is_full_load_needed):
        line += gen_Mmap2Stream_and_Stream2Mmap_poly_code(PARA_LIMB_PORTS_PER_POLY_PORT, designParamsVar)
        
    if(is_partial_load_needed):
        line += gen_Mmap2Stream_and_Stream2Mmap_poly_code(partial_load_size, designParamsVar)
        
    return line

def gen_poly_load_store(designParamsVar):
    code = ""

    if(designParamsVar.DOUBLE_BUF_EN):
        code += gen_Mmap2Stream_poly(designParamsVar)
        code += "\n"
        code += gen_Stream2Mmap_poly(designParamsVar)
        code += "\n"
    else:
        code += gen_Mmap2Stream_and_Stream2Mmap_poly(designParamsVar)

    return code