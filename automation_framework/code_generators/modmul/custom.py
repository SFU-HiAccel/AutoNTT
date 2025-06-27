def gen_custom_red(designParamsVar):

  code = designParamsVar.CUSTOM_REDUCTION_CONTENT["kernel_defs"]

  return code

def gen_custom_red_mod_gen_host_func_def(designParamsVar):
  code = designParamsVar.CUSTOM_REDUCTION_CONTENT["host_mod_gen_defs"]
  return code

def gen_custom_red_host_func_def(designParamsVar):
  code = designParamsVar.CUSTOM_REDUCTION_CONTENT["host_reduction_defs"]
  return code

def gen_custom_red_mod_gen_host_func_call(designParamsVar):
  code = designParamsVar.CUSTOM_REDUCTION_CONTENT["host_mod_gen_call"]
  return code

def gen_custom_red_host_func_call(designParamsVar):
  code = designParamsVar.CUSTOM_REDUCTION_CONTENT["host_reduction_call"]
  return code

def gen_custom_red_header_file_definitions(designParamsVar):
  code = designParamsVar.CUSTOM_REDUCTION_CONTENT["header_code"]
  return code

# WORD_SIZE = 52

# print("WORD_SIZE = " + str(WORD_SIZE) + "\n")
# code, total_dsp = gen_barrett(WORD_SIZE)
# print(code)