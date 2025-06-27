from code_generators.modmul.config import modmul_header_args

def gen_set_of_FIFOs(name, type, fifo_arr_size, fifo_depth, set_size):
    # TODO: check if args are not empty.
    line = ""
    for idx in range(set_size):
        if(fifo_depth==""):
            line += "    tapa::streams<" + str(type) + ", " + str(fifo_arr_size) + "> " + str(name) + str(idx) + "(\"" + str(name) + "" + str(idx) + "_stream\");" + "\n"
        else:
            line += "    tapa::streams<" + str(type) + ", " + str(fifo_arr_size) + ", " + str(fifo_depth) + "> " + str(name) + str(idx) + "(\"" + str(name) + "" + str(idx) + "_stream\");" + "\n"
    return line

# FIFOs between polynomail load (Mmap2Stream_poly) and buffers
def polyLoad_and_polyBuf_FIFOs(designParamsVar):
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    for port_idx in range(POLY_LS_PORTS_PER_PARA_LIMB):
        num_of_streams_per_load = "POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT"
        FIFO_name = "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G" + str(port_idx) + "_"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_load, "", NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)
        line += "\n"

    return line

# FIFOs between polyBuf and BU
def polyBuf_and_BU_FIFOs(designParamsVar):

    NUM_BU = designParamsVar.NUM_BU
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    num_of_streams_per_buf = "2"
    FIFO_name = "fwd_polyBuf_to_BU_L" + str(para_limb_idx) + "_"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_buf, "BU_BUF_FIFO_DEPTH", NUM_BU)
    line += "\n"

    num_of_streams_per_buf = "2"
    FIFO_name = "inv_polyBuf_to_BU_L" + str(para_limb_idx) + "_"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_buf, "BU_BUF_FIFO_DEPTH", NUM_BU)
    line += "\n"

    return line

# FIFOs between BU and polyBuf
def BU_and_polyBuf_FIFOs(designParamsVar):

    NUM_BU = designParamsVar.NUM_BU
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    num_of_streams_per_buf = "2"
    FIFO_name = "fwd_BU_to_polyBuf_L" + str(para_limb_idx) + "_"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_buf, "BU_BUF_FIFO_DEPTH", NUM_BU)
    line += "\n"

    num_of_streams_per_buf = "2"
    FIFO_name = "inv_BU_to_polyBuf_L" + str(para_limb_idx) + "_"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_buf, "BU_BUF_FIFO_DEPTH", NUM_BU)
    line += "\n"

    return line

# FIFOs between buffers and polynomail store (Stream2Mmap_poly)
def polyBuf_and_polyStore_FIFOs(designParamsVar):
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""

    for port_idx in range(POLY_LS_PORTS_PER_PARA_LIMB):
        num_of_streams_per_load = "POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT"
        FIFO_name = "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G" + str(port_idx) + "_"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_load, "", NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)
        line += "\n"

    return line

def gen_poly_FIFOs(designParamsVar):
    line = ""
    
    # FIFOs between polynomial load and polyBuf
    line += polyLoad_and_polyBuf_FIFOs(designParamsVar)

    # FIFOs between polyBuf and BU
    line += polyBuf_and_BU_FIFOs(designParamsVar)

    # FIFOs between BU and polyBuf
    line += BU_and_polyBuf_FIFOs(designParamsVar)

    # FIFOs between polyBuf and polynomial store
    line += polyBuf_and_polyStore_FIFOs(designParamsVar)

    return line

# FIFOs between TF load (Mmap2Stream_tf) and TFBuf
def loadTF_and_TFBuf_FIFOs(designParamsVar):
    TF_PORTS_PER_PARA_LIMB = designParamsVar.TF_PORTS_PER_PARA_LIMB
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""

    for port_idx in range(TF_PORTS_PER_PARA_LIMB):
        num_of_streams_per_load = "TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT"
        FIFO_name = "tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(port_idx) + "_"
        line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_load, "", NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT)
        line += "\n"
    return line

# FIFOs between TFBuf and BUs
def TFBuf_and_BU_FIFOs(designParamsVar):
    
    num_of_TFBufs = designParamsVar.NUM_BU//2
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""

    num_of_streams_per_buf = "2"
    FIFO_name = "tfBuf_to_BU_L" + str(para_limb_idx) + "_"
    line += gen_set_of_FIFOs(FIFO_name, "WORD", num_of_streams_per_buf, "BU_BUF_FIFO_DEPTH", num_of_TFBufs)
    line += "\n"

    return line

def gen_TF_FIFOs(designParamsVar):
    line = ""
    
    # FIFOs between mmap2Stram_tf and TFBuf
    line += loadTF_and_TFBuf_FIFOs(designParamsVar)
    
    # FIFOs between TFBuf and BUs
    line += TFBuf_and_BU_FIFOs(designParamsVar)

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