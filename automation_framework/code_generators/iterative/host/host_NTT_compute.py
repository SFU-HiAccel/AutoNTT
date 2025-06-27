def gen_tensorProd_NToR_fwd_NTT():
    line = ""
    
    line += "/*" + "\n"
    line += "Compute NTT using radix-2 tensor product based implementation" + "\n"
    line += "Input is provided in normal order and output is given in bit reversed order." + "\n"
    line += "TFs are actually required in bit reversed order. But we use bit reverse function to " + "\n"
    line += "convert." + "\n"
    line += "*/" + "\n"
    line += "void tensorProd_NToR_fwd_NTT(std::vector<WORD>& noInvec, std::vector<WORD>& boTFArr, WORD mod, VAR_TYPE_32 N, WORD NUM_BU){" + "\n"
    line += "  WORD stages = myLog2(N);//log2(((VAR_TYPE_32)N));" + "\n"
    line += "  if((1<<stages)!=N){" + "\n"
    line += "    printf(\"[Error]::Size is not a 2 to the power number\");" + "\n"
    line += "    exit(0);" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  WORD temp[N];" + "\n"
    line += "" + "\n"
    line += "  WORD beta = (1<<(stages-1))/NUM_BU;" + "\n"
    line += "  " + "\n"
    line += "  for(WORD l=stages; l>0; l--){" + "\n"
    line += "    for(WORD j=0; j<beta; j++){" + "\n"
    line += "      for(WORD i=0; i<NUM_BU; i++){" + "\n"
    line += "        WORD delta = j*NUM_BU + i;" + "\n"
    line += "        WORD tfIdx = (delta & ((1<<(logN-l)) - 1));" + "\n"
    line += "        //WORD br_tfIdx = bitReverseNumber(tfIdx, stages-1);" + "\n"
    line += "" + "\n"
    line += "        WORD tfVal = boTFArr[tfIdx];" + "\n"
    line += "" + "\n"
    line += "        WORD left = noInvec[delta];" + "\n"
    line += "        WORD right = (WORD)((((DWORD)noInvec[delta + NUM_BU*beta]) * ((DWORD)tfVal)) % ((DWORD)mod));" + "\n"
    line += "" + "\n"
    line += "        temp[2*delta] = (WORD)((((DWORD)left) + ((DWORD)right)) % ((DWORD)mod));" + "\n"
    line += "        " + "\n"
    line += "        if(left >= right){" + "\n"
    line += "          temp[2*delta+1] = (WORD)((((DWORD)left) - ((DWORD)right)) % ((DWORD)mod)); //probably, we can remove this last mod(%) operation" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          temp[2*delta+1] = (WORD)((((DWORD)mod) - (((DWORD)right) - ((DWORD)left))) % ((DWORD)mod));  //probably, we can remove this last mod(%) operation" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "    " + "\n"
    line += "    for(WORD h=0; h<N; h++){" + "\n"
    line += "      noInvec[h] = temp[h];" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def gen_host_NTT_compute_functions():

    line = ""

    # tensor product based NTT
    line += gen_tensorProd_NToR_fwd_NTT()
    line += "\n"

    return line
