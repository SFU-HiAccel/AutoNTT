from code_generators.common.helper_functions import num_arr_to_cppArrStr
from code_generators.common.helper_functions import binary_arr_to_cppArrStr


def gen_genTF_function():
    line = ""

    line += "/* Generate twiddle factors for radix 2 NTT. " + "\n"
    line += "In normal radix-2 case, twiddle factors are used in increasing power order" + "\n"
    line += "*/" + "\n"
    line += "void generateTFForRadix2NTT(WORD root, WORD size, WORD mod, std::vector<WORD>& TFArr){" + "\n"
    line += "  WORD tempTF = 1;" + "\n"
    line += "  for(int i=0; i<(size/2); i++){" + "\n"
    line += "    TFArr[i] = tempTF;" + "\n"
    line += "    tempTF = (WORD)((((DWORD)tempTF) * ((DWORD)root)) % ((DWORD)mod));" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "/* Generate TFs for num_of_limbs when poly size is 'size' */" + "\n"
    line += "void generateTFsForMultipleLimbs(VAR_TYPE_32 num_of_limbs, VAR_TYPE_32 size, std::vector<WORD>& workingModulus_arr, std::vector<WORD>& root_arr, std::vector<WORD> (&tfArr)[PARA_LIMBS]){" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<num_of_limbs; paraLimbCounter++){" + "\n"
    line += "    WORD root = root_arr[paraLimbCounter];" + "\n"
    line += "    WORD workingModulus = workingModulus_arr[paraLimbCounter];" + "\n"
    line += "    " + "\n"
    line += "    tfArr[paraLimbCounter].resize(size/2);" + "\n"
    line += "" + "\n"
    line += "    generateTFForRadix2NTT(root, size, workingModulus, tfArr[paraLimbCounter]);" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

# This function is to convert multiple parallel limbs into different DRAM ports.
# This function does not depend on FWD or INV
def gen_reorganize_para_limbs_to_ports_tf():

    line = ""

    line += "void reorganize_para_limbs_to_ports_tf(std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[PARA_LIMBS][TF_PORTS_PER_PARA_LIMB], std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> (&outVec)[TF_PORTS]){" + "\n"
    line += "" + "\n"
    line += "  for(int h_port_idx=0; h_port_idx<H_TF_PORTS_PER_PARA_LIMB; h_port_idx++){" + "\n"
    line += "    for(int port_counter=0; port_counter<V_TF_PORTS; port_counter++){" + "\n"
    line += "      //init" + "\n"
    line += "      int target_per_limb_port_start = port_counter*V_PARA_LIMB_PORTS_PER_TF_PORT;" + "\n"
    line += "      int target_limb_idx = target_per_limb_port_start/V_TF_PORTS_PER_PARA_LIMB;" + "\n"
    line += "      int target_limb_port_idx = h_port_idx*V_TF_PORTS_PER_PARA_LIMB;" + "\n"
    line += "      int target_actual_port_idx = h_port_idx*V_TF_PORTS + port_counter;" + "\n"
    line += "" + "\n"
    line += "      int num_of_data = inVec[target_limb_idx][target_limb_port_idx].size(); // This could be = inVec[0][target_limb_port_idx].size()" + "\n"
    line += "      outVec[target_actual_port_idx].resize(num_of_data);" + "\n"
    line += "" + "\n"
    line += "      //assign" + "\n"
    line += "      for(int data_counter=0; data_counter<num_of_data; data_counter++){" + "\n"
    line += "        TF_WIDE_DATA val = 0;" + "\n"
    line += "        for(int per_limb_port_counter=V_PARA_LIMB_PORTS_PER_TF_PORT-1; per_limb_port_counter>=0; per_limb_port_counter--){" + "\n"
    line += "          int total_per_limb_ports = port_counter*V_PARA_LIMB_PORTS_PER_TF_PORT + per_limb_port_counter;" + "\n"
    line += "          int limb_idx = total_per_limb_ports/V_TF_PORTS_PER_PARA_LIMB;" + "\n"
    line += "          int limb_port_idx = h_port_idx*V_TF_PORTS_PER_PARA_LIMB + total_per_limb_ports%V_TF_PORTS_PER_PARA_LIMB;" + "\n"
    line += "" + "\n"
    line += "          TF_WIDE_DATA_PER_PARA_LIMB limbVal;" + "\n"
    line += "          if(limb_idx<PARA_LIMBS){ " + "\n"
    line += "            limbVal = inVec[limb_idx][limb_port_idx][data_counter];" + "\n"
    line += "          }" + "\n"
    line += "          else{//In case, PARA_LIMBS is not perfectly divisible by PARA_LIMB_PORTS_PER_TF_PORT" + "\n"
    line += "            limbVal = 0;" + "\n"
    line += "          }" + "\n"
    line += "          val = val << TF_DRAM_PORT_WIDTH_PER_PARA_LIMB;" + "\n"
    line += "          val |= (TF_WIDE_DATA)limbVal;" + "\n"
    line += "        }" + "\n"
    line += "        outVec[target_actual_port_idx][data_counter] = val;" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line



def gen_fwd_TF_data_rearrange(designParamsVar):
    tf_mmap_count = designParamsVar.tf_mmap_count
    arr_TFToTF_idx = designParamsVar.arr_TFToTF_idx

    line = ""

    if tf_mmap_count == 1:  # Case when a single BUG requires only one port to load the TF.
        line += """
void fwd_organizeTFData(std::vector<WORD>& inp1, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inp1_512b)[DB_TF_PORT_NUM]) 
{
  int sum_tf_per_stage = 1;  // The TF required by each BUG.

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    for(int l=0;l<tf_depth;l++)
    {
      int idx = 0;
"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""      else """
            else:
                line += f"""      """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
        idx = {idx};                
      }}
"""
        line += f"""      else {{
        idx = {len(arr_TFToTF_idx) - 1};
      }}
"""
        line += """
      inp1_512b[idx].push_back(0);

    }
    sum_tf_per_stage <<= 1;
  }

  sum_tf_per_stage = 1;
  int distance_stage = halfN;
  int outer = V_BU_NUM, inner = 1;  // Decide how to pack it based on the BUG and the layer within the BUG.
  int previous_cycle = 0;  // The total depth of the previously packed TF.
  int idx_before = 0, idx_after = 0;

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    int inp1_idx = 0;
    if ((i%H_BU_NUM) == 0)
    {
      outer = V_BU_NUM;
      inner = 1;
    }
    if (((logN % H_BU_NUM) == LAST_H_BU_NUM) && (i == (logN-LAST_H_BU_NUM))) {  // change by forward, partial group's TF initialization when LAST_H_BU_NUM==4
      int shift = H_BU_NUM-LAST_H_BU_NUM;
      outer = V_BU_NUM >> shift;
      inner = 1 << shift;
    }

"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""    else """
            else:
                line += f"""    """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
      idx_before = idx_after;
      idx_after = {idx};              
    }}
"""
        line += f"""    else {{
      idx_before = idx_after;
      idx_after = {len(arr_TFToTF_idx) - 1};
    }}
    if (idx_before != idx_after) {{
      previous_cycle = 0;
    }}
"""
        line += """
    for(int k=0;k<inner;k++)
    {
      for(int l=0;l<tf_depth;l++)
      {
        TF_WIDE_DATA_PER_PARA_LIMB packTF = inp1_512b[idx_after][previous_cycle+l];
        for(int j=0;j<outer;j++)
        {
          packTF <<= DRAM_WORD_SIZE;
          packTF |= (TF_WIDE_DATA_PER_PARA_LIMB)inp1[inp1_idx];
          
          inp1_idx += (((i<H_BU_NUM)&&(j!=(outer-1)))?0:distance_stage);
        }
        inp1_512b[idx_after][previous_cycle+l]=(TF_WIDE_DATA_PER_PARA_LIMB)packTF;
      }
    }
    outer>>=1;
    inner<<=1;  
    sum_tf_per_stage <<= 1;
    distance_stage >>= 1;
    previous_cycle += tf_depth;
  }
}
"""
    elif tf_mmap_count == 2:  # Case when a single BUG needs to combine two ports to load the TF.
        line += """
void fwd_organizeTFData(std::vector<WORD>& inp1, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inp1_512b)[DB_TF_PORT_NUM]) 
{
  int sum_tf_per_stage = 1;  // The TF required by each BUG.

  // initialize
  for (int i = 0; i < logN; i++) 
  {
    int tf_depth = ((sum_tf_per_stage / V_BU_NUM) == 0) ? 1 : (sum_tf_per_stage / V_BU_NUM);
    for (int l = 0; l < tf_depth; l++) 
    {
      int idx = 0;
"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""      else """
            else:
                line += f"""      """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
        idx = {idx};                
      }}
"""
        line += f"""      else {{
        idx = {len(arr_TFToTF_idx) - 1};
      }}
"""
        line += """
      inp1_512b[idx*TF_PORT_NUM].push_back(0); // change into two ports, fisrt 512 bits
      inp1_512b[idx*TF_PORT_NUM+1].push_back(0); // change into two ports, second 512 bits
    }
    sum_tf_per_stage <<= 1;
  }

  sum_tf_per_stage = 1;
  int distance_stage = halfN;
  int outer = V_BU_NUM, inner = 1;  // Decide how to pack it based on the BUG and the layer within the BUG.
  int previous_cycle = 0;  // The total depth of the previously packed TF.
  TF_WIDE_DATA_PER_PARA_LIMB packTF[2];
  int idx_before = 0, idx_after = 0;

  // pack data to two 512 bits = 1024 bits
  for (int i = 0; i < logN; i++) 
  {
    int tf_depth = ((sum_tf_per_stage / V_BU_NUM) == 0) ? 1 : (sum_tf_per_stage / V_BU_NUM);
    int inp1_idx = 0;
    if ((i%H_BU_NUM) == 0)
    {
      outer = V_BU_NUM;
      inner = 1;
    }
    if (((logN % H_BU_NUM) == LAST_H_BU_NUM) && (i == (logN-LAST_H_BU_NUM))) {  // change by forward, partial group's TF initialization when LAST_H_BU_NUM==4
      int shift = H_BU_NUM-LAST_H_BU_NUM;
      outer = V_BU_NUM >> shift;
      inner = 1 << shift;
    }

"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""    else """
            else:
                line += f"""    """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
      idx_before = idx_after;
      idx_after = {idx};              
    }}
"""
        line += f"""    else {{
      idx_before = idx_after;
      idx_after = {len(arr_TFToTF_idx) - 1};
    }}
    if (idx_before != idx_after) {{
      previous_cycle = 0;
    }}
"""
        line += """

    for (int k = 0; k < inner; k++)
    {
      for (int l = 0; l < tf_depth; l++) 
      {
        packTF[0] = inp1_512b[idx_after*TF_PORT_NUM][previous_cycle + l]; // change into two ports, first 512 bits
        packTF[1] = inp1_512b[idx_after*TF_PORT_NUM+1][previous_cycle + l]; // change into two ports, second 512 bits
        
        // pack 1024 bits
        for (int j = 0; j < outer; j++)  // first load last value
        {
          int packTF_idx = (k*outer+j)/TF_PORT_SIZE; // change into two ports
          
          packTF[packTF_idx] <<= DRAM_WORD_SIZE;
          packTF[packTF_idx] |= (TF_WIDE_DATA_PER_PARA_LIMB)inp1[inp1_idx];

          inp1_idx += (((i < H_BU_NUM) && (j != (outer-1))) ? 0:distance_stage);
        }

        inp1_512b[idx_after*TF_PORT_NUM][previous_cycle + l] = (TF_WIDE_DATA_PER_PARA_LIMB)packTF[0];  // change into two ports
        inp1_512b[idx_after*TF_PORT_NUM+1][previous_cycle + l] = (TF_WIDE_DATA_PER_PARA_LIMB)packTF[1];  // change into two ports
      }
    }
    outer >>= 1;
    inner <<= 1;
    sum_tf_per_stage <<= 1;
    distance_stage >>= 1;
    previous_cycle += tf_depth;
  }
}
"""
    
    return line

def gen_inv_TF_data_rearrange(designParamsVar):
    tf_mmap_count = designParamsVar.tf_mmap_count
    arr_TFToTF_idx = designParamsVar.arr_TFToTF_idx
    
    line = ""

    if tf_mmap_count == 1:
        line += """
void inv_organizeTFData(std::vector<WORD>& inp1, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inp1_512b)[DB_TF_PORT_NUM]) 
{
  int sum_tf_per_stage = 1;
  int new_tf_depth[3] = {};

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    for(int l=0;l<tf_depth;l++)
    {
      int idx = 0;
"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""      else """
            else:
                line += f"""      """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
        idx = {idx};                
      }}
"""
        line += f"""      else {{
        idx = {len(arr_TFToTF_idx) - 1};
      }}
"""
        line += """
      inp1_512b[idx].push_back(0);
    }
    sum_tf_per_stage <<= 1;
  }

    sum_tf_per_stage = 1;
  int outer = V_BU_NUM, inner = 1;
  int previous_cycle = 0;
  int idx_before = 0, idx_after = 0;

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    int inp1_idx = 0;
    if ((i == 0) || (((i+(H_BU_NUM-LAST_H_BU_NUM)) % H_BU_NUM) == 0))   // change by inverse
    {
      outer = V_BU_NUM;
      inner = 1;
    } 

"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""    else """
            else:
                line += f"""    """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
      idx_before = idx_after;
      idx_after = {idx};              
    }}
"""
        line += f"""    else {{
      idx_before = idx_after;
      idx_after = {len(arr_TFToTF_idx) - 1};
    }}
    if (idx_before != idx_after) {{
      previous_cycle = 0;
    }}
"""
        line += """
    for(int k=0;k<inner;k++)
    {
      inp1_idx = k;
      for(int l=0;l<tf_depth;l++)
      {
        TF_WIDE_DATA_PER_PARA_LIMB packTF = inp1_512b[idx_after][previous_cycle+l];
        for(int j=0;j<outer;j++)
        {
          packTF <<= DRAM_WORD_SIZE;
          packTF |= (TF_WIDE_DATA_PER_PARA_LIMB)inp1[inp1_idx%sum_tf_per_stage];
          
          inp1_idx += inner;
        }
        inp1_512b[idx_after][previous_cycle+l]=(TF_WIDE_DATA_PER_PARA_LIMB)packTF;
      }
    }
    outer>>=1;
    inner<<=1;  
    sum_tf_per_stage <<= 1;
    previous_cycle += tf_depth;
  }
}
"""
    elif tf_mmap_count == 2:
        line += """
void inv_organizeTFData(std::vector<WORD>& inp1, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inp1_512b)[DB_TF_PORT_NUM]) 
{
  int sum_tf_per_stage = 1;

  // initialize
  for (int i = 0; i < logN; i++) 
  {
    int tf_depth = ((sum_tf_per_stage / V_BU_NUM) == 0) ? 1 : (sum_tf_per_stage / V_BU_NUM);
    for (int l = 0; l < tf_depth; l++) 
    {
      int idx = 0;
"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""      else """
            else:
                line += f"""      """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
        idx = {idx};                
      }}
"""
        line += f"""      else {{
        idx = {len(arr_TFToTF_idx) - 1};
      }}
"""
        line += """
      inp1_512b[idx*TF_PORT_NUM].push_back(0); // change into two ports, fisrt 512 bits
      inp1_512b[idx*TF_PORT_NUM+1].push_back(0); // change into two ports, second 512 bits
    }
    sum_tf_per_stage <<= 1;
  }

  sum_tf_per_stage = 1;
  int outer = V_BU_NUM, inner = 1;
  int previous_cycle = 0;
  TF_WIDE_DATA_PER_PARA_LIMB packTF[2]; // change into two ports
  int idx_before = 0, idx_after = 0;

  // pack data to two 512 bits = 1024 bits
  for (int i = 0; i < logN; i++) 
  {
    int tf_depth = ((sum_tf_per_stage / V_BU_NUM) == 0) ? 1 : (sum_tf_per_stage / V_BU_NUM);
    int inp1_idx = 0;
    if ((i == 0) || (((i+(H_BU_NUM-LAST_H_BU_NUM)) % H_BU_NUM) == 0))   // change by inverse
    {
      outer = V_BU_NUM;
      inner = 1;
    }

"""
        for idx in range(len(arr_TFToTF_idx) - 1):
            if idx != 0: 
                line += f"""    else """
            else:
                line += f"""    """
            line += f"""if ((LEN_{idx}<=i) && (i<LEN_{idx+1})) {{
      idx_before = idx_after;
      idx_after = {idx};              
    }}
"""
        line += f"""    else {{
      idx_before = idx_after;
      idx_after = {len(arr_TFToTF_idx) - 1};
    }}
    if (idx_before != idx_after) {{
      previous_cycle = 0;
    }}
"""
        line += """

    for (int k = 0; k < inner; k++)
    {
      inp1_idx = k;
      for (int l = 0; l < tf_depth; l++) 
      {
        packTF[0] = inp1_512b[idx_after*TF_PORT_NUM][previous_cycle + l]; // change into two ports, first 512 bits
        packTF[1] = inp1_512b[idx_after*TF_PORT_NUM+1][previous_cycle + l]; // change into two ports, second 512 bits
        
        // pack 1024 bits
        for (int j = 0; j < outer; j++)  // first load last value
        {
          int packTF_idx = (k*outer+j)/TF_PORT_SIZE; // change into two ports
          
          packTF[packTF_idx] <<= DRAM_WORD_SIZE;
          packTF[packTF_idx] |= (TF_WIDE_DATA_PER_PARA_LIMB)inp1[inp1_idx%sum_tf_per_stage];

          inp1_idx += inner;
        }

        inp1_512b[idx_after*TF_PORT_NUM][previous_cycle + l] = (TF_WIDE_DATA_PER_PARA_LIMB)packTF[0];  // change into two ports
        inp1_512b[idx_after*TF_PORT_NUM+1][previous_cycle + l] = (TF_WIDE_DATA_PER_PARA_LIMB)packTF[1];  // change into two ports
      }
    }
    outer >>= 1;
    inner <<= 1;
    sum_tf_per_stage <<= 1;
    previous_cycle += tf_depth;
  }
}

"""
    
    return line


# A wrapper function which include both FWD and INV tf coversion to DRAM ports
def gen_reorganize_input_tfs_to_ports():

    line  = ""
    
    line += "void reorganize_input_tfs_to_ports(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> (&outVec)[TF_PORTS], bool direction){" + "\n"
    line += "  " + "\n"
    line += "  std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> limbWiseInTFData[PARA_LIMBS][TF_PORTS_PER_PARA_LIMB];" + "\n"
    line += "  " + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    if(direction){" + "\n"
    line += "      fwd_organizeTFData(inVec[paraLimbCounter], limbWiseInTFData[paraLimbCounter]);" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      inv_organizeTFData(inVec[paraLimbCounter], limbWiseInTFData[paraLimbCounter]);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  reorganize_para_limbs_to_ports_tf(limbWiseInTFData, outVec);" + "\n"
    line += "}" + "\n"
    
    return line

def gen_TF_data_rearrange_functions(designParamsVar):
    line = ""

    # TF generation function
    line += gen_genTF_function()
    line += "\n"

    # Parallel limbs to DRAM port conversion
    line += gen_reorganize_para_limbs_to_ports_tf()
    line += "\n"

    # FWD TF rearrange
    line += gen_fwd_TF_data_rearrange(designParamsVar)
    line += "\n"

    # INV TF rearrange
    line += gen_inv_TF_data_rearrange(designParamsVar)
    line += "\n"

    # TF array to DRAM ports
    line += gen_reorganize_input_tfs_to_ports()
    line += "\n"

    return line