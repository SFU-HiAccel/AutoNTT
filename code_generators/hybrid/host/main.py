from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM, CUSTOM_REDUCTION
from code_generators.modmul.barrett import gen_barrett_host_func_call
from code_generators.modmul.montgomery import gen_montgomery_host_func_call
from code_generators.modmul.wlm import gen_wlm_host_func_call
from code_generators.modmul.custom import gen_custom_red_host_func_call
from code_generators.modmul.custom import gen_custom_red_mod_gen_host_func_call
from code_generators.modmul.config import modmul_funcCall_args

def gen_main(designParamsVar):
    REDUCTION_TYPE = designParamsVar.REDUCTION_TYPE

    line = ""

    line += "int main(int argc, char* argv[]) {" + "\n"
    line += "  gflags::ParseCommandLineFlags(&argc, &argv, /*remove_flags=*/true);" + "\n"
    line += "" + "\n"
    
    line += "  VAR_TYPE_32 seed = 7;" + "\n"
    line += "  VAR_TYPE_64 minMod = (((VAR_TYPE_64)1U)<<(WORD_SIZE-1))+1;" + "\n"
    line += "  VAR_TYPE_32 size = N;" + "\n"
    line += "" + "\n"
    line += "  std::cout << \"Polynomial size = \" << size << \", Minimum Modulus = \" << minMod << std::endl;" + "\n"
    line += "  std::cout << \"Parallel limb count = \" << (VAR_TYPE_32)PARA_LIMBS << std::endl;" + "\n"
    line += "" + "\n"

    line += "  // Generate inputs" + "\n"
    line += "  vector<WORD> invec[PARA_LIMBS];" + "\n"
    line += "  generate_random_polynomials_array(seed, minMod, size, PARA_LIMBS, invec);" + "\n"
    line += "" + "\n"

    line += "  // Calculate working modulus" + "\n"
    line += "  vector<WORD> workingModulus_arr(PARA_LIMBS);" + "\n"
    if(designParamsVar.REDUCTION_TYPE==WLM): # in case of WLM, we use special function to generate modulus quickly
        line += "  find_NTT_and_WLM_friendly_modulus_array(size, minMod, workingModulus_arr, PARA_LIMBS);" + "\n"
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION): 
        custom_mod_gen_call = gen_custom_red_mod_gen_host_func_call(designParamsVar)
        if(custom_mod_gen_call == ""): #if empty use default
            line += "  find_NTT_friendly_modulus_array(size, minMod, workingModulus_arr, PARA_LIMBS);" + "\n"
        else:
            line += "  " + custom_mod_gen_call
    else:
        line += "  find_NTT_friendly_modulus_array(size, minMod, workingModulus_arr, PARA_LIMBS);" + "\n"
    line += "" + "\n"

    line += "  // Find the primitive root of unity, inverse and two inverse (used in INTT)" + "\n"
    line += "  vector<WORD> root_arr(PARA_LIMBS);" + "\n"
    line += "  vector<WORD> rootInverse_arr(PARA_LIMBS);" + "\n"
    line += "  vector<WORD> twoInverse_arr(PARA_LIMBS);" + "\n"
    line += "  generate_NTT_variables(workingModulus_arr, size, PARA_LIMBS, root_arr, rootInverse_arr, twoInverse_arr);" + "\n"
    line += "" + "\n"

    line += "  // Print parameter summary" + "\n"
    line += "  std::cout << \"\\nParallel limb parameters:\" << std::endl;" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    std::cout << \"Para limb \" << paraLimbCounter << \": Modulus = \" << workingModulus_arr[paraLimbCounter] << \", root = \" << root_arr[paraLimbCounter] << \", rootInverse = \" << rootInverse_arr[paraLimbCounter] << \", twoInverse = \" << twoInverse_arr[paraLimbCounter] << std::endl;" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"

    line += "  // Calculating TFs - FWD" + "\n"
    line += "  vector<WORD> tfArr[PARA_LIMBS];" + "\n"
    line += "  generateTFsForMultipleLimbs(PARA_LIMBS, size, workingModulus_arr, root_arr, tfArr);" + "\n"
    line += "" + "\n"

    line += "  // Calculating TFs - INV" + "\n"
    line += "  vector<WORD> inv_tfArr[PARA_LIMBS];" + "\n"
    line += "  generateTFsForMultipleLimbs(PARA_LIMBS, size, workingModulus_arr, rootInverse_arr, inv_tfArr);" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    bitReverseVect(inv_tfArr[paraLimbCounter], size/2);" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"

    line += "  // NTT in host" + "\n"
    line += "  vector<WORD> fwdVec_ref[PARA_LIMBS];" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    fwdVec_ref[paraLimbCounter].resize(size);" + "\n"
    line += "    fwdVec_ref[paraLimbCounter] = invec[paraLimbCounter];" + "\n"
    line += "    bitReverseVect(fwdVec_ref[paraLimbCounter], size);" + "\n"
    line += "    WORD workingModulus = workingModulus_arr[paraLimbCounter];" + "\n"
    line += "    CT_RToN_fwd_NTT(fwdVec_ref[paraLimbCounter], tfArr[paraLimbCounter], workingModulus, size);" + "\n"
    line += "  }" + "\n"
    line += "  printf(\"\\nHost NTT computation completed\\n\");" + "\n"
    line += "" + "\n"

    line += "  // INTT in host" + "\n"
    line +="  vector<WORD> invVec_ref[PARA_LIMBS];" + "\n"
    line +="  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line +="    invVec_ref[paraLimbCounter].resize(size);" + "\n"
    line +="    invVec_ref[paraLimbCounter] = fwdVec_ref[paraLimbCounter];" + "\n"
    line +="    CT_NToR_INTT(invVec_ref[paraLimbCounter], inv_tfArr[paraLimbCounter], workingModulus_arr[paraLimbCounter], size);" + "\n"
    line +="    bitReverseVect(invVec_ref[paraLimbCounter], size);" + "\n"
    line +="    bool check_status = compareResults(invec[paraLimbCounter], invVec_ref[paraLimbCounter], size);" + "\n"
    line +="    if(check_status){" + "\n"
    line +="      printf(\"[Para limb %d]::Inverse Test Execution Passed\\n\", (int)paraLimbCounter);" + "\n"
    line +="    }" + "\n"
    line +="    else{" + "\n"
    line +="      printf(\"[Para limb %d]::Inverse Test Execution Failed\\n\", (int)paraLimbCounter);" + "\n"
    line +="      exit (1);" + "\n"
    line +="    }" + "\n"
    line +="  }" + "\n"
    line +="  printf(\"Host INTT computation completed\\n\\n\");" + "\n"
    line += "" + "\n"
    
    line += "  // Perform modulo reduction related pre computations" + "\n"
    if(designParamsVar.REDUCTION_TYPE==BARRETT):
        line += gen_barrett_host_func_call()
    elif(designParamsVar.REDUCTION_TYPE==MONTGOMERY):
        line += gen_montgomery_host_func_call()
    elif(designParamsVar.REDUCTION_TYPE==WLM):
        line += gen_wlm_host_func_call()
    elif(designParamsVar.REDUCTION_TYPE==CUSTOM_REDUCTION):
        line += gen_custom_red_host_func_call(designParamsVar)
    line += "" + "\n"

    line += "  bool direction;" + "\n"
    line += "  int64_t kernel_time_ns;" + "\n"
    line += "  bool status;" + "\n"
    line += "  VAR_TYPE_16 iter = 1;" + "\n"
    line += "  printf(\"\\nNumber of iterations=%d\\n\\n\",(int)iter);" + "\n"
    line += "" + "\n"

    line += "  // FWD" + "\n"
    line += "  direction = true;" + "\n"
    line += "" + "\n"

    line += "  // Poly data rearrangements" + "\n"
    line += "  vector<WORD> fwdVec_test[PARA_LIMBS];" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    fwdVec_test[paraLimbCounter].resize(size);" + "\n"
    line += "    fwdVec_test[paraLimbCounter] = invec[paraLimbCounter];" + "\n"
    line += "    bitReverseVect(fwdVec_test[paraLimbCounter], size);" + "\n"
    line += "  }" + "\n"
    line += "  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> portWiseInPolyData[POLY_LS_PORTS];" + "\n"
    line += "  fwd_reorganize_input_poly_to_ports(fwdVec_test, portWiseInPolyData);" + "\n"
    line += "" + "\n"

    line += "  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> portWiseOutData[POLY_LS_PORTS];" + "\n"
    line += "  init_kernerl_output_ports(portWiseOutData);" + "\n"

    line += "  // TF data rearrangements" + "\n"
    line += "  std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> portWiseInTFData[TF_PORTS];" + "\n"

    if( (designParamsVar.REDUCTION_TYPE==MONTGOMERY) or (designParamsVar.REDUCTION_TYPE==WLM) ): # in case montgomery, converted TFs have to be used
        line += "  reorganize_input_tfs_to_ports(tfArr_montgomery, portWiseInTFData, direction);" + "\n"
    else:
        line += "  reorganize_input_tfs_to_ports(tfArr, portWiseInTFData, direction);" + "\n"
    line += "" + "\n"

    line += "  printf(\"\\n====Forward Computation====\\n\");" + "\n"
    line += "" + "\n"
    
    line += "  kernel_time_ns = tapa::invoke(" + "\n"
    line += "      NTT_kernel, FLAGS_bitstream, " + "\n"
    
    for port_idx in range(designParamsVar.POLY_LS_PORTS):
        line += "      tapa::read_write_mmap<POLY_WIDE_DATA>(portWiseInPolyData[" + str(port_idx) + "])," + "\n"
    
    for port_idx in range(designParamsVar.TF_PORTS):
        line += "      tapa::read_only_mmap<TF_WIDE_DATA>(portWiseInTFData[" + str(port_idx) + "])," + "\n"
    
    for port_idx in range(designParamsVar.POLY_LS_PORTS):
        line += "      tapa::read_write_mmap<POLY_WIDE_DATA>(portWiseOutData[" + str(port_idx) + "])," + "\n"
    
    for para_limb_idx in range(designParamsVar.PARA_LIMBS):
        line += "      workingModulus_arr[" + str(para_limb_idx) + "]," + "\n"
    
    for para_limb_idx in range(designParamsVar.PARA_LIMBS):
        line += "      twoInverse_arr[" + str(para_limb_idx) + "]," + "\n"
    
    for para_limb_idx in range(designParamsVar.PARA_LIMBS):
        prefix = "      "
        suffix = "[" + str(para_limb_idx) + "]," + "\n"
        line += modmul_funcCall_args(designParamsVar, prefix, suffix)

    line += "      direction," + "\n"
    line += "      iter" + "\n"
    line += "      );" + "\n"
    line += "  clog << \"kernel time: \" << kernel_time_ns * 1e-9 << \" s\\n\" << endl;" + "\n"
    line += "" + "\n"

    line += "  std::vector<WORD> kernelOutArr[PARA_LIMBS];" + "\n"
    line += "  fwd_reorganize_ports_to_output_poly(portWiseOutData, kernelOutArr);" + "\n"
    line += "" + "\n"

    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    status = compareResults(fwdVec_ref[paraLimbCounter], kernelOutArr[paraLimbCounter], size);" + "\n"
    line += "    if(status){" + "\n"
    line += "      printf(\"[Para limb %d]::Forward Kernel Execution Passed\\n\", (int)paraLimbCounter);" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      printf(\"[Para limb %d]::Forward Kernel Execution Failed\\n\", (int)paraLimbCounter);" + "\n"
    line += "      exit (1);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"

    line += "  printf(\"\\n\");" + "\n"
    line += "" + "\n"


    line += "  // INV" + "\n"
    line += "  direction = false;" + "\n"
    line += "" + "\n"

    line += "  // Poly data rearrangements" + "\n"
    line += "  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> inv_portWiseInPolyData[POLY_LS_PORTS];" + "\n"
    line += "  inv_reorganize_input_poly_to_ports(fwdVec_ref, inv_portWiseInPolyData);" + "\n"
    line += "" + "\n"
    line += "  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> inv_portWiseOutData[POLY_LS_PORTS];" + "\n"
    line += "  init_kernerl_output_ports(inv_portWiseOutData);" + "\n"
    line += "" + "\n"

    line += "  // TF data rearrangements" + "\n"
    line += "  std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> inv_portWiseInTFData[TF_PORTS];" + "\n"
    if( (designParamsVar.REDUCTION_TYPE==MONTGOMERY) or (designParamsVar.REDUCTION_TYPE==WLM) ): # in case montgomery, converted TFs have to be used
        line += "  reorganize_input_tfs_to_ports(inv_tfArr_montgomery, inv_portWiseInTFData, direction);" + "\n"
    else:
        line += "  reorganize_input_tfs_to_ports(inv_tfArr, inv_portWiseInTFData, direction);" + "\n"
    line += "" + "\n"

    line += "  printf(\"\\n===Inverse Computation===\\n\");" + "\n"
    line += "" + "\n"

    line += "  kernel_time_ns = tapa::invoke(" + "\n"
    line += "      NTT_kernel, FLAGS_bitstream, " + "\n"

    for port_idx in range(designParamsVar.POLY_LS_PORTS):
        line += "      tapa::read_write_mmap<POLY_WIDE_DATA>(inv_portWiseOutData[" + str(port_idx) + "])," + "\n"

    for port_idx in range(designParamsVar.TF_PORTS):
        line += "      tapa::read_only_mmap<TF_WIDE_DATA>(inv_portWiseInTFData[" + str(port_idx) + "])," + "\n"
    
    for port_idx in range(designParamsVar.POLY_LS_PORTS):
        line += "      tapa::read_write_mmap<POLY_WIDE_DATA>(inv_portWiseInPolyData[" + str(port_idx) + "])," + "\n"
    
    for para_limb_idx in range(designParamsVar.PARA_LIMBS):
        line += "      workingModulus_arr[" + str(para_limb_idx) + "]," + "\n"
    
    for para_limb_idx in range(designParamsVar.PARA_LIMBS):
        line += "      twoInverse_arr[" + str(para_limb_idx) + "]," + "\n"
    
    for para_limb_idx in range(designParamsVar.PARA_LIMBS):
        prefix = "      "
        suffix = "[" + str(para_limb_idx) + "]," + "\n"
        line += modmul_funcCall_args(designParamsVar, prefix, suffix)

    line += "      direction," + "\n"
    line += "      iter" + "\n"
    line += "      );" + "\n"
    line += "  clog << \"kernel time: \" << kernel_time_ns * 1e-9 << \" s\\n\" << endl;" + "\n"
    line += "" + "\n"

    line += "  std::vector<WORD> inv_kernelOutArr[PARA_LIMBS];" + "\n"
    line += "  inv_reorganize_ports_to_output_poly(inv_portWiseOutData, inv_kernelOutArr);" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    bitReverseVect(inv_kernelOutArr[paraLimbCounter], size);" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
    line += "    status = compareResults(invec[paraLimbCounter], inv_kernelOutArr[paraLimbCounter], size);" + "\n"
    line += "    if(status){" + "\n"
    line += "      printf(\"[Para limb %d]::Inverse Kernel Execution Passed\\n\", (int)paraLimbCounter);" + "\n"
    line += "    }" + "\n"
    line += "    else{" + "\n"
    line += "      printf(\"[Para limb %d]::Inverse Kernel Execution Failed\\n\", (int)paraLimbCounter);" + "\n"
    line += "      exit (1);" + "\n"
    line += "    }" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"

    line += "  printf(\"\\nRun completed\\n\");" + "\n"
    line += "" + "\n"
    line += "  return 0;" + "\n"
    line += "}" + "\n"

    return line