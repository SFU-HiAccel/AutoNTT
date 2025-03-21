# Commenting this separate task and alligning this decision with split_shuffler
# # Similar to shuffler split logic in 'gen_shuffler_control' function, if the BUG is larger than 4x3, then split selector is used
def gen_dual_interface_FIFO_split_logic(designParamsVar):
    is_split_DIF = False

    if(designParamsVar.IS_SPLIT_SHUFFLER):
        is_split_DIF = True
    else:
        if( (designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ):
            is_split_DIF = True
        else:
            is_split_DIF = False
    return is_split_DIF

def gen_split_FIFO():
    line = ""
    line += "void dual_interface_FIFO_receive(" + "\n"
    line += "                  tapa::istream<WORD>& fwd_inVal," + "\n"
    line += "                  tapa::istream<WORD>& inv_inVal," + "\n"
    line += "                  tapa::ostream<WORD>& common_outVal," + "\n"
    line += "                  bool direction){" + "\n"
    line += "  " + "\n"
    line += "  bool inpStreamNotEmpty;" + "\n"
    line += "  for(;;){" + "\n"
    line += "    " + "\n"
    line += "    inpStreamNotEmpty = ( !fwd_inVal.empty() ) || ( !inv_inVal.empty() );" + "\n"
    line += "" + "\n"
    line += "    if(inpStreamNotEmpty){" + "\n"
    line += "      if(direction){" + "\n"
    line += "        common_outVal.write(fwd_inVal.read());" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        common_outVal.write(inv_inVal.read());" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"
    line += "void dual_interface_FIFO_send(" + "\n"
    line += "                  tapa::istream<WORD>& common_inVal," + "\n"
    line += "                  tapa::ostream<WORD>& fwd_outVal," + "\n"
    line += "                  tapa::ostream<WORD>& inv_outVal," + "\n"
    line += "                  bool direction){" + "\n"
    line += "  " + "\n"
    line += "  bool inpStreamNotEmpty;" + "\n"
    line += "  for(;;){" + "\n"
    line += "    " + "\n"
    line += "    inpStreamNotEmpty = !common_inVal.empty();" + "\n"
    line += "" + "\n"
    line += "    if(inpStreamNotEmpty){" + "\n"
    line += "      if(direction){" + "\n"
    line += "        fwd_outVal.write(common_inVal.read());" + "\n"
    line += "      }" + "\n"
    line += "      else{" + "\n"
    line += "        inv_outVal.write(common_inVal.read());" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    
    return line

def gen_comb_FIFO():
    line = ""
    line += "void dual_interface_FIFO_comb_receive(" + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal," + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal," + "\n"
    line += "                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& common_outVal," + "\n"
    line += "                  bool direction){" + "\n"
    line += "  " + "\n"
    line += "  bool inpStreamNotEmpty;" + "\n"
    line += "  for(;;){" + "\n"
    line += "    " + "\n"
    line += "    inpStreamNotEmpty = ( !fwd_inVal[0].empty() ) || ( !inv_inVal[0].empty() );" + "\n"
    line += "    for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "      inpStreamNotEmpty &= ( ( !fwd_inVal[j].empty() ) || ( !inv_inVal[j].empty() ) );" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    if(inpStreamNotEmpty){" + "\n"
    line += "      for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "        if(direction){" + "\n"
    line += "          common_outVal[j].write(fwd_inVal[j].read());" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          common_outVal[j].write(inv_inVal[j].read());" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"
    line += "void dual_interface_FIFO_comb_send(" + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& common_inVal," + "\n"
    line += "                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal," + "\n"
    line += "                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal," + "\n"
    line += "                  bool direction){" + "\n"
    line += "  " + "\n"
    line += "  bool inpStreamNotEmpty;" + "\n"
    line += "  for(;;){" + "\n"
    line += "    " + "\n"
    line += "    inpStreamNotEmpty = !common_inVal[0].empty();" + "\n"
    line += "    for(VAR_TYPE_8 j=1; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "      inpStreamNotEmpty &= !common_inVal[j].empty();" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "    if(inpStreamNotEmpty){" + "\n"
    line += "      for(VAR_TYPE_8 j=0; j<2*V_BUG_SIZE; j++){" + "\n"
    line += "        if(direction){" + "\n"
    line += "          fwd_outVal[j].write(common_inVal[j].read());" + "\n"
    line += "        }" + "\n"
    line += "        else{" + "\n"
    line += "          inv_outVal[j].write(common_inVal[j].read());" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"
    line += "void dual_interface_FIFO_comb(" + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& fwd_inVal," + "\n"
    line += "                  tapa::istreams<WORD, 2*V_BUG_SIZE>& inv_inVal," + "\n"
    line += "                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& fwd_outVal," + "\n"
    line += "                  tapa::ostreams<WORD, 2*V_BUG_SIZE>& inv_outVal," + "\n"
    line += "                  bool direction){" + "\n"
    line += "" + "\n"
    line += "  tapa::streams<WORD, 2*V_BUG_SIZE, LS_FIFO_BUF_SIZE> common_FIFO(\"common_FIFO_stream\");" + "\n"
    line += "" + "\n"
    line += "  tapa::task()" + "\n"
    line += "    .invoke<tapa::detach>(dual_interface_FIFO_comb_receive, fwd_inVal, inv_inVal, common_FIFO, direction)" + "\n"
    line += "    .invoke<tapa::detach>(dual_interface_FIFO_comb_send, common_FIFO, fwd_outVal, inv_outVal, direction)" + "\n"
    line += "    ;" + "\n"
    line += "}" + "\n"

    return line

def gen_dual_interface_FIFO(designParamsVar):
    line = ""
    is_split_FIFO = gen_dual_interface_FIFO_split_logic(designParamsVar)
    
    if(is_split_FIFO):
        line += gen_split_FIFO()
    else:
        line += gen_comb_FIFO()

    return line