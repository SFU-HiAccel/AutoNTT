from code_generators.common.helper_functions import num_arr_to_cppArrStr

def TFBuf_common_function_gen():
    line = ""

    line += "void BufModule_loadTF_wiFW(tapa::istream<WORD>&    inTfFromLoad," + "\n"
    line += "                           tapa::ostream<WORD>&    outTfToNextBuf," + "\n"
    line += "                           WORD                    TFArr[N/2]," + "\n"
    line += "                           VAR_TYPE_16             loadTFLoopCounter," + "\n"
    line += "                           VAR_TYPE_16             thisBufTFEnd," + "\n"
    line += "                           VAR_TYPE_16             forwardingStart){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_16 loadTFCounter = 0;" + "\n"
    line += "" + "\n"
    line += "  BUF_LOAD_TF:for(VAR_TYPE_16 i=0; i<loadTFLoopCounter; i++){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "    WORD readVal = inTfFromLoad.read();" + "\n"
    line += "    if(i<thisBufTFEnd){" + "\n"
    line += "      TFArr[loadTFCounter] = readVal;" + "\n"
    line += "      loadTFCounter++;" + "\n"
    line += "    }" + "\n"
    line += "    else if(i>=forwardingStart){" + "\n"
    line += "      outTfToNextBuf.write(readVal); " + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void BufModule_loadTF_woFW(tapa::istream<WORD>&    inTfFromLoad," + "\n"
    line += "                           WORD                    TFArr[N/2]," + "\n"
    line += "                           VAR_TYPE_16             loadTFLoopCounter," + "\n"
    line += "                           VAR_TYPE_16             thisBufTFEnd){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_16 loadCounter = 0;" + "\n"
    line += "  VAR_TYPE_16 loadTFCounter = 0;" + "\n"
    line += "" + "\n"
    line += "  BUF_LOAD_TF:for(VAR_TYPE_16 i=0; i<loadTFLoopCounter; i++){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "    WORD readVal = inTfFromLoad.read();" + "\n"
    line += "    if(i<thisBufTFEnd){" + "\n"
    line += "      TFArr[loadTFCounter] = readVal;" + "\n"
    line += "      loadTFCounter++;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"
    
    line += "void TFSend(tapa::ostreams<WORD,2>& tfToBUs," + "\n"
    line += "            WORD                    TFArr[N/2]," + "\n"
    line += "            const TF_GROUP_WORD     FWD_TF_GROUP_IDX0[logN]," + "\n"
    line += "            const TF_GROUP_WORD     FWD_TF_GROUP_IDX1[logN]," + "\n"
    line += "            const TF_GROUP_WORD     INV_TF_GROUP_IDX0[logN]," + "\n"
    line += "            const TF_GROUP_WORD     INV_TF_GROUP_IDX1[logN]," + "\n"
    line += "            bool                    direction," + "\n"
    line += "            VAR_TYPE_32             beta){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  TF_GROUP_WORD tfIdx_0;" + "\n"
    line += "  TF_GROUP_WORD tfIdx_1;" + "\n"
    line += "  WORD tfVal_0;" + "\n"
    line += "  WORD tfVal_1;" + "\n"
    line += "" + "\n"
    line += "  BETA_WORD sendCount_0 = 0;" + "\n"
    line += "  BETA_WORD countMask = 0;" + "\n"
    line += "  TF_GROUP_WORD tfGroup_access0 = 0;" + "\n"
    line += "  TF_GROUP_WORD tfGroup_access1 = 0;" + "\n"
    line += "" + "\n"
    line += "  BUF_COMP:for (VAR_TYPE_8 buffTrack=0; (buffTrack<logN); buffTrack++) {" + "\n"
    line += "    BUF_STAGE:for(sendCount_0 = 0 ;  sendCount_0 < beta; sendCount_0++){" + "\n"
    line += "      #pragma HLS PIPELINE II=1" + "\n"
    line += "      tfGroup_access0 = (direction) ? FWD_TF_GROUP_IDX0[buffTrack] : INV_TF_GROUP_IDX0[buffTrack];" + "\n"
    line += "      tfGroup_access1 = (direction) ? FWD_TF_GROUP_IDX1[buffTrack] : INV_TF_GROUP_IDX1[buffTrack];" + "\n"
    line += "      countMask = (direction) ? fwd_mask_arr[buffTrack] : inv_mask_arr[buffTrack];" + "\n"
    line += "" + "\n"
    line += "      tfIdx_0 = ((tfGroup_access0)) + (sendCount_0 & (countMask));" + "\n"
    line += "      tfIdx_1 = ((tfGroup_access1)) + (sendCount_0 & (countMask));" + "\n"
    line += "    " + "\n"
    line += "      tfVal_0 = TFArr[tfIdx_0];" + "\n"
    line += "      tfVal_1 = TFArr[tfIdx_1];" + "\n"
    line += "" + "\n"
    line += "      tfToBUs[0].write(tfVal_0);" + "\n"
    line += "      tfToBUs[1].write(tfVal_1);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer with TF with forwarding and with support for double buffering
def genTFModule_wiFW_wiDB(bufParamsVar):
    line = ""
    line += "void TFModule_wiFW_" + str(bufParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inTfFromLoad," + "\n"
    line += "                    tapa::ostream<WORD>&     outTfToNextBuf," + "\n"
    line += "                    tapa::ostreams<WORD,2>&  tfToBUs," + "\n"
    line += "                    bool                     direction," + "\n"
    line += "                    VAR_TYPE_8               iter," + "\n"
    line += "                    VAR_TYPE_32              BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(bufParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 TF_ARR_SIZE = " + str(bufParamsVar.TF_ARR_SIZE) + ";" + "\n"
    line += "    const VAR_TYPE_32 FWD_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.FWD_LOAD_TF_LOOP_COUNTER) + ";" + "\n"
    line += "    const VAR_TYPE_32 INV_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.INV_LOAD_TF_LOOP_COUNTER) + ";" + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_FWD = " + str(bufParamsVar.THIS_BUF_TF_END_FWD) + ";" + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_INV = " + str(bufParamsVar.THIS_BUF_TF_END_INV) + ";" + "\n"
    line += "    const VAR_TYPE_32 TF_FORWARDING_START_FWD = " + str(bufParamsVar.TF_FORWARDING_START_FWD) + "; " + "\n"
    line += "    const VAR_TYPE_32 TF_FORWARDING_START_INV = " + str(bufParamsVar.TF_FORWARDING_START_INV) + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX0[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX1[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX1 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX0[logN] = " + bufParamsVar.INV_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX1[logN] = " + bufParamsVar.INV_TF_GROUP_IDX1 + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD TFArr[2][TF_ARR_SIZE];" + "\n"
    line += "    #pragma HLS array_partition variable=TFArr type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = TFArr type = RAM_2P impl = uram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "    " + "\n"
    line += "    const VAR_TYPE_32 loadTFLoopCounter = (direction) ? FWD_LOAD_TF_LOOP_COUNTER : INV_LOAD_TF_LOOP_COUNTER;" + "\n"
    line += "    const VAR_TYPE_32 thisBufTFEnd = (direction) ? THIS_BUF_TF_END_FWD : THIS_BUF_TF_END_INV;" + "\n"
    line += "    const VAR_TYPE_32 forwardingStart = (direction) ? TF_FORWARDING_START_FWD : TF_FORWARDING_START_INV;" + "\n"
    line += "" + "\n"
    line += "    TF_GROUP_WORD tfIdx_0;" + "\n"
    line += "    TF_GROUP_WORD tfIdx_1;" + "\n"
    line += "    WORD tfVal_0;" + "\n"
    line += "    WORD tfVal_1;" + "\n"
    line += "" + "\n"
    line += "    BETA_WORD sendCount_0 = 0;" + "\n"
    line += "    BETA_WORD countMask = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access0 = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access1 = 0;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){" + "\n"
    line += "      TFSend(tfToBUs, TFArr[iterCount%2], FWD_TF_GROUP_IDX0, FWD_TF_GROUP_IDX1, INV_TF_GROUP_IDX0, INV_TF_GROUP_IDX1, direction, beta);" + "\n"
    line += "      BufModule_loadTF_wiFW(inTfFromLoad, outTfToNextBuf, TFArr[(iterCount+1)%2], loadTFLoopCounter, thisBufTFEnd, forwardingStart);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer with TF with forwarding and without support for double buffering
def genTFModule_wiFW_woDB(bufParamsVar):
    line = ""
    line += "void TFModule_wiFW_" + str(bufParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inTfFromLoad," + "\n"
    line += "                    tapa::ostream<WORD>&     outTfToNextBuf," + "\n"
    line += "                    tapa::ostreams<WORD,2>&  tfToBUs," + "\n"
    line += "                    bool                     direction," + "\n"
    line += "                    VAR_TYPE_8               iter," + "\n"
    line += "                    VAR_TYPE_32              BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(bufParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 TF_ARR_SIZE = " + str(bufParamsVar.TF_ARR_SIZE) + ";" + "\n"
    line += "    const VAR_TYPE_32 FWD_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.FWD_LOAD_TF_LOOP_COUNTER) + ";" + "\n"
    line += "    const VAR_TYPE_32 INV_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.INV_LOAD_TF_LOOP_COUNTER) + ";" + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_FWD = " + str(bufParamsVar.THIS_BUF_TF_END_FWD) + ";" + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_INV = " + str(bufParamsVar.THIS_BUF_TF_END_INV) + ";" + "\n"
    line += "    const VAR_TYPE_32 TF_FORWARDING_START_FWD = " + str(bufParamsVar.TF_FORWARDING_START_FWD) + "; " + "\n"
    line += "    const VAR_TYPE_32 TF_FORWARDING_START_INV = " + str(bufParamsVar.TF_FORWARDING_START_INV) + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX0[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX1[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX1 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX0[logN] = " + bufParamsVar.INV_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX1[logN] = " + bufParamsVar.INV_TF_GROUP_IDX1 + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD TFArr[TF_ARR_SIZE];" + "\n"
    line += "    #pragma HLS bind_storage variable = TFArr type = RAM_2P impl = uram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "    " + "\n"
    line += "    const VAR_TYPE_32 loadTFLoopCounter = (direction) ? FWD_LOAD_TF_LOOP_COUNTER : INV_LOAD_TF_LOOP_COUNTER;" + "\n"
    line += "    const VAR_TYPE_32 thisBufTFEnd = (direction) ? THIS_BUF_TF_END_FWD : THIS_BUF_TF_END_INV;" + "\n"
    line += "    const VAR_TYPE_32 forwardingStart = (direction) ? TF_FORWARDING_START_FWD : TF_FORWARDING_START_INV;" + "\n"
    line += "" + "\n"
    line += "    TF_GROUP_WORD tfIdx_0;" + "\n"
    line += "    TF_GROUP_WORD tfIdx_1;" + "\n"
    line += "    WORD tfVal_0;" + "\n"
    line += "    WORD tfVal_1;" + "\n"
    line += "" + "\n"
    line += "    BETA_WORD sendCount_0 = 0;" + "\n"
    line += "    BETA_WORD countMask = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access0 = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access1 = 0;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter; iterCount++){" + "\n"
    line += "      BufModule_loadTF_wiFW(inTfFromLoad, outTfToNextBuf, TFArr, loadTFLoopCounter, thisBufTFEnd, forwardingStart);" + "\n"
    line += "      TFSend(tfToBUs, TFArr, FWD_TF_GROUP_IDX0, FWD_TF_GROUP_IDX1, INV_TF_GROUP_IDX0, INV_TF_GROUP_IDX1, direction, beta);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer with TF with forwarding and with support for double buffering
def genTFModule_woFW_wiDB(bufParamsVar):
    line = ""
    line += "void TFModule_woFW_" + str(bufParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inTfFromLoad," + "\n"
    line += "                    tapa::ostreams<WORD,2>&  tfToBUs," + "\n"
    line += "                    bool                     direction," + "\n"
    line += "                    VAR_TYPE_8               iter," + "\n"
    line += "                    VAR_TYPE_32              BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(bufParamsVar.BETA) + ";" + "\n"
    line += "    const VAR_TYPE_32 TF_ARR_SIZE = " + str(bufParamsVar.TF_ARR_SIZE) + ";" + "\n"
    line += "    const VAR_TYPE_32 FWD_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.FWD_LOAD_TF_LOOP_COUNTER) + ";" + "\n"
    line += "    const VAR_TYPE_32 INV_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.INV_LOAD_TF_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_FWD = " + str(bufParamsVar.THIS_BUF_TF_END_FWD) + ";" + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_INV = " + str(bufParamsVar.THIS_BUF_TF_END_INV) + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX0[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX1[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX1 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX0[logN] = " + bufParamsVar.INV_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX1[logN] = " + bufParamsVar.INV_TF_GROUP_IDX1 + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD TFArr[2][TF_ARR_SIZE];" + "\n"
    line += "    #pragma HLS array_partition variable=TFArr type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = TFArr type = RAM_2P impl = uram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "    " + "\n"
    line += "    const VAR_TYPE_32 loadTFLoopCounter = (direction) ? FWD_LOAD_TF_LOOP_COUNTER : INV_LOAD_TF_LOOP_COUNTER;" + "\n"
    line += "    const VAR_TYPE_32 thisBufTFEnd = (direction) ? THIS_BUF_TF_END_FWD : THIS_BUF_TF_END_INV;" + "\n"
    line += "" + "\n"
    line += "    TF_GROUP_WORD tfIdx_0;" + "\n"
    line += "    TF_GROUP_WORD tfIdx_1;" + "\n"
    line += "    WORD tfVal_0;" + "\n"
    line += "    WORD tfVal_1;" + "\n"
    line += "" + "\n"
    line += "    BETA_WORD sendCount_0 = 0;" + "\n"
    line += "    BETA_WORD countMask = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access0 = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access1 = 0;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){" + "\n"
    line += "      TFSend(tfToBUs, TFArr[iterCount%2], FWD_TF_GROUP_IDX0, FWD_TF_GROUP_IDX1, INV_TF_GROUP_IDX0, INV_TF_GROUP_IDX1, direction, beta);" + "\n"
    line += "      BufModule_loadTF_woFW(inTfFromLoad, TFArr[(iterCount+1)%2], loadTFLoopCounter, thisBufTFEnd);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer with TF with forwarding and without support for double buffering
def genTFModule_woFW_woDB(bufParamsVar):
    line = ""
    line += "void TFModule_woFW_" + str(bufParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inTfFromLoad," + "\n"
    line += "                    tapa::ostreams<WORD,2>&  tfToBUs," + "\n"
    line += "                    bool                     direction," + "\n"
    line += "                    VAR_TYPE_8               iter," + "\n"
    line += "                    VAR_TYPE_32              BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(bufParamsVar.BETA) + ";" + "\n"
    line += "    const VAR_TYPE_32 TF_ARR_SIZE = " + str(bufParamsVar.TF_ARR_SIZE) + ";" + "\n"
    line += "    const VAR_TYPE_32 FWD_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.FWD_LOAD_TF_LOOP_COUNTER) + ";" + "\n"
    line += "    const VAR_TYPE_32 INV_LOAD_TF_LOOP_COUNTER = " + str(bufParamsVar.INV_LOAD_TF_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_FWD = " + str(bufParamsVar.THIS_BUF_TF_END_FWD) + ";" + "\n"
    line += "    const VAR_TYPE_32 THIS_BUF_TF_END_INV = " + str(bufParamsVar.THIS_BUF_TF_END_INV) + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX0[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD FWD_TF_GROUP_IDX1[logN] = " + bufParamsVar.FWD_TF_GROUP_IDX1 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX0[logN] = " + bufParamsVar.INV_TF_GROUP_IDX0 + ";" + "\n"
    line += "    const TF_GROUP_WORD INV_TF_GROUP_IDX1[logN] = " + bufParamsVar.INV_TF_GROUP_IDX1 + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD TFArr[TF_ARR_SIZE];" + "\n"
    line += "    #pragma HLS bind_storage variable = TFArr type = RAM_2P impl = uram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "    " + "\n"
    line += "    const VAR_TYPE_32 loadTFLoopCounter = (direction) ? FWD_LOAD_TF_LOOP_COUNTER : INV_LOAD_TF_LOOP_COUNTER;" + "\n"
    line += "    const VAR_TYPE_32 thisBufTFEnd = (direction) ? THIS_BUF_TF_END_FWD : THIS_BUF_TF_END_INV;" + "\n"
    line += "" + "\n"
    line += "    TF_GROUP_WORD tfIdx_0;" + "\n"
    line += "    TF_GROUP_WORD tfIdx_1;" + "\n"
    line += "    WORD tfVal_0;" + "\n"
    line += "    WORD tfVal_1;" + "\n"
    line += "" + "\n"
    line += "    BETA_WORD sendCount_0 = 0;" + "\n"
    line += "    BETA_WORD countMask = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access0 = 0;" + "\n"
    line += "    TF_GROUP_WORD tfGroup_access1 = 0;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter; iterCount++){" + "\n"
    line += "      BufModule_loadTF_woFW(inTfFromLoad, TFArr, loadTFLoopCounter, thisBufTFEnd);" + "\n"
    line += "      TFSend(tfToBUs, TFArr, FWD_TF_GROUP_IDX0, FWD_TF_GROUP_IDX1, INV_TF_GROUP_IDX0, INV_TF_GROUP_IDX1, direction, beta);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#calculate TF loading trip count for both forward and inverse loading
#For inverse _beta part should be multiply with actual beta
#For inverse _add part should be added to the above part after multiplying with beta
def tf_load_trip_count_calculate(buf_idx, designParamsVar):
    TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    NUM_BUF_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_BUF_PER_PARA_LIMB_TF_PORT
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT
    FWD_sizeArr = designParamsVar.FWD_sizeArr
    INV_sizeArr = designParamsVar.INV_sizeArr
    beta = designParamsVar.beta

    loadTFLoopCounter_fwd = 0
    loadTFLoopCounter_inv = 0
    loadTFLoopCounter_inv_beta = 0
    loadTFLoopCounter_inv_add = 0

    ddrPortId = ((buf_idx)//NUM_BUF_PER_PARA_LIMB_TF_PORT) 
    chainBroadcastingId = (((buf_idx)%NUM_BUF_PER_PARA_LIMB_TF_PORT)//TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT) 
    concatFactorId = ((buf_idx)%TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT) 

    for s in range(chainBroadcastingId, NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT):
        new_bufIdx = ddrPortId*NUM_BUF_PER_PARA_LIMB_TF_PORT + s*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1
        
        # print("BufIdx=" + str(BufIdx) + ", ddrPort=" + str(ddrPortId) + ", chainBroadcastingId=" + str(chainBroadcastingId) + ", concatFactorId=" + str(concatFactorId) + ", s=" + str(s) + ", new_bufIdx=" + str(new_bufIdx))

        loadTFLoopCounter_fwd += FWD_sizeArr[new_bufIdx]

        loadTFLoopCounter_inv_beta +=2

        loadTFLoopCounter_inv_add += INV_sizeArr[new_bufIdx] - 2

    loadTFLoopCounter_fwd = loadTFLoopCounter_fwd * beta
    loadTFLoopCounter_inv = loadTFLoopCounter_inv_add + (loadTFLoopCounter_inv_beta * beta)

    return loadTFLoopCounter_fwd, loadTFLoopCounter_inv

#calculate when TF loading is done for this buffer for forward & inverse computations
def tf_load_done_calculate(buf_idx, designParamsVar):
    FWD_sizeArr = designParamsVar.FWD_sizeArr
    INV_sizeArr = designParamsVar.INV_sizeArr
    beta = designParamsVar.beta

    tf_load_done_fwd = 0
    tf_load_done_inv = 0

    tf_load_done_fwd = FWD_sizeArr[buf_idx]
    tf_load_done_inv = INV_sizeArr[buf_idx] - 2

    tf_load_done_fwd = tf_load_done_fwd * beta
    tf_load_done_inv = tf_load_done_inv + 2*beta

    return tf_load_done_fwd, tf_load_done_inv

#calculate when TF loading is done for this buffer for forward & inverse computations
def tf_forwardin_start_calculate(buf_idx, designParamsVar):
    TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    NUM_BUF_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_BUF_PER_PARA_LIMB_TF_PORT
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT
    FWD_sizeArr = designParamsVar.FWD_sizeArr
    INV_sizeArr = designParamsVar.INV_sizeArr
    beta = designParamsVar.beta

    tf_forwarding_start_fwd = 0
    tf_forwarding_start_inv = 0

    ddrPortId = ((buf_idx)//NUM_BUF_PER_PARA_LIMB_TF_PORT) 
    chainBroadcastingId = (((buf_idx)%NUM_BUF_PER_PARA_LIMB_TF_PORT)//TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT) 
    concatFactorId = ((buf_idx)%TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT) 

    new_bufIdx = ddrPortId*NUM_BUF_PER_PARA_LIMB_TF_PORT + chainBroadcastingId*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1
    
    tf_forwarding_start_fwd = FWD_sizeArr[new_bufIdx]
    tf_forwarding_start_inv = INV_sizeArr[new_bufIdx] - 2

    tf_forwarding_start_fwd = tf_forwarding_start_fwd * beta
    tf_forwarding_start_inv = tf_forwarding_start_inv + 2*beta

    return tf_forwarding_start_fwd, tf_forwarding_start_inv

#This function generates TF group indexes array string for given buf module for both forward and inverse. This is used in generating BufModule
#The sharing considered here is half length PE BUs share the TF. i.e., For 256 PE design (0,128), (1,129),...
def bufWiseTFGroupIdxGen_halfPEsDistBufTogether(buf_idx, designParamsVar):

    logBU = designParamsVar.logBU
    logN = designParamsVar.logN
    beta = designParamsVar.beta
    logBeta = designParamsVar.logBeta
    
    modifiedBufIdx = buf_idx #For half PE dist BUs are being received TFs case
    
    #### FWD ####
    FWD_TF_grp_idx = [0]    #0 is anyway included to conver shift size is 0 case
    grp_idx = 0 # to track group index
    prev_shift_val = 0 # to keep track of previous value
    for shift in range(1, logBU+1):    #loop start from 1 as 0 is covered above
        current_shift_val = ((modifiedBufIdx) & ((1<<(shift)) - 1))
        if current_shift_val != prev_shift_val: #need to move into new group
            grp_idx = grp_idx + 1
        FWD_TF_grp_idx.append(grp_idx)
        prev_shift_val = current_shift_val

    #### INV ####
    INV_TF_grp_idx = [0]    #0 is anyway included to conver shift size is 0 case
    grp_idx = 0 # to track group index
    prev_shift_val = 0 # to keep track of previous value
    for shift in range(logBU-1, -1, -1):    #loop start from 1 as 0 is covered above
        current_shift_val = ((modifiedBufIdx) & (~((1<<(shift)) - 1)))
        if current_shift_val != prev_shift_val: #need to move into new group
            grp_idx = grp_idx +1
        INV_TF_grp_idx.append(grp_idx)
        prev_shift_val = current_shift_val
    
    #Convert both FWD and INV arrays into strings i.e., something like {0,0,1,1}
    # FWD_TF_grp_idx_str = [str(x) for x in FWD_TF_grp_idx]
    # INV_TF_grp_idx_str = [str(x) for x in INV_TF_grp_idx]

    # FWD_output_str = "{" + ",".join(FWD_TF_grp_idx_str) + "}"
    # INV_output_str = "{" + ",".join(INV_TF_grp_idx_str) + "}"

    # return FWD_output_str, INV_output_str

    #Added this content when decided to generate the TF group arrays for both BUs and decided to hard code them for the 
    #NTT stages. Until this point, the kernel code was not depend on the polynomial size and, based on the processing
    #polynomial size, it was picking up the TF group in respective stage. But in order to save some resources, decided to 
    #hard code TF group index for all the stages and following logic is for that.

    FWD_TF_grp_idx0 = []
    FWD_TF_grp_idx1 = []
    fwd_tfGroup_access0 = 0
    fwd_tfGroup_access1 = 0
    fwd_tfGroup_addr0 = 0

    INV_TF_grp_idx0 = []
    INV_TF_grp_idx1 = []
    inv_tfGroup_access0 = 0
    inv_tfGroup_access1 = 0
    inv_tfGroup_addr0 = 0

    for i in range(logN):
        #FWD
        if(i>=logBeta):
            fwd_tfGroup_access0 = FWD_TF_grp_idx[fwd_tfGroup_addr0] * beta
            fwd_tfGroup_access1 = ((FWD_TF_grp_idx[fwd_tfGroup_addr0]+1) * beta) if(fwd_tfGroup_addr0==logBU) else (FWD_TF_grp_idx[fwd_tfGroup_addr0] * beta)
            fwd_tfGroup_addr0 += 1

        #INV
        if(i<=logBU):
            inv_tfGroup_access0 = INV_TF_grp_idx[inv_tfGroup_addr0]
            inv_tfGroup_access1 = (INV_TF_grp_idx[inv_tfGroup_addr0] + INV_TF_grp_idx[logBU] + beta) if (inv_tfGroup_addr0>0) else (INV_TF_grp_idx[inv_tfGroup_addr0])
            inv_tfGroup_addr0 += 1

        FWD_TF_grp_idx0.append(fwd_tfGroup_access0)
        FWD_TF_grp_idx1.append(fwd_tfGroup_access1)

        INV_TF_grp_idx0.append(inv_tfGroup_access0)
        INV_TF_grp_idx1.append(inv_tfGroup_access1)

    #Convert both FWD and INV arrays into strings i.e., something like {0,0,1,1}
    # FWD_TF_grp_idx0_str = [str(x) for x in FWD_TF_grp_idx0]
    # FWD_TF_grp_idx1_str = [str(x) for x in FWD_TF_grp_idx1]
    # INV_TF_grp_idx0_str = [str(x) for x in INV_TF_grp_idx0]
    # INV_TF_grp_idx1_str = [str(x) for x in INV_TF_grp_idx1]

    # FWD_output_str0 = "{" + ",".join(FWD_TF_grp_idx0_str) + "}"
    # FWD_output_str1 = "{" + ",".join(FWD_TF_grp_idx1_str) + "}"
    # INV_output_str0 = "{" + ",".join(INV_TF_grp_idx0_str) + "}"
    # INV_output_str1 = "{" + ",".join(INV_TF_grp_idx1_str) + "}"

    FWD_output_str0 = num_arr_to_cppArrStr(FWD_TF_grp_idx0)
    FWD_output_str1 = num_arr_to_cppArrStr(FWD_TF_grp_idx1)
    INV_output_str0 = num_arr_to_cppArrStr(INV_TF_grp_idx0)
    INV_output_str1 = num_arr_to_cppArrStr(INV_TF_grp_idx1)

    return FWD_output_str0, FWD_output_str1, INV_output_str0, INV_output_str1

def gen_TF_buffer_tasks(designParamsVar):

    bufParamsVar = designParamsVar.bufParamsVar

    NUM_BU = designParamsVar.NUM_BU
    TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    NUM_BUF_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_BUF_PER_PARA_LIMB_TF_PORT
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT
    beta = designParamsVar.beta
    FWD_sizeArr = designParamsVar.FWD_sizeArr
    DOUBLE_BUF_EN = designParamsVar.DOUBLE_BUF_EN

    code = ""

    #generate TFModule wrappers
    for buf_idx in range(NUM_BU//2):  #half of the NUM_BU carries TFs

        bufParamsVar.BUFIDX0 = buf_idx

        bufParamsVar.BETA = beta

        tfDdrPortId = ((buf_idx)//NUM_BUF_PER_PARA_LIMB_TF_PORT) 
        tfChainBroadcastingId = (((buf_idx)%NUM_BUF_PER_PARA_LIMB_TF_PORT)//TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT) 
        
        # Calculate TF array size.
        # Only consider FWD as FWD require more TFs.
        bufParamsVar.TF_ARR_SIZE = FWD_sizeArr[buf_idx]*beta

        # calculate TF loading trip count for both forward and inverse loading
        # For inverse _beta part should be multiply with actual beta
        # For inverse _add part should be added to the above part after multiplying with beta
        bufParamsVar.FWD_LOAD_TF_LOOP_COUNTER, bufParamsVar.INV_LOAD_TF_LOOP_COUNTER = tf_load_trip_count_calculate(buf_idx, designParamsVar)

        # calculate when TF loading is done for this buffer for forward & inverse computations
        bufParamsVar.THIS_BUF_TF_END_FWD, bufParamsVar.THIS_BUF_TF_END_INV = tf_load_done_calculate(buf_idx, designParamsVar)

        # Calculate when TF forwarding should start for forward & inverse computations
        bufParamsVar.TF_FORWARDING_START_FWD, bufParamsVar.TF_FORWARDING_START_INV = tf_forwardin_start_calculate(buf_idx, designParamsVar)

        # This function generates TF group indexes array string for given buf module for both forward and inverse.
        bufParamsVar.FWD_TF_GROUP_IDX0, bufParamsVar.FWD_TF_GROUP_IDX1, bufParamsVar.INV_TF_GROUP_IDX0, bufParamsVar.INV_TF_GROUP_IDX1 = bufWiseTFGroupIdxGen_halfPEsDistBufTogether(buf_idx, designParamsVar)

        if (tfChainBroadcastingId==(NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT-1) ):   #no forwarding
            if(DOUBLE_BUF_EN):
                code += genTFModule_woFW_wiDB(bufParamsVar)
            else:
                code += genTFModule_woFW_woDB(bufParamsVar)
            code += "\n"
        else: #forwarding
            if(DOUBLE_BUF_EN):
                code += genTFModule_wiFW_wiDB(bufParamsVar)
            else:
                code += genTFModule_wiFW_woDB(bufParamsVar)
            code += "\n"

    return code

def gen_TF_buffers(designParamsVar):
    
    code = ""

    # generate supporting functions
    code += TFBuf_common_function_gen()
    code += "\n"

    # generate TF buffer tasks
    code += gen_TF_buffer_tasks(designParamsVar)
    code += "\n"

    return code