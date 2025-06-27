from code_generators.common.helper_functions import num_arr_to_cppArrStr

def gen_shuffler_in_config(designParamsVar):

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
    log_shift_jump_table = []
    log_mini_shift_amount_table = []

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

        log_shift_jump = shift_counts + log_mini_shift_reset_freq + log_mini_shift_amount

        log_shift_freq_table.append(log_shift_freq)
        log_mini_shift_reset_freq_table.append(log_mini_shift_reset_freq)
        log_mini_shift_amount_table.append(log_mini_shift_amount)
        log_shift_jump_table.append(log_shift_jump)

    #Convert all the arrays to strings
    log_shift_freq_table_output_str = num_arr_to_cppArrStr(log_shift_freq_table)
    log_mini_shift_reset_freq_table_output_str = num_arr_to_cppArrStr(log_mini_shift_reset_freq_table)
    log_mini_shift_amount_table_output_str = num_arr_to_cppArrStr(log_mini_shift_amount_table)
    log_shift_jump_table_output_str = num_arr_to_cppArrStr(log_shift_jump_table)

    return log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, log_shift_jump_table_output_str

    # print("log_shift_freq_table: " + str(log_shift_freq_table))
    # print("log_mini_shift_reset_freq_table: " + str(log_mini_shift_reset_freq_table))
    # print("mini_shift_amount_table: " + str(log_mini_shift_amount_table))
    # print("shift_jump_table: " + str(log_shift_jump_table))

####
# Generate shuffler shuffler_in
####
def gen_shuffler_in(designParamsVar):

  #generate shuffler in configurations
  log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, log_shift_jump_table_output_str = gen_shuffler_in_config(designParamsVar)

  line = ""
  line += "void shuffler_in(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal," + "\n"
  line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal," + "\n"
  line += "                   tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal," + "\n"
  line += "                   tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal," + "\n"
  line += "                   bool direction," + "\n"
  line += "                   VAR_TYPE_16 iter," + "\n"
  line += "                   VAR_TYPE_16 task_idx" + "\n"
  line += "                    ){" + "\n"
  line += "  " + "\n"
  line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
  line += "  const VAR_TYPE_8 shuffleLimit = ( (VAR_TYPE_32)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) ) - 1;" + "\n"
  line += "  VAR_TYPE_8 max_data_offset = (V_BUG_SIZE*2);" + "\n"
  line += "" + "\n"
  line += "  VAR_TYPE_8 mini_shift = 0;" + "\n"
  line += "  VAR_TYPE_8 major_shift = 0;" + "\n"
  line += "  VAR_TYPE_8 shift_amount = 0;" + "\n"
  line += "" + "\n"
  line += "  WORD inValRegArr[2*V_BUG_SIZE];" + "\n"
  line += "  WORD outValRegArr[2*V_BUG_SIZE];" + "\n"
  line += "" + "\n"
  line += "  //==== Auto generated variables start ====//" + "\n"
  line += "  VAR_TYPE_8 log_shift_freq_table[shuffleLimit] = " + log_shift_freq_table_output_str + ";" + "\n"
  line += "  VAR_TYPE_8 log_mini_shift_reset_freq_table[shuffleLimit] = " + log_mini_shift_reset_freq_table_output_str + ";" + "\n"
  line += "  VAR_TYPE_8 log_mini_shift_amount_table[shuffleLimit] = " + log_mini_shift_amount_table_output_str + ";" + "\n"
  line += "  VAR_TYPE_8 log_shift_jump_table[shuffleLimit] = " + log_shift_jump_table_output_str + ";" + "\n"
  line += "  //==== Auto generated variables end ====//" + "\n"
  line += "" + "\n"
  line += "  bool inpStreamNotEmpty;" + "\n"
  line += "  VAR_TYPE_8 comp_shuffler_id;" + "\n"
  line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
  line += "    for(VAR_TYPE_8 shuffler_id=0, inv_shuffler_id=shuffleLimit-1; shuffler_id<shuffleLimit; shuffler_id++, inv_shuffler_id--){" + "\n"
  line += "      IN_SHUF_COMP:for(VAR_TYPE_16 i=0; i<dataCount;){" + "\n"
  line += "        #pragma HLS PIPELINE II = 1" + "\n"
  line += "" + "\n"
  line += "        if(direction){" + "\n"
  line += "          comp_shuffler_id = shuffler_id;" + "\n"
  line += "        }" + "\n"
  line += "        else{" + "\n"
  line += "          comp_shuffler_id = shuffleLimit - shuffler_id - 1;" + "\n"
  line += "        }" + "\n"
  line += "" + "\n"
  line += "        VAR_TYPE_8 log_shift_freq = log_shift_freq_table[comp_shuffler_id];" + "\n"
  line += "        VAR_TYPE_8 log_mini_shift_reset_freq = log_mini_shift_reset_freq_table[comp_shuffler_id];" + "\n"
  line += "        VAR_TYPE_8 log_shift_jump = log_shift_jump_table[comp_shuffler_id];" + "\n"
  line += "        VAR_TYPE_8 log_mini_shift_amount = log_mini_shift_amount_table[comp_shuffler_id];" + "\n"
  line += "" + "\n"
  line += "        inpStreamNotEmpty = ( !fwd_inVal[0].empty() ) || ( !inv_inVal[0].empty() ) ;" + "\n"
  line += "        " + "\n"
  line += "        //Read data from input stream" + "\n"
  line += "        for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){" + "\n"
  line += "          #pragma HLS UNROLL" + "\n"
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
  line += "          //shift amount calculate" + "\n"
  line += "          major_shift = ( ( i & ( (1<<log_shift_freq) - 1 ) ) == 0) ? (((i >> log_shift_freq) << log_shift_jump) % (max_data_offset)) : (major_shift);" + "\n"
  line += "          mini_shift = ( ( i & ( (1<<log_mini_shift_reset_freq) - 1 ) ) == 0 ) ? (0) : ( ( i & ( (1<<log_mini_shift_reset_freq) - 1 ) ) << log_mini_shift_amount );" + "\n"
  line += "          if(direction){" + "\n"
  line += "            shift_amount = major_shift + mini_shift;" + "\n"
  line += "          }" + "\n"
  line += "          else{" + "\n"
  line += "            shift_amount = (max_data_offset - (major_shift + mini_shift))%max_data_offset;" + "\n"
  line += "          }" + "\n"
  line += "" + "\n"
  line += "          //shift" + "\n"
  line += "          for(VAR_TYPE_16 j=0; j<V_BUG_SIZE*2; j++){" + "\n"
  line += "            #pragma HLS UNROLL" + "\n"
  line += "            outValRegArr[(j+shift_amount)%max_data_offset] = inValRegArr[j];" + "\n"
  line += "          }" + "\n"
  line += "" + "\n"
  line += "          //write data to out stream" + "\n"
  line += "          for(VAR_TYPE_16 j=0; j<V_BUG_SIZE*2; j++){" + "\n"
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