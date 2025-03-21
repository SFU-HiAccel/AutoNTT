####################################
## load and store poly data
####################################

# Based on the BUG size, this function calculate the required polynomial BW(#ports and port width) for either polynomial
# loading or storing.
# outputs: port width, #ports
def calc_poly_load_store_port_num(designParamsVar):
    DRAM_WORD_SIZE = designParamsVar.DRAM_WORD_SIZE
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    DEFAULT_DRAM_PORT_WIDTH = designParamsVar.DEFAULT_DRAM_PORT_WIDTH

    mmap_count = (DRAM_WORD_SIZE * CONCAT_FACTOR) // DEFAULT_DRAM_PORT_WIDTH
    if mmap_count == 0:
        mmap_count = 1

    HBM_PORT_SIZE = DRAM_WORD_SIZE * (CONCAT_FACTOR // mmap_count)
    
    return HBM_PORT_SIZE, mmap_count 

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

    line = ""
    line += "void Mmap2Stream_poly_" + str(para_num_limbs) + "_limbs(" + "\n"
    line += "            tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap," + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "            tapa::ostreams<WORD, HBM_PORT_SIZE>& fwd_poly_stream_L" + str(para_limb_idx) + "," + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "            tapa::istreams<WORD, HBM_PORT_SIZE>& inv_poly_stream_L" + str(para_limb_idx) + "," + "\n"
    line += "            bool direction, VAR_TYPE_32 iter) {" + "\n"
    line += "" + "\n"

    line += "    VAR_TYPE_32 loopIter = (N/CONCAT_FACTOR)*(iter+1);" + "\n"
    line += "" + "\n"

    line += "    if (direction) {" + "\n"
    line += "        MMAP2S:for(VAR_TYPE_32 i_req = 0, i_resp = 0; i_resp < loopIter;) {" + "\n"
    line += "            #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    line += "            if ((i_req < loopIter) && " + "\n"
    line += "                (poly_mmap.read_addr.try_write(i_req%(N/CONCAT_FACTOR)))) {" + "\n"
    line += "                ++i_req;" + "\n"
    line += "            }" + "\n"
    line += "            " + "\n"
    line += "            if((!poly_mmap.read_data.empty()) && direction) {" + "\n"
    line += "                POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);" + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        line += "                for(VAR_TYPE_8 j=0; j<HBM_PORT_SIZE; j++) {" + "\n"
        line += "                    #pragma HLS UNROLL" + "\n"
        line += "                    WORD v0 = (val & ((((WORD_PLUS1)1)<<WORD_SIZE)-1));" + "\n"
        line += "                    fwd_poly_stream_L" + str(para_limb_idx) + "[j].write(v0);" + "\n"
        line += "                    val >>= DRAM_WORD_SIZE;" + "\n"
        line += "                }" + "\n"
        line += "" + "\n"
    line += "                ++i_resp;" + "\n"
    line += "            } " + "\n"
    line += "        }" + "\n"
    line += "    } else {" + "\n"
    line += "        STORE_POLY:for (int i_req = 0, i_resp = 0; i_resp < loopIter; ) {" + "\n"
    line += "            #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    
    line += "            bool inFIFONotEmpty = (!inv_poly_stream_L0[0].empty())"
    for para_limb_idx in range(1, para_num_limbs):
        line += " && (!inv_poly_stream_L" + str(para_limb_idx) + "[0].empty())"
    line += ";" + "\n"
    line += "            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < HBM_PORT_SIZE; i++) {" + "\n"
    line += "                #pragma HLS UNROLL" + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "                inFIFONotEmpty &= ((!inv_poly_stream_L" + str(para_limb_idx) + "[i].empty())) ;" + "\n"
    line += "            }" + "\n"
    line += "" + "\n"
    line += "            POLY_WIDE_DATA val0 = 0;" + "\n"
    line += "            if((i_resp < loopIter) && inFIFONotEmpty &&" + "\n"
    line += "                (!poly_mmap.write_addr.full()) &&" + "\n"
    line += "                (!poly_mmap.write_data.full())){" + "\n"
    line += "                " + "\n"
    
    for para_limb_idx in range(para_num_limbs-1, -1, -1):
        line += "                for(int j=HBM_PORT_SIZE-1; j>=0; --j){" + "\n"
        line += "                    #pragma HLS UNROLL" + "\n"
        line += "                    val0 <<= DRAM_WORD_SIZE;" + "\n"
        line += "                    WORD smallData0 = 0;" + "\n"
        line += "                    smallData0 = inv_poly_stream_L" + str(para_limb_idx) + "[j].read(nullptr);" + "\n"
        line += "                    val0 |= (POLY_WIDE_DATA)(smallData0);" + "\n"
        line += "                }" + "\n"
        line += "" + "\n"
    line += "                poly_mmap.write_addr.write(i_req%(N/CONCAT_FACTOR));" + "\n"
    line += "                poly_mmap.write_data.write(val0);" + "\n"
    line += "                i_req++;" + "\n"
    line += "            }" + "\n"
    line += "" + "\n"
    line += "" + "\n"
    line += "            // receive acks of write success" + "\n"
    line += "            if (!poly_mmap.write_resp.empty()) {" + "\n"
    line += "                i_resp += (unsigned(poly_mmap.write_resp.read(nullptr)) + 1);" + "\n"
    line += "            }" + "\n"
    line += "        }" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

def gen_fwd_store_inv_load_poly_code(designParamsVar, para_num_limbs):

    line = ""
    line += "void Stream2Mmap_poly_" + str(para_num_limbs) + "_limbs(" + "\n"
    line += "                    tapa::async_mmap<POLY_WIDE_DATA>& poly_mmap," + "\n"

    for para_limb_idx in range(para_num_limbs):
        line += "                    tapa::istreams<WORD, HBM_PORT_SIZE>& fwd_poly_stream_L" + str(para_limb_idx) + "," + "\n"

    for para_limb_idx in range(para_num_limbs):
        line += "                    tapa::ostreams<WORD, HBM_PORT_SIZE>& inv_poly_stream_L" + str(para_limb_idx) + "," + "\n"
    line += "                    bool direction, VAR_TYPE_32 iter){" + "\n"
    line += "" + "\n"
    line += "    int loopIter = (N/CONCAT_FACTOR)*(iter+1);" + "\n"
    line += "" + "\n"
    line += "    if(direction) {" + "\n"
    line += "        STORE_POLY:for (int i_req = 0, i_resp = 0; i_resp < loopIter; ) {" + "\n"
    line += "            #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    
    line += "            bool inFIFONotEmpty = (!fwd_poly_stream_L0[0].empty())"
    for para_limb_idx in range(1, para_num_limbs):
        line += " && (!fwd_poly_stream_L" + str(para_limb_idx) + "[0].empty())"
    line += ";" + "\n"

    line += "            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < HBM_PORT_SIZE; i++) {" + "\n"
    line += "                #pragma HLS UNROLL" + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "                inFIFONotEmpty &= ((!fwd_poly_stream_L" + str(para_limb_idx) + "[i].empty())) ;" + "\n"
    line += "            }" + "\n"
    line += "" + "\n"

    line += "            POLY_WIDE_DATA val0 = 0;" + "\n"
    line += "            if((i_resp < loopIter) && inFIFONotEmpty &&" + "\n"
    line += "                (!poly_mmap.write_addr.full()) &&" + "\n"
    line += "                (!poly_mmap.write_data.full())){" + "\n"
    line += "" + "\n"
    
    for para_limb_idx in range(para_num_limbs-1, -1, -1):
        line += "                for(int j=HBM_PORT_SIZE-1; j>=0; --j){" + "\n"
        line += "                    #pragma HLS UNROLL" + "\n"
        line += "                    val0 <<= DRAM_WORD_SIZE;" + "\n"
        line += "                    WORD smallData0 = 0;" + "\n"
        line += "                    smallData0 = fwd_poly_stream_L" + str(para_limb_idx) + "[j].read(nullptr);" + "\n"
        line += "                    val0 |= (POLY_WIDE_DATA)(smallData0);" + "\n"
        line += "                }" + "\n"
        line += "" + "\n"

    line += "                poly_mmap.write_addr.write(i_req%(N/CONCAT_FACTOR));" + "\n"
    line += "                poly_mmap.write_data.write(val0);" + "\n"
    line += "                i_req++;" + "\n"
    line += "            }" + "\n"
    line += "" + "\n"
    line += "" + "\n"
    line += "            // receive acks of write success" + "\n"
    line += "            if (!poly_mmap.write_resp.empty()) {" + "\n"
    line += "                i_resp += (unsigned(poly_mmap.write_resp.read(nullptr)) + 1);" + "\n"
    line += "            }" + "\n"
    line += "        }" + "\n"
    line += "    } else {" + "\n"
    line += "" + "\n"
    line += "        MMAP2S:for(VAR_TYPE_32 i_req = 0, i_resp = 0; i_resp < loopIter;) {" + "\n"
    line += "            #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    line += "            if ((i_req < loopIter) && " + "\n"
    line += "                (poly_mmap.read_addr.try_write(i_req%(N/CONCAT_FACTOR)))) {" + "\n"
    line += "                ++i_req;" + "\n"
    line += "            }" + "\n"
    line += "            " + "\n"
    line += "            if((!poly_mmap.read_data.empty()) ) {" + "\n"
    line += "                POLY_WIDE_DATA val = poly_mmap.read_data.read(nullptr);" + "\n"
    line += "" + "\n"

    for para_limb_idx in range(para_num_limbs):
        line += "                for(VAR_TYPE_8 j=0; j<HBM_PORT_SIZE; j++){" + "\n"
        line += "                    #pragma HLS UNROLL" + "\n"
        line += "                    WORD v0 = (val & ((((WORD_PLUS1)1)<<WORD_SIZE)-1));" + "\n"
        line += "                    inv_poly_stream_L" + str(para_limb_idx) + "[j].write(v0);" + "\n"
        line += "                    val >>= DRAM_WORD_SIZE;" + "\n"
        line += "                }" + "\n"
        line += "" + "\n"

    line += "                ++i_resp;" + "\n"
    line += "            }" + "\n"
    line += "        }" + "\n"
    line += "    }" + "\n"
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

def gen_poly_load_store_tasks(designParamsVar):
    code = ""
    # FWD load INV store
    code += gen_fwd_load_inv_store_poly(designParamsVar)

    # INV load FWD store
    code += gen_fwd_store_inv_load_poly(designParamsVar)

    return code