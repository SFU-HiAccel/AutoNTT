from code_generators.common.helper_functions import num_arr_to_cppArrStr

def gen_shuffler_buf_config(designParamsVar):

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
    log_max_buf_offset_table = []
    shift_counts_table = []
    poly_group_line_offset_num_line_table = []
    log_poly_group_total_num_line_table = []
    log_out_data_cycles_per_bufGrp_table = []
    total_lines_in_group_mask_table = []

    max_data_offset = (V_BUG_SIZE*2)

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
            
        
        
        log_shift_freq_mask = ( (1<<log_shift_freq) - 1 )
        log_mini_shift_reset_freq_mask = ( (1<<log_mini_shift_reset_freq) - 1 )


        log_max_buf_offset = 0
        if( shifFreqForNextDistArr[H_BUG_SIZE - 1] == 0 ): #no shift
            log_max_buf_offset = 0
        
        else:
            log_max_buf_offset = logV_BUG_SIZE+1
        

        shift_counts = 0
        for i in range(H_BUG_SIZE):
            if( shifFreqForNextDistArr[i]==0 ):
                shift_counts+=1
            
        

        total_lines_in_group = ( (2*V_BUG_SIZE) >> (log_mini_shift_reset_freq + log_mini_shift_amount)) * ( 1<<log_shift_freq )
        log_total_lines_in_group =   ( (logV_BUG_SIZE+1 + log_shift_freq) - ( log_mini_shift_reset_freq + log_mini_shift_amount ) ) if ( (logV_BUG_SIZE+1) > ( log_mini_shift_reset_freq + log_mini_shift_amount ) ) else (0) # I think may be we can remove this if condition and directly keep the equation
        total_lines_in_group_mask = ( ( 1 << log_total_lines_in_group ) - 1 )

        log_shift_freq_table.append(log_shift_freq)
        log_mini_shift_reset_freq_table.append(log_mini_shift_reset_freq)
        log_mini_shift_amount_table.append(log_mini_shift_amount)
        log_max_buf_offset_table.append(log_max_buf_offset)
        shift_counts_table.append(shift_counts)
        poly_group_line_offset_num_line_table.append(max_data_offset)
        log_poly_group_total_num_line_table.append(log_shift_freq + (logV_BUG_SIZE+1) - log_mini_shift_reset_freq - shift_counts - log_mini_shift_amount)
        log_out_data_cycles_per_bufGrp_table.append((logV_BUG_SIZE + 1 ) + log_shift_freq - log_mini_shift_reset_freq - shift_counts)
        total_lines_in_group_mask_table.append(total_lines_in_group_mask)
        
        
    # print("log_shift_freq_table: " + str(log_shift_freq_table))
    # print("log_mini_shift_reset_freq_table: " + str(log_mini_shift_reset_freq_table))
    # print("log_mini_shift_amount_table: " + str(log_mini_shift_amount_table))
    # print("log_max_buf_offset_table: " + str(log_max_buf_offset_table))
    # print("shift_counts_table: " + str(shift_counts_table))
    # print("poly_group_line_offset_num_line_table: " + str(poly_group_line_offset_num_line_table))
    # print("log_poly_group_total_num_line_table" + str(log_poly_group_total_num_line_table))
    # print("log_out_data_cycles_per_bufGrp_table" + str(log_out_data_cycles_per_bufGrp_table))
    # print("total_lines_in_group_mask_table" + str(total_lines_in_group_mask_table))

    #Convert all the arrays to strings
    # log_shift_freq_table_str = [str(x) for x in log_shift_freq_table]
    # log_mini_shift_reset_freq_table_str = [str(x) for x in log_mini_shift_reset_freq_table]
    # log_mini_shift_amount_table_str = [str(x) for x in log_mini_shift_amount_table]
    # log_max_buf_offset_table_str = [str(x) for x in log_max_buf_offset_table]
    # shift_counts_table_str = [str(x) for x in shift_counts_table]
    # poly_group_line_offset_num_line_table_str = [str(x) for x in poly_group_line_offset_num_line_table]
    # log_poly_group_total_num_line_table_str = [str(x) for x in log_poly_group_total_num_line_table]
    # log_out_data_cycles_per_bufGrp_table_str = [str(x) for x in log_out_data_cycles_per_bufGrp_table]
    # total_lines_in_group_mask_table_str = [str(x) for x in total_lines_in_group_mask_table]

    # log_shift_freq_table_output_str = "{" + ",".join(log_shift_freq_table_str) + "}"
    # log_mini_shift_reset_freq_table_output_str = "{" + ",".join(log_mini_shift_reset_freq_table_str) + "}"
    # log_mini_shift_amount_table_output_str = "{" + ",".join(log_mini_shift_amount_table_str) + "}"
    # log_max_buf_offset_table_output_str = "{" + ",".join(log_max_buf_offset_table_str) + "}"
    # shift_counts_table_output_str = "{" + ",".join(shift_counts_table_str) + "}"
    # poly_group_line_offset_num_line_table_output_str = "{" + ",".join(poly_group_line_offset_num_line_table_str) + "}"
    # log_poly_group_total_num_line_table_output_str = "{" + ",".join(log_poly_group_total_num_line_table_str) + "}"
    # log_out_data_cycles_per_bufGrp_table_output_str = "{" + ",".join(log_out_data_cycles_per_bufGrp_table_str) + "}"
    # total_lines_in_group_mask_table_output_str = "{" + ",".join(total_lines_in_group_mask_table_str) + "}"

    log_shift_freq_table_output_str = num_arr_to_cppArrStr(log_shift_freq_table)
    log_mini_shift_reset_freq_table_output_str = num_arr_to_cppArrStr(log_mini_shift_reset_freq_table)
    log_mini_shift_amount_table_output_str = num_arr_to_cppArrStr(log_mini_shift_amount_table)
    log_max_buf_offset_table_output_str = num_arr_to_cppArrStr(log_max_buf_offset_table)
    shift_counts_table_output_str = num_arr_to_cppArrStr(shift_counts_table)
    poly_group_line_offset_num_line_table_output_str = num_arr_to_cppArrStr(poly_group_line_offset_num_line_table)
    log_poly_group_total_num_line_table_output_str = num_arr_to_cppArrStr(log_poly_group_total_num_line_table)
    log_out_data_cycles_per_bufGrp_table_output_str = num_arr_to_cppArrStr(log_out_data_cycles_per_bufGrp_table)
    total_lines_in_group_mask_table_output_str = num_arr_to_cppArrStr(total_lines_in_group_mask_table)

    return log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, log_max_buf_offset_table_output_str, shift_counts_table_output_str, poly_group_line_offset_num_line_table_output_str, log_poly_group_total_num_line_table_output_str, log_out_data_cycles_per_bufGrp_table_output_str, total_lines_in_group_mask_table_output_str

def gen_split_shuffler_buf(designParamsVar):

    log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, log_max_buf_offset_table_output_str, shift_counts_table_output_str, poly_group_line_offset_num_line_table_output_str, log_poly_group_total_num_line_table_output_str, log_out_data_cycles_per_bufGrp_table_output_str, total_lines_in_group_mask_table_output_str = gen_shuffler_buf_config(designParamsVar)

    line = ""
    line += "void shuffler_single_buf(" + "\n"
    line += "                   tapa::istream<WORD>& fwd_inVal," + "\n"
    line += "                   tapa::istream<WORD>& inv_inVal," + "\n"
    line += "                   tapa::ostream<WORD>& fwd_outVal," + "\n"
    line += "                   tapa::ostream<WORD>& inv_outVal," + "\n"
    line += "                   bool direction," + "\n"
    line += "                   VAR_TYPE_16 BUG_id," + "\n"
    line += "                   VAR_TYPE_16 local_buf_id," + "\n"
    line += "                   VAR_TYPE_16 iter){" + "\n"
    line += "  " + "\n"
    line += "  WORD poly_buf[2*SINGLE_LIMB_BUF_SIZE];" + "\n"
    line += "  #pragma HLS bind_storage variable=poly_buf type=RAM_S2P impl=BRAM" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_8 buf_id = BUG_id*2*V_BUG_SIZE + local_buf_id;" + "\n"
    line += "" + "\n"
    line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
    line += "  const VAR_TYPE_8 shuffleLimit = (VAR_TYPE_32)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_8 max_data_offset = (V_BUG_SIZE*2);" + "\n"
    line += "  VAR_TYPE_16 receiveCount[2];" + "\n"
    line += "  VAR_TYPE_16 sendCount[2];" + "\n"
    line += "" + "\n"
    line += "  //==== Auto generated variables start ====//" + "\n"
    line += "  VAR_TYPE_16 log_shift_freq_table[shuffleLimit] = " + log_shift_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_mini_shift_reset_freq_table[shuffleLimit] = " + log_mini_shift_reset_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_mini_shift_amount_table[shuffleLimit] = " + log_mini_shift_amount_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_max_buf_offset_table[shuffleLimit] = " + log_max_buf_offset_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 shift_counts_table[shuffleLimit] = " + shift_counts_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 poly_group_line_offset_num_line_table[shuffleLimit] = " + poly_group_line_offset_num_line_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_poly_group_total_num_line_table[shuffleLimit] = " + log_poly_group_total_num_line_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_out_data_cycles_per_bufGrp_table[shuffleLimit] = " + log_out_data_cycles_per_bufGrp_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 total_lines_in_group_mask_table[shuffleLimit] = " + total_lines_in_group_mask_table_output_str + ";" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS array_partition variable=log_shift_freq_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_mini_shift_reset_freq_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_mini_shift_amount_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_max_buf_offset_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=shift_counts_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=poly_group_line_offset_num_line_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_poly_group_total_num_line_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_out_data_cycles_per_bufGrp_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=total_lines_in_group_mask_table type=complete dim=0" + "\n"
    line += "  //==== Auto generated variables end ====//" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    " + "\n"
    line += "    for(VAR_TYPE_16 i=0; i<2; i++){" + "\n"
    line += "      #pragma HLS UNROLL" + "\n"
    line += "      receiveCount[i] = 0;" + "\n"
    line += "      sendCount[i] = 0;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    VAR_TYPE_16 non_seq_idx;" + "\n"
    line += "    WORD read_val;" + "\n"
    line += "    bool val_valid = false;" + "\n"
    line += "    VAR_TYPE_16 seq_idx;" + "\n"
    line += "" + "\n"
    line += "    VAR_TYPE_16 write_shuffler_id = 0;" + "\n"
    line += "    VAR_TYPE_16 read_shuffler_id = 0;" + "\n"
    line += "    VAR_TYPE_16 comp_write_shuffler_id = 0;" + "\n"
    line += "    VAR_TYPE_16 comp_read_shuffler_id = 0;" + "\n"
    line += "" + "\n"
    line += "    VAR_TYPE_16 shuffleCount = 0;" + "\n"
    line += "" + "\n"
    line += "    BUF_COMP:for(; shuffleCount<shuffleLimit ;){" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      if(direction){" + "\n"
    line += "        comp_read_shuffler_id = read_shuffler_id;" + "\n"
    line += "        comp_write_shuffler_id = write_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        comp_read_shuffler_id = (read_shuffler_id < shuffleLimit) ? (shuffleLimit - read_shuffler_id - 1) : (0);" + "\n"
    line += "        comp_write_shuffler_id = (write_shuffler_id < shuffleLimit) ? (shuffleLimit - write_shuffler_id - 1) : (0);" + "\n"
    line += "      }" + "\n"
    line += "      VAR_TYPE_16 poly_group_line_offset_num_line;" + "\n"
    line += "      VAR_TYPE_16 log_poly_group_total_num_line;" + "\n"
    line += "      VAR_TYPE_16 log_out_data_cycles_per_bufGrp;" + "\n"
    line += "      VAR_TYPE_16 log_shift_freq;" + "\n"
    line += "      VAR_TYPE_16 log_mini_shift_reset_freq;" + "\n"
    line += "      VAR_TYPE_16 log_mini_shift_amount;" + "\n"
    line += "      VAR_TYPE_16 log_max_buf_offset;" + "\n"
    line += "      VAR_TYPE_16 shift_counts;" + "\n"
    line += "      VAR_TYPE_16 total_lines_in_group_mask;" + "\n"
    line += "" + "\n"
    line += "      VAR_TYPE_16 seq_addr_shuffler_id;" + "\n"
    line += "      VAR_TYPE_16 non_seq_addr_shuffler_id;" + "\n"
    line += "" + "\n"
    line += "      VAR_TYPE_16 seq_addr_count;" + "\n"
    line += "      VAR_TYPE_16 non_seq_addr_count;" + "\n"
    line += "" + "\n"
    line += "      if( direction ){" + "\n"
    line += "        seq_addr_shuffler_id = comp_write_shuffler_id;" + "\n"
    line += "        non_seq_addr_shuffler_id = comp_read_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        seq_addr_shuffler_id = comp_read_shuffler_id;" + "\n"
    line += "        non_seq_addr_shuffler_id = comp_write_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( (direction) && ( val_valid ) && ( fwd_outVal.try_write(read_val) ) ){" + "\n"
    line += "        sendCount[comp_read_shuffler_id%2]++;" + "\n"
    line += "      }" + "\n"
    line += "      else if( (!direction) && ( val_valid ) && ( inv_outVal.try_write(read_val) ) ){" + "\n"
    line += "        sendCount[comp_read_shuffler_id%2]++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( direction ){" + "\n"
    line += "        seq_addr_count = receiveCount[comp_write_shuffler_id%2];" + "\n"
    line += "        non_seq_addr_count = sendCount[comp_read_shuffler_id%2];" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        seq_addr_count = sendCount[comp_read_shuffler_id%2];" + "\n"
    line += "        non_seq_addr_count = receiveCount[comp_write_shuffler_id%2];" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      poly_group_line_offset_num_line = poly_group_line_offset_num_line_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_poly_group_total_num_line = log_poly_group_total_num_line_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_out_data_cycles_per_bufGrp = log_out_data_cycles_per_bufGrp_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_shift_freq = log_shift_freq_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_mini_shift_reset_freq = log_mini_shift_reset_freq_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_mini_shift_amount = log_mini_shift_amount_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_max_buf_offset = log_max_buf_offset_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      shift_counts = shift_counts_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      total_lines_in_group_mask = total_lines_in_group_mask_table[non_seq_addr_shuffler_id];" + "\n"
    line += "" + "\n"
    line += "      VAR_TYPE_16 read_idx_poly_group_line_offset = (non_seq_addr_count >> log_out_data_cycles_per_bufGrp) << (log_poly_group_total_num_line);" + "\n"
    line += "      VAR_TYPE_16 cycle_start_idx_buffer_id = ( ( non_seq_addr_count >> (log_shift_freq - log_mini_shift_reset_freq) ) << (shift_counts + log_mini_shift_amount ) ) & ( (1<<log_max_buf_offset)-1 );" + "\n"
    line += "      VAR_TYPE_16 read_idx_iter_offset = ( non_seq_addr_count & ((1<<(log_shift_freq - log_mini_shift_reset_freq)) - 1) ) << log_mini_shift_reset_freq;" + "\n"
    line += "      VAR_TYPE_16 index_offset_based_on_strat_buffer = (poly_group_line_offset_num_line - cycle_start_idx_buffer_id);" + "\n"
    line += "      VAR_TYPE_16 total_lines_in_group = ( (2*V_BUG_SIZE) >> (log_mini_shift_reset_freq + log_mini_shift_amount)) * ( 1<<log_shift_freq );" + "\n"
    line += "" + "\n"
    line += "      non_seq_idx = ( (non_seq_addr_shuffler_id%2)*(SINGLE_LIMB_BUF_SIZE) + \\" + "\n"
    line += "                (read_idx_poly_group_line_offset) + \\" + "\n"
    line += "                ( ( ( (( (buf_id + index_offset_based_on_strat_buffer) % (V_BUG_SIZE*2)) >> (shift_counts + log_mini_shift_reset_freq + log_mini_shift_amount)) << log_shift_freq ) + \\" + "\n"
    line += "                ( ( ( ( buf_id + index_offset_based_on_strat_buffer ) % (V_BUG_SIZE*2)) & ( ( 1 << (log_mini_shift_reset_freq + log_mini_shift_amount) ) -1 ) ) >> (log_mini_shift_amount) ) ) & total_lines_in_group_mask )  + \\" + "\n"
    line += "                (read_idx_iter_offset) ) & ( TWO_SINGLE_LIMB_BUF_SIZE_MASK );" + "\n"
    line += "                //3rd line - this line decide major group jump" + "\n"
    line += "                //4th line - this line decide jump within small group" + "\n"
    line += "" + "\n"
    line += "      seq_idx = (seq_addr_shuffler_id%2)*(SINGLE_LIMB_BUF_SIZE) +  seq_addr_count;" + "\n"
    line += "      " + "\n"
    line += "      if( direction ){" + "\n"
    line += "        read_val = poly_buf[non_seq_idx];" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        read_val = poly_buf[seq_idx];" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( ( (receiveCount[comp_read_shuffler_id%2] >> log_poly_group_total_num_line) > (sendCount[comp_read_shuffler_id%2] >> log_poly_group_total_num_line) )){" + "\n"
    line += "        val_valid = true;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        val_valid = false;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      //receive" + "\n"
    line += "      bool inFifoNotEmpty = ( !fwd_inVal.empty() ) || ( !inv_inVal.empty() ) ;" + "\n"
    line += "" + "\n"
    line += "      if(inFifoNotEmpty){" + "\n"
    line += "        if( direction ){" + "\n"
    line += "          poly_buf[seq_idx] = fwd_inVal.read();" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          poly_buf[non_seq_idx] = inv_inVal.read();" + "\n"
    line += "        }" + "\n"
    line += "        receiveCount[comp_write_shuffler_id%2]++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( receiveCount[comp_write_shuffler_id%2] == dataCount ){ //received all the data in this iteration" + "\n"
    line += "        write_shuffler_id++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if(sendCount[comp_read_shuffler_id%2]==dataCount){" + "\n"
    line += "        sendCount[comp_read_shuffler_id%2] = 0;" + "\n"
    line += "        receiveCount[comp_read_shuffler_id%2] = 0;" + "\n"
    line += "        read_shuffler_id++;" + "\n"
    line += "        shuffleCount++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def gen_comb_shuffler_buf(designParamsVar):

    log_shift_freq_table_output_str, log_mini_shift_reset_freq_table_output_str, log_mini_shift_amount_table_output_str, log_max_buf_offset_table_output_str, shift_counts_table_output_str, poly_group_line_offset_num_line_table_output_str, log_poly_group_total_num_line_table_output_str, log_out_data_cycles_per_bufGrp_table_output_str, total_lines_in_group_mask_table_output_str = gen_shuffler_buf_config(designParamsVar)

    line = ""

    line += "void shuffler_buf(tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal," + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal," + "\n"
    line += "                   tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal," + "\n"
    line += "                   tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal," + "\n"
    line += "                    bool direction," + "\n"
    line += "                   VAR_TYPE_16 BUG_id," + "\n"
    line += "                   VAR_TYPE_16 iter){" + "\n"
    line += "  " + "\n"
    line += "  WORD poly_buf[2*V_BUG_SIZE][2*SINGLE_LIMB_BUF_SIZE];" + "\n"
    line += "  #pragma HLS bind_storage variable=poly_buf type=RAM_S2P impl=BRAM latency=1" + "\n"
    line += "  #pragma HLS array_partition variable=poly_buf type=complete dim=1" + "\n"
    line += "" + "\n"
    line += "  const VAR_TYPE_16 dataCount = (N/(V_TOTAL_DATA));" + "\n"
    line += "  const VAR_TYPE_16 shuffleLimit = (VAR_TYPE_32)( (logN+(H_BUG_SIZE-1))/H_BUG_SIZE ) - 1;" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_16 max_data_offset = (V_BUG_SIZE*2);" + "\n"
    line += "  VAR_TYPE_16 receiveCount[2];" + "\n"
    line += "  VAR_TYPE_16 sendCount[2];" + "\n"
    line += "" + "\n"
    line += "  //==== Auto generated variables start ====//" + "\n"
    line += "  VAR_TYPE_16 log_shift_freq_table[shuffleLimit] = " + log_shift_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_mini_shift_reset_freq_table[shuffleLimit] = " + log_mini_shift_reset_freq_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_mini_shift_amount_table[shuffleLimit] = " + log_mini_shift_amount_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_max_buf_offset_table[shuffleLimit] = " + log_max_buf_offset_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 shift_counts_table[shuffleLimit] = " + shift_counts_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 poly_group_line_offset_num_line_table[shuffleLimit] = " + poly_group_line_offset_num_line_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_poly_group_total_num_line_table[shuffleLimit] = " + log_poly_group_total_num_line_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 log_out_data_cycles_per_bufGrp_table[shuffleLimit] = " + log_out_data_cycles_per_bufGrp_table_output_str + ";" + "\n"
    line += "  VAR_TYPE_16 total_lines_in_group_mask_table[shuffleLimit] = " + total_lines_in_group_mask_table_output_str + ";" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS array_partition variable=log_shift_freq_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_mini_shift_reset_freq_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_mini_shift_amount_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_max_buf_offset_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=shift_counts_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=poly_group_line_offset_num_line_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_poly_group_total_num_line_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=log_out_data_cycles_per_bufGrp_table type=complete dim=0" + "\n"
    line += "  #pragma HLS array_partition variable=total_lines_in_group_mask_table type=complete dim=0" + "\n"
    line += "  //==== Auto generated variables end ====//" + "\n"
    line += "" + "\n"
    line += "  ITER_LOOP:for(VAR_TYPE_16 iterCount=0; iterCount<(iter+1); iterCount++){" + "\n"
    line += "    " + "\n"
    line += "    for(VAR_TYPE_16 i=0; i<2; i++){" + "\n"
    line += "      #pragma HLS UNROLL" + "\n"
    line += "      receiveCount[i] = 0;" + "\n"
    line += "      sendCount[i] = 0;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    VAR_TYPE_16 non_seq_idx[2*V_BUG_SIZE];" + "\n"
    line += "    WORD read_val[2*V_BUG_SIZE];" + "\n"
    line += "    bool val_send_success[2*V_BUG_SIZE];" + "\n"
    line += "    for(VAR_TYPE_16 i=0; i<2*V_BUG_SIZE; i++){" + "\n"
    line += "      val_send_success[i] = false;" + "\n"
    line += "    }" + "\n"
    line += "    bool all_val_send_success = true;" + "\n"
    line += "    VAR_TYPE_16 seq_idx;" + "\n"
    line += "" + "\n"
    line += "    VAR_TYPE_16 write_shuffler_id = 0;" + "\n"
    line += "    VAR_TYPE_16 read_shuffler_id = 0;" + "\n"
    line += "    VAR_TYPE_16 inv_write_shuffler_id = shuffleLimit - 1;" + "\n"
    line += "    VAR_TYPE_16 inv_read_shuffler_id = shuffleLimit - 1;" + "\n"
    line += "    VAR_TYPE_16 comp_write_shuffler_id = 0;" + "\n"
    line += "    VAR_TYPE_16 comp_read_shuffler_id = 0;" + "\n"
    line += "" + "\n"
    line += "    VAR_TYPE_16 shuffleCount = 0;" + "\n"
    line += "" + "\n"
    line += "    BUF_COMP:for(; shuffleCount<shuffleLimit ;){" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "      if(direction){" + "\n"
    line += "        comp_read_shuffler_id = read_shuffler_id;" + "\n"
    line += "        comp_write_shuffler_id = write_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        comp_read_shuffler_id = inv_read_shuffler_id;" + "\n"
    line += "        comp_write_shuffler_id = inv_write_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      VAR_TYPE_16 log_shift_freq;" + "\n"
    line += "      VAR_TYPE_16 log_mini_shift_reset_freq;" + "\n"
    line += "      VAR_TYPE_16 log_mini_shift_amount;" + "\n"
    line += "      VAR_TYPE_16 log_max_buf_offset;" + "\n"
    line += "      VAR_TYPE_16 shift_counts;" + "\n"
    line += "      VAR_TYPE_16 poly_group_line_offset_num_line;" + "\n"
    line += "      VAR_TYPE_16 log_poly_group_total_num_line;" + "\n"
    line += "      VAR_TYPE_16 log_out_data_cycles_per_bufGrp;" + "\n"
    line += "      VAR_TYPE_16 total_lines_in_group_mask;" + "\n"
    line += "" + "\n"
    line += "      VAR_TYPE_16 seq_addr_shuffler_id;" + "\n"
    line += "      VAR_TYPE_16 non_seq_addr_shuffler_id;" + "\n"
    line += "" + "\n"
    line += "      VAR_TYPE_16 seq_addr_count;" + "\n"
    line += "      VAR_TYPE_16 non_seq_addr_count;" + "\n"
    line += "" + "\n"
    line += "      if( direction ){" + "\n"
    line += "        seq_addr_shuffler_id = comp_write_shuffler_id;" + "\n"
    line += "        non_seq_addr_shuffler_id = comp_read_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        seq_addr_shuffler_id = comp_read_shuffler_id;" + "\n"
    line += "        non_seq_addr_shuffler_id = comp_write_shuffler_id;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      log_shift_freq = log_shift_freq_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_mini_shift_reset_freq = log_mini_shift_reset_freq_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_mini_shift_amount = log_mini_shift_amount_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_max_buf_offset = log_max_buf_offset_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      shift_counts = shift_counts_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      poly_group_line_offset_num_line = poly_group_line_offset_num_line_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_poly_group_total_num_line = log_poly_group_total_num_line_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      log_out_data_cycles_per_bufGrp = log_out_data_cycles_per_bufGrp_table[non_seq_addr_shuffler_id];" + "\n"
    line += "      total_lines_in_group_mask = total_lines_in_group_mask_table[non_seq_addr_shuffler_id];" + "\n"
    line += "" + "\n"
    line += "      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){" + "\n"
    line += "        #pragma HLS UNROLL" + "\n"
    line += "        if( (direction) && ( !val_send_success[local_buf_id] ) && (!all_val_send_success) && ( fwd_outVal[local_buf_id].try_write(read_val[local_buf_id]) ) ){" + "\n"
    line += "          val_send_success[local_buf_id] = true;" + "\n"
    line += "        }" + "\n"
    line += "        else if( (!direction) && ( !val_send_success[local_buf_id] ) && (!all_val_send_success) && ( inv_outVal[local_buf_id].try_write(read_val[local_buf_id]) ) ){" + "\n"
    line += "          val_send_success[local_buf_id] = true;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      bool all_stream_send_success = val_send_success[0];" + "\n"
    line += "      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){" + "\n"
    line += "        #pragma HLS UNROLL" + "\n"
    line += "        all_stream_send_success &= val_send_success[local_buf_id];" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if(all_stream_send_success && (!all_val_send_success)){" + "\n"
    line += "        sendCount[comp_read_shuffler_id%2]++;" + "\n"
    line += "        all_val_send_success = true;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( direction ){" + "\n"
    line += "        seq_addr_count = receiveCount[comp_write_shuffler_id%2];" + "\n"
    line += "        non_seq_addr_count = sendCount[comp_read_shuffler_id%2];" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        seq_addr_count = sendCount[comp_read_shuffler_id%2];" + "\n"
    line += "        non_seq_addr_count = receiveCount[comp_write_shuffler_id%2];" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      VAR_TYPE_16 read_idx_poly_group_line_offset = ( ( non_seq_addr_count >> log_out_data_cycles_per_bufGrp) << (log_poly_group_total_num_line) ) & SINGLE_LIMB_BUF_SIZE_MASK;" + "\n"
    line += "      VAR_TYPE_16 cycle_start_idx_buffer_id = ( ( non_seq_addr_count >> (log_shift_freq - log_mini_shift_reset_freq) ) << (shift_counts + log_mini_shift_amount ) ) & ( (1<<log_max_buf_offset)-1 );" + "\n"
    line += "      VAR_TYPE_16 read_idx_iter_offset = ( non_seq_addr_count & ((1<<(log_shift_freq - log_mini_shift_reset_freq)) - 1) ) << log_mini_shift_reset_freq;" + "\n"
    line += "      VAR_TYPE_16 index_offset_based_on_strat_buffer = (poly_group_line_offset_num_line - cycle_start_idx_buffer_id);" + "\n"
    line += "" + "\n"
    line += "      seq_idx = (seq_addr_shuffler_id%2)*(SINGLE_LIMB_BUF_SIZE) +  seq_addr_count;" + "\n"
    line += "" + "\n"
    line += "      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){" + "\n"
    line += "        #pragma HLS UNROLL" + "\n"
    line += "        non_seq_idx[local_buf_id] = (non_seq_addr_shuffler_id%2)*(SINGLE_LIMB_BUF_SIZE) + \\" + "\n"
    line += "                (read_idx_poly_group_line_offset) + \\" + "\n"
    line += "                ( ( ( ( ( (local_buf_id + index_offset_based_on_strat_buffer) % (V_BUG_SIZE*2) ) >> (shift_counts + log_mini_shift_reset_freq + log_mini_shift_amount)) << log_shift_freq ) + \\" + "\n"
    line += "                ( ( ( ( local_buf_id + index_offset_based_on_strat_buffer ) % (V_BUG_SIZE*2)) & ( ( 1 << (log_mini_shift_reset_freq + log_mini_shift_amount) ) -1 ) ) >> (log_mini_shift_amount) ) ) & total_lines_in_group_mask ) + \\" + "\n"
    line += "                (read_idx_iter_offset);" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){" + "\n"
    line += "        if(direction){" + "\n"
    line += "          read_val[local_buf_id] = poly_buf[local_buf_id][non_seq_idx[local_buf_id]];" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          read_val[local_buf_id] = poly_buf[local_buf_id][seq_idx];" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( all_val_send_success && ( (receiveCount[comp_read_shuffler_id%2] >> log_poly_group_total_num_line) > (sendCount[comp_read_shuffler_id%2] >> log_poly_group_total_num_line) ) ){" + "\n"
    line += "        all_val_send_success = false;" + "\n"
    line += "        for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){" + "\n"
    line += "          #pragma HLS UNROLL" + "\n"
    line += "          val_send_success[local_buf_id] = false;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if(sendCount[comp_read_shuffler_id%2]==dataCount){" + "\n"
    line += "        sendCount[comp_read_shuffler_id%2] = 0;" + "\n"
    line += "        receiveCount[comp_read_shuffler_id%2] = 0;" + "\n"
    line += "        read_shuffler_id++;" + "\n"
    line += "        inv_read_shuffler_id--;" + "\n"
    line += "        shuffleCount++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      //receive" + "\n"
    line += "      bool inFifoNotEmpty = ( !fwd_inVal[0].empty() ) || ( !inv_inVal[0].empty() ) ;" + "\n"
    line += "" + "\n"
    line += "      for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){" + "\n"
    line += "        #pragma HLS UNROLL" + "\n"
    line += "        inFifoNotEmpty &= ( !fwd_inVal[local_buf_id].empty() ) || ( !inv_inVal[local_buf_id].empty() ) ;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if(inFifoNotEmpty){" + "\n"
    line += "        for(VAR_TYPE_16 local_buf_id=0; local_buf_id<2*V_BUG_SIZE; local_buf_id++){" + "\n"
    line += "          #pragma HLS UNROLL" + "\n"
    line += "            if(direction){" + "\n"
    line += "              poly_buf[local_buf_id][seq_idx] = fwd_inVal[local_buf_id].read();" + "\n"
    line += "            }" + "\n"
    line += "            else{" + "\n"
    line += "              poly_buf[local_buf_id][non_seq_idx[local_buf_id]] = inv_inVal[local_buf_id].read();" + "\n"
    line += "            }" + "\n"
    line += "        }" + "\n"
    line += "        receiveCount[comp_write_shuffler_id%2]++;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if( receiveCount[comp_write_shuffler_id%2] == dataCount ){ //received all the data in this iteration" + "\n"
    line += "        write_shuffler_id++;" + "\n"
    line += "        inv_write_shuffler_id = (inv_write_shuffler_id==0) ? (0) : inv_write_shuffler_id-1;" + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

####
# Generate shuffler_buf
####
def gen_shuffler_buf(designParamsVar, is_split_buffer):
    line = ""
    if(is_split_buffer):
        line += gen_split_shuffler_buf(designParamsVar)
    else:
        line += gen_comb_shuffler_buf(designParamsVar)
    return line