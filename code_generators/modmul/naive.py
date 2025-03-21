import sys
from code_generators.modmul.config import MAP_TO_LUT_THRESHOLD, DSP_WIDTH0_CASE0, DSP_WIDTH1_CASE0, DSP_WIDTH0_CASE1, DSP_WIDTH1_CASE1

#####################

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
  line += "ap_uint<" + str(output_size) + "> hardcoded_fullMul_0(ap_uint<" + str(d0_size) + "> u, ap_uint<" + str(d1_size) + "> v){" + "\n"
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

def gen_naive_reduce():
  line = ""
  line += "WORD naive_reduce(WORD u, WORD v, WORD mod)" + "\n"
  line += "{" + "\n"
  line += "  #pragma HLS inline" + "\n"
  line += "" + "\n"
  line += "  DWORD U = hardcoded_fullMul_0(u,v);" + "\n"
  line += "  WORD result = (WORD)(U % (DWORD)mod);" + "\n"
  line += "	return (WORD)result;" + "\n"
  line += "}" + "\n"
  return line

def mul_0_full_mull_WORD_WORD(WORD_SIZE):
  # print("Processing Barrett Mul0: " + str(WORD_SIZE) + " x " + str(WORD_SIZE))

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

def gen_naive(WORD_SIZE):

  WORD_PLUS1_SIZE = WORD_SIZE + 1

  dsp_count0, line0 = mul_0_full_mull_WORD_WORD(WORD_SIZE)

  line1 = gen_naive_reduce()

  total_dsp = dsp_count0
  line = line0 + "\n" + line1

  # print("\nTotal DSP = " + str(total_dsp))

  # print("\n==== Barrett Reduction Code ====")
  # print("\n")
  # print(line)
  return line, total_dsp

# WORD_SIZE = 52

# print("WORD_SIZE = " + str(WORD_SIZE) + "\n")
# code, total_dsp = gen_barrett(WORD_SIZE)
# print(code)