from code_generators.common.helper_functions import num_arr_to_cppArrStr

def gen_shuffler_out_shift_config(designParamsVar):

    logN = designParamsVar.logN
    V_BUG_SIZE = designParamsVar.V_BUG_SIZE
    H_BUG_SIZE = designParamsVar.H_BUG_SIZE
    logV_BUG_SIZE = designParamsVar.logV_BUG_SIZE
    BUG_CONCAT_FACTOR = designParamsVar.BUG_CONCAT_FACTOR
    logBUG_CONCAT_FACTOR = designParamsVar.logBUG_CONCAT_FACTOR
    V_TOTAL_DATA = designParamsVar.V_TOTAL_DATA
    log_V_TOTAL_DATA = designParamsVar.log_V_TOTAL_DATA

    shuffleLimit = ( (logN+(H_BUG_SIZE-1))//H_BUG_SIZE ) - 1

    log_shift_freq_table = []
    log_mini_shift_reset_freq_table = []
    log_mini_shift_amount_table = []
    shift_counts_table = []

    # for(VAR_TYPE_32 shuffler_id=0; shuffler_id<shuffleLimit; shuffler_id++){
    for shuffler_id in range(shuffleLimit):

        nextTotalSupportingStages = ( logN - (shuffler_id+1)*H_BUG_SIZE ) if ( (shuffler_id+2)*H_BUG_SIZE > logN ) else ( H_BUG_SIZE )

        nextSupportingDistArr = []
        for i in range(H_BUG_SIZE):
            nextSupportingDistArr.append(1 << ( (shuffler_id+1)*H_BUG_SIZE + i ))
        

        shifFreqForNextDistArr = []
        for i in range(H_BUG_SIZE):
            shifFreqForNextDistArr.append(nextSupportingDistArr[i]//V_TOTAL_DATA)
        

        log_shift_freq = 0
        log_mini_shift_reset_freq = 0
        log_mini_shift_amount = 0

        if ( shifFreqForNextDistArr[0] == 0 ): #no shift at all and these all must be 0
            log_shift_freq = 0
            log_mini_shift_reset_freq = 0
            log_mini_shift_amount = 0
        
        elif(nextTotalSupportingStages==H_BUG_SIZE):
            log_shift_freq = ( (shuffler_id+1)*(H_BUG_SIZE) ) - ( logV_BUG_SIZE + logBUG_CONCAT_FACTOR + 1 )
            log_mini_shift_reset_freq = 0
            log_mini_shift_amount = 0
        
        else:
            log_shift_freq = ( (shuffler_id+1)*(H_BUG_SIZE) ) - ( logV_BUG_SIZE + logBUG_CONCAT_FACTOR + 1 )
            total_unique_sets = ( 2*V_BUG_SIZE*BUG_CONCAT_FACTOR ) // ( 1<<nextTotalSupportingStages )
            lastSupportedStageDist = 1 << shuffler_id*H_BUG_SIZE

            if(total_unique_sets>lastSupportedStageDist):
                log_mini_shift_reset_freq = shuffler_id*H_BUG_SIZE - logBUG_CONCAT_FACTOR
                log_mini_shift_amount = (logV_BUG_SIZE + 1 + logBUG_CONCAT_FACTOR) - (nextTotalSupportingStages + shuffler_id*H_BUG_SIZE)
            
            else:
                log_mini_shift_reset_freq = (logV_BUG_SIZE+1) - nextTotalSupportingStages
                log_mini_shift_amount = 0

        
        shift_counts = 0
        
        for i in range(H_BUG_SIZE):
            if( shifFreqForNextDistArr[i]==0 ):
                shift_counts +=1

        log_shift_freq_table.append(log_shift_freq)
        log_mini_shift_reset_freq_table.append(log_mini_shift_reset_freq)
        log_mini_shift_amount_table.append(log_mini_shift_amount)
        shift_counts_table.append(shift_counts)

    # print("log_shift_freq_table: " + str(log_shift_freq_table))
    # print("log_mini_shift_reset_freq_table: " + str(log_mini_shift_reset_freq_table))
    # print("log_mini_shift_amount_table: " + str(log_mini_shift_amount_table))
    # print("shift_counts_table: " + str(shift_counts_table))

    #Convert all the arrays to strings
    # log_shift_freq_table_str = [str(x) for x in log_shift_freq_table]
    # log_mini_shift_reset_freq_table_str = [str(x) for x in log_mini_shift_reset_freq_table]
    # log_mini_shift_amount_table_str = [str(x) for x in log_mini_shift_amount_table]
    # shift_counts_table_str = [str(x) for x in shift_counts_table]

    # log_shift_freq_table_output_str = "{" + ",".join(log_shift_freq_table_str) + "}"
    # log_mini_shift_reset_freq_table_output_str = "{" + ",".join(log_mini_shift_reset_freq_table_str) + "}"
    # log_mini_shift_amount_table_output_str = "{" + ",".join(log_mini_shift_amount_table_str) + "}"
    # shift_counts_table_output_str = "{" + ",".join(shift_counts_table_str) + "}"

    log_shift_freq_table_output_str = num_arr_to_cppArrStr(log_shift_freq_table)
    log_mini_shift_reset_freq_table_output_str = num_arr_to_cppArrStr(log_mini_shift_reset_freq_table)
    log_mini_shift_amount_table_output_str = num_arr_to_cppArrStr(log_mini_shift_amount_table)
    shift_counts_table_output_str = num_arr_to_cppArrStr(shift_counts_table)

    return log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, shift_counts_table_output_str


####
# In the case of single BUG designs/very small designs, we don't have inter BUG communication
####
def gen_shuffler_out_shift_wo_inter_BUG_com(designParamsVar):

    #generate suffler_out_shift configs
    log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, shift_counts_table_output_str = gen_shuffler_out_shift_config(designParamsVar)

    line = ""
    line += "void shuffler_out_shift(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal," + "\n"
    line += "                        tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal," + "\n"
    line += "                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal," + "\n"
    line += "                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal," + "\n"
    line += "                        bool direction," + "\n"
    line += "                        VAR_TYPE_16 iter," + "\n"
    line += "                        VAR_TYPE_8 task_id){" + "\n"
    line += "  " + "\n"
    line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
    line += "  const VAR_TYPE_8 shuffleLimit = (VAR_TYPE_32)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;" + "\n"
    line += "  VAR_TYPE_8 max_data_offset = (V_BUG_SIZE*2);" + "\n"
    line += "" + "\n"
    line += "  WORD inValRegArr[2*V_BUG_SIZE];" + "\n"
    line += "  WORD outValRegArr[2*V_BUG_SIZE];" + "\n"
    line += "" + "\n"
    line += "  //==== Auto generated variables start ====//" + "\n"
    line += "  VAR_TYPE_8 log_shift_freq_table[shuffleLimit] = " + log_shift_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_8 log_mini_shift_reset_freq_table[shuffleLimit] = " + log_mini_shift_reset_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_8 log_mini_shift_amount_table[shuffleLimit] = " + log_mini_shift_amount_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_8 shift_counts_table[shuffleLimit] = " + shift_counts_table_output_str + ";" + "\n"
    line += "  //==== Auto generated variables end ====//" + "\n"
    line += "" + "\n"
    line += "  bool inpStreamNotEmpty;" + "\n"
    line += "  VAR_TYPE_8 comp_shuffler_id;" + "\n"
    line += "  VAR_TYPE_8 shift_amount = 0;" + "\n"
    line += "  VAR_TYPE_8 adjusted_shift_amount = 0;" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    for(VAR_TYPE_8 shuffler_id=0, inv_shuffler_id=shuffleLimit-1; shuffler_id<shuffleLimit; shuffler_id++, inv_shuffler_id--){" + "\n"
    line += "      OUT_SHUF_COMP:for(VAR_TYPE_16 i=0; i<dataCount;){" + "\n"
    line += "        #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    line += "        if(direction){" + "\n"
    line += "          comp_shuffler_id = shuffler_id;" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          comp_shuffler_id = inv_shuffler_id;" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        VAR_TYPE_16 log_shift_freq = log_shift_freq_table[comp_shuffler_id];" + "\n"
    line += "        VAR_TYPE_16 log_mini_shift_reset_freq = log_mini_shift_reset_freq_table[comp_shuffler_id];" + "\n"
    line += "        VAR_TYPE_16 log_mini_shift_amount = log_mini_shift_amount_table[comp_shuffler_id];" + "\n"
    line += "        VAR_TYPE_16 shift_counts = shift_counts_table[comp_shuffler_id];" + "\n"
    line += "" + "\n"
    line += "        //read data from in stream" + "\n"
    line += "        inpStreamNotEmpty = ( !fwd_inVal[0].empty() ) || ( !inv_inVal[0].empty() );" + "\n"
    line += "        for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "          inpStreamNotEmpty &= ( !fwd_inVal[j].empty() ) || ( !inv_inVal[j].empty() );" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if(inpStreamNotEmpty){" + "\n"
    line += "" + "\n"
    line += "          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "            #pragma HLS UNROLL" + "\n"
    line += "            if(direction){" + "\n"
    line += "              inValRegArr[j] = fwd_inVal[j].read();" + "\n"
    line += "            }" + "\n"
    line += "            else{" + "\n"
    line += "              inValRegArr[j] = inv_inVal[j].read();" + "\n"
    line += "            }" + "\n"
    line += "          }" + "\n"
    line += "" + "\n"
    line += "          //shuffle" + "\n"
    line += "          shift_amount = ( ( i & ( (1<<(log_shift_freq-log_mini_shift_reset_freq)) - 1 ) ) == 0) ? ( ( max_data_offset - (((i >> (log_shift_freq-log_mini_shift_reset_freq)) << (shift_counts + log_mini_shift_amount)) % (max_data_offset)) ) % (max_data_offset) ) : (shift_amount);" + "\n"
    line += "" + "\n"
    line += "          if(direction){" + "\n"
    line += "            adjusted_shift_amount = shift_amount;" + "\n"
    line += "          }" + "\n"
    line += "          else{" + "\n"
    line += "            adjusted_shift_amount = ( max_data_offset - shift_amount ) % max_data_offset;" + "\n"
    line += "          }" + "\n"
    line += "" + "\n"
    line += "          for(VAR_TYPE_16 j=0; j<V_BUG_SIZE*2; j++){" + "\n"
    line += "            #pragma HLS UNROLL" + "\n"
    line += "            outValRegArr[(j+adjusted_shift_amount)%max_data_offset] = inValRegArr[j];" + "\n"
    line += "          }" + "\n"
    line += "" + "\n"
    line += "          //write data to out stream" + "\n"
    line += "          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "            #pragma HLS UNROLL" + "\n"
    line += "            if(direction){" + "\n"
    line += "              fwd_outVal[j].write(outValRegArr[j]);" + "\n"
    line += "            }" + "\n"
    line += "            else{" + "\n"
    line += "              inv_outVal[j].write(outValRegArr[j]);" + "\n"
    line += "            }" + "\n"
    line += "          }" + "\n"
    line += "          i++;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def gen_shuffler_out_shift_wi_inter_BUG_com(designParamsVar):
    
    #generate suffler_out_shift configs
    log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, shift_counts_table_output_str = gen_shuffler_out_shift_config(designParamsVar)

    #get number of inter BUG communication
    num_of_inter_BUG_comm = designParamsVar.NUM_INTER_BUG_COM

    line = ""
    line += "void shuffler_out_shift(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal," + "\n"
    for comm_idx in range(num_of_inter_BUG_comm):
        line += "                        tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal_inter_" + str(comm_idx) + "," + "\n"
    line += "                        tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal_intra," + "\n"
    for comm_idx in range(num_of_inter_BUG_comm):
        line += "                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal_inter_" + str(comm_idx) + "," + "\n"
    line += "                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal_intra," + "\n"
    line += "                        tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal," + "\n"
    line += "                        bool direction," + "\n"
    line += "                        VAR_TYPE_16 iter," + "\n"
    line += "                        VAR_TYPE_16 task_id){" + "\n"
    line += "  " + "\n"
    line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
    line += "  const VAR_TYPE_8 shuffleLimit = (VAR_TYPE_8)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;" + "\n"
    line += "  VAR_TYPE_8 max_data_offset = (V_BUG_SIZE*2);" + "\n"
    line += "" + "\n"
    line += "  WORD inValRegArr[2*V_BUG_SIZE];" + "\n"
    line += "  WORD outValRegArr[2*V_BUG_SIZE];" + "\n"
    line += "" + "\n"
    line += "  //==== Auto generated variables start ====//" + "\n"
    line += "  VAR_TYPE_8 log_shift_freq_table[shuffleLimit] = " + log_shift_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_8 log_mini_shift_reset_freq_table[shuffleLimit] = " + log_mini_shift_reset_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_8 log_mini_shift_amount_table[shuffleLimit] = " + log_mini_shift_amount_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_8 shift_counts_table[shuffleLimit] = " + shift_counts_table_output_str + ";" + "\n"
    line += "  //==== Auto generated variables end ====//" + "\n"
    line += "" + "\n"
    line += "  bool inpStreamNotEmpty;" + "\n"
    line += "  VAR_TYPE_8 comp_shuffler_id;" + "\n"
    line += "  VAR_TYPE_8 shift_amount = 0;" + "\n"
    line += "  VAR_TYPE_8 adjusted_shift_amount = 0;" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    for(VAR_TYPE_8 shuffler_id=0, inv_shuffler_id=shuffleLimit-1; shuffler_id<shuffleLimit; shuffler_id++, inv_shuffler_id--){" + "\n"
    line += "      OUT_SHUF_COMP:for(VAR_TYPE_16 i=0; i<dataCount;){" + "\n"
    line += "        #pragma HLS PIPELINE II = 1" + "\n"
    line += "" + "\n"
    line += "        if(direction){" + "\n"
    line += "          comp_shuffler_id = shuffler_id;" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          comp_shuffler_id = inv_shuffler_id;" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        VAR_TYPE_8 log_shift_freq = log_shift_freq_table[comp_shuffler_id];" + "\n"
    line += "        VAR_TYPE_8 log_mini_shift_reset_freq = log_mini_shift_reset_freq_table[comp_shuffler_id];" + "\n"
    line += "        VAR_TYPE_8 log_mini_shift_amount = log_mini_shift_amount_table[comp_shuffler_id];" + "\n"
    line += "        VAR_TYPE_8 shift_counts = shift_counts_table[comp_shuffler_id];" + "\n"
    line += "" + "\n"
    line += "        //read data from in stream" + "\n"
    line += "        inpStreamNotEmpty = ( !fwd_inVal[0].empty() ) "
    
    for comm_idx in range(num_of_inter_BUG_comm):
        line += "|| ( !inv_inVal_inter_" + str(comm_idx) + "[0].empty() ) " 

    line += "|| ( !inv_inVal_intra[0].empty() );" + "\n"
    line += "        for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "          inpStreamNotEmpty &= ( !fwd_inVal[j].empty() ) " 
    for comm_idx in range(num_of_inter_BUG_comm):
        line += "|| ( !inv_inVal_inter_" + str(comm_idx) + "[j].empty() ) " 
    line += "|| ( !inv_inVal_intra[j].empty() );" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if(inpStreamNotEmpty){" + "\n"
    line += "" + "\n"
    line += "          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "            #pragma HLS UNROLL" + "\n"
    line += "            if(direction){" + "\n"
    line += "              inValRegArr[j] = fwd_inVal[j].read();" + "\n"
    line += "            }" + "\n"
    line += "            else{" + "\n"
    if(num_of_inter_BUG_comm==0):
        line += "              inValRegArr[j] = inv_inVal_intra[j].read();" + "\n"
    else:
        line += "              if(comp_shuffler_id==0){" + "\n"
        line += "                inValRegArr[j] = inv_inVal_inter_0[j].read();" + "\n"
        line += "              }" + "\n"

        for comm_idx in range(1, num_of_inter_BUG_comm):
            line += "              else if(comp_shuffler_id==" + str(comm_idx) + "){" + "\n"
            line += "                inValRegArr[j] = inv_inVal_inter_" + str(comm_idx) + "[j].read();" + "\n"
            line += "              }" + "\n"
        
        line += "              else{" + "\n"
        line += "                inValRegArr[j] = inv_inVal_intra[j].read();" + "\n"
        line += "              }" + "\n"
    line += "            }" + "\n"
    line += "          }" + "\n"
    line += "" + "\n"
    line += "          //shuffle amount gen" + "\n"
    line += "          shift_amount = ( ( i & ( (1<<(log_shift_freq-log_mini_shift_reset_freq)) - 1 ) ) == 0) ? ( ( max_data_offset - (((i >> (log_shift_freq-log_mini_shift_reset_freq)) << (shift_counts + log_mini_shift_amount)) % (max_data_offset)) ) % (max_data_offset) ) : (shift_amount);" + "\n"
    line += "" + "\n"
    line += "          if(direction){" + "\n"
    line += "            adjusted_shift_amount = shift_amount;" + "\n"
    line += "          }" + "\n"
    line += "          else{" + "\n"
    line += "            adjusted_shift_amount = ( max_data_offset - shift_amount ) % max_data_offset;" + "\n"
    line += "          }" + "\n"
    line += "" + "\n"
    line += "          //shuffle" + "\n"
    line += "          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "            #pragma HLS UNROLL" + "\n"
    line += "            outValRegArr[(j+adjusted_shift_amount)%max_data_offset] = inValRegArr[j];" + "\n"
    line += "          }" + "\n"
    line += "" + "\n"
    line += "          //write data to out stream" + "\n"
    line += "          for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "            #pragma HLS UNROLL" + "\n"
    line += "            if(direction){" + "\n"
    if(num_of_inter_BUG_comm==0):
        line += "              fwd_outVal_intra[j].write(outValRegArr[j]);" + "\n"
    else:
        line += "              if(comp_shuffler_id==0){" + "\n"
        line += "                fwd_outVal_inter_0[j].write(outValRegArr[j]);" + "\n"
        line += "              }" + "\n"
        for comm_idx in range(1, num_of_inter_BUG_comm):
            line += "              else if(comp_shuffler_id==" + str(comm_idx) + "){" + "\n"
            line += "                fwd_outVal_inter_" + str(comm_idx) + "[j].write(outValRegArr[j]);" + "\n"
            line += "              }" + "\n"
        line += "              else{" + "\n"
        line += "                fwd_outVal_intra[j].write(outValRegArr[j]);" + "\n"
        line += "              }" + "\n"
    line += "            }" + "\n"
    line += "            else{" + "\n"
    line += "              inv_outVal[j].write(outValRegArr[j]);" + "\n"
    line += "            }" + "\n"
    line += "          }" + "\n"
    line += "          i++;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

####
# Generate shuffler_out_shift
####
def gen_shuffler_out_shift(designParamsVar, is_inter_BUG_connections):
    line = ""
    if(is_inter_BUG_connections):
        line = gen_shuffler_out_shift_wi_inter_BUG_com(designParamsVar)
    else:
        line = gen_shuffler_out_shift_wo_inter_BUG_com(designParamsVar)
    return line