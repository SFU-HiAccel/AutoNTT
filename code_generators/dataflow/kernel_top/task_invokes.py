from code_generators.modmul.config import modmul_funcCall_args
from code_generators.modmul.config import NAIVE_RED, MONTGOMERY, BARRETT, WLM

from code_generators.dataflow.poly_load_store.poly_load_store import gen_poly_load_store_configs
from code_generators.dataflow.TFs.TF_load import gen_tf_load_configs

def gen_fwd_load_inv_store_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs):
    
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    mmap_count = designParamsVar.mmap_count

    line = ""

    line += "        .invoke(Mmap2Stream_poly_" + str(para_num_limbs) + "_limbs, polyVectorIn_G" + str(port_idx) + ", "

    # FWD
    for para_limb_counter in range(para_num_limbs):
        para_limb_idx = para_limb_base + para_limb_counter
        if(mmap_count==1): # only 1 polyVectorIn_G per para limb
            line += "fwd_shuffler_to_BU_L" + str(para_limb_idx) + "_0, "
        else:
            line += "fwd_shuffler_to_BU_L" + str(para_limb_idx) + "_0_" + str(local_port_idx_per_para_limb) + ", "
    
    # INV
    for para_limb_counter in range(para_num_limbs):
        para_limb_idx = para_limb_base + para_limb_counter
        if(mmap_count==1): # only 1 polyVectorIn_G per para limb
            line += "inv_BU_to_shuffler_L" + str(para_limb_idx) + "_" + str(PARTIAL_COUNT-1) + ", "
        else:
            line += "inv_BU_to_shuffler_L" + str(para_limb_idx) + "_" + str(PARTIAL_COUNT-1) + "_" + str(local_port_idx_per_para_limb) + ", "
    
    
    line += "direction, iter)\n"


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
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    mmap_count = designParamsVar.mmap_count

    line = ""

    line += "        .invoke(Stream2Mmap_poly_" + str(para_num_limbs) + "_limbs, polyVectorOut_G" + str(port_idx) + ", "

    # FWD
    for para_limb_counter in range(para_num_limbs):
        para_limb_idx = para_limb_base + para_limb_counter
        if(mmap_count==1): # only 1 polyVectorIn_G per para limb
            line += "fwd_BU_to_shuffler_L" + str(para_limb_idx) + "_" + str(PARTIAL_COUNT-1) + ", "
        else:
            line += "fwd_BU_to_shuffler_L" + str(para_limb_idx) + "_" + str(PARTIAL_COUNT-1) + "_" + str(local_port_idx_per_para_limb) + ", "

    # INV
    for para_limb_counter in range(para_num_limbs):
        para_limb_idx = para_limb_base + para_limb_counter
        if(mmap_count==1): # only 1 polyVectorIn_G per para limb
            line += "inv_shuffler_to_BU_L" + str(para_limb_idx) + "_0, "
        else:
            line += "inv_shuffler_to_BU_L" + str(para_limb_idx) + "_0_" + str(local_port_idx_per_para_limb) + ", "
    
    line += "direction, iter)\n"

    return line

def gen_fwd_store_inv_load(designParamsVar):

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
            line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        elif( is_full_load_store_needed and is_partial_load_store_needed ): #both fully and partial load -> means one limb fits in to less than one port
            #full loads
            for port_counter in range(POLY_LS_PORTS-1): 
                port_idx = port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
                line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)
            
            #partial loads
            port_idx = POLY_LS_PORTS-1
            local_port_idx_per_para_limb = 0
            para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*(POLY_LS_PORTS-1)
            para_num_limbs = partial_load_store_size
            line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        else: # only full load
            for port_counter in range(POLY_LS_PORTS): 
                port_idx = port_counter
                local_port_idx_per_para_limb = 0
                para_limb_base = PARA_LIMB_PORTS_PER_POLY_PORT*port_counter
                para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
                line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    else: #For a single limb, it requires multiple ports
        for port_counter in range(POLY_LS_PORTS):
            port_idx = port_counter
            local_port_idx_per_para_limb = port_counter % POLY_LS_PORTS_PER_PARA_LIMB
            para_limb_base = port_counter//POLY_LS_PORTS_PER_PARA_LIMB
            para_num_limbs = PARA_LIMB_PORTS_PER_POLY_PORT
            line += gen_fwd_store_inv_load_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    return line


def gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs):
    
    multi_ports_tf_mmap_count = designParamsVar.multi_ports_tf_mmap_count
    tf_mmap_count = designParamsVar.tf_mmap_count
    arr_tfArr_length_val = designParamsVar.arr_tfArr_length_val

    line = ""

    line += "        .invoke(Mmap2Stream_tf_" + str(para_num_limbs) + "_limbs, "
    line += "TFArr_G" + str(port_idx) + ", "
    
    for para_limb_counter in range(para_num_limbs):
        para_limb_idx = para_limb_base + para_limb_counter
        if tf_mmap_count == 1:  # only 1 TFArr_G in HBM
            line += "tf_MM2S_to_loadTF_L" + str(para_limb_idx) + "_" + str(local_port_idx_per_para_limb) + ", "
        else:
            line += "tf_MM2S_to_loadTF_L" + str(para_limb_idx) + "_" + str(local_port_idx_per_para_limb//tf_mmap_count) + "[" + str(local_port_idx_per_para_limb%tf_mmap_count) + "], "
    
    line += str(arr_tfArr_length_val[local_port_idx_per_para_limb//tf_mmap_count]) + ", "
    line += "iter)\n"

    return line

def gen_mmap2Stream_tf(designParamsVar):
    
    V_TF_PORTS = designParamsVar.V_TF_PORTS
    H_TF_PORTS_PER_PARA_LIMB = designParamsVar.H_TF_PORTS_PER_PARA_LIMB

    V_TF_PORTS_PER_PARA_LIMB = designParamsVar.V_TF_PORTS_PER_PARA_LIMB
    V_PARA_LIMB_PORTS_PER_TF_PORT = designParamsVar.V_PARA_LIMB_PORTS_PER_TF_PORT

    is_full_load_needed, is_partial_load_needed, partial_load_size = gen_tf_load_configs(designParamsVar)

    line = ""

    if(V_TF_PORTS_PER_PARA_LIMB <= 1): #For a single limb, it only requires max one port
        
        if( not(is_full_load_needed) and is_partial_load_needed ) : #only one partial load
            for h_port_idx in range(H_TF_PORTS_PER_PARA_LIMB):
                port_idx = h_port_idx
                local_port_idx_per_para_limb = h_port_idx
                para_limb_base = 0
                para_num_limbs = partial_load_size
                line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        elif( is_full_load_needed and is_partial_load_needed ): #both fully and partial load -> means one limb fits in to less than one port
            for h_port_idx in range(H_TF_PORTS_PER_PARA_LIMB):
                #full loads
                for port_counter in range(V_TF_PORTS-1): 
                    port_idx = h_port_idx*V_TF_PORTS + port_counter
                    local_port_idx_per_para_limb = h_port_idx
                    para_limb_base = V_PARA_LIMB_PORTS_PER_TF_PORT*port_counter
                    para_num_limbs = V_PARA_LIMB_PORTS_PER_TF_PORT
                    line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)
                
                #partial loads
                port_idx = h_port_idx*V_TF_PORTS + (V_TF_PORTS-1)
                local_port_idx_per_para_limb = h_port_idx
                para_limb_base = V_PARA_LIMB_PORTS_PER_TF_PORT*(V_TF_PORTS-1)
                para_num_limbs = partial_load_size
                line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

        else: # only full load
            for h_port_idx in range(H_TF_PORTS_PER_PARA_LIMB):
                for port_counter in range(V_TF_PORTS): 
                    port_idx = h_port_idx*V_TF_PORTS + port_counter
                    local_port_idx_per_para_limb = h_port_idx
                    para_limb_base = V_PARA_LIMB_PORTS_PER_TF_PORT*port_counter
                    para_num_limbs = V_PARA_LIMB_PORTS_PER_TF_PORT
                    line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)
                
    else: #For a single limb, it requires multiple ports
        for h_port_idx in range(H_TF_PORTS_PER_PARA_LIMB):
            for port_counter in range(V_TF_PORTS):
                port_idx = h_port_idx*V_TF_PORTS + port_counter
                local_port_idx_per_para_limb = h_port_idx*V_TF_PORTS_PER_PARA_LIMB + port_counter % V_TF_PORTS_PER_PARA_LIMB
                para_limb_base = port_counter//V_TF_PORTS_PER_PARA_LIMB
                para_num_limbs = V_PARA_LIMB_PORTS_PER_TF_PORT
                line += gen_mmap2Stream_tf_code(designParamsVar, port_idx, local_port_idx_per_para_limb, para_limb_base, para_num_limbs)

    return line

def gen_load_tf(designParamsVar):
    
    multi_ports_tf_mmap_count = designParamsVar.multi_ports_tf_mmap_count
    tf_mmap_count = designParamsVar.tf_mmap_count
    arr_tfArr_length_val = designParamsVar.arr_tfArr_length_val
    arr_TFToTF_idx = designParamsVar.arr_TFToTF_idx
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    
    for idx in range(multi_ports_tf_mmap_count // tf_mmap_count):
        if tf_mmap_count == 1:  # only 1 TFArr_G in HBM
            line += f"        .invoke<tapa::detach>(load_tf, tf_MM2S_to_loadTF_L{para_limb_idx}_{idx}, tf_loadTF_to_TFGen_L{para_limb_idx}_{arr_TFToTF_idx[idx]}, direction, {arr_tfArr_length_val[idx]}, iter)\n"
        else:  # more than 1 TFArr_G in HBM, 2 ..
            line += "        .invoke<tapa::detach>(load_tf, "
            for i in range(tf_mmap_count):
                line += f"tf_MM2S_to_loadTF_L{para_limb_idx}_{idx}[{i}], "
            line += f"tf_loadTF_to_TFGen_L{para_limb_idx}_{arr_TFToTF_idx[idx]}, direction, {arr_tfArr_length_val[idx]}, iter)\n"

    return line

# Generate TF buffer tasks 
def gen_TFBuf(designParamsVar, x, y):
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    H_BU_NUM = designParamsVar.H_BU_NUM
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    is_last_TFGen = designParamsVar.is_last_TFGen
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    if H_BU_NUM == 1:
        line += f"        .invoke(TFGen{x*H_BU_NUM+y}, tf_loadTF_to_TFGen_L{para_limb_idx}_{x*H_BU_NUM+y}, tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}, tf_inv_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}, direction, iter)\n"
    elif (is_last_TFGen[x*H_BU_NUM+y] == 1):  # if (x*H_BU_NUM+y) == (logN - 1):
        line += f"        .invoke(TFGen{x*H_BU_NUM+y}, tf_loadTF_to_TFGen_L{para_limb_idx}_{x*H_BU_NUM+y}, tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}, tf_inv_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}, {x*H_BU_NUM+y}, direction, iter)\n"
    else:
        line += f"        .invoke(TFGen{x*H_BU_NUM+y}, tf_loadTF_to_TFGen_L{para_limb_idx}_{x*H_BU_NUM+y}, tf_loadTF_to_TFGen_L{para_limb_idx}_{x*H_BU_NUM+y+1}, tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}, tf_inv_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}, {x*H_BU_NUM+y}, direction, iter)\n"
        
    return line

# Generate BUs in BUGs 
def gen_BUGs(designParamsVar, x, y):

    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    H_BU_NUM = designParamsVar.H_BU_NUM
    logN = designParamsVar.logN
    mmap_count = designParamsVar.mmap_count
    partial_group = designParamsVar.partial_group
    is_last_TFGen = designParamsVar.is_last_TFGen
    DRAM_WORD_SIZE = designParamsVar.DRAM_WORD_SIZE
    para_limb_idx = designParamsVar.para_limb_idx
    REDUCTION_TYPE = designParamsVar.REDUCTION_TYPE

    prefix = ""
    suffix = str(para_limb_idx) + ", "
    modified_modmul_args = modmul_funcCall_args(designParamsVar, prefix, suffix)

    # Invocation logic based on `arr`
    if LAST_H_BU_NUM != 0 and x == (PARTIAL_COUNT - 1):
        current_total_stage = LAST_H_BU_NUM  
    else:
        current_total_stage = H_BU_NUM
    n = 1 << H_BU_NUM
    arr = []
    k = 1
    while k < n:
        halfsize = k 
        tablestep = n // (2 * k)
        temp = []
        for i in range(0, n, 2 * k):
            tfIdx = 0
            for j in range(i, i + halfsize):
                l = j + halfsize
                temp.append(j)
                temp.append(l)
                tfIdx += tablestep
        arr.append(temp)
        k *= 2
    if partial_group == True and x == (PARTIAL_COUNT - 1):
        offset = H_BU_NUM - LAST_H_BU_NUM
    else:
        offset = 0

    line = ""
    for z in range(n // 2):
        if current_total_stage == 1:  # if partial group only has 1 stage
            if x == (PARTIAL_COUNT - 1) and mmap_count != 1:  # the first and last BU group and mutil-HBM
                a = z // ((n // 2) // mmap_count)
                line += f"        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L{para_limb_idx}_{x}[{arr[y][z*2]}], fwd_shuffler_to_BU_L{para_limb_idx}_{x}[{arr[y][z*2+1]}], "
                line += f"inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[y][z*2]}], inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[y][z*2+1]}], "
                line += f"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}[{z}], tf_inv_TFGen_to_BU_L{para_limb_idx}_{logN-x*H_BU_NUM-y-1}[{z}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}_{a}[{arr[0][z*2] % (512 // DRAM_WORD_SIZE)}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}_{a}[{arr[0][z*2+1] % (512 // DRAM_WORD_SIZE)}], "
                line += f"inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}_{a}[{arr[y][z*2] % (512 // DRAM_WORD_SIZE)}], inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}_{a}[{arr[y][z*2+1] % (512 // DRAM_WORD_SIZE)}], "
                line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "iter)\n"
            else: 
                line += f"        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L{para_limb_idx}_{x}[{arr[y][z*2]}], fwd_shuffler_to_BU_L{para_limb_idx}_{x}[{arr[y][z*2+1]}], "
                line += f"inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[y][z*2]}], inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[y][z*2+1]}], "
                line += f"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}[{z}], tf_inv_TFGen_to_BU_L{para_limb_idx}_{logN-x*H_BU_NUM-y-1}[{z}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}[{arr[y][z*2]}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}[{arr[y][z*2+1]}], "
                line += f"inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[y][z*2]}], inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[y][z*2+1]}], "
                line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "iter)\n"
        elif y == 0:
            if x == 0 and mmap_count != 1:  # the first BU group and mutil-HBM
                a = z // ((n // 2) // mmap_count)
                line += f"        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L{para_limb_idx}_{x}_{a}[{arr[0][z*2] % (512 // DRAM_WORD_SIZE)}], fwd_shuffler_to_BU_L{para_limb_idx}_{x}_{a}[{arr[0][z*2+1] % (512 // DRAM_WORD_SIZE)}], "
                line += f"inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}_{a}[{arr[y][z*2] % (512 // DRAM_WORD_SIZE)}], inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}_{a}[{arr[y][z*2+1] % (512 // DRAM_WORD_SIZE)}], "
                line += f"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}[{z}], tf_inv_TFGen_to_BU_L{para_limb_idx}_{logN-x*H_BU_NUM-y-1}[{z}], fwd_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2]}], fwd_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2+1]}], "
                line += f"inv_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2]}], inv_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2+1]}], "
                line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "iter)\n"
            else :
                line += f"        .invoke<tapa::detach>(BU, fwd_shuffler_to_BU_L{para_limb_idx}_{x}[{arr[0][z*2]}], fwd_shuffler_to_BU_L{para_limb_idx}_{x}[{arr[0][z*2+1]}], "
                line += f"inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[0][z*2]}], inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[0][z*2+1]}], "
                line += f"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}[{z}], tf_inv_TFGen_to_BU_L{para_limb_idx}_{logN-x*H_BU_NUM-y-1}[{z}], fwd_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2]}], fwd_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2+1]}], "
                line += f"inv_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2]}], inv_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2+1]}], "
                line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "iter)\n"
        elif y == current_total_stage - 1:
            if x == (PARTIAL_COUNT - 1) and mmap_count != 1:  # the last BU group and mutil-HBM
                a = z // ((n // 2) // mmap_count)
                line += f"        .invoke<tapa::detach>(BU, fwd_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2]}], fwd_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2+1]}], "
                line += f"inv_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2]}], inv_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2+1]}], "
                line += f"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}[{z}], tf_inv_TFGen_to_BU_L{para_limb_idx}_{logN-x*H_BU_NUM-y-1}[{z}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}_{a}[{arr[0][z*2] % (512 // DRAM_WORD_SIZE)}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}_{a}[{arr[0][z*2+1] % (512 // DRAM_WORD_SIZE)}], "
                line += f"inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}_{a}[{arr[0][z*2] % (512 // DRAM_WORD_SIZE)}], inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}_{a}[{arr[0][z*2+1] % (512 // DRAM_WORD_SIZE)}], "
                line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "iter)\n"
            else:
                line += f"        .invoke<tapa::detach>(BU, fwd_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2]}], fwd_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2+1]}], "
                line += f"inv_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2]}], inv_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2+1]}], "
                line += f"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}[{z}], tf_inv_TFGen_to_BU_L{para_limb_idx}_{logN-x*H_BU_NUM-y-1}[{z}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}[{arr[0][z*2]}], fwd_BU_to_shuffler_L{para_limb_idx}_{x}[{arr[0][z*2+1]}], "
                line += f"inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[0][z*2]}], inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-1-x}[{arr[0][z*2+1]}], "
                line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "iter)\n"
        else:
            line += f"        .invoke<tapa::detach>(BU, fwd_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2]}], fwd_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2+1]}], "
            line += f"inv_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2]}], inv_midVals_L{para_limb_idx}_{y-1}_{x}[{arr[y+offset][z*2+1]}], "
            line += f"tf_fwd_TFGen_to_BU_L{para_limb_idx}_{x*H_BU_NUM+y}[{z}], tf_inv_TFGen_to_BU_L{para_limb_idx}_{logN-x*H_BU_NUM-y-1}[{z}], fwd_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2]}], fwd_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2+1]}], "
            line += f"inv_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2]}], inv_midVals_L{para_limb_idx}_{y}_{x}[{arr[y+offset][z*2+1]}], "
            line += "q" + str(para_limb_idx) + ", twoInverse" + str(para_limb_idx) + ", " + modified_modmul_args + "iter)\n"
    return line


def gen_shuffler(designParamsVar, x):
    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    H_BU_NUM = designParamsVar.H_BU_NUM
    check_spilt = designParamsVar.check_spilt
    para_limb_idx = designParamsVar.para_limb_idx

    line = ""
    if x != (PARTIAL_COUNT - 1):
        if check_spilt[x] == True:  # split situation
            line += f"        .invoke(shuffler_{x+1}_in, fwd_BU_to_shuffler_L{para_limb_idx}_{x}, inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-x-1}, fwd_shufIn_to_shufBuf_L{para_limb_idx}_{x}, inv_shufBuf_to_shufIn_L{para_limb_idx}_{PARTIAL_COUNT-x-2}, {x*H_BU_NUM}, direction, iter)\n"
            for z in range(CONCAT_FACTOR):
                line += f"        .invoke(shuffler_{x+1}, fwd_shufIn_to_shufBuf_L{para_limb_idx}_{x}, inv_shufBuf_to_shufIn_L{para_limb_idx}_{PARTIAL_COUNT-x-2}, fwd_shufBuf_to_shufOut_L{para_limb_idx}_{x}, inv_shufOut_to_shufBuf_L{para_limb_idx}_{PARTIAL_COUNT-x-2}, {z}, {x*H_BU_NUM}, direction, iter)\n"
            line += f"        .invoke(shuffler_{x+1}_out, fwd_shufBuf_to_shufOut_L{para_limb_idx}_{x}, inv_shufOut_to_shufBuf_L{para_limb_idx}_{PARTIAL_COUNT-x-2}, fwd_shuffler_to_BU_L{para_limb_idx}_{x+1}, inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-x-2}, {x*H_BU_NUM}, direction, iter)\n"
        else:
            line += f"        .invoke(shuffler_{x+1}, fwd_BU_to_shuffler_L{para_limb_idx}_{x}, inv_BU_to_shuffler_L{para_limb_idx}_{PARTIAL_COUNT-x-2}, fwd_shuffler_to_BU_L{para_limb_idx}_{x+1}, inv_shuffler_to_BU_L{para_limb_idx}_{PARTIAL_COUNT-x-1}, {x*H_BU_NUM}, direction, iter)\n"

    return line

def gen_task_invokes(designParamsVar):

    PARTIAL_COUNT = designParamsVar.PARTIAL_COUNT
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    H_BU_NUM = designParamsVar.H_BU_NUM
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

        # generate TF split tasks
        line += "        //TF split tasks" + "\n"
        line += gen_load_tf(designParamsVar)
        line += "\n"

        for x in range(PARTIAL_COUNT):
            line += "        //BUG " + str(x) + "\n"
            if LAST_H_BU_NUM != 0 and x == (PARTIAL_COUNT - 1):
                current_total_stage = LAST_H_BU_NUM
            else:
                current_total_stage = H_BU_NUM
            for y in range(current_total_stage):
                # generate TF buffer tasks
                # line += "        //TF buffer tasks" + "\n"
                line += gen_TFBuf(designParamsVar, x, y)
                line += "\n"

                # generate BUG tasks
                # line += "        //BUGs" + "\n"
                line += gen_BUGs(designParamsVar, x, y)
                line += "\n"

            # generate shuffler tasks
            # line += "        //shuffler tasks" + "\n"
            line += gen_shuffler(designParamsVar, x)
            line += "\n"

    line += "    ;" + "\n"

    return line