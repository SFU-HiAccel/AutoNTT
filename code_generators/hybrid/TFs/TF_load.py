####################################
## load TF data
####################################

from code_generators.hybrid.TFs.TF_common import partition
from code_generators.hybrid.TFs.TF_common import verifyFwdInvPartitions

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

#### 
# Function to calculate TFs loaded by each port
# Given the TF load horizontal partitions (i.e., to how many groups total layers are divided into) and other parameters, this function
# 1. calculate TFs required for each layer
# 2. find the best partitioning stratergy considering both FWD and INV numbers
# and return loading numbers.
####
def gen_tf_load_counters(designParamsVar):

    #local params
    logN = designParamsVar.logN
    TF_LOAD_H_SEGS_PER_PARA_LIMB = designParamsVar.TF_LOAD_H_SEGS_PER_PARA_LIMB
    POLY_SIZE = designParamsVar.POLY_SIZE
    H_BUG_SIZE = designParamsVar.H_BUG_SIZE
    V_BUG_SIZE = designParamsVar.V_BUG_SIZE
    BUG_CONCAT_FACTOR = designParamsVar.BUG_CONCAT_FACTOR

    fwd_layerWiseTFBufDepth = [0]*H_BUG_SIZE
    inv_layerWiseTFBufDepth = [0]*H_BUG_SIZE
    
    for stage in range(logN):

        # total TFs
        fwd_num_tfs_in_this_stage = 1 << stage

        inv_num_tfs_in_this_stage = 1 << stage
        inv_tf_change_freq = (POLY_SIZE//2)//inv_num_tfs_in_this_stage # distance between two TF values


        # check partial BUG
        fwd_dataFlowIter = stage//H_BUG_SIZE
        fwd_numberOfSupportedStages = (H_BUG_SIZE) if ( logN-(fwd_dataFlowIter*H_BUG_SIZE) > H_BUG_SIZE ) else ( logN-(fwd_dataFlowIter*H_BUG_SIZE) )
        fwd_tf_grp_size_BUG = 1 << (fwd_numberOfSupportedStages-1) #to support remaining layers, how many poly. values are grouped together is (1 << (num_partial_layers)). Since 2 poly val. need 1 TF, this is the eqn for TFs
        fwd_num_tf_grps_per_BUG = V_BUG_SIZE//fwd_tf_grp_size_BUG

        inv_dataFlowIter = (logN - 1 - stage)//H_BUG_SIZE
        inv_numberOfSupportedStages =  (H_BUG_SIZE) if ( logN-(inv_dataFlowIter*H_BUG_SIZE) > H_BUG_SIZE ) else ( logN-(inv_dataFlowIter*H_BUG_SIZE) )
        inv_tf_grp_size_BUG = 1 << (inv_numberOfSupportedStages-1) #to support remaining layers, how many poly. values are grouped together is (1 << (num_partial_layers)). Since 2 poly val. need 1 TF, this is the eqn for TFs
        inv_num_tf_grps_per_BUG = V_BUG_SIZE//inv_tf_grp_size_BUG

        #layer specific dist
        fwd_layer_id = stage % H_BUG_SIZE
        fwd_per_BUG_diff_num_data = (1 << fwd_layer_id) #how many unique TF values are passed from this layer

        inv_layer_id = (logN - stage - 1) % H_BUG_SIZE
        inv_per_BUG_diff_num_data = ( 1 << ( (H_BUG_SIZE - 1) - inv_layer_id ) ) #how many unique TF values are passed from this layer

        #per buffer if two unique values are going or not
        #only first layer share values among 2 consec BUs. All the remaining layers always have two different values accessed by the consecutive BUs
        #That does not happen only when partial grp size is 1. i.e., every BU is a partial BU.
        fwd_num_val_accessed_by_consec_BUs = ( 1 ) if ( ( fwd_layer_id == 0 ) and ( fwd_tf_grp_size_BUG !=1 ) ) else ( 2 )
        inv_num_val_accessed_by_consec_BUs = ( 2 ) if ( ( inv_layer_id == 0 ) and ( inv_tf_grp_size_BUG !=1 ) ) else ( 1 )

        #As # BUGs increases, TFs can be spread accross different buffers. this determines that
        #if total number of TFs only fit into one BUG, duplicates among BUGs. 
        #Else, if number of TFs are larger than a single BUG, hence spread accross BUGs
        fwd_BUG_concat_dist_factor =  ( 1 ) if ( fwd_num_tfs_in_this_stage <= V_BUG_SIZE ) else ( ( fwd_num_tfs_in_this_stage//fwd_per_BUG_diff_num_data ) if ( (fwd_num_tfs_in_this_stage/fwd_per_BUG_diff_num_data) <= BUG_CONCAT_FACTOR ) else ( BUG_CONCAT_FACTOR ) )
        inv_BUG_concat_dist_factor = ( ( (BUG_CONCAT_FACTOR*V_BUG_SIZE)//(inv_tf_change_freq*inv_per_BUG_diff_num_data) ) if ( ( (BUG_CONCAT_FACTOR*V_BUG_SIZE)//(inv_tf_change_freq*inv_per_BUG_diff_num_data) ) > 0 ) else (1) ) if ( inv_tf_change_freq > V_BUG_SIZE ) else ( BUG_CONCAT_FACTOR )

        #number of unique tf values going per single iteration
        fwd_unique_tf_per_iter = fwd_per_BUG_diff_num_data * fwd_num_tf_grps_per_BUG * fwd_BUG_concat_dist_factor
        inv_unique_tf_per_iter = (inv_per_BUG_diff_num_data//inv_num_tf_grps_per_BUG) * inv_BUG_concat_dist_factor

        #Number of total TFs going into a buffer
        #Eqn is: per "num_val_accessed_by_consec_BUs" depth "unique_tf_per_iter" values were stored. Then how much depth for "num_tfs_in_this_stage"
        fwd_num_tfs_per_buf = fwd_num_tfs_in_this_stage // ( fwd_unique_tf_per_iter//fwd_num_val_accessed_by_consec_BUs )
        fwd_layerWiseTFBufDepth[fwd_layer_id] += fwd_num_tfs_per_buf

        inv_num_tfs_per_buf = inv_num_tfs_in_this_stage // ( inv_unique_tf_per_iter // inv_num_val_accessed_by_consec_BUs )
        inv_layerWiseTFBufDepth[inv_layer_id] += inv_num_tfs_per_buf
    
    #make each depth even as two values going to be packed together
    for layer in range(H_BUG_SIZE):
        if( fwd_layerWiseTFBufDepth[layer]%2==1 ):#odd
            fwd_layerWiseTFBufDepth[layer]+=1
        
        if( inv_layerWiseTFBufDepth[layer]%2==1 ):#odd
            inv_layerWiseTFBufDepth[layer]+=1

    fwd_tf_load_counter = 0
    inv_tf_load_counter = 0

    cummulative_sum_of_assigned_layers = 0
    
    # calc. number of layers per segment
    fwd_TFData_segs = partition(fwd_layerWiseTFBufDepth, H_BUG_SIZE, TF_LOAD_H_SEGS_PER_PARA_LIMB)
    inv_TFData_segs = partition(inv_layerWiseTFBufDepth, H_BUG_SIZE, TF_LOAD_H_SEGS_PER_PARA_LIMB)

    # partitioning can be different for FWD and INV. Verify the equality and update (if necessary) 
    # partitioning with minimum effect
    fwd_TFData_segs, inv_TFData_segs = verifyFwdInvPartitions(fwd_TFData_segs, inv_TFData_segs)

    #update final layers per segment and their load direction
    #load  direction: In the case of some segments are closer to the end of BUG, we load from the end of the segment.
    #Because tasks related to start and end of the BUG would like to be closer to HBM. Starting from the middle can
    #have some negative impact in floorplanning(have not tested).
    layers_per_seg = []
    load_direction_per_seg = [] #From start=True, From end=False

    cummulative_sum_of_assigned_layers = 0
    for seg_id in range(len(fwd_TFData_segs)):
        num_layers_per_seg = len(fwd_TFData_segs[seg_id])
        layers_per_seg.append(num_layers_per_seg)
        if(cummulative_sum_of_assigned_layers< ((H_BUG_SIZE+1)//2) ):
            load_direction_per_seg.append(True)
        else:
            load_direction_per_seg.append(False)
        
        cummulative_sum_of_assigned_layers += num_layers_per_seg

    #calculate FWD and INV load counters for each seg

    FWD_TF_load_counter_per_seg = []
    INV_TF_load_counter_per_seg = []
    cummulative_sum_of_assigned_layers = 0

    for h_seg_id in range(TF_LOAD_H_SEGS_PER_PARA_LIMB):
        num_layers = layers_per_seg[h_seg_id]; #remaining layers/remaining segments

        fwd_tf_load_counter = 0
        inv_tf_load_counter = 0

        if(load_direction_per_seg[h_seg_id]):
            for layer_id in range(cummulative_sum_of_assigned_layers, cummulative_sum_of_assigned_layers+num_layers):
                fwd_tf_load_counter += fwd_layerWiseTFBufDepth[layer_id]//2
                inv_tf_load_counter += inv_layerWiseTFBufDepth[layer_id]//2
        else:
            for layer_id in range(cummulative_sum_of_assigned_layers+num_layers-1, cummulative_sum_of_assigned_layers-1, -1):
                fwd_tf_load_counter += fwd_layerWiseTFBufDepth[layer_id]//2
                inv_tf_load_counter += inv_layerWiseTFBufDepth[layer_id]//2
        
        FWD_TF_load_counter_per_seg.append(fwd_tf_load_counter)
        INV_TF_load_counter_per_seg.append(inv_tf_load_counter)
        cummulative_sum_of_assigned_layers+=num_layers

    return FWD_TF_load_counter_per_seg, INV_TF_load_counter_per_seg

def gen_tf_load_code(task_idx, fwd_load_counter, inv_load_counter, para_num_limbs):
    line = ""
    line += "void Mmap2Stream_tf_" + str(task_idx) + "_" + str(para_num_limbs) + "_limbs(tapa::async_mmap<TF_WIDE_DATA>& tf_mmap," + "\n"
    
    for para_limb_idx in range(para_num_limbs):
        line += "                 tapa::ostreams<DWORD, TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2>& tf_stream_L" + str(para_limb_idx) + "_0," + "\n"

    line += "                 bool direction," + "\n"
    line += "                 VAR_TYPE_16 iter) {" + "\n"
    line += "" + "\n"
    line += "  " + "\n"
    line += "  VAR_TYPE_16 fwd_total_depth = " + str(fwd_load_counter) + ";" + "\n"
    line += "  VAR_TYPE_16 inv_total_depth = " + str(inv_load_counter) + ";" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_16 total_depth;" + "\n"
    line += "  if(direction){" + "\n"
    line += "    total_depth = fwd_total_depth;" + "\n"
    line += "  }" + "\n"
    line += "  else{" + "\n"
    line += "    total_depth = inv_total_depth;" + "\n"
    line += "  }" + "\n"
    line += "  " + "\n"
    line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    LOAD_TF:for (int i_req = 0, i_resp=0; i_resp < (total_depth);) {" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      if( ( i_req < (total_depth) ) && (tf_mmap.read_addr.try_write(i_req)) ){" + "\n"
    line += "        i_req++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( !tf_mmap.read_data.empty() ){" + "\n"
    line += "        TF_WIDE_DATA val = tf_mmap.read_data.read();" + "\n"
    line += "        " + "\n"

    for para_limb_idx in range(para_num_limbs):
        line += "        for(VAR_TYPE_8 j=0; j<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2; j++){" + "\n"
        line += "          DWORD smallVal = (DWORD)(val & ((((TF_WIDE_DATA)1)<<(2*WORD_SIZE))-1));" + "\n"
        line += "          tf_stream_L" + str(para_limb_idx) + "_0[j].write(smallVal);" + "\n"
        line += "          val >>= (2*DRAM_WORD_SIZE);" + "\n"
        line += "        }" + "\n"
        line += "        " + "\n"

    line += "        i_resp++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  #ifndef __SYNTHESIS__" + "\n"
    line += "  printf(\"[Mmap2Stream_tf]: TF loading done\\n\");" + "\n"
    line += "  #endif" + "\n"
    line += "" + "\n"
    line += "}" + "\n"

    return line

def gen_tf_load(designParamsVar):

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_tf_load_configs(designParamsVar)
    
    fwd_load_counters, inv_load_counters = gen_tf_load_counters(designParamsVar)

    PARA_LIMB_PORTS_PER_TF_PORT = designParamsVar.PARA_LIMB_PORTS_PER_TF_PORT

    # calc number of required tasks
    num_of_tf_load_tasks = len(fwd_load_counters)

    # generate code
    code = ""
    
    if(is_full_load_needed):
        for task_idx in range(num_of_tf_load_tasks):
            code += gen_tf_load_code(task_idx, fwd_load_counters[task_idx], inv_load_counters[task_idx], PARA_LIMB_PORTS_PER_TF_PORT)
    
    if(is_partial_load_needed):
        for task_idx in range(num_of_tf_load_tasks):
            code += gen_tf_load_code(task_idx, fwd_load_counters[task_idx], inv_load_counters[task_idx], partial_load_size)

    return code