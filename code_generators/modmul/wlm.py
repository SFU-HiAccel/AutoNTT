import sys
from code_generators.modmul.config import MAP_TO_LUT_THRESHOLD, DSP_WIDTH0_CASE0, DSP_WIDTH1_CASE0, DSP_WIDTH0_CASE1, DSP_WIDTH1_CASE1
from dse.dse_config import DSP_DATA_WIDTHS

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
            print(d_size0)
            print(d_size1)
            print(output_mask_size)
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

def gen_hardcoded_fullMul_0(d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en):
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

def gen_hardcoded_fullMul_1(d0_size, d1_size, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en):
  output_size = d0_size + d1_size

  line = ""
  line += "ap_uint<" + str(output_size) + "> WLM_mul_default_multiplier_" + str(d0_size) + "x" + str(d1_size) + "(ap_uint<" + str(d0_size) + "> u, ap_uint<" + str(d1_size) + "> v){" + "\n"
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

def full_mull_WORD_WORD(WORD_SIZE):
  # print("Processing Full Mul0: " + str(WORD_SIZE) + " x " + str(WORD_SIZE))

  DSP_WIDTH0_arr = [DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1, DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1]
  DSP_WIDTH1_arr = [DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1, DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1]
  dsp_count_arr = [0, 0, 0, 0]
  d0_LUT_en_arr = [False, False, False, False]
  d1_LUT_en_arr = [False, False, False, False]

  #get the dsp amount for case0
  dsp_count_arr[0], d0_LUT_en_arr[0], d1_LUT_en_arr[0] = full_mul_dsp_count(WORD_SIZE, WORD_SIZE, DSP_WIDTH0_arr[0], DSP_WIDTH1_arr[0])
  # print("\tOption1: WORD Select (" + str(DSP_WIDTH0_arr[0]) + ", " + str(DSP_WIDTH1_arr[0]) + "): dsp_count=" + str(dsp_count_arr[0]) + " d0_LUT_en=" + str(d0_LUT_en_arr[0]) + " d1_LUT_en=" +str(d1_LUT_en_arr[0]))

  #get the dsp amount for case1
  dsp_count_arr[1], d0_LUT_en_arr[1], d1_LUT_en_arr[1] = full_mul_dsp_count(WORD_SIZE, WORD_SIZE, DSP_WIDTH0_arr[1], DSP_WIDTH1_arr[1])
  # print("\tOption2: WORD Select (" + str(DSP_WIDTH0_arr[1]) + ", " + str(DSP_WIDTH1_arr[1]) + "): dsp_count=" + str(dsp_count_arr[1]) + " d0_LUT_en=" + str(d0_LUT_en_arr[1]) + " d1_LUT_en=" +str(d1_LUT_en_arr[1]))

  #get the dsp amount for case3
  dsp_count_arr[2], d0_LUT_en_arr[2], d1_LUT_en_arr[2] = full_mul_dsp_count(WORD_SIZE, WORD_SIZE, DSP_WIDTH0_arr[2], DSP_WIDTH1_arr[2])
  # print("\tOption3: WORD Select (" + str(DSP_WIDTH0_arr[2]) + ", " + str(DSP_WIDTH1_arr[2]) + "): dsp_count=" + str(dsp_count_arr[2]) + " d0_LUT_en=" + str(d0_LUT_en_arr[2]) + " d1_LUT_en=" +str(d1_LUT_en_arr[2]))

  #get the dsp amount for case4
  dsp_count_arr[3], d0_LUT_en_arr[3], d1_LUT_en_arr[3] = full_mul_dsp_count(WORD_SIZE, WORD_SIZE, DSP_WIDTH0_arr[3], DSP_WIDTH1_arr[3])
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

  line = gen_hardcoded_fullMul_0(WORD_SIZE, WORD_SIZE, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en)

  return dsp_count, line

def WLM_mul_default_multiplier(MULTIPLIER_SIZE, WLM_WORD_SIZE):
  # print("Processing Barrette Mul1: " + str(MULTIPLIER_SIZE) + " x " + str(WLM_WORD_SIZE))

  DSP_WIDTH0_arr = [DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1, DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1]
  DSP_WIDTH1_arr = [DSP_WIDTH1_CASE0, DSP_WIDTH1_CASE1, DSP_WIDTH0_CASE0, DSP_WIDTH0_CASE1]
  dsp_count_arr = [0, 0, 0, 0]
  d0_LUT_en_arr = [False, False, False, False]
  d1_LUT_en_arr = [False, False, False, False]

  #get the dsp amount for case0
  dsp_count_arr[0], d0_LUT_en_arr[0], d1_LUT_en_arr[0] = full_mul_dsp_count(MULTIPLIER_SIZE, WLM_WORD_SIZE, DSP_WIDTH0_arr[0], DSP_WIDTH1_arr[0])
  # print("\tOption1: WORD Select (" + str(DSP_WIDTH0_arr[0]) + ", " + str(DSP_WIDTH1_arr[0]) + "): dsp_count=" + str(dsp_count_arr[0]) + " d0_LUT_en=" + str(d0_LUT_en_arr[0]) + " d1_LUT_en=" +str(d1_LUT_en_arr[0]))

  #get the dsp amount for case1
  dsp_count_arr[1], d0_LUT_en_arr[1], d1_LUT_en_arr[1] = full_mul_dsp_count(MULTIPLIER_SIZE, WLM_WORD_SIZE, DSP_WIDTH0_arr[1], DSP_WIDTH1_arr[1])
  # print("\tOption2: WORD Select (" + str(DSP_WIDTH0_arr[1]) + ", " + str(DSP_WIDTH1_arr[1]) + "): dsp_count=" + str(dsp_count_arr[1]) + " d0_LUT_en=" + str(d0_LUT_en_arr[1]) + " d1_LUT_en=" +str(d1_LUT_en_arr[1]))

  #get the dsp amount for case3
  dsp_count_arr[2], d0_LUT_en_arr[2], d1_LUT_en_arr[2] = full_mul_dsp_count(MULTIPLIER_SIZE, WLM_WORD_SIZE, DSP_WIDTH0_arr[2], DSP_WIDTH1_arr[2])
  # print("\tOption3: WORD Select (" + str(DSP_WIDTH0_arr[2]) + ", " + str(DSP_WIDTH1_arr[2]) + "): dsp_count=" + str(dsp_count_arr[2]) + " d0_LUT_en=" + str(d0_LUT_en_arr[2]) + " d1_LUT_en=" +str(d1_LUT_en_arr[2]))

  #get the dsp amount for case4
  dsp_count_arr[3], d0_LUT_en_arr[3], d1_LUT_en_arr[3] = full_mul_dsp_count(MULTIPLIER_SIZE, WLM_WORD_SIZE, DSP_WIDTH0_arr[3], DSP_WIDTH1_arr[3])
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

  line = gen_hardcoded_fullMul_1(MULTIPLIER_SIZE, WLM_WORD_SIZE, DSP_WIDTH0, DSP_WIDTH1, d0_LUT_en, d1_LUT_en)

  return dsp_count, line

def gen_wlm_header(WORD_SIZE, WLM_WORD_SIZE, MULTIPLIER_SIZE):
    num_iter = (WORD_SIZE+WLM_WORD_SIZE-1)//WLM_WORD_SIZE
    small_word_size = WLM_WORD_SIZE

    line = ""
    line += "WORD wlm_reduce(WORD u, WORD v, WORD q, WORD multiplier) " + "\n"
    line += "{" + "\n"
    line += "  #pragma HLS inline" + "\n"
    line += "  " + "\n"
    line += "  DWORD product_uv;" + "\n"
    line += "  product_uv = hardcoded_fullMul_" + str(WORD_SIZE) + "x" + str(WORD_SIZE) + "(u,v);" + "\n"
    line += "" + "\n"
    line += "  //==== Iteration 0 ====" + "\n"
    line += "  DWORD t0_h = product_uv >> " + str(small_word_size) + ";" + "\n"
    line += "  WLM_WORD t0_l = product_uv % (((WORD)1)<<" + str(small_word_size) + ");" + "\n"
    line += "" + "\n"
    line += "  WLM_WORD t0_i = ((((WORD)1)<<" + str(small_word_size) + ") - t0_l) % (((WORD)1)<<" + str(small_word_size) + ");" + "\n"
    line += "  " + "\n"
    line += "  WLM_WORD carry_0 = t0_i.range(" + str(small_word_size-1) + "," + str(small_word_size-1) + ") | t0_l.range(" + str(small_word_size-1) + "," + str(small_word_size-1) + ");" + "\n"
    line += "" + "\n"
    line += "  DWORD t1 = t0_h + WLM_mul_default_multiplier_" + str(MULTIPLIER_SIZE) + "x" + str(WLM_WORD_SIZE) + "(multiplier, t0_i) + carry_0;" + "\n"
    line += "\n"
    for iter in range(1, num_iter):
        
        small_word_size = (WLM_WORD_SIZE) if(((WORD_SIZE-((iter)*WLM_WORD_SIZE))>=WLM_WORD_SIZE)) else (WORD_SIZE-((iter)*WLM_WORD_SIZE))
        line += "  //==== Iteration " + str(iter) + " ====" + "\n"
        line += "  DWORD t" + str(iter) + "_h = t" + str(iter) + " >> " + str(small_word_size) + ";" + "\n"
        line += "  WLM_WORD t" + str(iter) + "_l = t" + str(iter) + " % (((WORD)1)<<" + str(small_word_size) + ");" + "\n"
        line += "" + "\n"
        line += "  WLM_WORD t" + str(iter) + "_i = ((((WORD)1)<<" + str(small_word_size) + ") - t" + str(iter) + "_l) % (((WORD)1)<<" + str(small_word_size) + ");" + "\n"
        line += "  " + "\n"
        line += "  WLM_WORD carry_" + str(iter) + " = t" + str(iter) + "_i.range(" + str(small_word_size-1) + "," + str(small_word_size-1) + ") | t" + str(iter) + "_l.range(" + str(small_word_size-1) + "," + str(small_word_size-1) + ");" + "\n"
        line += "  " + "\n"
        if(small_word_size!=WLM_WORD_SIZE):
            line += "  WORD mod_multiplier = multiplier << (WLM_WORD_SIZE-" + str(small_word_size) + ");" + "\n"
            line += "" + "\n"
            line += "  DWORD t" + str(iter+1) + " = t" + str(iter) + "_h + WLM_mul_default_multiplier_" + str(MULTIPLIER_SIZE+(WLM_WORD_SIZE-small_word_size)) + "x" + str(small_word_size) + "(mod_multiplier, t" + str(iter) + "_i) + carry_" + str(iter) + ";" + "\n"
        else:
            line += "  DWORD t" + str(iter+1) + " = t" + str(iter) + "_h + WLM_mul_default_multiplier_" + str(MULTIPLIER_SIZE) + "x" + str(WLM_WORD_SIZE) + "(multiplier, t" + str(iter) + "_i) + carry_" + str(iter) + ";" + "\n"
        line += "\n"

    line += "  DWORD t" + str(num_iter+1) + " = t" + str(num_iter) + "-q;" + "\n"
    line += "  WORD res;" + "\n"
    line += "  if(t" + str(num_iter) + "<q){" + "\n"
    line += "    res = t" + str(num_iter) + ";" + "\n"
    line += "  }" + "\n"
    line += "  else{" + "\n"
    line += "    res = t" + str(num_iter+1) + ";" + "\n"
    line += "  }" + "\n"
    line += "" + "\n"
    line += "  return (WORD)res;" + "\n"
    line += "}" + "\n"

    return line

def gen_wlm(WORD_SIZE, WLM_WORD_SIZE):

    num_iter = (WORD_SIZE+WLM_WORD_SIZE-1)//WLM_WORD_SIZE

    MULTIPLIER_SIZE = WORD_SIZE - WLM_WORD_SIZE

    dsp_count0, line0 = full_mull_WORD_WORD(WORD_SIZE)

    dsp_count1, line1 = WLM_mul_default_multiplier(MULTIPLIER_SIZE, WLM_WORD_SIZE)

    #check if partial mul exist
    partial_mul_en = True if ( (WORD_SIZE%WLM_WORD_SIZE)!=0 ) else False

    if(partial_mul_en):
        final_small_word_size = WORD_SIZE % WLM_WORD_SIZE
        MOD_MULTIPLIER_WORD_SIZE = MULTIPLIER_SIZE + (WLM_WORD_SIZE-final_small_word_size)
        dsp_count2, line2 = WLM_mul_default_multiplier(MOD_MULTIPLIER_WORD_SIZE, final_small_word_size)
    else:
        dsp_count2 = 0
        line2 = ""

    line3 = gen_wlm_header(WORD_SIZE, WLM_WORD_SIZE, MULTIPLIER_SIZE)

    if(partial_mul_en):
        total_dsp = dsp_count0 + dsp_count1*(num_iter-1) + dsp_count2
    else:
        total_dsp = dsp_count0 + dsp_count1*num_iter

    line = line0 + "\n" + line1 + "\n" + line2 + "\n" + line3

    # print("\nTotal DSP = " + str(total_dsp))

    # print("\n==== Barrette Reduction Code ====")
    # print("\n")
    # print(line)
    return line, total_dsp

def gen_wlm_host_func_def():
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
  line += "" + "\n"

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
  line += "" + "\n"

  line += "void convert_tfs_in_limbs_array_to_montgomery_form(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<WORD> (&outVec)[PARA_LIMBS], std::vector<VAR_TYPE_8>& shift_montgomery, std::vector<WORD>& workingModulus_arr){" + "\n"
  line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
  line += "    VAR_TYPE_32 size = inVec[paraLimbCounter].size();" + "\n"
  line += "    outVec[paraLimbCounter].resize(size);" + "\n"
  line += "    convert_in_array(inVec[paraLimbCounter], outVec[paraLimbCounter], shift_montgomery[paraLimbCounter], workingModulus_arr[paraLimbCounter]);" + "\n"
  line += "  }" + "\n"
  line += "}" + "\n"
  line += "" + "\n"

  line += "WORD WLM_find_multiplier(WORD mod){" + "\n"
  line += "  if((mod-1)%(((WORD_PLUS1)1)<<WLM_WORD_SIZE)!=0){" + "\n"
  line += "    std::cout << \"[ERROR]:: The modulus \" << mod << \" can not be divided by WLM word size \" << WLM_WORD_SIZE << std::endl;" + "\n"
  line += "    exit(1);" + "\n"
  line += "  }" + "\n"
  line += "  WORD multiplier = (mod-1)/(((WORD_PLUS1)1)<<WLM_WORD_SIZE);" + "\n"
  line += "  return multiplier;" + "\n"
  line += "}" + "\n"
  line += "" + "\n"

  line += "void WLM_find_multiplier_arr(std::vector<WORD>& workingModulus_arr, std::vector<WLM_MULTIPLIER_WORD>& multiplier_arr){" + "\n"
  line += "  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){" + "\n"
  line += "    multiplier_arr[paraLimbCounter] = WLM_find_multiplier(workingModulus_arr[paraLimbCounter]);" + "\n"
  line += "    std::cout << \"WLM multiplier[\" << paraLimbCounter << \"] = \" << multiplier_arr[paraLimbCounter] << std::endl;" + "\n"
  line += "  }" + "\n"
  line += "}" + "\n"
  line += "" + "\n"

  return line

def gen_wlm_host_func_call():
  line = ""
  line += "  vector<VAR_TYPE_8> shift_montgomery(PARA_LIMBS);" + "\n"
  line += "  vector<WORD> r(PARA_LIMBS);" + "\n"
  line += "  vector<WORD> r_inverse(PARA_LIMBS);" + "\n"
  line += "  vector<WORD> k(PARA_LIMBS);" + "\n"
  line += "  pre_computation_montgomery_array(workingModulus_arr, shift_montgomery, r, r_inverse, k);" + "\n"
  line += "  vector<WLM_MULTIPLIER_WORD> multiplier(PARA_LIMBS);" + "\n"
  line += "  WLM_find_multiplier_arr(workingModulus_arr, multiplier);" + "\n"
  line += "  " + "\n"

  line += "  //convert TFs into the montgomery form" + "\n"
  line += "  vector<WORD> tfArr_montgomery[PARA_LIMBS];" + "\n"
  line += "  vector<WORD> inv_tfArr_montgomery[PARA_LIMBS];" + "\n"
  line += "  convert_tfs_in_limbs_array_to_montgomery_form(tfArr, tfArr_montgomery, shift_montgomery, workingModulus_arr);" + "\n"
  line += "  convert_tfs_in_limbs_array_to_montgomery_form(inv_tfArr, inv_tfArr_montgomery, shift_montgomery, workingModulus_arr);" + "\n"

  return line

def gen_wlm_header_file_definitions(WLM_WORD_SIZE):
  line = ""
  line += "\n"
  line += "// WLM related" + "\n"
  line += "const VAR_TYPE_8 WLM_WORD_SIZE=" + str(WLM_WORD_SIZE) + ";" + "\n"
  line += "#define WLM_WORD ap_uint<WLM_WORD_SIZE>" + "\n"
  line += "#define WLM_MULTIPLIER_WORD ap_uint<WORD_SIZE-WLM_WORD_SIZE>" + "\n"
  line += "\n"
  return line


# WORD_SIZE = 30
# WLM_WORD_SIZE = 16
# gen_wlm(WORD_SIZE, WLM_WORD_SIZE)