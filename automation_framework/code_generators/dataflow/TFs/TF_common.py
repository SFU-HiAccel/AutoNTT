def compute_tfArr_length(logN, V_BU_NUM):
    tfArr_length = 0
    tfArr_length_list = []
    sum_tf_per_stage = 1
    for i in range(logN):
        tf_depth = (sum_tf_per_stage // V_BU_NUM) if (sum_tf_per_stage // V_BU_NUM) != 0 else 1
        tfArr_length += tf_depth
        tfArr_length_list.append(tf_depth)
        sum_tf_per_stage <<= 1
    return tfArr_length, tfArr_length_list

def gen_TF_load_config(designParamsVar):

    logN = designParamsVar.logN
    H_BU_NUM = designParamsVar.H_BU_NUM
    V_BU_NUM = designParamsVar.V_BU_NUM
    multi_ports_tf_mmap_count = designParamsVar.multi_ports_tf_mmap_count
    tf_mmap_count = designParamsVar.tf_mmap_count

    arr_TFToTF_idx = []
    arr_tfArr_length_val = []
    is_last_TFGen = []

    # print("multi_ports_tf_mmap_count", multi_ports_tf_mmap_count)
    # print("tf_mmap_count", tf_mmap_count)


    # calculate the value of two array related to multi-ports
    # logN=14:[0, 5, 10, 13]    logN=15:[0, 5, 10, 14]   logN=16:[0, 5, 10, 15]    logN=17:[0, 5, 10, 15, 16]
    for idx in range(multi_ports_tf_mmap_count // tf_mmap_count):
        if ((idx * H_BU_NUM) < (logN - 1)):
            arr_TFToTF_idx.append(idx * H_BU_NUM)
        else:
            arr_TFToTF_idx.append(logN - 1)

    tfArr_length, tfArr_length_list  = compute_tfArr_length(logN, V_BU_NUM)
    for idx in range(len(arr_TFToTF_idx) - 1):
        temp_val = 0
        for idx_2 in range(arr_TFToTF_idx[idx], arr_TFToTF_idx[idx+1]):
            temp_val += tfArr_length_list[idx_2]
        arr_tfArr_length_val.append(temp_val)
    arr_tfArr_length_val.append(tfArr_length_list[len(tfArr_length_list)-1])

    for idx in range(logN):
        if ((idx+1) in arr_TFToTF_idx) or (idx == (logN - 1)):
            is_last_TFGen.append(1)
        else:
            is_last_TFGen.append(0)

    designParamsVar.arr_TFToTF_idx = arr_TFToTF_idx
    designParamsVar.arr_tfArr_length_val = arr_tfArr_length_val
    designParamsVar.is_last_TFGen = is_last_TFGen
    designParamsVar.tfArr_length = tfArr_length
    designParamsVar.tfArr_length_list = tfArr_length_list