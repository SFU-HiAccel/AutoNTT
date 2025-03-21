
# This function is to convert multiple parallel limbs into different DRAM ports.
# This function does not depend on FWD or INV
def gen_reorganize_para_limbs_to_ports_poly():
    
    line = ""

    line += "void reorganize_para_limbs_to_ports_poly(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){" + "\n"
    line += "  int num_of_data = (N/CONCAT_FACTOR);" + "\n"
    line += "" + "\n"
    line += "  //check" + "\n"
    line += "  if(num_of_data!=(inVec[0][0].size())){" + "\n"
    line += "    printf(\"[ERROR]::Size mismatch detected in reorganize_para_limbs_to_ports_poly. expected = %d, received=%d\\n\", num_of_data, (int)(inVec[0][0].size()));" + "\n"
    line += "    exit(1);" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  //init" + "\n"
    line += "  for(int port_idx=0; port_idx<POLY_LS_PORTS; port_idx++){" + "\n"
    line += "    outVec[port_idx].resize(num_of_data);" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  for(int data_counter=0; data_counter<num_of_data; data_counter++){" + "\n"
    line += "    for(int port_counter=0; port_counter<POLY_LS_PORTS; port_counter++){" + "\n"
    line += "      POLY_WIDE_DATA val = 0;" + "\n"
    line += "      for(int per_limb_port_counter=PARA_LIMB_PORTS_PER_POLY_PORT-1; per_limb_port_counter>=0; per_limb_port_counter--){" + "\n"
    line += "        int total_per_limb_ports = port_counter*PARA_LIMB_PORTS_PER_POLY_PORT + per_limb_port_counter;" + "\n"
    line += "        int limb_idx = total_per_limb_ports/POLY_LS_PORTS_PER_PARA_LIMB;" + "\n"
    line += "        int limb_port_idx = total_per_limb_ports%POLY_LS_PORTS_PER_PARA_LIMB;" + "\n"
    line += "        " + "\n"
    line += "        POLY_WIDE_DATA_PER_PARA_LIMB limbVal;" + "\n"
    line += "        if(limb_idx<PARA_LIMBS){ " + "\n"
    line += "          limbVal = inVec[limb_idx][limb_port_idx][data_counter];" + "\n"
    line += "        }" + "\n"
    line += "        else{ //In case, PARA_LIMBS is not perfectly divisible by PARA_LIMB_PORTS_PER_POLY_PORT" + "\n"
    line += "          limbVal = 0;" + "\n"
    line += "        }" + "\n"
    line += "        val = val << POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB;" + "\n"
    line += "        val |= (POLY_WIDE_DATA)limbVal;" + "\n"
    line += "      }" + "\n"
    line += "      outVec[port_counter][data_counter] = val;" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

# This function is to convert different DRAM ports into multiple parallel limbs.
# This function does not depend on FWD or INV
def gen_reorganize_ports_to_para_limbs_poly():
    
    line = ""

    line += "void reorganize_ports_to_para_limbs_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB]){" + "\n"
    line += "  int num_of_data = (N/CONCAT_FACTOR);" + "\n"
    line += "" + "\n"
    line += "  //check" + "\n"
    line += "  if(num_of_data!=(inVec[0].size())){" + "\n"
    line += "    printf(\"[ERROR]::Size mismatch detected in reorganize_para_limbs_to_ports_poly. expected = %d, received=%d\\n\", num_of_data, (int)(inVec[0].size()));" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  //init" + "\n"
    line += "  for(int limb_counter=0; limb_counter<PARA_LIMBS; limb_counter++){" + "\n"
    line += "    for(int port_counter=0; port_counter<POLY_LS_PORTS_PER_PARA_LIMB; port_counter++){" + "\n"
    line += "      outVec[limb_counter][port_counter].resize(num_of_data);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  for(int data_counter=0; data_counter<num_of_data; data_counter++){" + "\n"
    line += "    for(int port_counter=0; port_counter<POLY_LS_PORTS; port_counter++){" + "\n"
    line += "      POLY_WIDE_DATA val = inVec[port_counter][data_counter];" + "\n"
    line += "      for(int per_limb_port_counter=0; per_limb_port_counter<PARA_LIMB_PORTS_PER_POLY_PORT; per_limb_port_counter++){" + "\n"
    line += "        int total_per_limb_ports = port_counter*PARA_LIMB_PORTS_PER_POLY_PORT + per_limb_port_counter;" + "\n"
    line += "        int limb_idx = total_per_limb_ports/POLY_LS_PORTS_PER_PARA_LIMB;" + "\n"
    line += "        int limb_port_idx = total_per_limb_ports%POLY_LS_PORTS_PER_PARA_LIMB;" + "\n"
    line += "        " + "\n"
    line += "        POLY_WIDE_DATA_PER_PARA_LIMB limbVal = val & (((POLY_WIDE_DATA)1 << POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)-1);" + "\n"
    line += "        val = val >> POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB;" + "\n"
    line += "        if(limb_idx<PARA_LIMBS){  //In case, PARA_LIMBS is not perfectly divisible by PARA_LIMB_PORTS_PER_POLY_PORT(else of this if), we ignore extra data padded." + "\n"
    line += "          outVec[limb_idx][limb_port_idx][data_counter] = limbVal;" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def gen_fwd_poly_data_rearrange():
    line = ""
    
    line += "void cyclicDivideData(std::vector<WORD>& inVec, std::vector<WORD> (&outVec)[CONCAT_FACTOR]){" + "\n"
    line += "  for(int i=0; i<N; i++){" + "\n"
    line += "    outVec[i%CONCAT_FACTOR].push_back(inVec[i]);" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    line += "void fwd_reorganize_in_poly_per_para_limb(std::vector<WORD>& inVec, std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[HBM_PORT_NUM]){" + "\n"
    line += "  std::vector<WORD> blockInData[CONCAT_FACTOR];" + "\n"
    line += "  cyclicDivideData(inVec, blockInData);" + "\n"
    line += "" + "\n"
    line += "    for(int i=0; i<(N/CONCAT_FACTOR); i++){" + "\n"
    line += "      POLY_WIDE_DATA_PER_PARA_LIMB val[HBM_PORT_NUM] = {0};   // G0, G1, G2, G3 -> val[0], val[1], val[2], val[3]," + "\n"
    line += "      for(int s=0; s<HBM_PORT_NUM; s++) {" + "\n"
    line += "        for(int j=HBM_PORT_SIZE-1; j>=0; j--){" + "\n"
    line += "          val[s] <<= DRAM_WORD_SIZE;" + "\n"
    line += "          val[s] |= ((POLY_WIDE_DATA_PER_PARA_LIMB)blockInData[s*HBM_PORT_SIZE+j][i]);" + "\n"
    line += "        }" + "\n"
    line += "        outVec[s].push_back((POLY_WIDE_DATA_PER_PARA_LIMB)val[s]);" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "" + "\n"
    line += "}" + "\n"

    line += "void fwd_reorganize_out_poly_per_para_limb(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[HBM_PORT_NUM], std::vector<WORD>& outVec){" + "\n"
    line += "" + "\n"
    line += "  int index[CONCAT_FACTOR];" + "\n"
    line += "  for(int i = 0; i < CONCAT_FACTOR/2; i++) {" + "\n"
    line += "    index[i] = i*2;" + "\n"
    line += "    index[i+CONCAT_FACTOR/2] = i*2+1;" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "    for(int j = 0; j < CONCAT_FACTOR; j++) {" + "\n"
    line += "      for(int i = 0; i < (N/CONCAT_FACTOR); i++) { //0 - 64" + "\n"
    line += "        int inVec_index_1_dimen = index[j]/HBM_PORT_SIZE;" + "\n"
    line += "        int inVec_index_2_dimen = index[j]%HBM_PORT_SIZE;" + "\n"
    line += "        " + "\n"
    line += "        POLY_WIDE_DATA_PER_PARA_LIMB val = inVec[inVec_index_1_dimen][i];" + "\n"
    line += "        " + "\n"
    line += "        WORD smallVal = (WORD)(val.range((inVec_index_2_dimen*DRAM_WORD_SIZE)+(WORD_SIZE-1),(inVec_index_2_dimen*DRAM_WORD_SIZE)));" + "\n"
    line += "        outVec.push_back(smallVal); " + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void fwd_reorganize_input_poly_to_ports(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){" + "\n"
    line += "  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseInPolyData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];" + "\n"
    line += "  " + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    fwd_reorganize_in_poly_per_para_limb(inVec[paraLimbCounter], limbWiseInPolyData[paraLimbCounter]);" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  reorganize_para_limbs_to_ports_poly(limbWiseInPolyData, outVec);" + "\n"
    line += "}" + "\n"
    line += "" + "\n"

    line += "void fwd_reorganize_ports_to_output_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<WORD> (&outVec)[PARA_LIMBS]){" + "\n"
    line += "  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseOutData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];" + "\n"
    line += "  reorganize_ports_to_para_limbs_poly(inVec, limbWiseOutData);" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    //outVec[paraLimbCounter].resize(N); // Values are getting added instead assign" + "\n" 
    line += "    fwd_reorganize_out_poly_per_para_limb(limbWiseOutData[paraLimbCounter], outVec[paraLimbCounter]);" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"
    
    return line

def gen_inv_poly_data_rearrange():
    line = ""

    line += "void inv_reorganize_out_poly_per_para_limb(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[HBM_PORT_NUM], std::vector<WORD>& outVec){" + "\n"
    line += "" + "\n"
    line += "    for(int i=0; i<(N/CONCAT_FACTOR); i++)" + "\n"
    line += "    {" + "\n"
    line += "      for(int s=0; s<HBM_PORT_NUM; s++) {" + "\n"
    line += "        POLY_WIDE_DATA_PER_PARA_LIMB val = inVec[s][i];" + "\n"
    line += "        for(int j=0; j<HBM_PORT_SIZE; j++)" + "\n"
    line += "        {" + "\n"
    line += "          int val_index = (j);" + "\n"
    line += "          WORD smallVal = (WORD)(val.range((val_index*DRAM_WORD_SIZE)+(WORD_SIZE-1),(val_index*DRAM_WORD_SIZE)));" + "\n"
    line += "" + "\n"
    line += "          outVec.push_back(smallVal);" + "\n"
    line += "        }" + "\n"
    line += "      }" + "\n"
    line += "    }" + "\n"
    line += "}" + "\n"

    line += "void inv_reorganize_ports_to_output_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<WORD> (&outVec)[PARA_LIMBS]){" + "\n"
    line += "  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseOutData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];" + "\n"
    line += "  reorganize_ports_to_para_limbs_poly(inVec, limbWiseOutData);" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    //outVec[paraLimbCounter].resize(N); // Values are getting added instead assign" + "\n"
    line += "    inv_reorganize_out_poly_per_para_limb(limbWiseOutData[paraLimbCounter], outVec[paraLimbCounter]);" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

# This function is to initialize output DRAM ports to 0
def gen_init_kernerl_output_ports():

    line = ""

    line += "/* This function is to initialize output DRAM ports to 0 */" + "\n"
    line += "void init_kernerl_output_ports(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS]){" + "\n"
    line += "  for(int i=0; i<(N/CONCAT_FACTOR); i++){" + "\n"
    line += "    for(int j=0; j<POLY_LS_PORTS; j++){" + "\n"
    line += "      inVec[j].push_back(0);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "}" + "\n"

    return line

def gen_poly_data_rearrange_functions():
    line = ""

    # Parallel limbs to DRAM port conversion
    line += gen_reorganize_para_limbs_to_ports_poly()
    line += "\n"

    # DRAM port to parallel limbs conversion
    line += gen_reorganize_ports_to_para_limbs_poly()
    line += "\n"

    # FWD poly rearrange
    line += gen_fwd_poly_data_rearrange()
    line += "\n"

    # INV poly rearrange
    line += gen_inv_poly_data_rearrange()
    line += "\n"

    # Initialize output DRAM ports
    line += gen_init_kernerl_output_ports()
    line += "\n"

    return line