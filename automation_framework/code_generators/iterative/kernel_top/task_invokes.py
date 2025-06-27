from code_generators.modmul.config import modmul_funcCall_args

from code_generators.iterative.poly.poly_load_store import gen_poly_load_store_configs

from code_generators.iterative.TFs.TF_load import gen_tf_load_configs

# generate Mmap2Stream_poly tasks
def gen_polyLoad(designParamsVar):

    POLY_LS_PORTS = designParamsVar.POLY_LS_PORTS
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_poly_load_store_configs(designParamsVar)

    line = ""

    if(POLY_LS_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_load_needed) and is_partial_load_needed ) : #only one partial load
            line += "        .invoke(Mmap2Stream_poly_" + str(partial_load_size) + "_limbs, polyVectorIn_G0, " 
            for para_limb_counter in range(partial_load_size):
                para_limb_idx = para_limb_counter
                line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, " 
            line += "0, iter)" + "\n"

        elif( is_full_load_needed and is_partial_load_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_idx in range(POLY_LS_PORTS-1): 
                line += "        .invoke(Mmap2Stream_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorIn_G" + str(port_idx) + ", " 
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, " 
                line += "" + str(port_idx) + ", iter)" + "\n"
            
            #partial loads
            line += "        .invoke(Mmap2Stream_poly_" + str(partial_load_size) + "_limbs, polyVectorIn_G" + str(POLY_LS_PORTS-1) + ", " 
            for para_limb_counter in range(partial_load_size):
                para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*(POLY_LS_PORTS-1) + para_limb_counter
                line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, " 
            line += "" + str(POLY_LS_PORTS-1) + ", iter)" + "\n"

        else: # only full load
            for port_idx in range(POLY_LS_PORTS): 
                line += "        .invoke(Mmap2Stream_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorIn_G" + str(port_idx) + ", " 
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, " 
                line += "" + str(port_idx) + ", iter)" + "\n"

    else: #For a single limb, it requires multiple ports
        for port_idx in range(POLY_LS_PORTS):
            para_limb_idx = port_idx//POLY_LS_PORTS_PER_PARA_LIMB
            local_port_idx_per_para_limb = port_idx % POLY_LS_PORTS_PER_PARA_LIMB
            line += "        .invoke(Mmap2Stream_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorIn_G" + str(port_idx) + ", polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G" + str(local_port_idx_per_para_limb) + "_0, " + str(port_idx) + ", iter)" + "\n"

    return line



# generate Mmap2Stream_poly tasks
def gen_polyLoadStore(designParamsVar):

    POLY_LS_PORTS = designParamsVar.POLY_LS_PORTS
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_poly_load_store_configs(designParamsVar)

    line = ""

    if(POLY_LS_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_load_needed) and is_partial_load_needed ) : #only one partial load
            line += "        .invoke(Mmap2Stream_and_Stream2Mmap_poly_" + str(partial_load_size) + "_limbs, polyVectorInOut_G0, " 
            
            for para_limb_counter in range(partial_load_size):
                para_limb_idx = para_limb_counter
                line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, "
            
            for para_limb_counter in range(partial_load_size):
                para_limb_idx = para_limb_counter
                line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, "
            line += "0, iter)" + "\n"

        elif( is_full_load_needed and is_partial_load_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_idx in range(POLY_LS_PORTS-1): 
                line += "        .invoke(Mmap2Stream_and_Stream2Mmap_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorInOut_G" + str(port_idx) + ", " 
                
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, " 
                
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, " 

                line += "" + str(port_idx) + ", iter)" + "\n"
            
            #partial loads
            line += "        .invoke(Mmap2Stream_and_Stream2Mmap_poly_" + str(partial_load_size) + "_limbs, polyVectorInOut_G" + str(POLY_LS_PORTS-1) + ", " 
            
            for para_limb_counter in range(partial_load_size):
                para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*(POLY_LS_PORTS-1) + para_limb_counter
                line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, " 

            for para_limb_counter in range(partial_load_size):
                para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*(POLY_LS_PORTS-1) + para_limb_counter
                line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, " 

            line += "" + str(POLY_LS_PORTS-1) + ", iter)" + "\n"

        else: # only full load
            for port_idx in range(POLY_LS_PORTS): 
                line += "        .invoke(Mmap2Stream_and_Stream2Mmap_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorInOut_G" + str(port_idx) + ", " 
                
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, " 

                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G0_0, " 

                line += "" + str(port_idx) + ", iter)" + "\n"

    else: #For a single limb, it requires multiple ports
        for port_idx in range(POLY_LS_PORTS):
            para_limb_idx = port_idx//POLY_LS_PORTS_PER_PARA_LIMB
            local_port_idx_per_para_limb = port_idx % POLY_LS_PORTS_PER_PARA_LIMB
            line += "        .invoke(Mmap2Stream_and_Stream2Mmap_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorInOut_G" + str(port_idx) + ", polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G" + str(local_port_idx_per_para_limb) + "_0, polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G" + str(local_port_idx_per_para_limb) + "_0, " + str(port_idx) + ", iter)" + "\n"

    return line

# generate Mmap2Stream_tf tasks
def gen_TFLoad(designParamsVar):

    TF_PORTS = designParamsVar.TF_PORTS
    TF_PORTS_PER_PARA_LIMB = designParamsVar.TF_PORTS_PER_PARA_LIMB
    PARA_LIMB_PORTS_PER_TF_PORT = designParamsVar.PARA_LIMB_PORTS_PER_TF_PORT

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_tf_load_configs(designParamsVar)

    line = ""

    if(TF_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_load_needed) and is_partial_load_needed ) : #only one partial load
            line += "        .invoke(Mmap2Stream_tf_" + str(partial_load_size) + "_limbs, TFArr_G0, " 
            for para_limb_counter in range(partial_load_size):
                para_limb_idx = para_limb_counter
                line += "tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G0_0, " 
            line += "direction, iter, 0)" + "\n"

        elif( is_full_load_needed and is_partial_load_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_idx in range(TF_PORTS-1): 
                line += "        .invoke(Mmap2Stream_tf_" + str(PARA_LIMB_PORTS_PER_TF_PORT) + "_limbs, TFArr_G" + str(port_idx) + ", " 
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_TF_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_TF_PORT*port_idx + para_limb_counter
                    line += "tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G0_0, " 
                line += "direction, iter, 0)" + "\n"
            
            #partial loads
            line += "        .invoke(Mmap2Stream_tf_" + str(partial_load_size) + "_limbs, TFArr_G" + str(TF_PORTS-1) + ", " 
            for para_limb_counter in range(partial_load_size):
                para_limb_idx = PARA_LIMB_PORTS_PER_TF_PORT*(TF_PORTS-1) + para_limb_counter
                line += "tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G0_0, " 
            line += "direction, iter, 0)" + "\n"

        else: # only full load
            for port_idx in range(TF_PORTS): 
                line += "        .invoke(Mmap2Stream_tf_" + str(PARA_LIMB_PORTS_PER_TF_PORT) + "_limbs, TFArr_G" + str(port_idx) + ", " 
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_TF_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_TF_PORT*port_idx + para_limb_counter
                    line += "tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G0_0, " 
                line += "direction, iter, 0)" + "\n"
                
    else: #For a single limb, it requires multiple ports
        for port_idx in range(TF_PORTS):
            para_limb_idx = port_idx//TF_PORTS_PER_PARA_LIMB
            local_port_idx_per_para_limb = port_idx % TF_PORTS_PER_PARA_LIMB
            line += "        .invoke(Mmap2Stream_tf_" + str(PARA_LIMB_PORTS_PER_TF_PORT) + "_limbs, TFArr_G" + str(port_idx) + ", tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(local_port_idx_per_para_limb) + "_0, direction, iter, " + str(local_port_idx_per_para_limb) + ")" + "\n"

    return line


# generate TFBuf tasks
def gen_TFBuf(designParamsVar):
    NUM_BU = designParamsVar.NUM_BU
    NUM_BUF_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_BUF_PER_PARA_LIMB_TF_PORT
    TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = designParamsVar.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT

    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    #BufModule with TFs
    for idx in range(NUM_BU//2):
        idx0 = idx    

        TF_HBM_IDX0 = idx0//NUM_BUF_PER_PARA_LIMB_TF_PORT   #Which HBM the values are being red
        TF_CHAIN_GROUP_IDX0 = (idx0%NUM_BUF_PER_PARA_LIMB_TF_PORT)//TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT    #Withing the chain what is the index of the group
        TF_CHAIN_IDX0 = idx0%TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT    #within the group what is the index        
        
        # print("idx:" + str(idx) +", HBM_IDX:" + str(HBM_IDX) + ", CHAIN_GROUP:" + str(CHAIN_GROUP_IDX) + ", CHAIN_IDX:" +str(CHAIN_IDX))
        if( TF_CHAIN_GROUP_IDX0==(NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT-1) ): #no forwarding
            line += "        .invoke(TFModule_woFW_" + str(idx0) + ", tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_HBM_IDX0) + "_" + str(TF_CHAIN_GROUP_IDX0) + "[" + str(TF_CHAIN_IDX0) + "], tfBuf_to_BU_L" + str(para_limb_idx) + "_" + str(idx0) + ", direction, iter, " + str(idx0) + ")" + "\n"
        else:                                           #all forwaring
            line += "        .invoke(TFModule_wiFW_" + str(idx0) + ", tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_HBM_IDX0) + "_" + str(TF_CHAIN_GROUP_IDX0) + "[" + str(TF_CHAIN_IDX0) + "], tfLoad_to_TFBuf_L" + str(para_limb_idx) + "_G" + str(TF_HBM_IDX0) + "_" + str(TF_CHAIN_GROUP_IDX0+1) + "[" + str(TF_CHAIN_IDX0) + "], tfBuf_to_BU_L" + str(para_limb_idx) + "_" + str(idx0) + ", direction, iter, " + str(idx0) + ")" + "\n"

    return line

# generate polyBuf tasks
def gen_polyBuf(designParamsVar):

    NUM_BU = designParamsVar.NUM_BU
    NUM_BUF_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_BUF_PER_PARA_LIMB_POLY_PORT
    POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = designParamsVar.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT
    NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = designParamsVar.NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT

    para_limb_idx = designParamsVar.para_limb_idx

    line = ""

    #BufModule with Poly
    for idx in range(NUM_BU):
        idx0 = idx

        POLY_HBM_IDX0 = idx0//NUM_BUF_PER_PARA_LIMB_POLY_PORT   #Which HBM the values are being red
        POLY_CHAIN_GROUP_IDX0 = (idx0%NUM_BUF_PER_PARA_LIMB_POLY_PORT)//POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT    #Withing the chain what is the index of the group
        POLY_CHAIN_IDX0 = idx0%POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT    #within the group what is the index
        
        # print("idx:" + str(idx) +", HBM_IDX:" + str(HBM_IDX) + ", CHAIN_GROUP:" + str(CHAIN_GROUP_IDX) + ", CHAIN_IDX:" +str(CHAIN_IDX))
        if( POLY_CHAIN_GROUP_IDX0==(NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT-1) ): #no forwarding
            line += "        .invoke(BufModule_woFW_" + str(idx0) + ", polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G" + str(POLY_HBM_IDX0) + "_" + str(POLY_CHAIN_GROUP_IDX0) + "[" + str(POLY_CHAIN_IDX0) + "], fwd_BU_to_polyBuf_L" + str(para_limb_idx) + "_" + str(idx0) + ", inv_BU_to_polyBuf_L" + str(para_limb_idx) + "_" + str(idx0) + ", fwd_polyBuf_to_BU_L" + str(para_limb_idx) + "_" + str(idx0) + ", inv_polyBuf_to_BU_L" + str(para_limb_idx) + "_" + str(idx0) + ", polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G" + str(POLY_HBM_IDX0) + "_" + str(POLY_CHAIN_GROUP_IDX0) + "[" + str(POLY_CHAIN_IDX0) + "], direction, iter, " + str(idx0) + ")" + "\n"
        else:                                           #all forwaring
            line += "        .invoke(BufModule_wiFW_" + str(idx0) + ", polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G" + str(POLY_HBM_IDX0) + "_" + str(POLY_CHAIN_GROUP_IDX0) + "[" + str(POLY_CHAIN_IDX0) + "], polyLoad_to_polyBuf_L" + str(para_limb_idx) + "_G" + str(POLY_HBM_IDX0) + "_" + str(POLY_CHAIN_GROUP_IDX0+1) + "[" + str(POLY_CHAIN_IDX0) + "], fwd_BU_to_polyBuf_L" + str(para_limb_idx) + "_" + str(idx0) + ", inv_BU_to_polyBuf_L" + str(para_limb_idx) + "_" + str(idx0)  + ", fwd_polyBuf_to_BU_L" + str(para_limb_idx) + "_" + str(idx0) + ", inv_polyBuf_to_BU_L" + str(para_limb_idx) + "_" + str(idx0) + ", polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G" + str(POLY_HBM_IDX0) + "_" + str(POLY_CHAIN_GROUP_IDX0+1) + "[" + str(POLY_CHAIN_IDX0) + "], polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G" + str(POLY_HBM_IDX0) + "_" + str(POLY_CHAIN_GROUP_IDX0) + "[" + str(POLY_CHAIN_IDX0) + "], direction, iter, " + str(idx0) + ")" + "\n"
    
    return line

# this function generates FIFO connections BUs
def gen_BU(designParamsVar):
    NUM_BU = designParamsVar.NUM_BU
    para_limb_idx = designParamsVar.para_limb_idx

    prefix = ""
    suffix = str(para_limb_idx) + ", "
    modmul_args = modmul_funcCall_args(designParamsVar, prefix, suffix)

    line = ""

    for idx in range(NUM_BU):
        readBuf0 = idx>>1
        readBuf1 = readBuf0 + (NUM_BU//2)
        readBufPort = idx%2
        
        TFBuf = idx%(NUM_BU//2) #(0,128), (1,129), (2,130), (3,131), ...
        TFPort = idx//(NUM_BU//2)

        line += "        .invoke(BU, fwd_polyBuf_to_BU_L" + str(para_limb_idx) + "_" + str(readBuf0) + "[" + str(readBufPort) + "], fwd_polyBuf_to_BU_L" + str(para_limb_idx) + "_" + str(readBuf1) + "[" + str(readBufPort) + "], inv_polyBuf_to_BU_L" + str(para_limb_idx) + "_" + str(idx) + ", tfBuf_to_BU_L" + str(para_limb_idx) + "_" + str(TFBuf) + "[" + str(TFPort) + "], fwd_BU_to_polyBuf_L" + str(para_limb_idx) + "_" + str(idx) + ", inv_BU_to_polyBuf_L" + str(para_limb_idx) + "_" + str(readBuf0) + "[" + str(readBufPort) + "], inv_BU_to_polyBuf_L" + str(para_limb_idx) + "_" + str(readBuf1) + "[" + str(readBufPort) + "], q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modmul_args + "direction, iter, " + str(idx) + ")" + "\n"

    return line

# generate Stream2Mmap_poly tasks
def gen_polyStore(designParamsVar):

    POLY_LS_PORTS = designParamsVar.POLY_LS_PORTS
    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB
    PARA_LIMB_PORTS_PER_POLY_PORT = designParamsVar.PARA_LIMB_PORTS_PER_POLY_PORT

    is_full_store_needed, is_partial_store_needed, partial_store_size = gen_poly_load_store_configs(designParamsVar)

    line = ""

    if(POLY_LS_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_store_needed) and is_partial_store_needed ) : #only one partial load
            line += "        .invoke(Stream2Mmap_poly_" + str(partial_store_size) + "_limbs, polyVectorOut_G0, " 
            for para_limb_counter in range(partial_store_size):
                para_limb_idx = para_limb_counter
                line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, " 
            line += "0, iter)" + "\n"

        elif( is_full_store_needed and is_partial_store_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_idx in range(POLY_LS_PORTS-1): 
                line += "        .invoke(Stream2Mmap_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorOut_G" + str(port_idx) + ", " 
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, " 
                line += "" + str(port_idx) + ", iter)" + "\n"
            
            #partial loads
            line += "        .invoke(Stream2Mmap_poly_" + str(partial_store_size) + "_limbs, polyVectorOut_G" + str(POLY_LS_PORTS-1) + ", " 
            for para_limb_counter in range(partial_store_size):
                para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*(POLY_LS_PORTS-1) + para_limb_counter
                line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, " 
            line += "" + str(POLY_LS_PORTS-1) + ", iter)" + "\n"

        else: # only full load
            for port_idx in range(POLY_LS_PORTS): 
                line += "        .invoke(Stream2Mmap_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorOut_G" + str(port_idx) + ", " 
                for para_limb_counter in range(PARA_LIMB_PORTS_PER_POLY_PORT):
                    para_limb_idx = PARA_LIMB_PORTS_PER_POLY_PORT*port_idx + para_limb_counter
                    line += "polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G0_0, " 
                line += "" + str(port_idx) + ", iter)" + "\n"

    else: #For a single limb, it requires multiple ports
        for port_idx in range(POLY_LS_PORTS):
            para_limb_idx = port_idx//POLY_LS_PORTS_PER_PARA_LIMB
            local_port_idx_per_para_limb = port_idx % POLY_LS_PORTS_PER_PARA_LIMB
            line += "        .invoke(Stream2Mmap_poly_" + str(PARA_LIMB_PORTS_PER_POLY_PORT) + "_limbs, polyVectorOut_G" + str(port_idx) + ", polyBuf_to_polyStore_L" + str(para_limb_idx) + "_G" + str(local_port_idx_per_para_limb) + "_0, " + str(port_idx) + ", iter)" + "\n"

    return line




    POLY_LS_PORTS_PER_PARA_LIMB = designParamsVar.POLY_LS_PORTS_PER_PARA_LIMB

    line = ""

    for port_idx in range(POLY_LS_PORTS_PER_PARA_LIMB):
        line += "        .invoke(Stream2Mmap_poly, polyVectorOut_G" + str(port_idx) + ", polyBuf_to_polyStore_G" + str(port_idx) + "_0, " + str(port_idx) + ", iter)" + "\n"

    return line

def gen_task_invokes(designParamsVar):

    PARA_LIMBS = designParamsVar.PARA_LIMBS
    DOUBLE_BUF_EN = designParamsVar.DOUBLE_BUF_EN

    line = "    tapa::task()" + "\n"
    
    if(DOUBLE_BUF_EN):
        # generate Mmap2Stream_poly tasks
        line += "        //polynomial loading tasks (Mmap2Stream_poly)" + "\n"
        line += gen_polyLoad(designParamsVar)
        line += "\n"
    else:
        # generate Mmap2Stream_and_Stream2Mmap_poly tasks
        line += "        //polynomial loading and storing tasks (Mmap2Stream_and_Stream2Mmap_poly)" + "\n"
        line += gen_polyLoadStore(designParamsVar)
        line += "\n"

    # generate Mmap2Stream_tf tasks
    line += "        //TF loading tasks (Mmap2Stream_tf)" + "\n"
    line += gen_TFLoad(designParamsVar)
    line += "\n"

    for para_limb_idx in range(PARA_LIMBS):

        designParamsVar.para_limb_idx = para_limb_idx

        line += "        /* Limb" + str(para_limb_idx) + " */" + "\n"

        # generate TFBuf tasks
        line += "        //TF buffer tasks" + "\n"
        line += gen_TFBuf(designParamsVar)
        line += "\n"

        # generate polyBuf tasks
        line += "        //polynomial buffer tasks" + "\n"
        line += gen_polyBuf(designParamsVar)
        line += "\n"

        # generate BU tasks
        line += "        //BU tasks" + "\n"
        line += gen_BU(designParamsVar)
        line += "\n"

    if(DOUBLE_BUF_EN):
        # generate Stream2Mmap_poly tasks
        line += "        //polynomial storing tasks (Stream2Mmap_poly)" + "\n"
        line += gen_polyStore(designParamsVar)
        line += "\n"

    line += "    ;" + "\n"

    return line