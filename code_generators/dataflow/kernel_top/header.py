from code_generators.modmul.config import modmul_header_args
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

def gen_top_header(designParamsVar):

    
    POLY_LS_PORTS = designParamsVar.POLY_LS_PORTS
    TF_PORTS = designParamsVar.TF_PORTS
    PARA_LIMBS = designParamsVar.PARA_LIMBS
    REDUCTION_TYPE = designParamsVar.REDUCTION_TYPE

    line = "void NTT_kernel(\n"
    for i in range(POLY_LS_PORTS):
        line += f"    tapa::mmap<POLY_WIDE_DATA> polyVectorIn_G{i},\n"
    for i in range(TF_PORTS):
        line += f"    tapa::mmap<TF_WIDE_DATA> TFArr_G{i},\n"
    for i in range(POLY_LS_PORTS):
        line += f"    tapa::mmap<POLY_WIDE_DATA> polyVectorOut_G{i},\n"
    
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