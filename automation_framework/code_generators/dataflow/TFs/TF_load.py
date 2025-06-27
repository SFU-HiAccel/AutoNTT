####################################
## load TF data
####################################

# This function generates the number of TF ports required. 
# TF loading is done as follows.
# Each BUG gets its own ports to load TFs. Within a BUG, TFs belonging to each layer are loaded sequentially using the same ports. i.e., chain broadcasting fashion
# TF ports are not shared between BUGs. This is because polynomial data flow between BUGs is not continous. Due to shufflers, polynomial data flow can be getting delayed in later BUGs.
# This causes TF buffer emptying rate different among BUGs causing chain broadcasting difficult among different BUGs.
# It has been decided to provide a separate port(s) for last layer anyways as it needs to load significantly higher number of TFs (POLY_SIZE/2) compared to the other layers.
# This function generates 3 outputs.
# 1. TF_PORT_SIZE : TF port width
# 2. tf_mmap_count : How many vertical TF ports are required to parallel loading for each BUG
# 3. multi_ports_tf_mmap_count : Total TF ports required considering each BUG
def calc_TF_load_port_num(designParamsVar):
    DRAM_WORD_SIZE = designParamsVar.DRAM_WORD_SIZE
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    DEFAULT_DRAM_PORT_WIDTH = designParamsVar.DEFAULT_DRAM_PORT_WIDTH
    logN = designParamsVar.logN
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    H_BU_NUM = designParamsVar.H_BU_NUM

    tf_mmap_count = (DRAM_WORD_SIZE * (CONCAT_FACTOR // 2)) // DEFAULT_DRAM_PORT_WIDTH
    if tf_mmap_count == 0:
        tf_mmap_count = 1

    if H_BU_NUM == 1:
        multi_ports_tf_mmap_count = logN
    elif (LAST_H_BU_NUM == 0) or (LAST_H_BU_NUM == 1):
        multi_ports_tf_mmap_count = (logN // H_BU_NUM) + 1
    else:
        multi_ports_tf_mmap_count = (logN // H_BU_NUM) + 2
    multi_ports_tf_mmap_count *= tf_mmap_count

    TF_PORT_SIZE = DRAM_WORD_SIZE * ((CONCAT_FACTOR>>1) // tf_mmap_count)

    return TF_PORT_SIZE, tf_mmap_count, multi_ports_tf_mmap_count

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

def gen_Mmap2Stream_tf_code(designParamsVar, para_num_limbs):

    line = ""
    line += "void Mmap2Stream_tf_" + str(para_num_limbs) + "_limbs(" + "\n"
    line += "                tapa::async_mmap<TF_WIDE_DATA>& tf_mmap," + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "                tapa::ostream<TF_WIDE_DATA_PER_PARA_LIMB>& tf_stream_L" + str(para_limb_idx) + "," + "\n"
    line += "                VAR_TYPE_32 tfArr_length," + "\n"
    line += "                VAR_TYPE_32 iter) {" + "\n"
    line += "" + "\n"
    line += "    VAR_TYPE_32 loopIter;" + "\n"
    line += "    #pragma HLS bind_op variable=loopIter op=mul impl=fabric latency=0" + "\n"
    line += "" + "\n"
    line += "    loopIter = tfArr_length*(iter+1);" + "\n"
    line += "    TF_WIDE_DATA readVal;" + "\n"
    line += "    TF_WIDE_DATA_PER_PARA_LIMB val;" + "\n"
    line += "" + "\n"
    line += "    LOAD_TF:for (VAR_TYPE_32 i_req = 0, i_req_address = 0, i_resp = 0; i_resp < loopIter; ) {" + "\n"
    line += "        #pragma HLS PIPELINE II=1" + "\n"
    line += "        if ((i_req < loopIter) && " + "\n"
    line += "            (tf_mmap.read_addr.try_write(i_req_address))) {" + "\n"
    line += "            i_req_address = (i_req_address == (tfArr_length - 1) ? (0) : (i_req_address + 1));" + "\n"
    line += "            ++i_req;" + "\n"
    line += "        }" + "\n"
    line += "        " + "\n"
    line += "        if((!tf_mmap.read_data.empty())) {" + "\n"
    line += "            readVal = tf_mmap.read_data.read(nullptr);" + "\n"
    line += "" + "\n"
    for para_limb_idx in range(para_num_limbs):
        line += "            val = readVal & ((((TF_WIDE_DATA_PLUS1)1)<<TF_WIDE_DATA_SIZE_PER_PARA_LIMB) - 1);" + "\n"
        line += "            tf_stream_L" + str(para_limb_idx) + ".write(val);" + "\n"
        line += "            readVal >>= TF_WIDE_DATA_SIZE_PER_PARA_LIMB;" + "\n"
        line += "" + "\n"
    line += "            ++i_resp;" + "\n"
    line += "        }" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

    


def gen_load_tf_code(designParamsVar):

    mmap_count = designParamsVar.mmap_count
    tf_mmap_count = designParamsVar.tf_mmap_count

    function_signature = f"""
void load_tf(\n"""
    for i in range(tf_mmap_count):
        function_signature += f"               tapa::istream<TF_WIDE_DATA_PER_PARA_LIMB>& tf_stream{i},\n"
    function_signature += f"""               tapa::ostreams<WORD, V_BU_NUM>& tf_stream_out,
               bool direction, VAR_TYPE_32 tfArr_length, VAR_TYPE_32 iter) {{

"""

    function_signature += """    LOAD_POLY:for (;;) {
        #pragma HLS PIPELINE II=1

        if ("""
    for i in range(tf_mmap_count):
        function_signature += f"""(!tf_stream{tf_mmap_count-1-i}.empty())"""
        if i != tf_mmap_count-1: 
            function_signature += " && "  

    function_signature += f""") {{"""
    for i in range(tf_mmap_count):
        function_signature += f"""
            TF_WIDE_DATA_PER_PARA_LIMB val{i} = tf_stream{tf_mmap_count-1-i}.read();
            for(int j=TF_PORT_SIZE-1; j>=0; j--) {{
                #pragma HLS UNROLL
                WORD v0 = (val{i} & ((((WORD_PLUS1)1)<<WORD_SIZE)-1));
                tf_stream_out[TF_PORT_SIZE*{tf_mmap_count-1-i}+j].write(v0);
                val{i} >>= DRAM_WORD_SIZE;
            }}
            """
          
    function_signature += """
        }
    }      
}
"""

    return function_signature

def gen_tf_load(designParamsVar):

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_tf_load_configs(designParamsVar)

    V_PARA_LIMB_PORTS_PER_TF_PORT = designParamsVar.V_PARA_LIMB_PORTS_PER_TF_PORT

    # generate code
    code = ""

    if(is_full_load_needed):
        code += gen_Mmap2Stream_tf_code(designParamsVar, V_PARA_LIMB_PORTS_PER_TF_PORT)
    
    if(is_partial_load_needed):
        code += gen_Mmap2Stream_tf_code(designParamsVar, partial_load_size)
    
    code += gen_load_tf_code(designParamsVar)

    return code