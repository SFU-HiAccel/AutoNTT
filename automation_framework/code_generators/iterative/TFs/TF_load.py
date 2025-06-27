# In case of parallel limb support is needed and multiple limbs can be combined into a single port,
# there is a possibility that you would need a load function which does not need full capacity 
# of multiple limb support per port, but only smaller number of limbs. e.g., PARA_LIMBS=5, LIMBS_PER_PORT=2
# This function determines whether that condition occurs, and if yes only how many limb should be supported
# in that extra load/store task.
def gen_tf_load_configs(designParamsVar):
    PARA_LIMBS = designParamsVar.PARA_LIMBS
    
    DEFAULT_DRAM_PORT_WIDTH = designParamsVar.DEFAULT_DRAM_PORT_WIDTH
    TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = designParamsVar.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB

    is_full_load_needed = True
    is_partial_load_needed = False
    partial_load_size = 0

    if( PARA_LIMBS < (DEFAULT_DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB)  ): # All parallel limbs can be fit into a single port and not full capacity of the port is needed
        is_full_load_needed = False
        is_partial_load_needed = True
        partial_load_size = PARA_LIMBS
    elif( ( PARA_LIMBS % (DEFAULT_DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB) ) != 0 ): # All parallel limbs can not be fit into a single port, and it requires a port without full capacity to support a limb
        is_full_load_needed = True
        is_partial_load_needed = True
        partial_load_size = ( PARA_LIMBS % (DEFAULT_DRAM_PORT_WIDTH//TF_DRAM_PORT_WIDTH_PER_PARA_LIMB) )
    
    return is_full_load_needed, is_partial_load_needed, partial_load_size

def gen_tf_load_code(para_num_limbs, designParamsVar):
    
    line = ""

    line += "void Mmap2Stream_tf_" + str(para_num_limbs) + "_limbs(" + "\n"
    line += "                 tapa::async_mmap<TF_WIDE_DATA>& tf_mmap," + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "                 tapa::ostreams<WORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT>& tf_stream_L" + str(para_limb_idx) + "," + "\n"
    line += "                 bool direction, VAR_TYPE_16 iter, VAR_TYPE_16 port_idx) {" + "\n"
    line += "                  " + "\n"
    line += "  VAR_TYPE_16 beta = (N)/(2*NUM_BU);" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_16 loopCounter = 0;" + "\n"
    line += "" + "\n"
    line += "  COMP_LIMIT:for(VAR_TYPE_16 s=0; s<NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT; s++){" + "\n"
    line += "    VAR_TYPE_16 new_bufIdx = port_idx*NUM_BUF_PER_PARA_LIMB_TF_PORT + s*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1;" + "\n"
    line += "    if(direction){" + "\n"
    line += "      loopCounter += FWD_NUM_TF_GRPS_PER_BUF[new_bufIdx]*beta;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      loopCounter += (VAR_TYPE_16)(INV_NUM_TF_GRPS_PER_BUF[new_bufIdx] - (VAR_TYPE_16)2 + 2*beta);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"

    if(designParamsVar.DOUBLE_BUF_EN):
        line += "  LOAD_ITER: for(VAR_TYPE_16 iterCount=0; iterCount<(iter+2); iterCount++){" + "\n"
    else:
        line += "  LOAD_ITER: for(VAR_TYPE_16 iterCount=0; iterCount<iter; iterCount++){" + "\n"

    line += "    LOAD_TF:for (int i_req = 0, i_resp=0; i_resp < loopCounter;) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "      " + "\n"
    line += "      if( (i_req < loopCounter) && (tf_mmap.read_addr.try_write(i_req)) ){" + "\n"
    line += "        i_req++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( !tf_mmap.read_data.empty() ){" + "\n"
    line += "        TF_WIDE_DATA comb_tfVal = tf_mmap.read_data.read();" + "\n"
    line += "        " + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        line += "        for(int j=0; j<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){" + "\n"
        line += "          #pragma HLS UNROLL" + "\n"
        line += "          tf_stream_L" + str(para_limb_idx) + "[j].write(comb_tfVal & ((((TF_WIDE_DATA)1)<<WORD_SIZE)-1));" + "\n"
        line += "          comb_tfVal >>= DRAM_WORD_SIZE;" + "\n"
        line += "        }" + "\n"
        line += "        " + "\n"

    line += "        i_resp++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "  #ifndef __SYNTHESIS__" + "\n"
    line += "  printf(\"[Mmap2Stream_tf %d]: TF loading done\\n\", (int)port_idx);" + "\n"
    line += "  #endif" + "\n"
    line += "}" + "\n"

    return line
    

def gen_tf_load(designParamsVar):

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_tf_load_configs(designParamsVar)
    
    PARA_LIMB_PORTS_PER_TF_PORT = designParamsVar.PARA_LIMB_PORTS_PER_TF_PORT

    line = ""

    if(is_full_load_needed):
        line += gen_tf_load_code(PARA_LIMB_PORTS_PER_TF_PORT, designParamsVar)
        
    if(is_partial_load_needed):
        line += gen_tf_load_code(partial_load_size, designParamsVar)

    return line

    return line