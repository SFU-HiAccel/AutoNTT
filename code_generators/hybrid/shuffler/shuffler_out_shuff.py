def gen_shuffler_out_shuff_config(designParamsVar):
    idx_arr = []

    logN = designParamsVar.logN
    V_BUG_SIZE = designParamsVar.V_BUG_SIZE
    H_BUG_SIZE = designParamsVar.H_BUG_SIZE
    logV_BUG_SIZE = designParamsVar.logV_BUG_SIZE
    BUG_CONCAT_FACTOR = designParamsVar.BUG_CONCAT_FACTOR
    logBUG_CONCAT_FACTOR = designParamsVar.logBUG_CONCAT_FACTOR
    V_TOTAL_DATA = designParamsVar.V_TOTAL_DATA
    log_V_TOTAL_DATA = designParamsVar.log_V_TOTAL_DATA

    shuffleLimit = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1

    for shuffler_id in range (shuffleLimit):
        
        comp_shuffler_id = shuffler_id

        nextSupportingDistArr = []
        shifFreqForNextDistArr = []
        # precomp
        nextTotalSupportingStages =  (H_BUG_SIZE) if ( ( logN - ((comp_shuffler_id+1)*H_BUG_SIZE) ) > (H_BUG_SIZE) ) else ( ( logN - ((comp_shuffler_id+1)*H_BUG_SIZE) ) )

        for i in range(H_BUG_SIZE):
            nextSupportingDistArr.append( 1 << ( (comp_shuffler_id+1)*H_BUG_SIZE + i ) )
        
        
        for i in range(H_BUG_SIZE):
            shifFreqForNextDistArr.append(nextSupportingDistArr[i]//V_TOTAL_DATA)

        log_shift_freq = 0
        log_mini_shift_reset_freq = 0
        log_mini_shift_amount = 0

        if ( shifFreqForNextDistArr[0] == 0 ):
            log_shift_freq = 0
            log_mini_shift_reset_freq = 0
            log_mini_shift_amount = 0
        elif( nextTotalSupportingStages==H_BUG_SIZE ):
            log_shift_freq = ( (comp_shuffler_id+1)*(H_BUG_SIZE) ) - ( logV_BUG_SIZE + logBUG_CONCAT_FACTOR + 1 )
            log_mini_shift_reset_freq = 0
            log_mini_shift_amount = 0
        else:
            log_shift_freq = ( (comp_shuffler_id+1)*(H_BUG_SIZE) ) - ( logV_BUG_SIZE + logBUG_CONCAT_FACTOR + 1 )
            total_unique_sets = ( 2*V_BUG_SIZE*BUG_CONCAT_FACTOR ) // ( 1<<nextTotalSupportingStages )
            lastSupportedStageDist = 1 << (comp_shuffler_id*H_BUG_SIZE)

            if(total_unique_sets>lastSupportedStageDist):
                log_mini_shift_reset_freq = comp_shuffler_id*H_BUG_SIZE - logBUG_CONCAT_FACTOR
                log_mini_shift_amount = (logV_BUG_SIZE + 1 + logBUG_CONCAT_FACTOR) - (nextTotalSupportingStages + comp_shuffler_id*H_BUG_SIZE)
            else:
                log_mini_shift_reset_freq = (logV_BUG_SIZE+1) - nextTotalSupportingStages
                log_mini_shift_amount = 0

        shift_counts = 0

        for i in range(H_BUG_SIZE):
            if( shifFreqForNextDistArr[i]==0 ):
                shift_counts += 1

        shift_counts_mask = ( ( 1 << shift_counts ) - 1 )

        max_data_offset = (V_BUG_SIZE*2)

        shift_amount = 0

        log_blockSize = ( (comp_shuffler_id+1)*H_BUG_SIZE )
        log_blockSize_mask = ( (1 << (log_blockSize)) - 1 )
        log_totalDataPerBlock = log_blockSize + logV_BUG_SIZE + 1
        log_totalDataPerBlock_mask = (( 1<<log_totalDataPerBlock ) - 1)

        shuf_id_arr = []

        for k in range(BUG_CONCAT_FACTOR):
            for j in range(V_BUG_SIZE*2):
                read_idx = k * (V_BUG_SIZE*2) + j

                write_idx = 0
                if( shift_counts == 0 ): #all cyclic 
                    distanceBetweenVals = 1<<(H_BUG_SIZE - nextTotalSupportingStages)
                    log_distanceBetweenVals = (H_BUG_SIZE - nextTotalSupportingStages)
                    scaling_factor = (2*V_BUG_SIZE)//distanceBetweenVals
                    mini_shift_amount = 1 << log_mini_shift_amount
                    mini_scaling_factor = distanceBetweenVals//mini_shift_amount
                
                    write_idx = k * (V_BUG_SIZE*2) + \
                            + (j//distanceBetweenVals) + ( ( (j%distanceBetweenVals)//mini_shift_amount ) + ( (j%mini_shift_amount) * mini_scaling_factor ) ) * scaling_factor
                
                else: #all block and block+cyclic
                    write_idx = ( ( read_idx ) & ( ~log_totalDataPerBlock_mask ) ) + \
                            ( ( read_idx & log_totalDataPerBlock_mask ) >> log_blockSize ) + \
                            ( ( read_idx & ( ~shift_counts_mask ) ) & ( log_blockSize_mask ) ) + \
                            ( ( read_idx & shift_counts_mask ) << ( log_blockSize ) )
            
                shuf_id_arr.append(write_idx)
        idx_arr.append(shuf_id_arr)
    
    # return shuf_id_arr[0:(2*V_BUG_SIZE)]
    return idx_arr

####
# Generate shuffler_out_shift
####
def gen_shuffler_out_shuff(designParamsVar, is_inter_BUG_connections):

    logN = designParamsVar.logN
    V_BUG_SIZE = designParamsVar.V_BUG_SIZE
    H_BUG_SIZE = designParamsVar.H_BUG_SIZE
    
    # decide if the design is runing with a partial BUG.
    # In this case it has a seperate output pattern in the last round

    is_partial_BUG = False
    if((logN%H_BUG_SIZE)!=0):
        is_partial_BUG = True
        # last_round_pattern = gen_shuffler_out_shuff_config(designParamsVar)
        all_round_patterns = gen_shuffler_out_shuff_config(designParamsVar)
        last_round_pattern = all_round_patterns[-1][0:(2*V_BUG_SIZE)]
    
    #get number of inter BUG communication
    num_of_inter_BUG_comm = designParamsVar.NUM_INTER_BUG_COM
    line = ""
    line += "void shuffler_out_shuff(" + "\n"
    for comm_idx in range(num_of_inter_BUG_comm):
        for strm_idx in range(2*V_BUG_SIZE):
            line += "                  tapa::istream<WORD>& fwd_inVal_inter" + str(comm_idx) + "_" + str(strm_idx) + "," + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal_intra," + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal," + "\n"
    line += "                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal," + "\n"
    line += "                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal_intra," + "\n"
    for comm_idx in range(num_of_inter_BUG_comm):
        for strm_idx in range(2*V_BUG_SIZE):
            line += "                  tapa::ostream<WORD>& inv_outVal_inter" + str(comm_idx) + "_" + str(strm_idx) + "," + "\n"
    line += "                    bool direction," + "\n"
    line += "                   VAR_TYPE_16 iter" + "\n"
    line += "                    ){" + "\n"
    line += "  " + "\n"
    line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
    line += "  const VAR_TYPE_8 shuffleLimit = ( (VAR_TYPE_32)(logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;" + "\n"
    line += "" + "\n"
    line += "  WORD inValRegArr[V_TOTAL_DATA];" + "\n"
    line += "  WORD outValRegArr[V_TOTAL_DATA];" + "\n"
    line += "" + "\n"
    line += "  bool inpStreamNotEmpty;" + "\n"
    line += "  VAR_TYPE_8 comp_shuffler_id = 0;" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    for(VAR_TYPE_8 shuffler_id=0, inv_shuffler_id=shuffleLimit-1; shuffler_id<shuffleLimit; shuffler_id++, inv_shuffler_id--){" + "\n"
    line += "" + "\n"
    line += "      if(direction){" + "\n"
    line += "        comp_shuffler_id = shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        comp_shuffler_id = inv_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      OUT_SHUF_COMP:for(VAR_TYPE_16 i=0; i<dataCount;){" + "\n"
    line += "        #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    line += "        //read data from in stream" + "\n"
    if(num_of_inter_BUG_comm==0): # no inter BUG comm
        line += "        if( (direction) ){" + "\n"
        line += "          inpStreamNotEmpty = !fwd_inVal_intra[0].empty();" + "\n"
        line += "" + "\n"
        line += "          for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "            inpStreamNotEmpty &= !fwd_inVal_intra[j].empty();" + "\n"
        line += "          }" + "\n"
        line += "" + "\n"
        line += "          if(inpStreamNotEmpty){" + "\n"
        line += "            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "              inValRegArr[j] = fwd_inVal_intra[j].read();" + "\n"
        line += "            }" + "\n"
        line += "          }" + "\n"
        line += "        }" + "\n"
    else:
        line += "        if(direction && (comp_shuffler_id==0)){" + "\n"
        line += "          inpStreamNotEmpty = !fwd_inVal_inter0_0.empty();" + "\n"
        for idx in range(1, 2*V_BUG_SIZE):
            line += "          inpStreamNotEmpty &= !fwd_inVal_inter0_" + str(idx) + ".empty();" + "\n"
        line += "" + "\n"
        line += "          if(inpStreamNotEmpty){" + "\n"
        for idx in range(2*V_BUG_SIZE):
            line += "            inValRegArr[" + str(idx) + "] = fwd_inVal_inter0_" + str(idx) + ".read();" + "\n"
        line += "          }" + "\n"
        line += "" + "\n"
        line += "        }" + "\n"

        for comm_idx in range(1, num_of_inter_BUG_comm):
            line += "        else if(direction && (comp_shuffler_id==" + str(comm_idx) + ")){" + "\n"
            line += "          inpStreamNotEmpty = !fwd_inVal_inter" + str(comm_idx) + "_0.empty();" + "\n"
            for idx in range(1, 2*V_BUG_SIZE):
                line += "          inpStreamNotEmpty &= !fwd_inVal_inter" + str(comm_idx) + "_" + str(idx) + ".empty();" + "\n"
            line += "" + "\n"
            line += "          if(inpStreamNotEmpty){" + "\n"
            for idx in range(2*V_BUG_SIZE):
                line += "            inValRegArr[" + str(idx) + "] = fwd_inVal_inter" + str(comm_idx) + "_" + str(idx) + ".read();" + "\n"
            line += "          }" + "\n"
            line += "" + "\n"
            line += "        }" + "\n"
        line += "        else if( (direction) ){" + "\n"
        line += "          inpStreamNotEmpty = !fwd_inVal_intra[0].empty();" + "\n"
        line += "" + "\n"
        line += "          for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "            inpStreamNotEmpty &= !fwd_inVal_intra[j].empty();" + "\n"
        line += "          }" + "\n"
        line += "" + "\n"
        line += "          if(inpStreamNotEmpty){" + "\n"
        line += "            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "              inValRegArr[j] = fwd_inVal_intra[j].read();" + "\n"
        line += "            }" + "\n"
        line += "          }" + "\n"
        line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          inpStreamNotEmpty = !inv_inVal[0].empty();" + "\n"
    line += "" + "\n"
    line += "          for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "            inpStreamNotEmpty &= !inv_inVal[j].empty();" + "\n"
    line += "          }" + "\n"
    line += "" + "\n"
    line += "          if(inpStreamNotEmpty){" + "\n"
    line += "            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "              inValRegArr[j] = inv_inVal[j].read();" + "\n"
    line += "            }" + "\n"
    line += "          }" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if(inpStreamNotEmpty){" + "\n"
    line += "" + "\n"
    if(is_partial_BUG):
        line += "          //Handle partial BUG" + "\n"
        line += "          if( (direction) && (comp_shuffler_id==(shuffleLimit-1)) ){" + "\n"
        for idx in range(2*V_BUG_SIZE):
            line += "            outValRegArr[" + str(last_round_pattern[idx]) + "] = inValRegArr[" + str(idx) + "];" + "\n"
        line += "          }" + "\n"
        line += "          else if( (!direction) && (comp_shuffler_id==(shuffleLimit-1)) ){" + "\n"
        for idx in range(2*V_BUG_SIZE):
            line += "            outValRegArr[" + str(idx) + "] = inValRegArr[" + str(last_round_pattern[idx]) + "];" + "\n"
        line += "          }" + "\n"
        line += "          else{" + "\n"
        line += "            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "              outValRegArr[j] = inValRegArr[j];" + "\n"
        line += "            }" + "\n"
        line += "          }" + "\n"
    else:
        line += "        for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "          outValRegArr[j] = inValRegArr[j];" + "\n"
        line += "        }" + "\n"
    line += "" + "\n"
    line += "          //write data to out stream" + "\n"
    line += "          if(direction){" + "\n"
    line += "            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "              #pragma HLS UNROLL" + "\n"
    line += "              fwd_outVal[j].write(outValRegArr[j]);" + "\n"
    line += "            }" + "\n"
    line += "          }" + "\n"
    line += "          else{" + "\n"
    if(num_of_inter_BUG_comm==0): #No inter BUG comm
        line += "            for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "              #pragma HLS UNROLL" + "\n"
        line += "              inv_outVal_intra[j].write(outValRegArr[j]);" + "\n"
        line += "            }" + "\n"
    else:
        line += "            if(comp_shuffler_id==0){" + "\n"
        for idx in range(2*V_BUG_SIZE):
            line += "              inv_outVal_inter0_" + str(idx) + ".write(outValRegArr[" + str(idx) + "]);" + "\n"
        line += "            }" + "\n"
        for comm_idx in range(1, num_of_inter_BUG_comm):
            line += "            else if(comp_shuffler_id==" + str(comm_idx) + "){" + "\n"
            for idx in range(2*V_BUG_SIZE):
                line += "              inv_outVal_inter" + str(comm_idx) + "_" + str(idx) + ".write(outValRegArr[" + str(idx) + "]);" + "\n"
            line += "            }" + "\n"
        line += "            else{" + "\n"
        line += "              for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
        line += "                #pragma HLS UNROLL" + "\n"
        line += "                inv_outVal_intra[j].write(outValRegArr[j]);" + "\n"
        line += "              }" + "\n"
        line += "            }" + "\n"
    line += "          }" + "\n"
    line += "          i++;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line