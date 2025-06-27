from code_generators.modmul.config import modmul_header_args
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

def gen_top_header(designParamsVar):

    num_poly_ports = designParamsVar.POLY_LS_PORTS
    num_tf_ports = designParamsVar.TF_PORTS
    PARA_LIMBS = designParamsVar.PARA_LIMBS
    REDUCTION_TYPE = designParamsVar.REDUCTION_TYPE

    line = ""
    line += "void NTT_kernel(" + "\n"
    for idx in range(num_poly_ports):
        line += "    tapa::mmap<POLY_WIDE_DATA> polyVectorInOut_G" + str(idx) + "," + "\n"
    for idx in range(num_tf_ports):
        line += "    tapa::mmap<TF_WIDE_DATA> TFArr_G" + str(idx) + "," + "\n"
    for idx in range(num_poly_ports):
        line += "    tapa::mmap<POLY_WIDE_DATA> polyVectorInOut_G" + str(num_poly_ports+idx) + "," + "\n"
    
    for limb_idx in range(PARA_LIMBS):
        line += "    WORD q" + str(limb_idx) + "," + "\n"

    for limb_idx in range(PARA_LIMBS):
        line += "    WORD twoInverse" + str(limb_idx) + "," + "\n"

    for limb_idx in range(PARA_LIMBS):
        prefix = "    "
        suffix = str(limb_idx) + "," + "\n"
        line += modmul_header_args(designParamsVar, prefix, suffix)

    line += "    bool direction," + "\n"
    line += "    VAR_TYPE_16 iter" + "\n"
    line += "    )" + "\n"

    return line