# Content of computation in polyBuf
def polyBuf_compute_common_function_gen():
    line = ""

    line += "void BufModule_comp_stage_polySend(tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                                tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                                bool                    direction," + "\n"
    line += "                                WORD                    polyBuf0[N/NUM_BU]," + "\n"
    line += "                                VAR_TYPE_32             beta){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  BETA_WORD sendCount_0 = 0;" + "\n"
    line += "" + "\n"
    line += "  BETA_WORD inLeftIdx;" + "\n"
    line += "  BETA_WORD inRightIdx;" + "\n"
    line += "  WORD inVal0;" + "\n"
    line += "  WORD inVal1;" + "\n"
    line += "" + "\n"
    line += "  //compute data" + "\n"
    line += "  BUF_STAGE:for(; ( sendCount_0<beta ); sendCount_0++){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "    if(direction){" + "\n"
    line += "      inLeftIdx = sendCount_0;" + "\n"
    line += "      inRightIdx = beta+sendCount_0;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      inLeftIdx = 2*sendCount_0;" + "\n"
    line += "      inRightIdx = 2*sendCount_0 + (BETA_WORD)1;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    inVal0 = polyBuf0[inLeftIdx];" + "\n"
    line += "    inVal1 = polyBuf0[inRightIdx];" + "\n"
    line += "" + "\n"
    line += "    if( direction ){" + "\n"
    line += "      fwd_PolyToBUs[0].write(inVal0);" + "\n"
    line += "      fwd_PolyToBUs[1].write(inVal1);" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      inv_PolyToBUs[0].write(inVal0);" + "\n"
    line += "      inv_PolyToBUs[1].write(inVal1);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"
    line += "" + "\n"

    line += "void BufModule_comp_stage_polyReceive(tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                                tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                                bool                    direction," + "\n"
    line += "                                WORD                    polyBuf0[N/NUM_BU]," + "\n"
    line += "                                VAR_TYPE_32             beta){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  BETA_WORD outLeftIdx;" + "\n"
    line += "  BETA_WORD outRightIdx;" + "\n"
    line += "  WORD outVal0;" + "\n"
    line += "  WORD outVal1;" + "\n"
    line += "" + "\n"
    line += "  BETA_WORD receiveCount_0 = 0;" + "\n"
    line += "" + "\n"
    line += "  //compute data" + "\n"
    line += "  BUF_STAGE:for(; ( receiveCount_0 < beta ); receiveCount_0++){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "    #pragma HLS dependence variable=polyBuf0 intra WAW false" + "\n"
    line += "" + "\n"
    line += "    if(direction){" + "\n"
    line += "      outLeftIdx = 2*receiveCount_0;" + "\n"
    line += "      outRightIdx = (2*receiveCount_0) + 1;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      outLeftIdx = receiveCount_0;" + "\n"
    line += "      outRightIdx = receiveCount_0 + beta;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    if(direction){" + "\n"
    line += "        outVal0 = fwd_polyFromBUs[0].read();" + "\n"
    line += "        outVal1 = fwd_polyFromBUs[1].read();" + "\n"
    line += "        polyBuf0[outLeftIdx] = outVal0;" + "\n"
    line += "        polyBuf0[outRightIdx] = outVal1;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "        outVal0 = inv_polyFromBUs[0].read();" + "\n"
    line += "        outVal1 = inv_polyFromBUs[1].read();" + "\n"
    line += "        polyBuf0[outLeftIdx] = outVal0;" + "\n"
    line += "        polyBuf0[outRightIdx] = outVal1;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void BufModule_comp(tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                                tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                                tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                                tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                                bool                    direction," + "\n"
    line += "                                VAR_TYPE_32             iter," + "\n"
    line += "                                WORD                    polyBuf0[N/NUM_BU]," + "\n"
    line += "                                WORD                    polyBuf1[N/NUM_BU]," + "\n"
    line += "                                VAR_TYPE_32             beta){" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "  VAR_TYPE_8 buffTrack = 0;" + "\n"
    line += "" + "\n"
    line += "  //compute data" + "\n"
    line += "  BUF_COMP:for (; (buffTrack<logN); buffTrack++) {" + "\n"
    line += "    if(buffTrack%2){" + "\n"
    line += "      BufModule_comp_stage_polySend(fwd_PolyToBUs, inv_PolyToBUs, direction, polyBuf1, beta);" + "\n"
    line += "      BufModule_comp_stage_polyReceive(fwd_polyFromBUs, inv_polyFromBUs, direction, polyBuf0, beta);" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      BufModule_comp_stage_polySend(fwd_PolyToBUs, inv_PolyToBUs, direction, polyBuf0, beta);" + "\n"
    line += "      BufModule_comp_stage_polyReceive(fwd_polyFromBUs, inv_polyFromBUs, direction, polyBuf1, beta);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line


# Common functions with the support for double buffering
def polyBuf_load_store_wiDB_common_function_gen():
    line = ""
    line += "void BufModule_poly_load_store_wiFW(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                           tapa::ostream<WORD>&    outPolyToNextBuf," + "\n"
    line += "                           WORD                    polyBuf[N/NUM_BU]," + "\n"
    line += "                           VAR_TYPE_32             loadStoreDataLoopCounter," + "\n"
    line += "                           VAR_TYPE_32             loadStoreThisBufDataEnd," + "\n"
    line += "                           tapa::istream<WORD>&    inpPolyFromNextBuf," + "\n"
    line += "                           tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                           VAR_TYPE_32             BufIdx){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_32 loadCounter = 0;" + "\n"
    line += "  VAR_TYPE_32 storeCounter = 0;" + "\n"
    line += "  WORD loadReadData;" + "\n"
    line += "  bool loadReadValid=false;" + "\n"
    line += "  VAR_TYPE_32 loadThreshold;" + "\n"
    line += "" + "\n"
    line += "  WORD storeReadData;" + "\n"
    line += "  bool storeReadValid=false;" + "\n"
    line += "" + "\n"
    line += "  //Load data" + "\n"
    line += "  BUF_LOAD_STORE_POLY:for(; ((loadCounter<loadStoreDataLoopCounter)); ){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "    if( storeReadValid && (outPolyToStore.try_write(storeReadData)) ){" + "\n"
    line += "      storeCounter++;" + "\n"
    line += "      storeReadValid = false;" + "\n"
    line += "    }" + "\n"
    line += "    " + "\n"
    line += "    if( (storeCounter<loadStoreThisBufDataEnd) ){" + "\n"
    line += "      storeReadData = polyBuf[storeCounter];" + "\n"
    line += "      storeReadValid = true;" + "\n"
    line += "    }" + "\n"
    line += "    else if ( (!storeReadValid) && (storeCounter<loadStoreDataLoopCounter) && inpPolyFromNextBuf.try_read(storeReadData) ){" + "\n"
    line += "      storeReadValid = true;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    if( (!loadReadValid) && (loadCounter<storeCounter) && (inpPolyFromLoad.try_read(loadReadData)) ){" + "\n"
    line += "      loadReadValid = true;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    if( loadReadValid && (loadCounter<loadStoreThisBufDataEnd) ){" + "\n"
    line += "      polyBuf[loadCounter] = loadReadData;" + "\n"
    line += "      loadReadValid = false;" + "\n"
    line += "      loadCounter++;" + "\n"
    line += "    }" + "\n"
    line += "    else if( loadReadValid && (outPolyToNextBuf.try_write(loadReadData)) ){" + "\n"
    line += "      loadReadValid = false;" + "\n"
    line += "      loadCounter++;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void BufModule_poly_load_store_woFW(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                           WORD                    polyBuf[N/NUM_BU]," + "\n"
    line += "                           VAR_TYPE_32             loadStoreDataLoopCounter," + "\n"
    line += "                           VAR_TYPE_32             loadStoreThisBufDataEnd," + "\n"
    line += "                           tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                           VAR_TYPE_32             BufIdx){" + "\n"
    line += "  " + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_32 loadCounter = 0;" + "\n"
    line += "  VAR_TYPE_32 storeCounter=0;" + "\n"
    line += "  WORD loadReadData;" + "\n"
    line += "" + "\n"
    line += "  WORD storeReadData;" + "\n"
    line += "  bool storeReadValid=false;" + "\n"
    line += "" + "\n"
    line += "  //Load data" + "\n"
    line += "  BUF_LOAD_POLY:for(; ((loadCounter<loadStoreDataLoopCounter)); ){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "    if( storeReadValid && (outPolyToStore.try_write(storeReadData)) ){" + "\n"
    line += "      storeCounter++;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    if( (storeCounter<loadStoreThisBufDataEnd) ){" + "\n"
    line += "      storeReadData = polyBuf[storeCounter];" + "\n"
    line += "      storeReadValid = true;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      storeReadValid = false;" + "\n"
    line += "    }" + "\n"
    line += "    " + "\n"
    line += "    if( (loadCounter<storeCounter) && (inpPolyFromLoad.try_read(loadReadData)) ){" + "\n"
    line += "      polyBuf[loadCounter] = loadReadData;" + "\n"
    line += "      loadCounter++;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    return line

# Common functions without the support for double buffering
def polyBuf_load_store_woDB_common_function_gen():
    line = ""

    line += "void BufModule_poly_load_wiFW(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                           tapa::ostream<WORD>&    outPolyToNextBuf," + "\n"
    line += "                           WORD                    polyBuf[N/NUM_BU]," + "\n"
    line += "                           VAR_TYPE_32             loadStoreDataLoopCounter," + "\n"
    line += "                           VAR_TYPE_32             loadStoreThisBufDataEnd," + "\n"
    line += "                           VAR_TYPE_32             BufIdx){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_32 loadCounter = 0;" + "\n"
    line += "" + "\n"
    line += "  //Load data" + "\n"
    line += "  BUF_LOAD_STORE_POLY:for(; ((loadCounter<loadStoreDataLoopCounter)); loadCounter++){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "    WORD loadReadData = inpPolyFromLoad.read();" + "\n"
    line += "" + "\n"
    line += "    if( loadCounter<loadStoreThisBufDataEnd ){" + "\n"
    line += "      polyBuf[loadCounter] = loadReadData;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      outPolyToNextBuf.write(loadReadData);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void BufModule_poly_store_wiFW(WORD                    polyBuf[N/NUM_BU]," + "\n"
    line += "                           VAR_TYPE_32             loadStoreDataLoopCounter," + "\n"
    line += "                           VAR_TYPE_32             loadStoreThisBufDataEnd," + "\n"
    line += "                           tapa::istream<WORD>&    inpPolyFromNextBuf," + "\n"
    line += "                           tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                           VAR_TYPE_32             BufIdx){" + "\n"
    line += "" + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_32 storeCounter = 0;" + "\n"
    line += "" + "\n"
    line += "  WORD storeReadData;" + "\n"
    line += "  bool storeReadValid=false;" + "\n"
    line += "" + "\n"
    line += "  //Store data" + "\n"
    line += "  BUF_LOAD_STORE_POLY:for(; ((storeCounter<loadStoreDataLoopCounter)); ){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "    if( storeReadValid && (outPolyToStore.try_write(storeReadData)) ){" + "\n"
    line += "      storeCounter++;" + "\n"
    line += "      storeReadValid = false;" + "\n"
    line += "    }" + "\n"
    line += "    " + "\n"
    line += "    if( (storeCounter<loadStoreThisBufDataEnd) ){" + "\n"
    line += "      storeReadData = polyBuf[storeCounter];" + "\n"
    line += "      storeReadValid = true;" + "\n"
    line += "    }" + "\n"
    line += "    else if ( (!storeReadValid) && (inpPolyFromNextBuf.try_read(storeReadData)) ){" + "\n"
    line += "      storeReadValid = true;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void BufModule_poly_load_woFW(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                           WORD                    polyBuf[N/NUM_BU]," + "\n"
    line += "                           VAR_TYPE_32             loadStoreDataLoopCounter," + "\n"
    line += "                           VAR_TYPE_32             loadStoreThisBufDataEnd," + "\n"
    line += "                           VAR_TYPE_32             BufIdx){" + "\n"
    line += "  " + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_32 loadCounter = 0;" + "\n"
    line += "" + "\n"
    line += "  //Load data" + "\n"
    line += "  BUF_LOAD_POLY:for(; ((loadCounter<loadStoreDataLoopCounter)); loadCounter++){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "    WORD loadReadData = inpPolyFromLoad.read();" + "\n"
    line += "    polyBuf[loadCounter] = loadReadData;" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void BufModule_poly_store_woFW(WORD                    polyBuf[N/NUM_BU]," + "\n"
    line += "                           VAR_TYPE_32             loadStoreDataLoopCounter," + "\n"
    line += "                           VAR_TYPE_32             loadStoreThisBufDataEnd," + "\n"
    line += "                           tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                           VAR_TYPE_32             BufIdx){" + "\n"
    line += "  " + "\n"
    line += "  #pragma HLS inline off" + "\n"
    line += "" + "\n"
    line += "  VAR_TYPE_32 storeCounter=0;" + "\n"
    line += "" + "\n"
    line += "  WORD storeReadData;" + "\n"
    line += "  bool storeReadValid=false;" + "\n"
    line += "" + "\n"
    line += "  //Load data" + "\n"
    line += "  BUF_LOAD_POLY:for(; ((storeCounter<loadStoreDataLoopCounter)); ){" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "    if( storeReadValid && (outPolyToStore.try_write(storeReadData)) ){" + "\n"
    line += "      storeCounter++;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    if( (storeCounter<loadStoreThisBufDataEnd) ){" + "\n"
    line += "      storeReadData = polyBuf[storeCounter];" + "\n"
    line += "      storeReadValid = true;" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      storeReadValid = false;" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def polyBuf_common_function_gen(designParamsVar):

    line  = ""

    line += polyBuf_compute_common_function_gen()

    if(designParamsVar.DOUBLE_BUF_EN):
        line += polyBuf_load_store_wiDB_common_function_gen()
    else:
        line += polyBuf_load_store_woDB_common_function_gen()

    return line

# This is the content of Buffer only with polynomail handling with forwarding and with support for double buffering
def genBufModule_wiFW_wiDB_even(BufModuleParamsVar):
    line = ""
    line += "void BufModule_wiFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToNextBuf," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::istream<WORD>&    inpPolyFromNextBuf," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[2][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "    WORD polyBuf2[N/NUM_BU];" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf2 type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%2], polyBuf2, beta);" + "\n"
    line += "      BufModule_poly_load_store_wiFW(inpPolyFromLoad, outPolyToNextBuf, polyBuf[(iterCount+1)%2], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, inpPolyFromNextBuf, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

# This is the content of Buffer only with polynomail handling with forwarding and without support for double buffering
def genBufModule_wiFW_woDB_even(BufModuleParamsVar):
    line = ""
    line += "void BufModule_wiFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToNextBuf," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::istream<WORD>&    inpPolyFromNextBuf," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[2][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter; iterCount++){" + "\n"
    line += "      BufModule_poly_load_wiFW(inpPolyFromLoad, outPolyToNextBuf, polyBuf[0], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, BufIdx);" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[0], polyBuf[1], beta);" + "\n"
    line += "      BufModule_poly_store_wiFW(polyBuf[0], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, inpPolyFromNextBuf, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer only with polynomial handling without forwarding and support for double buffering
def genBufModule_woFW_wiDB_even(BufModuleParamsVar):
    line = ""
    line += "void BufModule_woFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[2][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "    WORD polyBuf2[N/NUM_BU];" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf2 type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%2], polyBuf2, beta);" + "\n"
    line += "      BufModule_poly_load_store_woFW(inpPolyFromLoad, polyBuf[(iterCount+1)%2], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer only with polynomial handling without forwarding and without support for double buffering
def genBufModule_woFW_woDB_even(BufModuleParamsVar):
    line = ""
    line += "void BufModule_woFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[2][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter; iterCount++){" + "\n"
    line += "      BufModule_poly_load_woFW(inpPolyFromLoad, polyBuf[0], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, BufIdx);" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[0], polyBuf[1], beta);" + "\n"
    line += "      BufModule_poly_store_woFW(polyBuf[0], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer only with polynomail handling with forwarding and with support for double buffering
def genBufModule_wiFW_wiDB_odd(BufModuleParamsVar):
    line = ""
    line += "void BufModule_wiFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToNextBuf," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::istream<WORD>&    inpPolyFromNextBuf," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[3][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%3], polyBuf[(iterCount+2)%3], beta);" + "\n"
    line += "      BufModule_poly_load_store_wiFW(inpPolyFromLoad, outPolyToNextBuf, polyBuf[(iterCount+1)%3], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, inpPolyFromNextBuf, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer only with polynomail handling with forwarding and with support for double buffering
def genBufModule_wiFW_woDB_odd(BufModuleParamsVar):
    line = ""
    line += "void BufModule_wiFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToNextBuf," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::istream<WORD>&    inpPolyFromNextBuf," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[2][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter; iterCount++){" + "\n"
    line += "      BufModule_poly_load_wiFW(inpPolyFromLoad, outPolyToNextBuf, polyBuf[0], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, BufIdx);" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[0], polyBuf[1], beta);" + "\n"
    line += "      BufModule_poly_store_wiFW(polyBuf[1], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, inpPolyFromNextBuf, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer only with polynomail handling without forwarding and with support for double buffering
def genBufModule_woFW_wiDB_odd(BufModuleParamsVar):
    line = ""
    line += "void BufModule_woFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[3][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter+2; iterCount++){" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[iterCount%3], polyBuf[(iterCount+2)%3], beta);" + "\n"
    line += "      BufModule_poly_load_store_woFW(inpPolyFromLoad, polyBuf[(iterCount+1)%3], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#This is the content of Buffer only with polynomail handling without forwarding and without support for double buffering
def genBufModule_woFW_woDB_odd(BufModuleParamsVar):
    line = ""
    line += "void BufModule_woFW_" + str(BufModuleParamsVar.BUFIDX0) + "(tapa::istream<WORD>&    inpPolyFromLoad," + "\n"
    line += "                      tapa::istreams<WORD,2>& fwd_polyFromBUs," + "\n"
    line += "                      tapa::istreams<WORD,2>& inv_polyFromBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& fwd_PolyToBUs," + "\n"
    line += "                      tapa::ostreams<WORD,2>& inv_PolyToBUs," + "\n"
    line += "                      tapa::ostream<WORD>&    outPolyToStore," + "\n"
    line += "                      bool                    direction," + "\n"
    line += "                      VAR_TYPE_8              iter," + "\n"
    line += "                      VAR_TYPE_32             BufIdx" + "\n"
    line += "                    ) {" + "\n"
    line += "" + "\n"
    line += "    //==== Auto generated variables start ====//" + "\n"
    line += "    const BETA_WORD BETA = " + str(BufModuleParamsVar.BETA) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_DATA_LOOP_COUNTER = " + str(BufModuleParamsVar.LOAD_STORE_DATA_LOOP_COUNTER) + "; " + "\n"
    line += "    const VAR_TYPE_32 LOAD_STORE_THIS_BUF_DATA_END = " + str(BufModuleParamsVar.LOAD_STORE_THIS_BUF_DATA_END) + ";" + "\n"
    line += "    //==== Auto generated variables end ====//" + "\n"
    line += "    " + "\n"
    line += "    WORD polyBuf[2][N/NUM_BU];" + "\n"
    line += "    #pragma HLS array_partition variable=polyBuf type=complete  dim=1" + "\n"
    line += "    #pragma HLS bind_storage variable = polyBuf type = RAM_T2P impl = bram latency=1" + "\n"
    line += "" + "\n"
    line += "    const BETA_WORD beta = BETA;" + "\n"
    line += "" + "\n"
    line += "    const VAR_TYPE_32 loadStoreDataLoopCounter = LOAD_STORE_DATA_LOOP_COUNTER; " + "\n"
    line += "    const VAR_TYPE_32 loadStoreThisBufDataEnd = LOAD_STORE_THIS_BUF_DATA_END;" + "\n"
    line += "" + "\n"
    line += "    ITER_LOOP:for(VAR_TYPE_8 iterCount=0; iterCount<iter; iterCount++){" + "\n"
    line += "      BufModule_poly_load_woFW(inpPolyFromLoad, polyBuf[0], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, BufIdx);" + "\n"
    line += "      BufModule_comp(fwd_polyFromBUs, inv_polyFromBUs, fwd_PolyToBUs, inv_PolyToBUs, direction, iter, polyBuf[0], polyBuf[1], beta);" + "\n"
    line += "      BufModule_poly_store_woFW(polyBuf[1], loadStoreDataLoopCounter, loadStoreThisBufDataEnd, outPolyToStore, BufIdx);" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line

#Calculate load store trip count
def load_store_trip_count_calculate(BufIdx, designParamsVar):
    POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    NUM_BUF_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_BUF_PER_PARA_LIMB_POLY_PORT
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT
    POLY_SIZE = designParamsVar.POLY_SIZE
    NUM_BU = designParamsVar.NUM_BU

    result = (NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT - (((BufIdx)%NUM_BUF_PER_PARA_LIMB_POLY_PORT)//POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT)) * (POLY_SIZE//NUM_BU)

    return result

#calculate when this buffer poly loading ends
def poly_load_store_end_calculate(designParamsVar):
    POLY_SIZE = designParamsVar.POLY_SIZE
    NUM_BU = designParamsVar.NUM_BU

    result = (POLY_SIZE//NUM_BU)

    return result

def gen_poly_buffer_tasks(designParamsVar):

    bufParamsVar = designParamsVar.bufParamsVar

    logN = designParamsVar.logN

    POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    NUM_BUF_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_BUF_PER_PARA_LIMB_POLY_PORT
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT

    NUM_BU = designParamsVar.NUM_BU
    
    beta = designParamsVar.beta

    code = ""

    #generate BufModule wrappers
    for BufIdx in range(NUM_BU): # TODO: Some definitions can be shared among different buffers. Later to optimize.

        bufParamsVar.BUFIDX0 = BufIdx

        bufParamsVar.BETA = beta

        polyDdrPortId = ((BufIdx)//NUM_BUF_PER_PARA_LIMB_POLY_PORT) 
        polyChainBroadcastingId = (((BufIdx)%NUM_BUF_PER_PARA_LIMB_POLY_PORT)//POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT) 

        #Calculate load store trip count
        bufParamsVar.LOAD_STORE_DATA_LOOP_COUNTER = load_store_trip_count_calculate(BufIdx, designParamsVar)

        #calculate when this buffer poly. loading ends
        bufParamsVar.LOAD_STORE_THIS_BUF_DATA_END = poly_load_store_end_calculate(designParamsVar)

        if (polyChainBroadcastingId==(NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT-1) ):   #no forwarding
            if(designParamsVar.DOUBLE_BUF_EN):
                if(logN%2==0):
                    code += genBufModule_woFW_wiDB_even(bufParamsVar)
                else:
                    code += genBufModule_woFW_wiDB_odd(bufParamsVar)
                code += "\n"
            else:
                if(logN%2==0):
                    code += genBufModule_woFW_woDB_even(bufParamsVar)
                else:
                    code += genBufModule_woFW_woDB_odd(bufParamsVar)
                code += "\n"
        else: #forwarding
            if(designParamsVar.DOUBLE_BUF_EN):
                if(logN%2==0):
                    code += genBufModule_wiFW_wiDB_even(bufParamsVar)
                else:
                    code += genBufModule_wiFW_wiDB_odd(bufParamsVar)
                code += "\n"
            else:
                if(logN%2==0):
                    code += genBufModule_wiFW_woDB_even(bufParamsVar)
                else:
                    code += genBufModule_wiFW_woDB_odd(bufParamsVar)
                code += "\n"

    return code

def gen_poly_buffers(designParamsVar):
    
    code = ""

    # generate supporting functions
    code += polyBuf_common_function_gen(designParamsVar)
    code += "\n"

    # generate TF buffer tasks
    code += gen_poly_buffer_tasks(designParamsVar)
    code += "\n"

    return code