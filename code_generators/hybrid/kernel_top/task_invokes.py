from code_generators.modmul.config import modmul_funcCall_args
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

from code_generators.hybrid.shuffler.shuffler_out_shuff import gen_shuffler_out_shuff_config

from code_generators.hybrid.poly_load_store.poly_load_store import gen_poly_load_store_configs
from code_generators.hybrid.TFs.TF_load import gen_tf_load_configs

from code_generators.hybrid.flow_controllers.dual_interface_FIFO import gen_dual_interface_FIFO_split_logic


def gen_fwd_load_inv_store_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs):

    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.BUG_PER_PARA_LIMB_POLY_PORT
    BUG_PER_PARA_LIMB_POLY_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    SEQ_BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.SEQ_BUG_PER_PARA_LIMB_POLY_PORT
    num_of_stream_groups_per_BUG = (2*designParamsVar.V_BUG_SIZE) // designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT

    line = ""

    line += "        .invoke(fwd_load_inv_store_poly_" + str(para_num_limbs) + "_limbs, polyVectorInOut_G" + str(port_idx) + ", "
    
    # deciding number of streams coming from/going to the task similar to the condition in poly_load_store/poly_load_store.py
    if( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ): # if this is the case, that means one port is supporting only one BUG. i.e., either multiple ports have to support the streams required for entire BUG or have to do sequentially 
        # INV FIFO inputs for data storing
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for seq_BUG_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) // num_of_stream_groups_per_BUG
                group_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) % num_of_stream_groups_per_BUG
                line += "inv_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(group_idx) + ", "

        # FWD FIFO output for data loading
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for seq_BUG_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) // num_of_stream_groups_per_BUG
                group_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) % num_of_stream_groups_per_BUG
                line += "fwd_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(group_idx) + ", "

    else: # if this is the case, that means one port is supporting many BUGs. Hence, can support all the streams of one BUG for sure.
        # INV FIFO inputs for data storing
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for local_BUG_idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (BUG_PER_PARA_LIMB_POLY_PORT * local_port_idx_per_para_limb) + local_BUG_idx # calculate actual BUG idx based on the port
                line += "inv_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
    
        # FWD FIFO output for data loading
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for local_BUG_idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (BUG_PER_PARA_LIMB_POLY_PORT * local_port_idx_per_para_limb) + local_BUG_idx # calculate actual BUG idx based on the port
                line += "fwd_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "

    # other constants
    line += "direction, iter)" + "\n"
    
    return line

def gen_fwd_load_inv_store(designParamsVar):

    POLY_LS_PORTS = designParamsVar.POLY_LS_PORTS
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    is_full_load_store_needed, is_partial_load_store_needed, partial_load_store_size = gen_poly_load_store_configs(designParamsVar)

    line = ""

    if(POLY_LS_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_load_store_needed) and is_partial_load_store_needed ) : #only one partial load
            port_idx = 0
            local_port_idx_per_para_limb = 0
            para_limb_base = 0
            para_num_limbs = partial_load_store_size
            line += gen_fwd_load_inv_store_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        elif( is_full_load_store_needed and is_partial_load_store_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_counter in range(POLY_LS_PORTS-1): 
                port_idx = port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
                line += gen_fwd_load_inv_store_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)
            
            #partial loads
            port_idx = (POLY_LS_PORTS-1)
            local_port_idx_per_para_limb = 0
            para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*(POLY_LS_PORTS-1)
            para_num_limbs = partial_load_store_size
            line += gen_fwd_load_inv_store_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        else: # only full load
            for port_counter in range(POLY_LS_PORTS): 
                port_idx = port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
                line += gen_fwd_load_inv_store_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    else: #For a single limb, it requires multiple ports
        for port_counter in range(POLY_LS_PORTS):
            port_idx = port_counter
            local_port_idx_per_para_limb = port_counter % POLY_LS_PORTS_PER_PARA_LIMB
            para_limb_base = port_counter//POLY_LS_PORTS_PER_PARA_LIMB
            para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
            line += gen_fwd_load_inv_store_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    return line


def gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs):

    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.BUG_PER_PARA_LIMB_POLY_PORT
    BUG_PER_PARA_LIMB_POLY_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    SEQ_BUG_PER_PARA_LIMB_POLY_PORT = designParamsVar.SEQ_BUG_PER_PARA_LIMB_POLY_PORT
    num_of_stream_groups_per_BUG = (2*designParamsVar.V_BUG_SIZE) // designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT

    line = ""

    line += "        .invoke(fwd_store_inv_load_poly_" + str(para_num_limbs) + "_limbs, polyVectorInOut_G" + str(port_idx) + ", "
    
    # deciding number of streams coming from/going to the task similar to the condition in poly_load_store/poly_load_store.py
    if( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ): # if this is the case, that means one port is supporting only one BUG. i.e., either multiple ports have to support the streams required for entire BUG or have to do sequentially 
        # FWD FIFO output for data storing
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for seq_BUG_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) // num_of_stream_groups_per_BUG
                group_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) % num_of_stream_groups_per_BUG
                line += "fwd_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(group_idx) + ", "

        # INV FIFO input for data loading
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for seq_BUG_idx in range(SEQ_BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) // num_of_stream_groups_per_BUG
                group_idx = (local_port_idx_per_para_limb*SEQ_BUG_PER_PARA_LIMB_POLY_PORT+seq_BUG_idx) % num_of_stream_groups_per_BUG
                line += "inv_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(group_idx) + ", "

    else: # if this is the case, that means one port is supporting many BUGs. Hence, can support all the streams of one BUG for sure.
        # FWD FIFO inputs for data storing
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for local_BUG_idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (BUG_PER_PARA_LIMB_POLY_PORT * local_port_idx_per_para_limb) + local_BUG_idx # calculate actual BUG idx based on the port
                line += "fwd_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
    
        # INV FIFO output for data loading
        for para_limb_counter in range(para_num_limbs):
            para_limb_idx = para_limb_base + para_limb_counter
            for local_BUG_idx in range(BUG_PER_PARA_LIMB_POLY_PORT):
                BUG_idx = (BUG_PER_PARA_LIMB_POLY_PORT * local_port_idx_per_para_limb) + local_BUG_idx # calculate actual BUG idx based on the port
                line += "inv_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "

    # other constants
    line += "direction, iter)" + "\n"
    
    return line

def gen_fwd_store_inv_load(designParamsVar):

    POLY_LS_PORTS = designParamsVar.POLY_LS_PORTS
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    is_full_load_store_needed, is_partial_load_store_needed, partial_load_store_size = gen_poly_load_store_configs(designParamsVar)

    line = ""

    if(POLY_LS_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_load_store_needed) and is_partial_load_store_needed ) : #only one partial load
            port_idx = POLY_LS_PORTS + 0
            local_port_idx_per_para_limb = 0
            para_limb_base = 0
            para_num_limbs = partial_load_store_size
            line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        elif( is_full_load_store_needed and is_partial_load_store_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_counter in range(POLY_LS_PORTS-1): 
                port_idx = POLY_LS_PORTS + port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
                line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)
            
            #partial loads
            port_idx = POLY_LS_PORTS + (POLY_LS_PORTS-1)
            local_port_idx_per_para_limb = 0
            para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*(POLY_LS_PORTS-1)
            para_num_limbs = partial_load_store_size
            line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        else: # only full load
            for port_counter in range(POLY_LS_PORTS): 
                port_idx = POLY_LS_PORTS + port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
                line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    else: #For a single limb, it requires multiple ports
        for port_counter in range(POLY_LS_PORTS):
            port_idx = POLY_LS_PORTS + port_counter
            local_port_idx_per_para_limb = port_counter % POLY_LS_PORTS_PER_PARA_LIMB
            para_limb_base = port_counter//POLY_LS_PORTS_PER_PARA_LIMB
            para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
            line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    return line


def gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs):
    TF_PORTS_PER_PARA_LIMB = designParamsVar.TF_PORTS_PER_PARA_LIMB
    TF_LOAD_H_SEGS_PER_PARA_LIMB = designParamsVar.TF_LOAD_H_SEGS_PER_PARA_LIMB
    num_ports_per_seg = TF_PORTS_PER_PARA_LIMB//TF_LOAD_H_SEGS_PER_PARA_LIMB

    line = ""
    
    seg_idx = local_port_idx_per_para_limb//num_ports_per_seg   # each horizontal segment has different data load counts
    line += "        .invoke(Mmap2Stream_tf_" + str(seg_idx) + "_" + str(para_num_limbs) + "_limbs, TFArr_G" + str(port_idx) + ", "
    for para_limb_counter in range(para_num_limbs):
        para_limb_idx = para_limb_base + para_limb_counter
        line += "tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(local_port_idx_per_para_limb) + "_0,"
    line += " direction, iter)" + "\n"

    return line

def gen_mmap2Stream_tf(designParamsVar):
    TF_PORTS = designParamsVar.TF_PORTS
    TF_PORTS_PER_PARA_LIMB = designParamsVar.TF_PORTS_PER_PARA_LIMB
    PARA_LIMB_PORTS_PER_TF_PORT = designParamsVar.PARA_LIMB_PORTS_PER_TF_PORT

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_tf_load_configs(designParamsVar)

    line = ""

    if(TF_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_load_needed) and is_partial_load_needed ) : #only one partial load
            port_idx = 0
            local_port_idx_per_para_limb = 0
            para_limb_base = 0
            para_num_limbs = partial_load_size
            line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        elif( is_full_load_needed and is_partial_load_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_counter in range(TF_PORTS-1): 
                port_idx = port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_TF_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_TF_PORT
                line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)
            
            #partial loads
            port_idx = (TF_PORTS-1)
            local_port_idx_per_para_limb = 0
            para_limb_base = PARA_LIMB_PORTS_PER_TF_PORT*(TF_PORTS-1)
            para_num_limbs = partial_load_size
            line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        else: # only full load
            for port_counter in range(TF_PORTS): 
                port_idx = port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_TF_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_TF_PORT
                line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)
                
    else: #For a single limb, it requires multiple ports
        for port_counter in range(TF_PORTS):
            port_idx = port_counter
            local_port_idx_per_para_limb = port_counter % TF_PORTS_PER_PARA_LIMB
            para_limb_base = port_counter//TF_PORTS_PER_PARA_LIMB
            para_num_limbs = PARA_LIMB_PORTS_PER_TF_PORT
            line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    return line

# This task bridge the load/store functions which sometimes work on 2*V_BUG_SIZE streams and sometime work on POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT streams.
# After/Before this task, every group of streams contains 2*V_BUG_SIZE streams. i.e., the size of BUG streams.
# Hence, when load/store tasks work on POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT streams, this task should combine them to make 2*V_BUG_SIZE/split them to make POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT.
# The current way this task handle above scenario is as follows:
# As split condition is set to work with V_BUG_SIZE>4 and smallest number POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT can take is 8 (as current framework only target max 64 bit data size, and DRAM data width is 512)
# we can safetely assume that all the BUGs requiring 8 streams or more going to be working with split_DIF.
# If we were to remove this constraint, we could always make DIF work as split_DIF, which would help above bridging problem easily. 
def gen_inDIF(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    is_split_DIF = gen_dual_interface_FIFO_split_logic(designParamsVar)
    BUG_PER_PARA_LIMB_POLY_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    num_of_stream_groups_per_BUG = (2*designParamsVar.V_BUG_SIZE) // designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    if (is_split_DIF):
        if( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ): # works with POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT streams
            for BUG_idx in range(num_of_BUGs):
                # Receive
                for stream_grp_idx in range(num_of_stream_groups_per_BUG):
                    for stream_idx in range(designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT):
                        BUG_stream_idx = (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT * stream_grp_idx) + stream_idx
                        line += "        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(stream_grp_idx) + "[" + str(stream_idx) + "], inv_poly_inSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], poly_inFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], direction)" + "\n"
                line += "\n"

                # send
                for stream_grp_idx in range(num_of_stream_groups_per_BUG):
                    for stream_idx in range(designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT):
                        BUG_stream_idx = (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT * stream_grp_idx) + stream_idx
                        line += "        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], fwd_poly_DIF_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], inv_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(stream_grp_idx) + "[" + str(stream_idx) + "], direction)" + "\n"
                line += "\n"

        else: # works with 2*V_BUG_SIZE streams
            # Receive
            for BUG_idx in range(num_of_BUGs):
                for input_idx in range(2*designParamsVar.V_BUG_SIZE):
                    line += "        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], inv_poly_inSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], poly_inFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], direction)" + "\n"
                line += "\n"

            # send
            for BUG_idx in range(num_of_BUGs):
                for input_idx in range(2*designParamsVar.V_BUG_SIZE):
                    line += "        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_inFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], fwd_poly_DIF_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], inv_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], direction)" + "\n"
                line += "\n"

    else: # with current split conditions, combined DIF will not be used with scenarios where multiple WIDE_DATA loading is needed to support one BUG
        for BUG_idx in range(num_of_BUGs):
            line += "        .invoke<tapa::detach>(dual_interface_FIFO_comb, fwd_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_inSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_DIF_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction)" + "\n"

    return line
    
# Generate input_selector tasks based on split conditions
def gen_inSel(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR

    is_split_selector = designParamsVar.IS_SPLIT_SHUFFLER
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    if(is_split_selector):
        for BUG_idx in range(num_of_BUGs):
            for stream_idx in range(2*designParamsVar.V_BUG_SIZE):
                line += "        .invoke(input_selector_single, fwd_poly_DIF_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], fwd_poly_shufOutShuff_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_BUG_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], fwd_poly_inSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_inSel_to_shufOutShuff_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_inSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], direction, iter)" + "\n"
            line += "\n"
    else:
        for BUG_idx in range(num_of_BUGs):
            line += "        .invoke(input_selector, fwd_poly_DIF_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_shufOutShuff_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_BUG_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_inSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_inSel_to_shufOutShuff_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_inSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction, iter, " + str(BUG_idx) + ")" + "\n"

    return line

# Generate TF buffer tasks 
def gen_TFBuf(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    TFBuffersParamsVar = designParamsVar.TFBuffersParamsVar
    TFBuffers_per_BUG_per_layer = designParamsVar.V_BUG_SIZE//2
    num_of_ver_TFBufs = TFBuffers_per_BUG_per_layer*num_of_BUGs
    num_of_streams_per_group = designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT//2
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""

    for BUG_idx in range(num_of_BUGs):

        cummulative_layers = 0
        for h_seg_id in range(designParamsVar.TF_LOAD_H_SEGS_PER_PARA_LIMB):
            layers_in_seg = TFBuffersParamsVar.layers_per_seg[h_seg_id]
            load_direction = TFBuffersParamsVar.load_direction_per_seg[h_seg_id]
            seg_start = cummulative_layers
            seg_end = cummulative_layers + layers_in_seg
            if(load_direction):
                for layer_idx in range(seg_start, seg_end-1): # TFBuf with forwarding
                    line += "        //TF buffers for BUG" + str(BUG_idx) + " - Layer" + str(layer_idx) + "\n"
                    for buf_idx in range(TFBuffers_per_BUG_per_layer):
                        modified_buf_idx = num_of_ver_TFBufs*h_seg_id + TFBuffers_per_BUG_per_layer*BUG_idx + buf_idx # This is if TFBuffers are indexed segment wise instead BUG wise
                        TF_port_grpup_idx = modified_buf_idx // num_of_streams_per_group

                        stream_set_idx0 = layer_idx - seg_start # as load direction is forward, this follows relative layer idx in the segment
                        stream_set_idx1 = stream_set_idx0 + 1

                        stream_idx = modified_buf_idx % num_of_streams_per_group

                        BU_idx0 = 2*buf_idx
                        BU_idx1 = 2*buf_idx + 1

                        line += "        .invoke(TFBuf_wiFW_" + str(layer_idx) + ", tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_port_grpup_idx) + "_" + str(stream_set_idx0) + "[" + str(stream_idx) + "], tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_port_grpup_idx) + "_" + str(stream_set_idx1) + "[" + str(stream_idx) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx0) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx1) + "], direction, " + str(BUG_idx) + ", " + str(layer_idx) + ", " + str(buf_idx) + ", iter)" + "\n"
                    line += "\n"

                # Last TFBuf without forwarding
                layer_idx = seg_end-1
                line += "        //TF buffers for BUG" + str(BUG_idx) + " - Layer" + str(layer_idx) + "\n"
                for buf_idx in range(TFBuffers_per_BUG_per_layer):
                        modified_buf_idx = num_of_ver_TFBufs*h_seg_id + TFBuffers_per_BUG_per_layer*BUG_idx + buf_idx # This is if TFBuffers are indexed segment wise instead BUG wise
                        TF_port_grpup_idx = modified_buf_idx // num_of_streams_per_group

                        stream_set_idx0 = layer_idx - seg_start # as load direction is forward, this follows relative layer idx in the segment
                        stream_set_idx1 = stream_set_idx0 + 1

                        stream_idx = modified_buf_idx % num_of_streams_per_group

                        BU_idx0 = 2*buf_idx
                        BU_idx1 = 2*buf_idx + 1

                        line += "        .invoke(TFBuf_woFW_" + str(layer_idx) + ", tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_port_grpup_idx) + "_" + str(stream_set_idx0) + "[" + str(stream_idx) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx0) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx1) + "], direction, " + str(BUG_idx) + ", " + str(layer_idx) + ", " + str(buf_idx) + ", iter)" + "\n"
                line += "\n"
            
            else:
                # First TFBuf without forwarding
                layer_idx = seg_start
                line += "        //TF buffers for BUG" + str(BUG_idx) + " - Layer" + str(layer_idx) + "\n"
                for buf_idx in range(TFBuffers_per_BUG_per_layer):
                        modified_buf_idx = num_of_ver_TFBufs*h_seg_id + TFBuffers_per_BUG_per_layer*BUG_idx + buf_idx # This is if TFBuffers are indexed segment wise instead BUG wise
                        TF_port_grpup_idx = modified_buf_idx // num_of_streams_per_group

                        stream_set_idx0 = seg_end - layer_idx - 1 # as load direction is backward, this follows relative layer idx in the segment in reverse order
                        stream_set_idx1 = stream_set_idx0 + 1

                        stream_idx = modified_buf_idx % num_of_streams_per_group

                        BU_idx0 = 2*buf_idx
                        BU_idx1 = 2*buf_idx + 1

                        line += "        .invoke(TFBuf_woFW_" + str(layer_idx) + ", tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_port_grpup_idx) + "_" + str(stream_set_idx0) + "[" + str(stream_idx) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx0) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx1) + "], direction, " + str(BUG_idx) + ", " + str(layer_idx) + ", " + str(buf_idx) + ", iter)" + "\n"
                line += "\n"

                for layer_idx in range(seg_start+1, seg_end): # TFBuf with forwarding
                    line += "        //TF buffers for BUG" + str(BUG_idx) + " - Layer" + str(layer_idx) + "\n"
                    for buf_idx in range(TFBuffers_per_BUG_per_layer):
                        modified_buf_idx = num_of_ver_TFBufs*h_seg_id + TFBuffers_per_BUG_per_layer*BUG_idx + buf_idx # This is if TFBuffers are indexed segment wise instead BUG wise
                        TF_port_grpup_idx = modified_buf_idx // num_of_streams_per_group

                        stream_set_idx0 = seg_end - layer_idx - 1 # as load direction is backward, this follows relative layer idx in the segment in reverse order
                        stream_set_idx1 = stream_set_idx0 + 1

                        stream_idx = modified_buf_idx % num_of_streams_per_group

                        BU_idx0 = 2*buf_idx
                        BU_idx1 = 2*buf_idx + 1

                        line += "        .invoke(TFBuf_wiFW_" + str(layer_idx) + ", tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_port_grpup_idx) + "_" + str(stream_set_idx0) + "[" + str(stream_idx) + "], tf_load_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_port_grpup_idx) + "_" + str(stream_set_idx1) + "[" + str(stream_idx) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx0) + "], tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(layer_idx) + "[" + str(BU_idx1) + "], direction, " + str(BUG_idx) + ", " + str(layer_idx) + ", " + str(buf_idx) + ", iter)" + "\n"
                    line += "\n"
        
            cummulative_layers = cummulative_layers + layers_in_seg
            
    return line

# Generate BUs in BUGs 
def gen_BUGs(designParamsVar):
    BUG_CONCAT_FACTOR = designParamsVar.BUG_CONCAT_FACTOR
    H_BUG_SIZE = designParamsVar.H_BUG_SIZE
    V_BUG_SIZE = designParamsVar.V_BUG_SIZE
    para_limb_idx = designParamsVar.para_limb_idx
    REDUCTION_TYPE = designParamsVar.REDUCTION_TYPE

    prefix = ""
    suffix = str(para_limb_idx) + ", "
    modified_modmul_args = modmul_funcCall_args(designParamsVar, prefix, suffix)

    line = ""
    for BUG_idx in range(BUG_CONCAT_FACTOR):
        line += "        //BUG" + str(BUG_idx) + "" + "\n"
        for BU_layer_idx in range(H_BUG_SIZE):
            for v_BU_idx  in range(V_BUG_SIZE):
                line += "        .invoke(BU, "
                
                inp_dist = 1 << BU_layer_idx
                inp_idx0 = (v_BU_idx//inp_dist)*(2*inp_dist) + (v_BU_idx%inp_dist)
                inp_idx1 = inp_idx0 + inp_dist

                # FWD input FIFOs
                if( BU_layer_idx==0 ): #first layer
                    line += "fwd_poly_inSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], fwd_poly_inSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "
                else:   #intemediate layer
                    line += "fwd_poly_H" + str(BU_layer_idx - 1) + "_to_H" + str(BU_layer_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], fwd_poly_H" + str(BU_layer_idx - 1) + "_to_H" + str(BU_layer_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "

                # INV input FIFOs
                if( BU_layer_idx==(H_BUG_SIZE-1) ): #last layer
                    line += "inv_poly_outSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], inv_poly_outSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "
                else:
                    line += "inv_poly_H" + str(BU_layer_idx + 1) + "_to_H" + str(BU_layer_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], inv_poly_H" + str(BU_layer_idx + 1) + "_to_H" + str(BU_layer_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "
                
                # TF input FIFO
                line += "tf_TFBuf_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_H" + str(BU_layer_idx) + "[" + str(v_BU_idx) + "], " 
                
                # FWD output FIFOs
                if( BU_layer_idx==H_BUG_SIZE-1 ): #last layer
                    line += "fwd_poly_BUG_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], fwd_poly_BUG_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "
                else:
                    line += "fwd_poly_H" + str(BU_layer_idx) + "_to_H" + str(BU_layer_idx + 1) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], fwd_poly_H" + str(BU_layer_idx) + "_to_H" + str(BU_layer_idx + 1) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "
                
                # INV output FIFOs
                if( BU_layer_idx==0 ):
                    line += "inv_poly_BUG_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], inv_poly_BUG_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "
                else:
                    line += "inv_poly_H" + str(BU_layer_idx) + "_to_H" + str(BU_layer_idx - 1) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx0) + "], inv_poly_H" + str(BU_layer_idx) + "_to_H" + str(BU_layer_idx - 1) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(inp_idx1) + "], "

                line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "direction, iter, " + str(BUG_idx) + ", " + str(BU_layer_idx) + ")" + "\n"
            line += "" + "\n"
    return line

# Generate output_selector tasks based on split conditions
def gen_outSel(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR

    is_split_selector = designParamsVar.IS_SPLIT_SHUFFLER
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    if(is_split_selector):
        for BUG_idx in range(num_of_BUGs):
            for stream_idx in range(2*designParamsVar.V_BUG_SIZE):
                line += "        .invoke(output_slector_single, fwd_poly_BUG_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_DIF_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_shufIn_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], fwd_poly_outSel_to_shufIn_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], fwd_poly_outSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_outSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], direction, iter)" + "\n"
            line += "\n"
    else:
        for BUG_idx in range(num_of_BUGs):
            line += "        .invoke(output_slector, fwd_poly_BUG_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_DIF_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shuf_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_outSel_to_shuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_outSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_outSel_to_BUG_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction, iter, " + str(BUG_idx) + ")" + "\n"

    return line

# This task bridge the load/store functions which sometimes work on 2*V_BUG_SIZE streams and sometime work on POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT streams.
# After/Before this task, every group of streams contains 2*V_BUG_SIZE streams. i.e., the size of BUG streams.
# Hence, when load/store tasks work on POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT streams, this task should combine them to make 2*V_BUG_SIZE/split them to make POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT.
# The current way this task handle above scenario is as follows:
# As split condition is set to work with V_BUG_SIZE>4 and smallest number POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT can take is 8 (as current framework only target max 64 bit data size, and DRAM data width is 512)
# we can safetely assume that all the BUGs requiring 8 streams or more going to be working with split_DIF.
# If we were to remove this constraint, we could always make DIF work as split_DIF, which would help above bridging problem easily. 
def gen_outDIF(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    is_split_DIF = gen_dual_interface_FIFO_split_logic(designParamsVar)
    BUG_PER_PARA_LIMB_POLY_WIDE_DATA = designParamsVar.BUG_PER_PARA_LIMB_POLY_WIDE_DATA
    num_of_stream_groups_per_BUG = (2*designParamsVar.V_BUG_SIZE) // designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    if (is_split_DIF):
        if( (BUG_PER_PARA_LIMB_POLY_WIDE_DATA==1) and (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT != 2*designParamsVar.V_BUG_SIZE) ): # works with POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT streams
            for BUG_idx in range(num_of_BUGs):
                # Receive
                for stream_grp_idx in range(num_of_stream_groups_per_BUG):
                    for stream_idx in range(designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT):
                        BUG_stream_idx = (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT * stream_grp_idx) + stream_idx
                        line += "        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], inv_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(stream_grp_idx) + "[" + str(stream_idx) + "], poly_outFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], direction)" + "\n"
                line += "\n"

                # send
                for stream_grp_idx in range(num_of_stream_groups_per_BUG):
                    for stream_idx in range(designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT):
                        BUG_stream_idx = (designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT * stream_grp_idx) + stream_idx
                        line += "        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], fwd_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "_" + str(stream_grp_idx) + "[" + str(stream_idx) + "], inv_poly_DIF_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(BUG_stream_idx) + "], direction)" + "\n"
                line += "\n"

        else: # works with 2*V_BUG_SIZE streams
            # Receive
            for BUG_idx in range(num_of_BUGs):
                for input_idx in range(2*designParamsVar.V_BUG_SIZE):
                    line += "        .invoke<tapa::detach>(dual_interface_FIFO_receive, fwd_poly_outSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], inv_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], poly_outFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], direction)" + "\n"
                line += "\n"

            # send
            for BUG_idx in range(num_of_BUGs):
                for input_idx in range(2*designParamsVar.V_BUG_SIZE):
                    line += "        .invoke<tapa::detach>(dual_interface_FIFO_send, poly_outFIFO_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], fwd_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], inv_poly_DIF_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(input_idx) + "], direction)" + "\n"
                line += "\n"

    else: # with current split conditions, combined DIF will not be used with scenarios where multiple WIDE_DATA loading is needed to support one BUG
        for BUG_idx in range(num_of_BUGs):
            line += "        .invoke<tapa::detach>(dual_interface_FIFO_comb, fwd_poly_outSel_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_load_to_DIF_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_DIF_to_store_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_DIF_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction)" + "\n"

    return line

def gen_shuffler_in(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    for BUG_idx in range(num_of_BUGs):
        line += "        .invoke(shuffler_in, fwd_poly_outSel_to_shufIn_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shufBuf_to_shufIn_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_shufIn_to_shufBuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shufIn_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction, iter, " + str(BUG_idx) + ")" + "\n"
    
    return line


def gen_shuffler_buf(designParamsVar, is_split_buffer):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    num_of_streams_per_group = 2*designParamsVar.V_BUG_SIZE
    para_limb_idx = designParamsVar.para_limb_idx
    
    line = ""
    
    if is_split_buffer:
        for BUG_idx in range(num_of_BUGs):
            for stream_idx in range(num_of_streams_per_group):
                line += "        .invoke(shuffler_single_buf, fwd_poly_shufIn_to_shufBuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_shufOutShift_to_shufBuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], fwd_poly_shufBuf_to_shufOutShift_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], inv_poly_shufBuf_to_shufIn_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + "[" + str(stream_idx) + "], direction, " + str(BUG_idx) + ", " + str(stream_idx) + ", iter)" + "\n"
            line += "\n"
    else:
        for BUG_idx in range(num_of_BUGs):
            line += "        .invoke(shuffler_buf, fwd_poly_shufIn_to_shufBuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shufOutShift_to_shufBuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_shufBuf_to_shufOutShift_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shufBuf_to_shufIn_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction, " + str(BUG_idx) + ", iter)" + "\n"

    return line

def gen_shuffler_out_shift(designParamsVar, num_of_inter_BUG_comm):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    for BUG_idx in range(num_of_BUGs):
        line += "        .invoke(shuffler_out_shift, fwd_poly_shufBuf_to_shufOutShift_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        for comm_idx in range(num_of_inter_BUG_comm):
            line += "inv_poly_shufOutShuff_to_shufOutShift_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        line += "inv_poly_shufOutShuff_to_shufOutShift_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        for comm_idx in range(num_of_inter_BUG_comm):
            line += "fwd_poly_shufOutShift_to_shufOutShuff_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        line += "fwd_poly_shufOutShift_to_shufOutShuff_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shufOutShift_to_shufBuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction, iter, " + str(BUG_idx) + ")" + "\n"
    
    return line




def gen_comb_shuffler_tasks(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    for BUG_idx in range(num_of_BUGs):
        line += "        .invoke(shuffler, fwd_poly_outSel_to_shuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shufOutSplit_to_shuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", fwd_poly_shuf_to_shufOutSplit_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shuf_to_outSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction, " + str(BUG_idx) + ", iter)" + "\n"

    return line

def gen_shuffler_out_split(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR

    num_of_inter_BUG_comm = designParamsVar.NUM_INTER_BUG_COM
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    for BUG_idx in range(num_of_BUGs):
        line += "        .invoke(shuffler_out_split, fwd_poly_shuf_to_shufOutSplit_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        for comm_idx in range(num_of_inter_BUG_comm):
            line += "inv_poly_shufOutShuff_to_shufOutSplit_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        line += "inv_poly_shufOutShuff_to_shufOutSplit_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        for comm_idx in range(num_of_inter_BUG_comm):
            line += "fwd_poly_shufOutSplit_to_shufOutShuff_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", "
        line += "fwd_poly_shufOutSplit_to_shufOutShuff_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", inv_poly_shufOutSplit_to_shuf_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", direction, iter, " + str(BUG_idx) + ")" + "\n"

    return line

def gen_shuffler_out_shuff(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    num_of_inter_BUG_comm = designParamsVar.NUM_INTER_BUG_COM
    TOTAL_V_BUG_DATA = 2*designParamsVar.V_BUG_SIZE
    is_split_shuffler = designParamsVar.IS_SPLIT_SHUFFLER
    para_limb_idx = designParamsVar.para_limb_idx

    all_round_patterns = gen_shuffler_out_shuff_config(designParamsVar)

    inter_BUG_patterns = all_round_patterns[0:num_of_inter_BUG_comm]

    def swap_idx_and_val(arr_in): # This function swap the values in the array with indexes
        inv_idx_arr = []
        for i in range(len(arr_in)):
            for j in range(len(arr_in)):
                if(i==arr_in[j]):
                    inv_idx_arr.append(j)
        return inv_idx_arr

    inv_inter_BUG_patterns = []
    for idx in range(num_of_inter_BUG_comm):
        inv_arr = swap_idx_and_val(inter_BUG_patterns[idx])
        inv_inter_BUG_patterns.append(inv_arr)
    
    line = ""

    for BUG_idx in range(num_of_BUGs):
        line += "        .invoke(shuffler_out_shuff, \\" + "\n"

        for comm_idx in range(num_of_inter_BUG_comm):
            for data_idx in range(TOTAL_V_BUG_DATA):
                read_idx = inv_inter_BUG_patterns[comm_idx][BUG_idx*TOTAL_V_BUG_DATA + data_idx]
                read_BUG_idx = read_idx//TOTAL_V_BUG_DATA
                stream_idx = read_idx%TOTAL_V_BUG_DATA
                if(is_split_shuffler):
                    line += "            fwd_poly_shufOutShift_to_shufOutShuff_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(read_BUG_idx) + "[" + str(stream_idx) + "], \\" + "\n"
                else:
                    line += "            fwd_poly_shufOutSplit_to_shufOutShuff_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(read_BUG_idx) + "[" + str(stream_idx) + "], \\" + "\n"

        if(is_split_shuffler):
            line += "            fwd_poly_shufOutShift_to_shufOutShuff_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", \\" + "\n"
        else:
            line += "            fwd_poly_shufOutSplit_to_shufOutShuff_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", \\" + "\n"
        
        line += "            inv_poly_inSel_to_shufOutShuff_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", \\" + "\n"
        line += "            fwd_poly_shufOutShuff_to_inSel_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", \\" + "\n"
        
        if(is_split_shuffler):
            line += "            inv_poly_shufOutShuff_to_shufOutShift_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", \\" + "\n"
        else:
            line += "            inv_poly_shufOutShuff_to_shufOutSplit_intra_L" + str(para_limb_idx) + "_BUG" + str(BUG_idx) + ", \\" + "\n"

        for comm_idx in range(num_of_inter_BUG_comm):
            for data_idx in range(TOTAL_V_BUG_DATA):
                read_idx = inter_BUG_patterns[comm_idx][BUG_idx*TOTAL_V_BUG_DATA + data_idx]
                read_BUG_idx = read_idx//TOTAL_V_BUG_DATA
                stream_idx = read_idx%TOTAL_V_BUG_DATA
                if(is_split_shuffler):
                    line += "            inv_poly_shufOutShuff_to_shufOutShift_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(read_BUG_idx) + "[" + str(stream_idx) + "], \\" + "\n"
                else:
                    line += "            inv_poly_shufOutShuff_to_shufOutSplit_inter" + str(comm_idx) + "_L" + str(para_limb_idx) + "_BUG" + str(read_BUG_idx) + "[" + str(stream_idx) + "], \\" + "\n"

        line += "            direction, iter" + "\n"
        line += "        )" + "\n"
        line += "\n"

    return line




def gen_comb_shuffler(designParamsVar):
    line = ""
    line += gen_comb_shuffler_tasks(designParamsVar)
    line += "\n"
    line += gen_shuffler_out_split(designParamsVar)
    line += "\n"

    return line

def gen_shuffler(designParamsVar):
    num_of_BUGs = designParamsVar.BUG_CONCAT_FACTOR
    is_split_shuffler, is_split_buffer, is_inter_BUG_connections = designParamsVar.IS_SPLIT_SHUFFLER, designParamsVar.IS_SPLIT_BUFFER, designParamsVar.IS_INTER_BUG_CONNECTIONS
    num_of_inter_BUG_comm = designParamsVar.NUM_INTER_BUG_COM

    line = ""

    if(is_split_shuffler):
        line += gen_shuffler_in(designParamsVar)
        line += "\n"
        line += gen_shuffler_buf(designParamsVar, is_split_buffer)
        line += "\n"
        line += gen_shuffler_out_shift(designParamsVar, num_of_inter_BUG_comm)
        line += "\n"
    else:
        line += gen_comb_shuffler(designParamsVar)
        line += "\n"
    line += gen_shuffler_out_shuff(designParamsVar)

    return line

def gen_task_invokes(designParamsVar):

    PARA_LIMBS = designParamsVar.PARA_LIMBS

    line = "    tapa::task()" + "\n"
    
    # generate fwd_load_inv_store tasks
    line += "        //polynomial loading/storing tasks: FWD loading and INV storing" + "\n"
    line += gen_fwd_load_inv_store(designParamsVar)
    line += "\n"

    # generate fwd_store_inv_load tasks
    line += "        //polynomial loading/storing tasks: FWD storing and INV loading" + "\n"
    line += gen_fwd_store_inv_load(designParamsVar)
    line += "\n"

    # generate TF load tasks
    line += "        //TF loading tasks" + "\n"
    line += gen_mmap2Stream_tf(designParamsVar)
    line += "\n"

    for para_limb_idx in range(PARA_LIMBS):

        designParamsVar.para_limb_idx = para_limb_idx
        
        line += "        /* Limb" + str(para_limb_idx) + " */" + "\n"

        # generate dual interface tasks fwd input side
        line += "        //Dual Interface FIFO (DIF) tasks from FWD in side" + "\n"
        line += gen_inDIF(designParamsVar)
        line += "\n"

        # generate input_selector tasks
        line += "        //input_selector tasks" + "\n"
        line += gen_inSel(designParamsVar)
        line += "\n"

        # generate TF buffer tasks
        line += "        //TF buffer tasks" + "\n"
        line += gen_TFBuf(designParamsVar)
        line += "\n"

        # generate BUG tasks
        line += "        //BUGs" + "\n"
        line += gen_BUGs(designParamsVar)
        line += "\n"

        # generate output_selector tasks
        line += "        //output_selector tasks" + "\n"
        line += gen_outSel(designParamsVar)
        line += "\n"

        # generate dual interface tasks fwd output side
        line += "        //Dual Interface FIFO (DIF) tasks from FWD out side" + "\n"
        line += gen_outDIF(designParamsVar)
        line += "\n"

        # generate shuffler tasks
        line += "        //shuffler tasks" + "\n"
        line += gen_shuffler(designParamsVar)
        line += "\n"

    line += "    ;" + "\n"

    return line