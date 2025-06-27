from code_generators.modmul.config import modmul_header_args
from code_generators.modmul.config import modmul_kernel_funcCall
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

####
# This task is to generate BU based on the different modulo reduction method
####
def gen_BU(designParamsVar):
    line = ""

    line += "void BU(" + "\n"
    line += "    tapa::istream<WORD>& fwd_inVal0," + "\n"
    line += "    tapa::istream<WORD>& fwd_inVal1, " + "\n"
    line += "    tapa::istreams<WORD,2>& inv_inVals," + "\n"
    line += "    tapa::istream<WORD>& inTf," + "\n"
    line += "    tapa::ostreams<WORD,2 >& fwd_outVal," + "\n"
    line += "    tapa::ostream<WORD>& inv_outVal0," + "\n"
    line += "    tapa::ostream<WORD>& inv_outVal1," + "\n"
    line += "    WORD q," + "\n"
    line += "    WORD twoInverse," + "\n"
    
    prefix = "    "
    suffix = ",\n"
    line += modmul_header_args(designParamsVar, prefix, suffix)

    line += "    bool direction," + "\n"
    line += "    VAR_TYPE_16 iter," + "\n"
    line += "    int BUIdx" + "\n"
    line += "    ){" + "\n"
    line += "  " + "\n"
    line += "  int i=0;" + "\n"

    if(designParamsVar.DOUBLE_BUF_EN):
        line += "  VAR_TYPE_32 numBUIter = ((N*logN)/(2*NUM_BU)) * (iter+2);" + "\n"
    else:
        line += "  VAR_TYPE_32 numBUIter = ((N*logN)/(2*NUM_BU)) * iter;" + "\n"

    line += "" + "\n"
    line += "  WORD left;" + "\n"
    line += "  WORD right;" + "\n"
    line += "" + "\n"
    line += "  BU_COMP:for (;i<numBUIter; ) {" + "\n"
    line += "    #pragma HLS PIPELINE II=1" + "\n"
    line += "    if((((!fwd_inVal0.empty()) && (!fwd_inVal1.empty())) || ((!inv_inVals[0].empty()) && (!inv_inVals[1].empty())))  && (!inTf.empty())){" + "\n"
    line += "      if(direction){" + "\n"
    line += "        left = fwd_inVal0.read();" + "\n"
    line += "        right = fwd_inVal1.read();" + "\n"
    line += "      } else {" + "\n"
    line += "        left = inv_inVals[0].read();" + "\n"
    line += "        right = inv_inVals[1].read();" + "\n"
    line += "      }" + "\n"
    line += "      WORD tfVal = inTf.read();" + "\n"
    line += "" + "\n"
    
    line += modmul_kernel_funcCall(designParamsVar)

    line += "      WORD_PLUS1 intemAdd = reducedProduct + left;" + "\n"
    line += "      WORD updatedLeft;" + "\n"
    line += "      if(intemAdd>=q){" + "\n"
    line += "        updatedLeft = intemAdd - q;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        updatedLeft = intemAdd;" + "\n"
    line += "      }" + "\n"
    line += "      " + "\n"
    line += "      WORD updatedRight;" + "\n"
    line += "      if(left >= reducedProduct){" + "\n"
    line += "        updatedRight = left - reducedProduct;" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        updatedRight = q - (reducedProduct - left); " + "\n"
    line += "      }" + "\n"
    line += "" + "\n"
    line += "      if(!direction){ //Multiply with 2 inverse here. Equation=> (a>>1) + a[0]((mod+1)/2)" + "\n"
    line += "        multiplyTwoInverse(&updatedLeft, &twoInverse);" + "\n"
    line += "        multiplyTwoInverse(&updatedRight, &twoInverse);" + "\n"
    line += "      }" + "\n"
    line += "      " + "\n"
    line += "      if(direction){" + "\n"
    line += "        fwd_outVal[0].write(updatedLeft);" + "\n"
    line += "        fwd_outVal[1].write(updatedRight);" + "\n"
    line += "      } else {" + "\n"
    line += "        inv_outVal0.write(updatedLeft);" + "\n"
    line += "        inv_outVal1.write(updatedRight);" + "\n"
    line += "      }" + "\n"
    line += "      i++;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line