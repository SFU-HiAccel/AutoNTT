def shuffler_and_BU_FIFOs(designParamsVar):
    mmap_count = designParamsVar.mmap_count
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""
    
    # Step 3: Stream duplications
    line += "    // Forward and Inverse Shuffler streams\n"
    if mmap_count == 1:  # only 1 polyVectorIn_G in HBM
        for i in range(0, PARTIAL_COUNT):
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> fwd_shuffler_to_BU_L{para_limb_idx}_{i}(\"fwd_shuffler_to_BU_L{para_limb_idx}_{i}\");\n"
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> inv_shuffler_to_BU_L{para_limb_idx}_{i}(\"inv_shuffler_to_BU_L{para_limb_idx}_{i}\");\n"
    else:
        for i in range(mmap_count):  # delete load_poly
            line += f"    tapa::streams<WORD, HBM_PORT_SIZE, FIFO_DEPTH> fwd_shuffler_to_BU_L{para_limb_idx}_0_{i}(\"fwd_shuffler_to_BU_L{para_limb_idx}_0_{i}\");\n"
            line += f"    tapa::streams<WORD, HBM_PORT_SIZE, FIFO_DEPTH> inv_shuffler_to_BU_L{para_limb_idx}_0_{i}(\"inv_shuffler_to_BU_L{para_limb_idx}_0_{i}\");\n"
        for i in range(1, PARTIAL_COUNT):
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> fwd_shuffler_to_BU_L{para_limb_idx}_{i}(\"fwd_shuffler_to_BU_L{para_limb_idx}_{i}\");\n"
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> inv_shuffler_to_BU_L{para_limb_idx}_{i}(\"inv_shuffler_to_BU_L{para_limb_idx}_{i}\");\n"
    
    return line

def BU_and_shuffler_FIFOs(designParamsVar):
    mmap_count = designParamsVar.mmap_count
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    line += "\n    // BU to Shuffler streams\n"
    if mmap_count == 1:  # only 1 polyVectorOut_G in HBM
        for i in range(0, PARTIAL_COUNT):
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> fwd_BU_to_shuffler_L{para_limb_idx}_{i}(\"fwd_BU_to_shuffler_L{para_limb_idx}_{i}\");\n"
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> inv_BU_to_shuffler_L{para_limb_idx}_{i}(\"inv_BU_to_shuffler_L{para_limb_idx}_{i}\");\n"
    else:
        for i in range(PARTIAL_COUNT-1):
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> fwd_BU_to_shuffler_L{para_limb_idx}_{i}(\"fwd_BU_to_shuffler_L{para_limb_idx}_{i}\");\n"
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> inv_BU_to_shuffler_L{para_limb_idx}_{i}(\"inv_BU_to_shuffler_L{para_limb_idx}_{i}\");\n"
        for i in range(mmap_count):  # delete store_poly
            line += f"    tapa::streams<WORD, HBM_PORT_SIZE, FIFO_DEPTH> fwd_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1}_{i}(\"fwd_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1}_{i}\");\n"
            line += f"    tapa::streams<WORD, HBM_PORT_SIZE, FIFO_DEPTH> inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1}_{i}(\"inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1}_{i}\");\n"

    return line

def splitShuffler_FIFOs(designParamsVar):
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    check_spilt = designParamsVar.check_spilt
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    
    for i in range(PARTIAL_COUNT - 1):  # shuffler is less one than BU group
        if check_spilt[i] == True:  # split situation
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> fwd_shufIn_to_shufBuf_L{para_limb_idx}_{i}(\"fwd_shufIn_to_shufBuf_L{para_limb_idx}_{i}\");\n"

    for i in range(PARTIAL_COUNT - 1):  # shuffler is less one than BU group
        if check_spilt[i] == True:  # split situation
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> fwd_shufBuf_to_shufOut_L{para_limb_idx}_{i}(\"fwd_shufBuf_to_shufOut_L{para_limb_idx}_{i}\");\n"

    for i in range(PARTIAL_COUNT - 1):  # shuffler is less one than BU group
        if check_spilt[i] == True:  # split situation
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> inv_shufOut_to_shufBuf_L{para_limb_idx}_{PARTIAL_COUNT-i-2}(\"inv_shufOut_to_shufBuf_L{para_limb_idx}_{PARTIAL_COUNT-i-2}\");\n"

    for i in range(PARTIAL_COUNT - 1):  # shuffler is less one than BU group
        if check_spilt[i] == True:  # split situation
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> inv_shufBuf_to_shufIn_L{para_limb_idx}_{PARTIAL_COUNT-i-2}(\"inv_shufBuf_to_shufIn_L{para_limb_idx}_{PARTIAL_COUNT-i-2}\");\n"
    return line

def BU_FIFOs(designParamsVar):
    H_BU_NUM = designParamsVar.H_BU_NUM
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    para_limb_idx = designParamsVar.para_limb_idx


    line = "\n    // Mid BU streams\n"
    for y in range(PARTIAL_COUNT):
        x_range = LAST_H_BU_NUM if LAST_H_BU_NUM != 0 and y == (PARTIAL_COUNT - 1) else H_BU_NUM
        for x in range(x_range - 1):
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> fwd_midVals_L{para_limb_idx}_{x}_{y}(\"fwd_midVals_L{para_limb_idx}_{x}_{y}\");\n"
            line += f"    tapa::streams<WORD, {CONCAT_FACTOR}, FIFO_DEPTH> inv_midVals_L{para_limb_idx}_{x}_{y}(\"inv_midVals_L{para_limb_idx}_{x}_{y}\");\n"

    return line

def gen_poly_FIFOs(designParamsVar):
    
    mmap_count = designParamsVar.mmap_count
    logN = designParamsVar.logN
    H_BU_NUM = designParamsVar.H_BU_NUM
    V_BU_NUM = designParamsVar.V_BU_NUM
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    check_spilt = designParamsVar.check_spilt
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    partial_group = designParamsVar.partial_group
    
    line = ""
    
    # Step 3: Stream duplications
    line += shuffler_and_BU_FIFOs(designParamsVar)
    line += "\n"

    line += BU_and_shuffler_FIFOs(designParamsVar)
    line += "\n"

    line += splitShuffler_FIFOs(designParamsVar)
    line += "\n"

    line += BU_FIFOs(designParamsVar)
    line += "\n"

    return line

def MM2S_and_loadTF_FIFOs(designParamsVar):
    tf_mmap_count = designParamsVar.tf_mmap_count
    multi_ports_tf_mmap_count = designParamsVar.multi_ports_tf_mmap_count
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    if tf_mmap_count == 1:  # only 1 TFArr_G in HBM
        line += "\n"
        for idx in range(multi_ports_tf_mmap_count):
            line += f"    tapa::stream<TF_WIDE_DATA_PER_PARA_LIMB, FIFO_DEPTH> tf_MM2S_to_loadTF_L{para_limb_idx}_{idx}(\"tf_MM2S_to_loadTF_L{para_limb_idx}_{idx}\");\n"
    else:
        line += "\n"
        for idx in range(multi_ports_tf_mmap_count >> 1):
            line += f"    tapa::streams<TF_WIDE_DATA_PER_PARA_LIMB, TF_PORT_NUM, FIFO_DEPTH> tf_MM2S_to_loadTF_L{para_limb_idx}_{idx}(\"tf_MM2S_to_loadTF_L{para_limb_idx}_{idx}\");\n"
    line += "\n"

    return line

def loadTF_and_TFGen_FIFOs(designParamsVar):
    logN = designParamsVar.logN
    V_BU_NUM = designParamsVar.V_BU_NUM
    para_limb_idx = designParamsVar.para_limb_idx
    line = ""
    
    for i in range(logN):
        line += f"    tapa::streams<WORD, {V_BU_NUM}, TF_FIFO_DEPTH> tf_loadTF_to_TFGen_L{para_limb_idx}_{i}(\"tf_loadTF_to_TFGen_L{para_limb_idx}_{i}\");\n"
        
    return line

def TFGen_and_BU_FIFOs(designParamsVar):
    logN = designParamsVar.logN
    V_BU_NUM = designParamsVar.V_BU_NUM
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""
    
    # FWD
    for i in range(logN):
        line += f"    tapa::streams<WORD, {V_BU_NUM}, FIFO_DEPTH> tf_fwd_TFGen_to_BU_L{para_limb_idx}_{i}(\"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{i}\");\n"

    # INV
    for i in range(logN):
        line += f"    tapa::streams<WORD, {V_BU_NUM}, FIFO_DEPTH> tf_inv_TFGen_to_BU_L{para_limb_idx}_{i}(\"tf_inv_TFGen_to_BU_L{para_limb_idx}_{i}\");\n"
        
    return line

def gen_TF_FIFOs(designParamsVar):
    tf_mmap_count = designParamsVar.tf_mmap_count
    multi_ports_tf_mmap_count = designParamsVar.multi_ports_tf_mmap_count
    logN = designParamsVar.logN
    V_BU_NUM = designParamsVar.V_BU_NUM

    line = ""
    
    line += "\n    // TF streams"
    line += MM2S_and_loadTF_FIFOs(designParamsVar)
    line += "\n"

    line += loadTF_and_TFGen_FIFOs(designParamsVar)
    line += "\n"

    line += TFGen_and_BU_FIFOs(designParamsVar)
    line += "\n"

    return line

def gen_FIFOs(designParamsVar):
    line = ""

    PARA_LIMBS = designParamsVar.PARA_LIMBS

    for para_limb_idx in range(PARA_LIMBS):
        
        designParamsVar.para_limb_idx = para_limb_idx

        line += "    /* Limb" + str(para_limb_idx) + " */" + "\n"
    
        # generate polynomial communication related FIFOs
        line += gen_poly_FIFOs(designParamsVar)

        # generate TF communication related FIFOs
        line += gen_TF_FIFOs(designParamsVar)

    return line