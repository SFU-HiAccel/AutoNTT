from code_generators.hybrid.flow_controllers.dual_interface_FIFO import gen_dual_interface_FIFO_split_logic

def gen_set_of_FIFOs(name, type, fifo_arr_size, fifo_depth, set_size):
    # TODO: check if args are not empty.
    line = ""
    for idx in range(set_size):
        if(fifo_depth==""):
            line += "    tapa::streams<" + str(type) + ", " + str(fifo_arr_size) + "> " + str(name) + str(idx) + "(\"" + str(name) + "" + str(idx) + "_stream\");" + "\n"
        else:
            line += "    tapa::streams<" + str(type) + ", " + str(fifo_arr_size) + ", " + str(fifo_depth) + "> " + str(name) + str(idx) + "(\"" + str(name) + "" + str(idx) + "_stream\");" + "\n"
    return line

# FIFOs between fwd_load_inv_store and DIF
def fwdLoadInvStore_and_DIF_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    BUG_per_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    #deciding number of streams coming from/going to the task similar to the condition in poly_load_store/poly_load_store.py
    if( (BUG_per_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ):  # if this is the case, that means data coming from one port is supporting only one BUG. i.e., either multiple ports have to support the streams required for entire BUG or have to do sequentially 
        num_streams_per_BUG = "POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT"
        num_of_stream_groups_per_BUG = (2*designParamsVar.V_BUG_SIZE) // designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
        for BUG_idx in range (num_of_BUGs):
            FIFO_name = "fwd_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_stream_groups_per_BUG)
            line += "\n"
            
            FIFO_name = "inv_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_stream_groups_per_BUG)
            line += "\n"

    else: # if this is the case, that means one port is supporting many BUGs. Hence, can support all the streams of one BUG for sure.
        num_streams_per_BUG = "2*V_BUG_SIZE"
        FIFO_name = "fwd_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_BUGs)
        line += "\n"
        
        FIFO_name = "inv_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_BUGs)
        line += "\n"

    return line

# FIFOs with DIF on the FWD input side
# Only need if split DIF is used.
def inDIF_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    is_split_FIFO = gen_dual_interface_FIFO_split_logic(designParamsVar)
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    if(is_split_FIFO):
        FIFO_name = "poly_inFIFO_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "LS_FIFO_BUF_SIZE", num_of_BUGs)
        line += "\n"

    return line

# FIFOs between DIF and input_selector
def DIF_and_inSel_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    FIFO_name = "fwd_poly_DIF_to_inSel_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    
    FIFO_name = "inv_poly_inSel_to_DIF_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    return line

# FIFOs between input_selector and BUG
def inSel_and_BUG_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    FIFO_name = "fwd_poly_inSel_to_BUG_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    
    FIFO_name = "inv_poly_BUG_to_inSel_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    return line

# FIFOs within BUG layers
def BUG_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    num_of_horizontal_layers = designParamsVar.H_BUG_SIZE
    para_limb_idx = designParamsVar.para_limb_idx


    line = ""
    for layer_idx in range(num_of_horizontal_layers-1):
        #FWD FIFOs
        FIFO_name = "fwd_poly_H" + str(layer_idx) + "_to_H" + str(layer_idx+1) + "_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"

        #INV FIFOs
        FIFO_name = "inv_poly_H" + str(layer_idx+1) + "_to_H" + str(layer_idx) + "_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
    return line

# FIFOs between BUG and output_selector
def BUG_and_outSel_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    FIFO_name = "fwd_poly_BUG_to_outSel_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"

    FIFO_name = "inv_poly_outSel_to_BUG_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    return line

# FIFOs connecting tasks in shuffler
def shuffler_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    is_split_shuffler, is_inter_BUG_connections = designParamsVar.IS_SPLIT_SHUFFLER, designParamsVar.IS_INTER_BUG_CONNECTIONS
    num_of_inter_BUG_comm = designParamsVar.NUM_INTER_BUG_COM
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    if (is_split_shuffler):
        # FIFOs between output_selector and shuffler_in
        FIFO_name = "fwd_poly_outSel_to_shufIn_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_shufIn_to_outSel_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"

        # FIFOs between shuffler_in and shuffler_buf
        FIFO_name = "fwd_poly_shufIn_to_shufBuf_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_shufBuf_to_shufIn_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"

        # FIFOs between shuffler_buf and shuffler_out_shift
        FIFO_name = "fwd_poly_shufBuf_to_shufOutShift_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_shufOutShift_to_shufBuf_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"

        # FIFOs between shuffler_out_shift and shuffler_out_shuff
        for idx in range(num_of_inter_BUG_comm):
            FIFO_name = "fwd_poly_shufOutShift_to_shufOutShuff_inter" + str(idx) + "_L" + str(para_limb_idx) + "_BUG"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
            line += "\n"
            FIFO_name = "inv_poly_shufOutShuff_to_shufOutShift_inter" + str(idx) + "_L" + str(para_limb_idx) + "_BUG"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
            line += "\n"
        FIFO_name = "fwd_poly_shufOutShift_to_shufOutShuff_intra_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_shufOutShuff_to_shufOutShift_intra_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"

    else:
        # FIFOs between output_selector and shuffler 
        FIFO_name = "fwd_poly_outSel_to_shuf_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_shuf_to_outSel_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"

        # FIFOs between shuffler and shuffler_out_split
        FIFO_name = "fwd_poly_shuf_to_shufOutSplit_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_shufOutSplit_to_shuf_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"

        # FIFOs between shuffler_out_split and shuffler_out_shuff_split
        for idx in range(num_of_inter_BUG_comm):
            FIFO_name = "fwd_poly_shufOutSplit_to_shufOutShuff_inter" + str(idx) + "_L" + str(para_limb_idx) + "_BUG"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
            line += "\n"
            FIFO_name = "inv_poly_shufOutShuff_to_shufOutSplit_inter" + str(idx) + "_L" + str(para_limb_idx) + "_BUG"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
            line += "\n"
        FIFO_name = "fwd_poly_shufOutSplit_to_shufOutShuff_intra_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_shufOutShuff_to_shufOutSplit_intra_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
        line += "\n"
    
    #FIFOs between shuffler_out_shuff and input_selector
    FIFO_name = "fwd_poly_shufOutShuff_to_inSel_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    FIFO_name = "inv_poly_inSel_to_shufOutShuff_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"

    return line

# FIFOs between output_selector and DIF
def outSel_and_DIF_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    FIFO_name = "fwd_poly_outSel_to_DIF_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    
    FIFO_name = "inv_poly_DIF_to_outSel_L" + str(para_limb_idx) + "_BUG"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "", num_of_BUGs)
    line += "\n"
    return line

# FIFOs with DIF on the FWD output side
# Only need if split DIF is used.
def outDIF_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    is_split_FIFO = gen_dual_interface_FIFO_split_logic(designParamsVar)
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    if(is_split_FIFO):
        FIFO_name = "poly_outFIFO_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "2*V_BUG_SIZE", "LS_FIFO_BUF_SIZE", num_of_BUGs)
        line += "\n"

    return line

# FIFOs between DIF and fwd_store_inv_load
def DIF_and_fwdStoreInvLoad_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    BUG_per_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""

    #deciding number of streams coming from/going to the task similar to the condition in poly_load_store/poly_load_store.py
    if( (BUG_per_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ):  # if this is the case, that means one port is supporting only one BUG. i.e., either multiple ports have to support the streams required for entire BUG or have to do sequentially 
        num_streams_per_BUG = "POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT"
        num_of_stream_groups_per_BUG = (2*designParamsVar.V_BUG_SIZE) // designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
        for BUG_idx in range (num_of_BUGs):
            FIFO_name = "fwd_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_stream_groups_per_BUG)
            line += "\n"
            FIFO_name = "inv_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_"
            line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_stream_groups_per_BUG)
            line += "\n"

    else: # if this is the case, that means one port is supporting many BUGs. Hence, can support all the streams of one BUG for sure.
        num_streams_per_BUG = "2*V_BUG_SIZE"
        FIFO_name = "fwd_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_BUGs)
        line += "\n"
        FIFO_name = "inv_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", num_streams_per_BUG, "", num_of_BUGs)
        line += "\n"

    return line

def gen_poly_FIFOs(designParamsVar):
    line = ""
    
    # FIFOs between fwdLoadInvStore and DIF
    line += fwdLoadInvStore_and_DIF_FIFOs(designParamsVar)

    # FIFOs inside DIF from the FWD input side
    line += inDIF_FIFOs(designParamsVar)

    # FIFOs between DIF and input_selector
    line += DIF_and_inSel_FIFOs(designParamsVar)

    # FIFOs between input_selector and BUG
    line += inSel_and_BUG_FIFOs(designParamsVar)

    # FIFOs within BUG layers
    line += BUG_FIFOs(designParamsVar)

    # FIFOs between BUG and output_selector
    line += BUG_and_outSel_FIFOs(designParamsVar)

    # FIFOs connecting tasks in shuffler
    line += shuffler_FIFOs(designParamsVar)

    # FIFOs between output_selector and DIF
    line += outSel_and_DIF_FIFOs(designParamsVar)

    # FIFOs inside DIF from the FWD output side
    line += outDIF_FIFOs(designParamsVar)

    # FIFOs between DIF and fwd_store_inv_load
    line += DIF_and_fwdStoreInvLoad_FIFOs(designParamsVar)

    return line

# FIFOs between TFBuf and BUGs
def loadTF_and_TFBuf_FIFOs(designParamsVar):
    TFBuffersParamsVar = designParamsVar.TFBuffersParamsVar
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""

    for h_seg_id in range(designParamsVar.TF_LOAD_H_SEGS_PER_PARA_LIMB):
        for v_seg_id in range(designParamsVar.TF_LOAD_V_SEGS_PER_PARA_LIMB):
            layers_in_seg = TFBuffersParamsVar.layers_per_seg[h_seg_id]

            TF_grpup_id = h_seg_id*(designParamsVar.TF_LOAD_V_SEGS_PER_PARA_LIMB) + v_seg_id
            FIFO_name = "tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_grpup_id) + "_"

            line += gen_set_of_FIFOs(FIFO_name, "DWORD", "TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2", "", layers_in_seg)
            line += "\n"
    return line

# FIFOs between TFBuf and BUG
def TFBuf_and_BUG_FIFOs(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    h_BUG_size = designParamsVar.H_BUG_SIZE
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    for BUG_idx in range(num_of_BUGs):
        FIFO_name = "tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", "V_BUG_SIZE", "", h_BUG_size)
        line += "\n"

    return line

def gen_TF_FIFOs(designParamsVar):
    line = ""
    
    # FIFOs between mmap2Stram_tf and TFBuf
    line += loadTF_and_TFBuf_FIFOs(designParamsVar)

    # FIFOs between TFBuf and BUG
    line += TFBuf_and_BUG_FIFOs(designParamsVar)

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