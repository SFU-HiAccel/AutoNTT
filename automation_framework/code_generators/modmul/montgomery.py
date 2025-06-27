import sys
from code_generators.modmul.config import MAP_TO_LUT_THRESHOLD, DSP_WIDTH0_CASE0, DSP_WIDTH1_CASE0, DSP_WIDTH0_CASE1, DSP_WIDTH1_CASE1


#This function calculates the number of DSP required to perform full
#multiplication of values with d0_size and d1_size.
#d0_size will be split in to word size of w0_size
#d1_size will be split in to word size of w1_size
def full_mul_dsp_count(d0_size, d1_size, w0_size, w1_size):

  #calc number of words
  d0_num_words = (d0_size + w0_size - 1)//w0_size
  d1_num_words = (d1_size + w1_size - 1)//w1_size

  #check if any word can be mapped to LUTs
  d0_LUT_en = False
  d1_LUT_en = False
  
  if( ( (d0_size % w0_size) > 0 ) and ( (d0_size % w0_size) <= MAP_TO_LUT_THRESHOLD ) ):
    d0_LUT_en = True

  if( ( (d1_size % w1_size) > 0 ) and ( (d1_size % w1_size) <= MAP_TO_LUT_THRESHOLD ) ):
    d1_LUT_en = True
    
  #calc the DSP count
  if( d0_LUT_en and d1_LUT_en ):
    dsp_count = (d0_num_words - 1) * (d1_num_words - 1)
  elif( d0_LUT_en ): #LUT mapping enabled for d0 split
    dsp_count = (d0_num_words - 1) * d1_num_words
  elif( d1_LUT_en ): #LUT mapping enabled for d1 split
    dsp_count = d0_num_words * (d1_num_words - 1)
  else: #no LUT mapping
    dsp_count = d0_num_words * d1_num_words
  
  return dsp_count, d0_LUT_en, d1_LUT_en

#This function calculates the number of DSP required to perform half
#multiplication of values with d0_size, d1_size and extract LSB mask_size bits.
#d0_size will be split in to word size of w0_size
#d1_size will be split in to word size of w1_size
#since only mask_size bits matter, splitting will be only done partially
#Note: This function is written considering (mask_size > d0_size) & (mask_size > d1_size) which
# is the case in barrette
def half_mul_dsp_count(d0_size, d1_size, w0_size, w1_size, mask_size):

  #calc number of words
  d0_num_words = (d0_size + w0_size - 1)//w0_size
  d1_num_words = (d1_size + w1_size - 1)//w1_size


  dsp_count = 0
  #calc the DSP count and check if any word can be mapped to LUTs

  d0_LUT_en = False
  d1_LUT_en = False
  for i in range(d0_num_words):
    for j in range(d1_num_words):
      d0_word_size = w0_size if ( ( d0_size - (i*w0_size) ) > w0_size ) else ( d0_size - (i*w0_size) )
      d1_word_size = w1_size if ( ( d1_size - (i*w1_size) ) > w1_size ) else ( d1_size - (i*w1_size) )

      shift_amount = i*w0_size + j*w1_size

      if( shift_amount < mask_size ): #need to do multiplication
        if( ( d0_word_size > 0 ) and ( d0_word_size <= MAP_TO_LUT_THRESHOLD ) ):
          d0_LUT_en = True
        if( ( d1_word_size > 0 ) and ( d1_word_size <= MAP_TO_LUT_THRESHOLD ) ):
          d1_LUT_en = True

        if( ( not(d0_LUT_en) and not(d1_LUT_en) ) ): #need a dsp to perform mul
          dsp_count+=1
  
  return dsp_count, d0_LUT_en, d1_LUT_en

#This function selects what is the minimu DSP and how it can be achived with minimum LUT usage
def select_option(dsp_count_arr, d0_LUT_en_arr, d1_LUT_en_arr):
  min_dsp = min(dsp_count_arr) # get the minimum dsp count

  min_dsp_idx = 0
  min_lut_count = 10  #assign big number to begin with
  for i in range(len(dsp_count_arr)):
    if( dsp_count_arr[i] == min_dsp ):
      #compute lut count in this selection
      if( d0_LUT_en_arr[i] and d1_LUT_en_arr[i] ): #both luts
        lut_count = 2
      elif( d0_LUT_en_arr[i] or d1_LUT_en_arr[i] ): #if either of them use luts
        lut_count = 1
      else:
        lut_count = 0
      
      #decide and assign
      if( lut_count < min_lut_count ): #if new lut count is less
        min_dsp_idx = i
        min_lut_count = lut_count
    
  return min_dsp_idx

def split_ap_uint(arg_str, d_size, DSP_WIDTH):
  num_words = (d_size+DSP_WIDTH-1)//DSP_WIDTH
  line = ""
  for i in range(num_words):
    word_size = DSP_WIDTH if ( ( d_size - (i*DSP_WIDTH) ) > DSP_WIDTH ) else ( d_size - (i*DSP_WIDTH) )
    line += "  ap_uint<" + str(word_size) + "> " + arg_str + "_" + str(i) + " = " + arg_str + " & ((1<<" + str(word_size) + ")-1);" + "\n"
    if(i<(num_words-1)):
      line += "  " + arg_str + " = " + arg_str + " >> " + str(word_size) + ";" + "\n"
  return line

def split_multiply(arg_str0, arg_str1, d_size0, d_size1, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, output_mask_size):
  num_words0 = (d_size0+DSP_WIDTH0-1)//DSP_WIDTH0
  num_words1 = (d_size1+DSP_WIDTH1-1)//DSP_WIDTH1
  line = ""
  for idx1 in range(num_words1):
    for idx0 in range(num_words0):
      word_size0 = DSP_WIDTH0 if ( ( d_size0 - (idx0*DSP_WIDTH0) ) > DSP_WIDTH0 ) else ( d_size0 - (idx0*DSP_WIDTH0) )
      word_size1 = DSP_WIDTH1 if ( ( d_size1 - (idx1*DSP_WIDTH1) ) > DSP_WIDTH1 ) else ( d_size1 - (idx1*DSP_WIDTH1) )
      output_word_size = word_size0 + word_size1
      shift_amount = idx0*DSP_WIDTH0 + idx1*DSP_WIDTH1
      mul_idx = num_words0*idx1 + idx0

      LUT_en0 = True if ( (word_size0>0) and (word_size0<=MAP_TO_LUT_THRESHOLD) ) else False
      LUT_en1 = True if ( (word_size1>0) and (word_size1<=MAP_TO_LUT_THRESHOLD) ) else False

      if(shift_amount<output_mask_size):
        line += "  ap_uint<" + str(output_word_size) + "> mul_" + str(mul_idx) + " = ((ap_uint<" + str(output_word_size) + ">)(" + arg_str0 + "_" + str(idx0) + ") * " + arg_str1 +  "_" + str(idx1) + "); //<<" + str(shift_amount) + "\n"
        if( LUT_en0 or LUT_en1 ):
          if( not(d0_LUT_en or d1_LUT_en) ):
            print("[ERROR]::Something wrong. Mapping to LUT has decided during the generation but not before\n")
            print("d_size0 = " + str(d_size0))
            print("d_size1 = " + str(d_size1))
            print("output_mask_size = " + str(output_mask_size))
            sys.exit()
          line += "#pragma HLS bind_op variable=mul_" + str(mul_idx) + " op=mul impl=fabric" + "\n"
        else:
          if( ( (d0_LUT_en) and ( idx0==(num_words0-1) )) or ( (d1_LUT_en) and ( idx1==(num_words1-1) ) ) ):
            print("[ERROR]::Something wrong. Mapping to LUT has decided before but here it is mapping to DSP\n")
            print("LUT_en0=" + str(LUT_en0) + ", LUT_en1=" + str(LUT_en1) + ", word_size0=" + str(word_size0) + ", word_size1=" + str(word_size1))
            sys.exit()
          line += "  #pragma HLS bind_op variable=mul_" + str(mul_idx) + " op=mul impl=dsp" + "\n"
    line += "\n"
  return line

def comb_multiply(d_size0, d_size1, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, output_size):
  num_words0 = (d_size0+DSP_WIDTH0-1)//DSP_WIDTH0
  num_words1 = (d_size1+DSP_WIDTH1-1)//DSP_WIDTH1

  first_mul_done = False

  line = ""
  for idx1 in range(num_words1):
    for idx0 in range(num_words0):
      shift_amount = idx0*DSP_WIDTH0 + idx1*DSP_WIDTH1
      mul_idx = num_words0*idx1 + idx0
      if(shift_amount<output_size):
        if(not(first_mul_done)):
          line += "( (((ap_uint<" + str(output_size) +">)mul_" + str(mul_idx) + ")<<" + str(shift_amount) + ")"
          first_mul_done = True
        else:
          line += " + (((ap_uint<" + str(output_size) +">)mul_" + str(mul_idx) + ")<<" + str(shift_amount) + ")"
  line += " )"
  
  return line

def gen_hardcoded_fullMul_1(d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en):
  output_size = d0_size + d1_size

  line = ""
  line += "ap_uint<" + str(output_size) + "> hardcoded_fullMul_" + str(d0_size) + "x" + str(d1_size) + "(ap_uint<" + str(d0_size) + "> u, ap_uint<" + str(d1_size) + "> v){" + "\n"
  line += "  #pragma HLS inline" + "\n"
  line += "" + "\n"
  line += split_ap_uint("u", d0_size, DSP_WIDTH0)
  line += "" + "\n"
  line += split_ap_uint("v", d1_size, DSP_WIDTH1)
  line += "  " + "\n"
  line += split_multiply("u", "v", d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, (d0_size+d1_size))
  line += "  " + "\n"
  line_comb = comb_multiply(d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, (d0_size+d1_size))
  line += "  ap_uint<" + str(output_size) + "> res = " + line_comb + ";" + "\n"
  line += "  return res;" + "\n"
  line += "}" + "\n"
  return line

def gen_hardcoded_lowerHalfMul_2(d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, out_size):
  output_size = out_size

  line = ""
  line += "ap_uint<" + str(output_size) + "> hardcoded_lowerHalfMul_" + str(d0_size) + "x" + str(d1_size) + "(ap_uint<" + str(d0_size) + "> u, ap_uint<" + str(d1_size) + "> v){" + "\n"
  line += "  #pragma HLS inline" + "\n"
  line += "" + "\n"
  line += split_ap_uint("u", d0_size, DSP_WIDTH0)
  line += "" + "\n"
  line += split_ap_uint("v", d1_size, DSP_WIDTH1)
  line += "  " + "\n"
  line += split_multiply("u", "v", d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, (output_size))
  line += "  " + "\n"
  line_comb = comb_multiply(d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, (output_size))
  line += "  ap_uint<" + str(output_size) + "> res = " + line_comb + " & WORD_SIZE_MASK;" + "\n"
  line += "  return res;" + "\n"
  line += "}" + "\n"
  return line

def default_multiplier_gen(ARG_SIZE0, ARG_SIZE1):
  # print("Processing Barrette Mul1: " + str(ARG_SIZE0) + " x " + str(ARG_SIZE1))

  DSP_WIDTH0_arr = [DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1, DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1]
  DSP_WIDTH1_arr = [DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1, DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1]
  dsp_count_arr = [0, 0, 0, 0]
  d0_LUT_en_arr = [False, False, False, False]
  d1_LUT_en_arr = [False, False, False, False]

  #get the dsp amount for case0
  dsp_count_arr[0], d0_LUT_en_arr[0], d1_LUT_en_arr[0] = full_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[0], DSP_WIDTH1_arr[0])
  # print("\tOption1: WORD Select (" + str(DSP_WIDTH0_arr[0]) + ", " + str(DSP_WIDTH1_arr[0]) + "): dsp_count=" + str(dsp_count_arr[0]) + " d0_LUT_en=" + str(d0_LUT_en_arr[0]) + " d1_LUT_en=" +str(d1_LUT_en_arr[0]))

  #get the dsp amount for case1
  dsp_count_arr[1], d0_LUT_en_arr[1], d1_LUT_en_arr[1] = full_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[1], DSP_WIDTH1_arr[1])
  # print("\tOption2: WORD Select (" + str(DSP_WIDTH0_arr[1]) + ", " + str(DSP_WIDTH1_arr[1]) + "): dsp_count=" + str(dsp_count_arr[1]) + " d0_LUT_en=" + str(d0_LUT_en_arr[1]) + " d1_LUT_en=" +str(d1_LUT_en_arr[1]))

  #get the dsp amount for case3
  dsp_count_arr[2], d0_LUT_en_arr[2], d1_LUT_en_arr[2] = full_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[2], DSP_WIDTH1_arr[2])
  # print("\tOption3: WORD Select (" + str(DSP_WIDTH0_arr[2]) + ", " + str(DSP_WIDTH1_arr[2]) + "): dsp_count=" + str(dsp_count_arr[2]) + " d0_LUT_en=" + str(d0_LUT_en_arr[2]) + " d1_LUT_en=" +str(d1_LUT_en_arr[2]))

  #get the dsp amount for case4
  dsp_count_arr[3], d0_LUT_en_arr[3], d1_LUT_en_arr[3] = full_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[3], DSP_WIDTH1_arr[3])
  # print("\tOption4: WORD Select (" + str(DSP_WIDTH0_arr[3]) + ", " + str(DSP_WIDTH1_arr[3]) + "): dsp_count=" + str(dsp_count_arr[3]) + " d0_LUT_en=" + str(d0_LUT_en_arr[3]) + " d1_LUT_en=" +str(d1_LUT_en_arr[3]))

  #decide which config to go with
  min_idx = select_option(dsp_count_arr, d0_LUT_en_arr, d1_LUT_en_arr)
  dsp_count = dsp_count_arr[min_idx]
  d0_LUT_en = d0_LUT_en_arr[min_idx]
  d1_LUT_en = d1_LUT_en_arr[min_idx]
  DSP_WIDTH0 = DSP_WIDTH0_arr[min_idx]
  DSP_WIDTH1 = DSP_WIDTH1_arr[min_idx]

  # print("\tSelection: WORD Select (" + str(DSP_WIDTH0) + ", " + str(DSP_WIDTH1) + "): dsp_count=" + str(dsp_count) + " d0_LUT_en=" + str(d0_LUT_en) + " d1_LUT_en=" +str(d1_LUT_en))
  # print("\n")

  line = gen_hardcoded_fullMul_1(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en)

  return dsp_count, line

# arg0 = data_size0, arg1 = data_size1, arg2=output_size
def half_multiplier_gen(ARG_SIZE0, ARG_SIZE1, OUT_SIZE):
  # print("Processing Barrette Mul2: " + str(ARG_SIZE0) + " x " + str(ARG_SIZE1) + " & ( (1 << " + str(WORD_SIZE) + " ) -1 )")

  DSP_WIDTH0_arr = [DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1, DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1]
  DSP_WIDTH1_arr = [DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1, DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1]
  dsp_count_arr = [0, 0, 0, 0]
  d0_LUT_en_arr = [False, False, False, False]
  d1_LUT_en_arr = [False, False, False, False]

  #get the dsp amount for case0
  dsp_count_arr[0], d0_LUT_en_arr[0], d1_LUT_en_arr[0] = half_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[0], DSP_WIDTH1_arr[0], OUT_SIZE)
  # print("\tOption1: WORD Select (" + str(DSP_WIDTH0_arr[0]) + ", " + str(DSP_WIDTH1_arr[0]) + "): dsp_count=" + str(dsp_count_arr[0]) + " d0_LUT_en=" + str(d0_LUT_en_arr[0]) + " d1_LUT_en=" +str(d1_LUT_en_arr[0]))

  #get the dsp amount for case1
  dsp_count_arr[1], d0_LUT_en_arr[1], d1_LUT_en_arr[1] = half_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[1], DSP_WIDTH1_arr[1], OUT_SIZE)
  # print("\tOption2: WORD Select (" + str(DSP_WIDTH0_arr[1]) + ", " + str(DSP_WIDTH1_arr[1]) + "): dsp_count=" + str(dsp_count_arr[1]) + " d0_LUT_en=" + str(d0_LUT_en_arr[1]) + " d1_LUT_en=" +str(d1_LUT_en_arr[1]))

  #get the dsp amount for case3
  dsp_count_arr[2], d0_LUT_en_arr[2], d1_LUT_en_arr[2] = half_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[2], DSP_WIDTH1_arr[2], OUT_SIZE)
  # print("\tOption3: WORD Select (" + str(DSP_WIDTH0_arr[2]) + ", " + str(DSP_WIDTH1_arr[2]) + "): dsp_count=" + str(dsp_count_arr[2]) + " d0_LUT_en=" + str(d0_LUT_en_arr[2]) + " d1_LUT_en=" +str(d1_LUT_en_arr[2]))

  #get the dsp amount for case4
  dsp_count_arr[3], d0_LUT_en_arr[3], d1_LUT_en_arr[3] = half_mul_dsp_count(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0_arr[3], DSP_WIDTH1_arr[3], OUT_SIZE)
  # print("\tOption4: WORD Select (" + str(DSP_WIDTH0_arr[3]) + ", " + str(DSP_WIDTH1_arr[3]) + "): dsp_count=" + str(dsp_count_arr[3]) + " d0_LUT_en=" + str(d0_LUT_en_arr[3]) + " d1_LUT_en=" +str(d1_LUT_en_arr[3]))
  #decide which config to go with
  min_idx = select_option(dsp_count_arr, d0_LUT_en_arr, d1_LUT_en_arr)
  dsp_count = dsp_count_arr[min_idx]
  d0_LUT_en = d0_LUT_en_arr[min_idx]
  d1_LUT_en = d1_LUT_en_arr[min_idx]
  DSP_WIDTH0 = DSP_WIDTH0_arr[min_idx]
  DSP_WIDTH1 = DSP_WIDTH1_arr[min_idx]

  # print("\tSelection: WORD Select (" + str(DSP_WIDTH0) + ", " + str(DSP_WIDTH1) + "): dsp_count=" + str(dsp_count) + " d0_LUT_en=" + str(d0_LUT_en) + " d1_LUT_en=" +str(d1_LUT_en))
  # print("\n")

  line = gen_hardcoded_lowerHalfMul_2(ARG_SIZE0, ARG_SIZE1, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en, OUT_SIZE)

  return dsp_count, line

def gen_montgomery_header(WORD_SIZE):
    
    line = ""
    line += "WORD montgomery_reduce(WORD u, WORD v, WORD q, WORD k) " + "\n"
    line += "{" + "\n"
    line += "  #pragma HLS inline" + "\n"
    line += "  " + "\n"
    line += "  DWORD product_uv;" + "\n"
    line += "  product_uv = hardcoded_fullMul_" + str(WORD_SIZE) + "x" + str(WORD_SIZE) + "(u,v);" + "\n"
    line += "" + "\n"
    line += "  TWORD uv_mul_k;" + "\n"
    line += "  WORD s = hardcoded_lowerHalfMul_" + str(WORD_SIZE*2) + "x" + str(WORD_SIZE) + "(product_uv,k);" + "\n"
    line += "" + "\n"
    line += "  DWORD s_mul_mod;" + "\n"
    line += "  // #pragma HLS bind_op variable=s_mul_mod op=mul impl=dsp latency=0" + "\n"
    line += "  s_mul_mod = hardcoded_fullMul_" + str(WORD_SIZE) + "x" + str(WORD_SIZE) + "(s,q);" + "\n"
    line += "" + "\n"
    line += "  DWORD_PLUS1 s_mul_mod_add_uv = product_uv + s_mul_mod;" + "\n"
    line += "" + "\n"
    line += "  WORD_PLUS1 t = (WORD_PLUS1)(s_mul_mod_add_uv >> WORD_SIZE);  // shift_montgomery = n" + "\n"
    line += "" + "\n"
    line += "	WORD res = ((WORD_PLUS1)(t) < (WORD_PLUS1)(q)) ? (WORD)(t) : (WORD)((WORD_PLUS1)(t) - (WORD_PLUS1)(q));" + "\n"
    line += "  return res; //convert_out(res, r_inverse, mod);" + "\n"
    line += "}" + "\n"

    return line

def gen_montgomery(WORD_SIZE):

    dsp_count0, line0 = default_multiplier_gen(WORD_SIZE, WORD_SIZE)

    dsp_count1, line1 = half_multiplier_gen(WORD_SIZE*2, WORD_SIZE, WORD_SIZE)

    line2 = gen_montgomery_header(WORD_SIZE)

    total_dsp = dsp_count0*2 + dsp_count1

    line = line0 + "\n" + line1 + "\n" + line2

    # print("\nTotal DSP = " + str(total_dsp))

    # print("\n==== Montgomery Reduction Code ====")
    # print("\n")
    # print(line)
    return line, total_dsp

def gen_montgomery_host_func_def():
  line = ""
  line += "void pre_computation_montgomery(WORD mod, uint8_t *shift_montgomery, WORD *r, WORD *r_inverse, WORD *k)" + "\n"
  line += "{" + "\n"
  line += "	if (mod < 3 || mod % 2 == 0) {" + "\n"
  line += "    printf(\"[Error]::Modulus must be an odd number at least 3\\n\");" + "\n"
  line += "    exit(1);" + "\n"
  line += "  }" + "\n"
  line += "" + "\n"
  line += "	// reducer" + "\n"
  line += "  *shift_montgomery = bit_length(mod);" + "\n"
  line += "  WORD_PLUS1 r_tmp = ((WORD_PLUS1)1U)<<(*shift_montgomery);" + "\n"
  line += "  *r_inverse = mod_inverse_pow2Num(*shift_montgomery, mod);" + "\n"
  line += "    " + "\n"
  line += "	// other precomputation" + "\n"
  line += "	*k = (WORD)((DWORD)((DWORD)((DWORD)(r_tmp)*(DWORD)(*r_inverse % mod)) - (DWORD)1) / (DWORD)(mod));" + "\n"
  line += "  *r = (WORD)((WORD_PLUS1)(r_tmp) - (WORD_PLUS1)(1));" + "\n"
  line += "  " + "\n"
  line += "  printf(\"\\nMontgomery details:\\n\");" + "\n"
  line += "  std::cout << \"r = \" << r_tmp << \", inverse of r = \" << *r_inverse << std::endl;" + "\n"
  line += "  std::cout << \"k = \" << *k << \", second r = \" << *r << std::endl;" + "\n"
  line += "}" + "\n"
  line += "" + "\n"

  line += "void pre_computation_montgomery_array(std::vector<WORD>& workingModulus_arr, std::vector<VAR_TYPE_8>& shift_montgomery, std::vector<WORD>& r, std::vector<WORD>& r_inverse, std::vector<WORD>& k){" + "\n"
  line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
  line += "    VAR_TYPE_8 shift_montgomery_val;" + "\n"
  line += "    WORD r_val, r_inverse_val, k_val;" + "\n"
  line += "    pre_computation_montgomery(workingModulus_arr[paraLimbCounter], &shift_montgomery_val, &r_val, &r_inverse_val, &k_val);" + "\n"
  line += "    shift_montgomery[paraLimbCounter] = shift_montgomery_val;" + "\n"
  line += "    r[paraLimbCounter] = r_val;" + "\n"
  line += "    r_inverse[paraLimbCounter] = r_inverse_val;" + "\n"
  line += "    k[paraLimbCounter] = k_val;" + "\n"
  line += "  }" + "\n"
  line += "}" + "\n"

  line += "WORD convert_in(WORD x, uint8_t shift_montgomery, WORD modulus) {" + "\n"
  line += "    return (WORD)((DWORD)((DWORD)(x) << (DWORD)(shift_montgomery)) % (DWORD)(modulus));  // return ((x << log2(r)) % modulus);" + "\n"
  line += "}" + "\n"
  line += "" + "\n"
  line += "void convert_in_array(std::vector<WORD>& inp1, std::vector<WORD>& inp1_montgomery, uint8_t shift_montgomery, WORD modulus) {" + "\n"
  line += "  for(int i=0;i<N/2;i++){" + "\n"
  line += "    inp1_montgomery.push_back(0);" + "\n"
  line += "  }" + "\n"
  line += "  for(int i=0; i<N/2; i++){" + "\n"
  line += "    inp1_montgomery[i] = convert_in(inp1[i], shift_montgomery, modulus);" + "\n"
  line += "  }" + "\n"
  line += "}" + "\n"

  line += "void convert_tfs_in_limbs_array_to_montgomery_form(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<WORD> (&outVec)[PARA_LIMBS], std::vector<VAR_TYPE_8>& shift_montgomery, std::vector<WORD>& workingModulus_arr){" + "\n"
  line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
  line += "    VAR_TYPE_32 size = inVec[paraLimbCounter].size();" + "\n"
  line += "    outVec[paraLimbCounter].resize(size);" + "\n"
  line += "    convert_in_array(inVec[paraLimbCounter], outVec[paraLimbCounter], shift_montgomery[paraLimbCounter], workingModulus_arr[paraLimbCounter]);" + "\n"
  line += "  }" + "\n"
  line += "}" + "\n"
  return line

def gen_montgomery_host_func_call():
  line = ""
  line += "  vector<VAR_TYPE_8> shift_montgomery(PARA_LIMBS);" + "\n"
  line += "  vector<WORD> r(PARA_LIMBS);" + "\n"
  line += "  vector<WORD> r_inverse(PARA_LIMBS);" + "\n"
  line += "  vector<WORD> k(PARA_LIMBS);" + "\n"
  line += "  pre_computation_montgomery_array(workingModulus_arr, shift_montgomery, r, r_inverse, k);" + "\n"

  line += "  " + "\n"
  line += "  //convert TFs into the montgomery form" + "\n"
  line += "  vector<WORD> tfArr_montgomery[PARA_LIMBS];" + "\n"
  line += "  vector<WORD> inv_tfArr_montgomery[PARA_LIMBS];" + "\n"
  line += "  convert_tfs_in_limbs_array_to_montgomery_form(tfArr, tfArr_montgomery, shift_montgomery, workingModulus_arr);" + "\n"
  line += "  convert_tfs_in_limbs_array_to_montgomery_form(inv_tfArr, inv_tfArr_montgomery, shift_montgomery, workingModulus_arr);" + "\n"
  return line

# WORD_SIZE = 52
# gen_montgomery(WORD_SIZE)
