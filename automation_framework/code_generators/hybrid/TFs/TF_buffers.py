from code_generators.hybrid.TFs.TF_common import partition
from code_generators.hybrid.TFs.TF_common import verifyFwdInvPartitions
from code_generators.common.helper_functions import num_arr_to_cppArrStr

import math
import sys

# class designParams:
#     WORD_SIZE = 0
#     REDUCTION_TYPE = 0
#     WLM_WORD_SIZE = 0
#     logN = 0
#     POLY_SIZE = 0
#     V_BUG_SIZE = 0
#     H_BUG_SIZE = 0
#     logV_BUG_SIZE = 0
#     BUG_CONCAT_FACTOR = 0
#     logBUG_CONCAT_FACTOR = 0
#     V_TOTAL_DATA = 0
#     log_V_TOTAL_DATA = 0
#     NUM_INTER_BUG_COM = 0
#     POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = 0
#     BUG_PER_PARA_LIMB_POLY_PORT = 0
#     BUG_PER_PARA_LIMB_POLY_WIDE_DATA = 0
#     SEQ_BUG_PER_PARA_LIMB_POLY_PORT = 0
#     TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = 0
#     TF_LOAD_V_SEGS_PER_PARA_LIMB = 0
#     TF_LOAD_H_SEGS_PER_PARA_LIMB = 0

class TFBuffersParams:
    TFArr_size = []
    fwd_tf_load_counter = []
    inv_tf_load_counter = []
    fwd_this_buf_limit = []
    inv_this_buf_limit = []

    fwd_log_stageWiseTFs = []
    inv_log_stageWiseTFs = []
    fwd_stageWiseOffset = []
    inv_stageWiseOffset = []
    fwd_log_num_val_accessed_by_consec_BUs_arr = []
    inv_log_num_val_accessed_by_consec_BUs_arr = []

    layers_per_seg = []
    load_direction_per_seg = []

def gen_tf_buf_config(designParamsVar):
    
    logN = designParamsVar.logN
    POLY_SIZE = designParamsVar.POLY_SIZE
    V_BUG_SIZE = designParamsVar.V_BUG_SIZE
    H_BUG_SIZE = designParamsVar.H_BUG_SIZE
    logV_BUG_SIZE = designParamsVar.logV_BUG_SIZE
    BUG_CONCAT_FACTOR = designParamsVar.BUG_CONCAT_FACTOR
    logBUG_CONCAT_FACTOR = designParamsVar.logBUG_CONCAT_FACTOR
    V_TOTAL_DATA = designParamsVar.V_TOTAL_DATA
    log_V_TOTAL_DATA = designParamsVar.log_V_TOTAL_DATA
    
    # TF_LOAD_V_SEGS_PER_PARA_LIMB = designParamsVar.TF_LOAD_V_SEGS_PER_PARA_LIMB
    TF_LOAD_H_SEGS_PER_PARA_LIMB = designParamsVar.TF_LOAD_H_SEGS_PER_PARA_LIMB;   #i.e., How many segments total H_BUG_SIZE layers are bokern into

    dataFlowIterLimit = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE )

    # Output arrays
    TFArr_size = []
    fwd_tf_load_counter = []
    inv_tf_load_counter = []
    fwd_this_buf_limit = []
    inv_this_buf_limit = []
    fwd_log_stageWiseTFs = []
    inv_log_stageWiseTFs = []
    fwd_stageWiseOffset = []
    inv_stageWiseOffset = []
    fwd_log_num_val_accessed_by_consec_BUs_arr = []
    inv_log_num_val_accessed_by_consec_BUs_arr = []

    for layers in range(H_BUG_SIZE):
        temp_fwd_log_stageWiseTFs = []
        temp_inv_log_stageWiseTFs = []
        temp_fwd_stageWiseOffset = []
        temp_inv_stageWiseOffset = []
        temp_fwd_log_num_val_accessed_by_consec_BUs_arr = []
        temp_inv_log_num_val_accessed_by_consec_BUs_arr = []
        
        for dataFlowIter in range(dataFlowIterLimit):
            temp_fwd_log_stageWiseTFs.append(1) #initializing to 2, because in partial BUG scenarios, some stages still send some garbage TFs values. 
            temp_inv_log_stageWiseTFs.append(1) #initializing to 2, because in partial BUG scenarios, some stages still send some garbage TFs values. 
            temp_fwd_stageWiseOffset.append(0)
            temp_inv_stageWiseOffset.append(0)
            temp_fwd_log_num_val_accessed_by_consec_BUs_arr.append(0) #avoid seg fault in csim for partial BUG. This values is being used for division
            temp_inv_log_num_val_accessed_by_consec_BUs_arr.append(0) #avoid seg fault in csim for partial BUG. This values is being used for division
        
        TFArr_size.append(0)
        fwd_tf_load_counter.append(0)
        inv_tf_load_counter.append(0)
        fwd_this_buf_limit.append(0)
        inv_this_buf_limit.append(0)
        fwd_log_stageWiseTFs.append(temp_fwd_log_stageWiseTFs)
        inv_log_stageWiseTFs.append(temp_inv_log_stageWiseTFs)
        fwd_stageWiseOffset.append(temp_fwd_stageWiseOffset)
        inv_stageWiseOffset.append(temp_inv_stageWiseOffset)
        fwd_log_num_val_accessed_by_consec_BUs_arr.append(temp_fwd_log_num_val_accessed_by_consec_BUs_arr)
        inv_log_num_val_accessed_by_consec_BUs_arr.append(temp_inv_log_num_val_accessed_by_consec_BUs_arr)

    fwd_layerWiseTFBufDepth = []
    inv_layerWiseTFBufDepth = []
    for i in range(H_BUG_SIZE):
        fwd_layerWiseTFBufDepth.append(0)
        inv_layerWiseTFBufDepth.append(0)

    for stage in range(logN):

        #total TFs
        fwd_num_tfs_in_this_stage = 1 << stage

        inv_num_tfs_in_this_stage = 1 << stage
        inv_tf_change_freq = (POLY_SIZE//2)//inv_num_tfs_in_this_stage #distance between two TF values
        inv_log_tf_change_freq = (logN-1) - stage

        #check partial BUG
        fwd_dataFlowIter = stage//H_BUG_SIZE
        fwd_numberOfSupportedStages = (H_BUG_SIZE) if ( logN-(fwd_dataFlowIter*H_BUG_SIZE) > H_BUG_SIZE ) else ( logN-(fwd_dataFlowIter*H_BUG_SIZE) )
        fwd_tf_grp_size_BUG = 1 << (fwd_numberOfSupportedStages-1) #to support remaining layers, how many poly. values are grouped together is (1 << (num_partial_layers)). Since 2 poly val. need 1 TF, this is the eqn for TFs
        fwd_num_tf_grps_per_BUG = V_BUG_SIZE//fwd_tf_grp_size_BUG
        fwd_log_num_tf_grps_per_BUG = logV_BUG_SIZE - (fwd_numberOfSupportedStages-1)

        inv_dataFlowIter = (logN - 1 - stage)//H_BUG_SIZE
        inv_numberOfSupportedStages =  (H_BUG_SIZE) if ( logN-(inv_dataFlowIter*H_BUG_SIZE) > H_BUG_SIZE ) else ( logN-(inv_dataFlowIter*H_BUG_SIZE) )
        inv_tf_grp_size_BUG = 1 << (inv_numberOfSupportedStages-1) #to support remaining layers, how many poly. values are grouped together is (1 << (num_partial_layers)). Since 2 poly val. need 1 TF, this is the eqn for TFs
        inv_num_tf_grps_per_BUG = V_BUG_SIZE//inv_tf_grp_size_BUG
        inv_log_num_tf_grps_per_BUG = logV_BUG_SIZE - (inv_numberOfSupportedStages-1)

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

        fwd_log_num_val_accessed_by_consec_BUs =  ( 0 ) if ( ( fwd_layer_id == 0 ) and ( fwd_tf_grp_size_BUG !=1 ) ) else ( 1 )
        inv_log_num_val_accessed_by_consec_BUs =  ( 1 ) if ( ( inv_layer_id == 0 ) and ( inv_tf_grp_size_BUG !=1 ) ) else ( 0 )

        #As # BUGs increases, TFs can be spread accross different buffers. this determines that
        #if total number of TFs only fit into one BUG, duplicates among BUGs. 
        #Else, if number of TFs are larger than a single BUG, hence spread accross BUGs
        fwd_BUG_concat_dist_factor =  ( 1 ) if ( fwd_num_tfs_in_this_stage <= V_BUG_SIZE ) else ( ( fwd_num_tfs_in_this_stage//fwd_per_BUG_diff_num_data ) if ( (fwd_num_tfs_in_this_stage/fwd_per_BUG_diff_num_data) <= BUG_CONCAT_FACTOR ) else ( BUG_CONCAT_FACTOR ) )
        inv_BUG_concat_dist_factor = ( ( (BUG_CONCAT_FACTOR*V_BUG_SIZE)//(inv_tf_change_freq*inv_per_BUG_diff_num_data) ) if ( ( (BUG_CONCAT_FACTOR*V_BUG_SIZE)//(inv_tf_change_freq*inv_per_BUG_diff_num_data) ) > 0 ) else (1) ) if ( inv_tf_change_freq > V_BUG_SIZE ) else ( BUG_CONCAT_FACTOR )
        
        fwd_log_BUG_concat_dist_factor = ( 0 ) if ( fwd_num_tfs_in_this_stage <= V_BUG_SIZE ) else ( ( stage - fwd_layer_id ) if ( (fwd_num_tfs_in_this_stage/fwd_per_BUG_diff_num_data) <= BUG_CONCAT_FACTOR ) else ( logBUG_CONCAT_FACTOR ) )
        inv_log_BUG_concat_dist_factor = ( ((logBUG_CONCAT_FACTOR+logV_BUG_SIZE) - (inv_log_tf_change_freq + ( (H_BUG_SIZE - 1) - inv_layer_id ))) if ( ( (BUG_CONCAT_FACTOR*V_BUG_SIZE)//(inv_tf_change_freq*inv_per_BUG_diff_num_data) ) > 0 ) else (0) ) if ( inv_tf_change_freq > V_BUG_SIZE ) else ( logBUG_CONCAT_FACTOR )

        #number of unique tf values going per single iteration
        fwd_unique_tf_per_iter = fwd_per_BUG_diff_num_data * fwd_num_tf_grps_per_BUG * fwd_BUG_concat_dist_factor
        inv_unique_tf_per_iter = (inv_per_BUG_diff_num_data//inv_num_tf_grps_per_BUG) * inv_BUG_concat_dist_factor

        fwd_log_unique_tf_per_iter = fwd_layer_id + fwd_log_num_tf_grps_per_BUG + fwd_log_BUG_concat_dist_factor
        inv_log_unique_tf_per_iter = ( ( (H_BUG_SIZE - 1) - inv_layer_id ) - inv_log_num_tf_grps_per_BUG ) + inv_log_BUG_concat_dist_factor

        #Number of total TFs going into a buffer
        #Eqn is: per "num_val_accessed_by_consec_BUs" depth "unique_tf_per_iter" values were stored. Then how much depth for "num_tfs_in_this_stage"
        fwd_num_tfs_per_buf = fwd_num_tfs_in_this_stage // ( fwd_unique_tf_per_iter//fwd_num_val_accessed_by_consec_BUs )
        fwd_layerWiseTFBufDepth[fwd_layer_id] += fwd_num_tfs_per_buf
        fwd_log_num_tfs_per_buf = stage - (fwd_log_unique_tf_per_iter - fwd_log_num_val_accessed_by_consec_BUs)

        inv_num_tfs_per_buf = inv_num_tfs_in_this_stage // ( inv_unique_tf_per_iter // inv_num_val_accessed_by_consec_BUs )
        inv_layerWiseTFBufDepth[inv_layer_id] += inv_num_tfs_per_buf
        inv_log_num_tfs_per_buf = stage - ( inv_log_unique_tf_per_iter - inv_log_num_val_accessed_by_consec_BUs )

        #update stageWise data
        if( fwd_dataFlowIter < (dataFlowIterLimit-1) ): #since offset does not need to be calculated with the last stage
            fwd_stageWiseOffset[fwd_layer_id][fwd_dataFlowIter+1] = fwd_stageWiseOffset[fwd_layer_id][fwd_dataFlowIter] + fwd_num_tfs_per_buf
        

        fwd_log_stageWiseTFs[fwd_layer_id][fwd_dataFlowIter] = fwd_log_num_tfs_per_buf
        fwd_log_num_val_accessed_by_consec_BUs_arr[fwd_layer_id][fwd_dataFlowIter] = fwd_log_num_val_accessed_by_consec_BUs
        
        if( (dataFlowIterLimit - 1 - inv_dataFlowIter) < (dataFlowIterLimit-1) ): #since offset does not need to be calculated with the last stage
            inv_stageWiseOffset[inv_layer_id][dataFlowIterLimit - 1 - inv_dataFlowIter + 1] = inv_stageWiseOffset[inv_layer_id][dataFlowIterLimit - 1 - inv_dataFlowIter] + inv_num_tfs_per_buf

        inv_log_stageWiseTFs[inv_layer_id][dataFlowIterLimit - 1 - inv_dataFlowIter] = inv_log_num_tfs_per_buf
        inv_log_num_val_accessed_by_consec_BUs_arr[inv_layer_id][dataFlowIterLimit - 1 - inv_dataFlowIter] = inv_log_num_val_accessed_by_consec_BUs
        

    #make each depth even as two values going to be packed together
    for layer in range(H_BUG_SIZE):
        if( fwd_layerWiseTFBufDepth[layer]%2==1 ):#odd
            fwd_layerWiseTFBufDepth[layer]+=1
        
        if( inv_layerWiseTFBufDepth[layer]%2==1 ):#odd
            inv_layerWiseTFBufDepth[layer]+=1
    
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

    #Deciding load direction
    from_start_segs = (TF_LOAD_H_SEGS_PER_PARA_LIMB+1)//2

    for seg_id in range(TF_LOAD_H_SEGS_PER_PARA_LIMB):
        num_layers_per_seg = len(fwd_TFData_segs[seg_id])
        layers_per_seg.append(num_layers_per_seg)
        if(seg_id<from_start_segs):
            load_direction_per_seg.append(True)
        else:
            load_direction_per_seg.append(False)

    #calculate FWD and INV load counters for each seg

    FWD_TF_load_counter_per_seg = []
    INV_TF_load_counter_per_seg = []
    cummulative_sum_of_assigned_layers = 0

    for h_seg_id in range(TF_LOAD_H_SEGS_PER_PARA_LIMB):
        num_layers = layers_per_seg[h_seg_id] #remaining layers/remaining segments

        if( load_direction_per_seg[h_seg_id] ): #if the loading direction is forward
            for layer_id in range( (cummulative_sum_of_assigned_layers+num_layers-1), cummulative_sum_of_assigned_layers-1, -1 ): #coming from the reverse of layers in this segment to support accumulation of remaining layers
                for update_id in range(layer_id, cummulative_sum_of_assigned_layers-1, -1): # starting from the current layer add this for all the previous layers
                    fwd_tf_load_counter[update_id] += fwd_layerWiseTFBufDepth[layer_id]//2
                    inv_tf_load_counter[update_id] += inv_layerWiseTFBufDepth[layer_id]//2
        else: #if the loading direction is backward
            for layer_id in range( cummulative_sum_of_assigned_layers, (cummulative_sum_of_assigned_layers+num_layers) ): #coming from the beging to end of this segment
                for update_id in range(layer_id, (cummulative_sum_of_assigned_layers+num_layers)): #starting from the current layer, add this to all the next layers since they need to foward this amount of data to the current layer
                    fwd_tf_load_counter[update_id] += fwd_layerWiseTFBufDepth[layer_id]//2
                    inv_tf_load_counter[update_id] += inv_layerWiseTFBufDepth[layer_id]//2
        
        cummulative_sum_of_assigned_layers+=num_layers

    for layer_id in range(H_BUG_SIZE):
        TFArr_size[layer_id] = max(fwd_layerWiseTFBufDepth[layer_id], inv_layerWiseTFBufDepth[layer_id])
        fwd_this_buf_limit[layer_id] = fwd_layerWiseTFBufDepth[layer_id]//2
        inv_this_buf_limit[layer_id] = inv_layerWiseTFBufDepth[layer_id]//2
    
    #assgning return variable
    TFBuffersParamsVar = TFBuffersParams()

    TFBuffersParamsVar.TFArr_size = TFArr_size
    TFBuffersParamsVar.fwd_tf_load_counter = fwd_tf_load_counter
    TFBuffersParamsVar.inv_tf_load_counter = inv_tf_load_counter
    TFBuffersParamsVar.fwd_this_buf_limit = fwd_this_buf_limit
    TFBuffersParamsVar.inv_this_buf_limit = inv_this_buf_limit
    TFBuffersParamsVar.fwd_log_stageWiseTFs = fwd_log_stageWiseTFs
    TFBuffersParamsVar.inv_log_stageWiseTFs = inv_log_stageWiseTFs
    TFBuffersParamsVar.fwd_stageWiseOffset = fwd_stageWiseOffset
    TFBuffersParamsVar.inv_stageWiseOffset = inv_stageWiseOffset
    TFBuffersParamsVar.fwd_log_num_val_accessed_by_consec_BUs_arr = fwd_log_num_val_accessed_by_consec_BUs_arr
    TFBuffersParamsVar.inv_log_num_val_accessed_by_consec_BUs_arr = inv_log_num_val_accessed_by_consec_BUs_arr
    
    TFBuffersParamsVar.layers_per_seg = layers_per_seg
    TFBuffersParamsVar.load_direction_per_seg = load_direction_per_seg

    return TFBuffersParamsVar

    # #prints 
    # print("\n")
    # print("TFArr_size=" + str(TFArr_size))
    # print("fwd_tf_load_counter=" + str(fwd_tf_load_counter))
    # print("inv_tf_load_counter=" + str(inv_tf_load_counter))
    # print("fwd_this_buf_limit=" + str(fwd_this_buf_limit))
    # print("inv_this_buf_limit=" + str(inv_this_buf_limit))

    # print("fwd_log_stageWiseTFs: " + str(fwd_log_stageWiseTFs))
    # print("inv_log_stageWiseTFs: " + str(inv_log_stageWiseTFs))
    # print("fwd_stageWiseOffset: " + str(fwd_stageWiseOffset))
    # print("inv_stageWiseOffset: " + str(inv_stageWiseOffset))
    # print("fwd_log_num_val_accessed_by_consec_BUs_arr: " + str(fwd_log_num_val_accessed_by_consec_BUs_arr))
    # print("inv_log_num_val_accessed_by_consec_BUs_arr: " + str(inv_log_num_val_accessed_by_consec_BUs_arr))

def TFBUF_common_function_gen():

    line = ""
    line += "void TFBuf_loadTF_wiFW(" + "\n"
    line += "           tapa::istream<DWORD>& loadTFStream," + "\n"
    line += "           tapa::ostream<DWORD>& loadTFToNext," + "\n"
    line += "           WORD TFArr[N/2]," + "\n"
    line += "           VAR_TYPE_16 tf_load_counter, " + "\n"
    line += "           VAR_TYPE_16 this_buf_limit){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  //load" + "\n"
    line += "  TF_LOAD:for(VAR_TYPE_16 i=0; i<tf_load_counter;){" + "\n"
    line += "    #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    line += "    bool inpStreamNotEmpty = !loadTFStream.empty();" + "\n"
    line += "" + "\n"
    line += "    if(inpStreamNotEmpty){" + "\n"
    line += "      if(i<this_buf_limit){" + "\n"
    line += "        DWORD val = loadTFStream.read();   " + "\n"
    line += "        TFArr[2*i] = (WORD)(val & ((((DWORD)1) << WORD_SIZE) - 1));" + "\n"
    line += "        TFArr[2*i+1] = (WORD)(val >> WORD_SIZE);" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        loadTFToNext.write((loadTFStream.read()));" + "\n"
    line += "      }" + "\n"
    line += "      i++;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"
    line += "void TFBuf_loadTF_woFW(" + "\n"
    line += "           tapa::istream<DWORD>& loadTFStream," + "\n"
    line += "           WORD TFArr[N/2]," + "\n"
    line += "           VAR_TYPE_16 tf_load_counter){" + "\n"
    line += "  " + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  //load" + "\n"
    line += "  TF_LOAD:for(VAR_TYPE_16 i=0; i<tf_load_counter;){" + "\n"
    line += "    #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    line += "    bool inpStreamNotEmpty = !loadTFStream.empty();" + "\n"
    line += "" + "\n"
    line += "    if(inpStreamNotEmpty){" + "\n"
    line += "      DWORD val = loadTFStream.read();   " + "\n"
    line += "      TFArr[2*i] = (WORD)(val & ((((DWORD)1) << WORD_SIZE) - 1));" + "\n"
    line += "      TFArr[2*i+1] = (WORD)(val >> WORD_SIZE);" + "\n"
    line += "      i++;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"
    line += "void TFBuf_comp(" + "\n"
    line += "           tapa::ostream<WORD>& tfToBu_0," + "\n"
    line += "           tapa::ostream<WORD>& tfToBu_1," + "\n"
    line += "           WORD TFArr[N/2]," + "\n"
    line += "           const VAR_TYPE_16 fwd_log_stageWiseTFs[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )]," + "\n"
    line += "           const VAR_TYPE_16 inv_log_stageWiseTFs[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )]," + "\n"
    line += "           const VAR_TYPE_16 fwd_stageWiseOffset[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )]," + "\n"
    line += "           const VAR_TYPE_16 inv_stageWiseOffset[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )]," + "\n"
    line += "           const VAR_TYPE_16 fwd_log_num_val_accessed_by_consec_BUs_arr[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )]," + "\n"
    line += "           const VAR_TYPE_16 inv_log_num_val_accessed_by_consec_BUs_arr[( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE )]," + "\n"
    line += "           VAR_TYPE_8 unit_id_0," + "\n"
    line += "           VAR_TYPE_8 unit_id_1," + "\n"
    line += "           VAR_TYPE_16 dataCount," + "\n"
    line += "           VAR_TYPE_8 dataFlowIterLimit," + "\n"
    line += "           bool direction){" + "\n"
    line += "  " + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  TF_DF_ITER:for(VAR_TYPE_8 dataFlowIter = 0; dataFlowIter<dataFlowIterLimit; dataFlowIter++){" + "\n"
    line += "      " + "\n"
    line += "    VAR_TYPE_16 log_num_TFs;" + "\n"
    line += "    VAR_TYPE_16 tf_offset;" + "\n"
    line += "    VAR_TYPE_16 log_num_val_accessed_by_consec_BUs;" + "\n"
    line += "    VAR_TYPE_16 log_countLimit;" + "\n"
    line += "" + "\n"
    line += "    if(direction){" + "\n"
    line += "      log_num_TFs = fwd_log_stageWiseTFs[dataFlowIter];" + "\n"
    line += "      tf_offset = fwd_stageWiseOffset[dataFlowIter];" + "\n"
    line += "      log_num_val_accessed_by_consec_BUs = fwd_log_num_val_accessed_by_consec_BUs_arr[dataFlowIter];" + "\n"
    line += "      log_countLimit = log_num_TFs - log_num_val_accessed_by_consec_BUs;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      log_num_TFs = inv_log_stageWiseTFs[dataFlowIter];" + "\n"
    line += "      tf_offset = inv_stageWiseOffset[dataFlowIter];" + "\n"
    line += "      log_num_val_accessed_by_consec_BUs = inv_log_num_val_accessed_by_consec_BUs_arr[dataFlowIter];" + "\n"
    line += "      log_countLimit = (logN - log_V_TOTAL_DATA) - (log_num_TFs - log_num_val_accessed_by_consec_BUs);" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    TF_COMP:for(VAR_TYPE_16 inpCount=0; inpCount<dataCount; inpCount++){" + "\n"
    line += "      #pragma HLS PIPELINE II = 1" + "\n"
    line += "      " + "\n"
    line += "      VAR_TYPE_16 tf_idx_0;" + "\n"
    line += "      VAR_TYPE_16 tf_idx_1;" + "\n"
    line += "      if(direction){" + "\n"
    line += "        tf_idx_0 = tf_offset + (inpCount & ( (1<<log_countLimit)-1 ) ) + ( (unit_id_0 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 )) << (log_countLimit) );" + "\n"
    line += "        tf_idx_1 = tf_offset + (inpCount & ( (1<<log_countLimit)-1 ) ) + ( (unit_id_1 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 )) << (log_countLimit) );" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        tf_idx_0 = tf_offset + ( (inpCount >> (log_countLimit) ) << log_num_val_accessed_by_consec_BUs ) + (unit_id_0 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 ));" + "\n"
    line += "        tf_idx_1 = tf_offset + ( (inpCount >> (log_countLimit) ) << log_num_val_accessed_by_consec_BUs ) + (unit_id_1 & ( (1<<log_num_val_accessed_by_consec_BUs) - 1 ));" + "\n"
    line += "      }" + "\n"
    line += "    " + "\n"
    line += "      WORD tfVal_0 = TFArr[tf_idx_0];" + "\n"
    line += "      WORD tfVal_1 = TFArr[tf_idx_1];" + "\n"
    line += "" + "\n"
    line += "      tfToBu_0.write(tfVal_0);" + "\n"
    line += "      tfToBu_1.write(tfVal_1);" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def TFBUF_wiFW_gen(TFBuffersParamsVar, layer_id):
    TFArr_size = TFBuffersParamsVar.TFArr_size[layer_id]
    fwd_tf_load_counter = TFBuffersParamsVar.fwd_tf_load_counter[layer_id]
    inv_tf_load_counter = TFBuffersParamsVar.inv_tf_load_counter[layer_id]
    fwd_this_buf_limit = TFBuffersParamsVar.fwd_this_buf_limit[layer_id]
    inv_this_buf_limit = TFBuffersParamsVar.inv_this_buf_limit[layer_id]
    fwd_log_stageWiseTFs = num_arr_to_cppArrStr(TFBuffersParamsVar.fwd_log_stageWiseTFs[layer_id])
    inv_log_stageWiseTFs = num_arr_to_cppArrStr(TFBuffersParamsVar.inv_log_stageWiseTFs[layer_id])
    fwd_stageWiseOffset = num_arr_to_cppArrStr(TFBuffersParamsVar.fwd_stageWiseOffset[layer_id])
    inv_stageWiseOffset = num_arr_to_cppArrStr(TFBuffersParamsVar.inv_stageWiseOffset[layer_id])
    fwd_log_num_val_accessed_by_consec_BUs_arr = num_arr_to_cppArrStr(TFBuffersParamsVar.fwd_log_num_val_accessed_by_consec_BUs_arr[layer_id])
    inv_log_num_val_accessed_by_consec_BUs_arr = num_arr_to_cppArrStr(TFBuffersParamsVar.inv_log_num_val_accessed_by_consec_BUs_arr[layer_id])

    line = ""
    line += "void TFBuf_wiFW_" + str(layer_id) + "(" + "\n"
    line += "           tapa::istream<DWORD>& loadTFStream," + "\n"
    line += "           tapa::ostream<DWORD>& loadTFToNext," + "\n"
    line += "           tapa::ostream<WORD>& tfToBu_0," + "\n"
    line += "           tapa::ostream<WORD>& tfToBu_1," + "\n"
    line += "           bool direction," + "\n"
    line += "           VAR_TYPE_8 BUG_id," + "\n"
    line += "           VAR_TYPE_8 TFGen_offset, " + "\n"
    line += "           VAR_TYPE_8 unit_id," + "\n"
    line += "           VAR_TYPE_16 iter){" + "\n"
    line += "  " + "\n"
    line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
    line += "  const VAR_TYPE_8 dataFlowIterLimit = (VAR_TYPE_8)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE );" + "\n"
    line += "" + "\n"
    line += "  //==== Auto generated variables start ====//" + "\n"
    line += "  const VAR_TYPE_16 TFArr_size = " + str(TFArr_size) + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_tf_load_counter = " + str(fwd_tf_load_counter) + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_tf_load_counter = " + str(inv_tf_load_counter) + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_this_buf_limit = " + str(fwd_this_buf_limit) + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_this_buf_limit = " + str(inv_this_buf_limit) + ";" + "\n"
    line += "" + "\n"
    line += "  const VAR_TYPE_16 fwd_log_stageWiseTFs[dataFlowIterLimit] = " + fwd_log_stageWiseTFs + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_log_stageWiseTFs[dataFlowIterLimit] = " + inv_log_stageWiseTFs + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_stageWiseOffset[dataFlowIterLimit] = " + fwd_stageWiseOffset + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_stageWiseOffset[dataFlowIterLimit] = " + inv_stageWiseOffset + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = " + fwd_log_num_val_accessed_by_consec_BUs_arr + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = " + inv_log_num_val_accessed_by_consec_BUs_arr + ";" + "\n"
    line += "  //==== Auto generated variables end ====//" + "\n"
    line += "  " + "\n"
    line += "  const VAR_TYPE_16 tf_load_counter = (direction) ? (fwd_tf_load_counter) : (inv_tf_load_counter);" + "\n"
    line += "  const VAR_TYPE_16 this_buf_limit = (direction) ? (fwd_this_buf_limit) : (inv_this_buf_limit);" + "\n"
    line += "" + "\n"
    line += "  WORD TFArr[2][TFArr_size];" + "\n"
    line += "  #pragma HLS bind_storage variable=TFArr type=RAM_T2P impl=uram latency=1" + "\n"
    line += "  #pragma HLS array_partition variable=TFArr type=complete dim=1" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_8 unit_id_0 = 2*unit_id;" + "\n"
    line += "  VAR_TYPE_8 unit_id_1 = 2*unit_id+1;" + "\n"
    line += "" + "\n"
    line += "  TF_ITER:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    TFBuf_loadTF_wiFW(loadTFStream, loadTFToNext, TFArr[iterCount%2], tf_load_counter, this_buf_limit);" + "\n"
    line += "    TFBuf_comp(tfToBu_0, tfToBu_1, TFArr[(iterCount+1)%2], fwd_log_stageWiseTFs, inv_log_stageWiseTFs, fwd_stageWiseOffset, inv_stageWiseOffset, fwd_log_num_val_accessed_by_consec_BUs_arr, inv_log_num_val_accessed_by_consec_BUs_arr, unit_id_0, unit_id_1, dataCount, dataFlowIterLimit, direction);" + "\n"
    line += "  }" + "\n"
    line += "}    " + "\n"

    return line

def TFBUF_woFW_gen(TFBuffersParamsVar, layer_id):
    TFArr_size = TFBuffersParamsVar.TFArr_size[layer_id]
    fwd_tf_load_counter = TFBuffersParamsVar.fwd_tf_load_counter[layer_id]
    inv_tf_load_counter = TFBuffersParamsVar.inv_tf_load_counter[layer_id]
    fwd_this_buf_limit = TFBuffersParamsVar.fwd_this_buf_limit[layer_id]
    inv_this_buf_limit = TFBuffersParamsVar.inv_this_buf_limit[layer_id]
    fwd_log_stageWiseTFs = num_arr_to_cppArrStr(TFBuffersParamsVar.fwd_log_stageWiseTFs[layer_id])
    inv_log_stageWiseTFs = num_arr_to_cppArrStr(TFBuffersParamsVar.inv_log_stageWiseTFs[layer_id])
    fwd_stageWiseOffset = num_arr_to_cppArrStr(TFBuffersParamsVar.fwd_stageWiseOffset[layer_id])
    inv_stageWiseOffset = num_arr_to_cppArrStr(TFBuffersParamsVar.inv_stageWiseOffset[layer_id])
    fwd_log_num_val_accessed_by_consec_BUs_arr = num_arr_to_cppArrStr(TFBuffersParamsVar.fwd_log_num_val_accessed_by_consec_BUs_arr[layer_id])
    inv_log_num_val_accessed_by_consec_BUs_arr = num_arr_to_cppArrStr(TFBuffersParamsVar.inv_log_num_val_accessed_by_consec_BUs_arr[layer_id])

    line = ""
    line += "void TFBuf_woFW_" + str(layer_id) + "(" + "\n"
    line += "           tapa::istream<DWORD>& loadTFStream," + "\n"
    line += "           tapa::ostream<WORD>& tfToBu_0," + "\n"
    line += "           tapa::ostream<WORD>& tfToBu_1," + "\n"
    line += "           bool direction," + "\n"
    line += "           VAR_TYPE_8 BUG_id," + "\n"
    line += "           VAR_TYPE_8 TFGen_offset, " + "\n"
    line += "           VAR_TYPE_8 unit_id," + "\n"
    line += "           VAR_TYPE_16 iter){" + "\n"
    line += "  " + "\n"
    line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
    line += "  const VAR_TYPE_8 dataFlowIterLimit = (VAR_TYPE_8)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE );" + "\n"
    line += "" + "\n"
    line += "  //==== Auto generated variables start ====//" + "\n"
    line += "  const VAR_TYPE_16 TFArr_size = " + str(TFArr_size) + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_tf_load_counter = " + str(fwd_tf_load_counter) + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_tf_load_counter = " + str(inv_tf_load_counter) + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_this_buf_limit = " + str(fwd_this_buf_limit) + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_this_buf_limit = " + str(inv_this_buf_limit) + ";" + "\n"
    line += "" + "\n"
    line += "  const VAR_TYPE_16 fwd_log_stageWiseTFs[dataFlowIterLimit] = " + fwd_log_stageWiseTFs + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_log_stageWiseTFs[dataFlowIterLimit] = " + inv_log_stageWiseTFs + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_stageWiseOffset[dataFlowIterLimit] = " + fwd_stageWiseOffset + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_stageWiseOffset[dataFlowIterLimit] = " + inv_stageWiseOffset + ";" + "\n"
    line += "  const VAR_TYPE_16 fwd_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = " + fwd_log_num_val_accessed_by_consec_BUs_arr + ";" + "\n"
    line += "  const VAR_TYPE_16 inv_log_num_val_accessed_by_consec_BUs_arr[dataFlowIterLimit] = " + inv_log_num_val_accessed_by_consec_BUs_arr + ";" + "\n"
    line += "  //==== Auto generated variables end ====//" + "\n"
    line += "  " + "\n"
    line += "  const VAR_TYPE_16 tf_load_counter = (direction) ? (fwd_tf_load_counter) : (inv_tf_load_counter);" + "\n"
    line += "  const VAR_TYPE_16 this_buf_limit = (direction) ? (fwd_this_buf_limit) : (inv_this_buf_limit);" + "\n"
    line += "" + "\n"
    line += "  WORD TFArr[2][TFArr_size];" + "\n"
    line += "  #pragma HLS bind_storage variable=TFArr type=RAM_T2P impl=uram latency=1" + "\n"
    line += "  #pragma HLS array_partition variable=TFArr type=complete dim=1" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_8 unit_id_0 = 2*unit_id;" + "\n"
    line += "  VAR_TYPE_8 unit_id_1 = 2*unit_id+1;" + "\n"
    line += "" + "\n"
    line += "  //comp" + "\n"
    line += "  TF_ITER:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    TFBuf_loadTF_woFW(loadTFStream, TFArr[iterCount%2], tf_load_counter);" + "\n"
    line += "    TFBuf_comp(tfToBu_0, tfToBu_1, TFArr[(iterCount+1)%2], fwd_log_stageWiseTFs, inv_log_stageWiseTFs, fwd_stageWiseOffset, inv_stageWiseOffset, fwd_log_num_val_accessed_by_consec_BUs_arr, inv_log_num_val_accessed_by_consec_BUs_arr, unit_id_0, unit_id_1, dataCount, dataFlowIterLimit, direction);" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def gen_TF_buffers(designParamsVar):
    # TFBuffersParamsVar = TFBuffersParams()
    TFBuffersParamsVar = designParamsVar.TFBuffersParamsVar

    line = ""
    line += TFBUF_common_function_gen()
    line += "\n"

    cummulative_layers = 0
    for seg_id in range(designParamsVar.TF_LOAD_H_SEGS_PER_PARA_LIMB):
        layers_in_seg = TFBuffersParamsVar.layers_per_seg[seg_id]
        load_direction_of_seg = TFBuffersParamsVar.load_direction_per_seg[seg_id]
        seg_start = cummulative_layers
        seg_end = cummulative_layers + layers_in_seg

        if(load_direction_of_seg):
            for layer_id in range(seg_start, seg_end-1):
                line += TFBUF_wiFW_gen(TFBuffersParamsVar, layer_id)
                line += "\n"
            line += TFBUF_woFW_gen(TFBuffersParamsVar, seg_end-1)
            line += "\n"
        else:
            line += TFBUF_woFW_gen(TFBuffersParamsVar, seg_start)
            line += "\n"
            for layer_id in range(seg_start+1, seg_end):
                line += TFBUF_wiFW_gen(TFBuffersParamsVar, layer_id)
                line += "\n"
        cummulative_layers = cummulative_layers + layers_in_seg

    return line