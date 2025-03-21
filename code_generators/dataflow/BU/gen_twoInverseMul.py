def gen_twoInverseMul():
    line = ""

    line += "void multiplyTwoInverse(WORD *val, WORD *twoInverse){" + "\n"
    line += "  #pragma HLS inline" + "\n"
    line += "  *val = (*val>>1) + (*val & 1)*(*twoInverse);" + "\n"
    line += "}" + "\n"

    return line
