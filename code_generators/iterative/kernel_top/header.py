from code_generators.modmul.config import modmul_header_args

def gen_top_header(designParamsVar):

    PARA_LIMBS = designParamsVar.PARA_LIMBS
    DOUBLE_BUF_EN = designParamsVar.DOUBLE_BUF_EN

    num_poly_ports = designParamsVar.POLY_LS_PORTS
    num_tf_ports = designParamsVar.TF_PORTS


    line = ""
    line += "void NTT_kernel(" + "\n"
    if(DOUBLE_BUF_EN):
        for idx in range(num_poly_ports):
            line += "    tapa::mmap<POLY_WIDE_DATA> polyVectorIn_G" + str(idx) + "," + "\n"
    else:
        for idx in range(num_poly_ports):
            line += "    tapa::mmap<POLY_WIDE_DATA> polyVectorInOut_G" + str(idx) + "," + "\n"
        
    for idx in range(num_tf_ports):
        line += "    tapa::mmap<TF_WIDE_DATA> TFArr_G" + str(idx) + "," + "\n"
    
    if(DOUBLE_BUF_EN):
        for idx in range(num_poly_ports):
            line += "    tapa::mmap<POLY_WIDE_DATA> polyVectorOut_G" + str(idx) + "," + "\n"
    
    for limb_idx in range(PARA_LIMBS):
        line += "    WORD q" + str(limb_idx) + "," + "\n"

    for limb_idx in range(PARA_LIMBS):
        line += "    WORD twoInverse" + str(limb_idx) + "," + "\n"
    
    for limb_idx in range(PARA_LIMBS):
        prefix = "    "
        suffix = str(limb_idx) + ",\n"
        line += modmul_header_args(designParamsVar, prefix, suffix)
    line += "    bool direction," + "\n"
    line += "    VAR_TYPE_16 iter" + "\n"
    line += "    )" + "\n"

    return line