from code_generators.modmul.config import modmul_header_args
from code_generators.modmul.config import modmul_kernel_funcCall
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

####
# This task is to generate BU based on the different modulo reduction method
####
def gen_BU(designParamsVar):

    REDUCTION_TYPE = designParamsVar.REDUCTION_TYPE

    line = ""
    line += "void BU(" + "\n"
    line += "    tapa::istream<WORD>& fwd_inVal0, tapa::istream<WORD>& fwd_inVal1, " + "\n"
    line += "    tapa::ostream<WORD>& inv_outVal0, tapa::ostream<WORD>& inv_outVal1," + "\n"
    line += "    tapa::istream<WORD>& fwd_inTf," + "\n"
    line += "    tapa::istream<WORD>& inv_inTf," + "\n"
    line += "    tapa::ostream<WORD>& fwd_outVal0, tapa::ostream<WORD>& fwd_outVal1," + "\n"
    line += "    tapa::istream<WORD>& inv_inVal0, tapa::istream<WORD>& inv_inVal1, " + "\n"
    line += "    WORD q," + "\n"
    line += "    WORD twoInverse," + "\n"
    
    prefix = "    "
    suffix = "," + "\n"
    line += modmul_header_args(designParamsVar, prefix, suffix)
        
    line += "    VAR_TYPE_32 iter) {" + "\n"
    line += "" + "\n"
    line += "    WORD left = 0;" + "\n"
    line += "    WORD right = 0;" + "\n"
    line += "    WORD tfVal = 0;" + "\n"
    line += "" + "\n"
    line += "    bool fwd_valid = false;" + "\n"
    line += "    bool inv_valid = false;" + "\n"
    line += "" + "\n"
    line += "    BU_COMP:for (;;) {" + "\n"
    line += "        #pragma HLS PIPELINE II=1" + "\n"
    line += "" + "\n"
    line += "        fwd_valid = (!(fwd_inVal0.empty() || fwd_inVal1.empty())) && (!fwd_inTf.empty());" + "\n"
    line += "        inv_valid = (!(inv_inVal0.empty() || inv_inVal1.empty())) && (!inv_inTf.empty());" + "\n"
    line += "" + "\n"
    line += "        if (fwd_valid){" + "\n"
    line += "            left = fwd_inVal0.read();" + "\n"
    line += "            right = fwd_inVal1.read();" + "\n"
    line += "            tfVal = fwd_inTf.read();" + "\n"
    line += "        } else if (inv_valid) {" + "\n"
    line += "            left = inv_inVal0.read();" + "\n"
    line += "            right = inv_inVal1.read();" + "\n"
    line += "            tfVal = inv_inTf.read();" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    
    line += modmul_kernel_funcCall(designParamsVar)

    line += "" + "\n"
    line += "        WORD_PLUS1 intemAdd = reducedProduct + left;" + "\n"
    line += "        WORD updatedLeft;" + "\n"
    line += "        if(intemAdd>=q){" + "\n"
    line += "            updatedLeft = intemAdd - q;" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "            updatedLeft = intemAdd;" + "\n"
    line += "        }" + "\n"
    line += "        " + "\n"
    line += "        WORD updatedRight;" + "\n"
    line += "        if(left >= reducedProduct){" + "\n"
    line += "            updatedRight = left - reducedProduct;" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "            updatedRight = q - (reducedProduct - left); " + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "        if(inv_valid){ //Multiply with 2 inverse here. Equation=> (a>>1) + a[0]((mod+1)/2)" + "\n"
    line += "            multiplyTwoInverse(&updatedLeft, &twoInverse);" + "\n"
    line += "            multiplyTwoInverse(&updatedRight, &twoInverse);" + "\n"
    line += "        }" + "\n"
    line += "        " + "\n"
    line += "        if(fwd_valid){" + "\n"
    line += "            fwd_outVal0.write(updatedLeft);" + "\n"
    line += "            fwd_outVal1.write(updatedRight);" + "\n"
    line += "        } else if(inv_valid){" + "\n"
    line += "            inv_outVal0.write(updatedLeft);" + "\n"
    line += "            inv_outVal1.write(updatedRight);" + "\n"
    line += "        }" + "\n"
    line += "" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    return line