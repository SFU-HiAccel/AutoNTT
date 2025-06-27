from code_generators.hybrid.shuffler.shuffler_in import gen_shuffler_in
from code_generators.hybrid.shuffler.shuffler_buf import gen_shuffler_buf
from code_generators.hybrid.shuffler.shuffler_out_shift import gen_shuffler_out_shift
from code_generators.hybrid.shuffler.shuffler_out_shuff import gen_shuffler_out_shuff
from code_generators.hybrid.shuffler.comb_shuffler import gen_comb_shuffler_tasks

####
# This is the shuffler task
# Generating shuffler task should handle a couple of cases
# 1. In the case of larger designs, we will use a split shuffler. i.e., shuffler_in, shuffler_buf_split, shuffler_out_shitf, shuffler_out_shuf
# 2. In the case of moderately larger designs, we will use a split shuffler with combined buffer. i.e., shuffler_in, shuffler_buf_comb, shuffler_out_shitf, shuffler_out_shuf
# 3. In the case of smaller designs, we will use a combined shuffler. i.e., shuffler(shuffler_in, shuffler_buf_comb, shuffler_out_shitf), shuffler_out_shuf
# 4. In the case of single BUG designs, we don't have inter BUG communication in shuffler_out_shuf.
# So this function will take care of generating control signals for these scenarios.
####
def gen_shuffler_control(designParamsVar):
    # Define variables to handle above described cases
    is_split_shuffler = True
    is_split_buffer = True
    is_inter_BUG_connections = True

    # Set variables based on the scenarios. These scenarios are set based on the heuristics
    # TODO: fine tune decision criteria
    
    if(designParamsVar.BUG_CONCAT_FACTOR==1): #single BUG
        is_inter_BUG_connections = False
    else:
        is_inter_BUG_connections = True

    if(designParamsVar.V_BUG_SIZE>16): #very large BUG
        is_split_shuffler = True
        is_split_buffer = True
    if(designParamsVar.V_BUG_SIZE>4): #Somewhat moderately large
        is_split_shuffler = True
        if(designParamsVar.WORD_SIZE>36):
            is_split_buffer = True
        else:
            is_split_buffer = False
    else:
        is_split_shuffler = False
        is_split_buffer = False

    return is_split_shuffler, is_split_buffer, is_inter_BUG_connections


####
# Generate shuffler based on different scenarios
####
def gen_shuffler(designParamsVar):
    
    # generate control signals to handle different shuffler scenarios
    is_split_shuffler, is_split_buffer, is_inter_BUG_connections = designParamsVar.IS_SPLIT_SHUFFLER, designParamsVar.IS_SPLIT_BUFFER, designParamsVar.IS_INTER_BUG_CONNECTIONS

    line = ""

    if(is_split_shuffler):
        line += gen_shuffler_in(designParamsVar)
        line += "\n"
        line += gen_shuffler_buf(designParamsVar, is_split_buffer)
        line += "\n"
        line += gen_shuffler_out_shift(designParamsVar, is_inter_BUG_connections)
        line += "\n"
        line += gen_shuffler_out_shuff(designParamsVar, is_inter_BUG_connections)
        line += "\n"
    else:
        line += gen_comb_shuffler_tasks(designParamsVar)
        line += "\n"
        line += gen_shuffler_out_shuff(designParamsVar, is_inter_BUG_connections)
        line += "\n"
        

    #     if(is_split_buffer):
    #         gen_split_shuffler_buf
    #     else:
    #         gen_comb_shuffler_buf
    #     if(is_inter_BUG_connections):
    #         gen_shuffler_out_shift_wi_inter_BUG_com
    #         gen_shuffler_out_shuf_wi_inter_BUG_com
    #     else:
    #         gen_shuffler_out_shift_wo_inter_BUG_com
    #         gen_shuffler_out_shuf_wo_inter_BUG_com
    # else:
    #     gen_comb_shuffler

    return line
