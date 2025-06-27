import sys

####
# During TF loading in hybrid arch, we have a couple of layers each containing some num of TFs to load.
# To optimize number of ports required to loading data, we combine a couple of layers together.
# However, this should be done carefully to balance number of data for each port.
# We use solution for linear partition problem in The Algorithm Design Manual to optimally find the best divsion.
####

#### V0 ####
# Noticed that this could return empty partitions

# def partition(s, n, k):
#     MAXINT = sys.maxsize
    
#     # DP table for values
#     m = [[0] * (k) for _ in range(n)]
#     # DP table for dividers
#     d = [[0] * (k) for _ in range(n)]
#     # Prefix sums array
#     p = [0] * (n + 1)
    
#     # Construct prefix sums
#     for i in range(1, n + 1):
#         p[i] = p[i - 1] + s[i - 1]
    
#     # Initialize boundaries
#     for i in range(0, n):
#         m[i][0] = p[i+1]
#     for j in range(0, k):
#         m[0][j] = s[0]
    
#     # Evaluate main recurrence
#     for i in range(1, n):
#         for j in range(1, k):
#             m[i][j] = MAXINT
#             for x in range(0, i):
#                 cost = max(m[x][j - 1], p[i+1] - p[x+1])
#                 if m[i][j] > cost:
#                     m[i][j] = cost
#                     d[i][j] = x+1
    
#     partition_arr = []
#     reconstruct_partition(s, d, n, k, partition_arr)
#     return partition_arr

# def reconstruct_partition(s, d, n, k, partition_arr):
#     if k == 1:
#         subArr= extract_partition(s, 0, n-1)
#     else:
#         reconstruct_partition(s, d, d[n-1][k-1], k - 1, partition_arr)
#         subArr = extract_partition(s, d[n-1][k-1], n - 1)
#     partition_arr.append(subArr)

# def extract_partition(s, start, end):
#     # print(" ".join(map(str, s[start:end + 1])))
#     subArr = s[start:end + 1]
#     return subArr

#### V1 ####

def partition(s, n, k):
    MAXINT = sys.maxsize

    # DP table for values
    m = [[0] * k for _ in range(n)]
    # DP table for dividers
    d = [[0] * k for _ in range(n)]
    # Prefix sums array
    p = [0] * (n + 1)

    # Construct prefix sums
    for i in range(1, n + 1):
        p[i] = p[i - 1] + s[i - 1]

    # Initialize boundaries
    for i in range(n):
        m[i][0] = p[i + 1]
    for j in range(k):
        m[0][j] = s[0]

    # Evaluate main recurrence
    for i in range(1, n):
        for j in range(1, k):
            m[i][j] = MAXINT
            for x in range(j - 1, i):  # updated to avoid empty splits
                cost = max(m[x][j - 1], p[i + 1] - p[x + 1])
                if m[i][j] > cost:
                    m[i][j] = cost
                    d[i][j] = x + 1

    partition_arr = []
    split_indices = reconstruct_split_indices(d, n, k)
    start = 0
    for end in split_indices:
        partition_arr.append(s[start:end])
        start = end
    partition_arr.append(s[start:])  # final segment

    return partition_arr


def reconstruct_split_indices(d, n, k):
    """Backtrack to get split indices (start of each partition)."""
    splits = []
    i, j = n - 1, k - 1
    while j > 0:
        splits.append(d[i][j])
        i = d[i][j] - 1
        j -= 1
    return sorted(splits) 

####
# This function is used in the case of partitioning solution is different for FWD and INV
# In such cases, we check the impact of imposing one's partitionin solution to the other
# and select the one with the minimum effect(i.e, one with the minimum load counter per seg).
####
def replacePartitioningSolution(fwd_partition, inv_partition):

    ## check FWD partitioning for INV ##

    #normalize
    normalize_inv_counters = [item for sublist in inv_partition for item in sublist]

    #extracting layer per seg in FWD partitioning
    fwd_layers_per_seg = [len(item) for item in fwd_partition]

    #update INV partitioning according to FWD partitioning
    layer_id = 0
    inv_updated_partition = []
    inv_updated_load_counter_per_seg = []
    for seg_id in range(len(fwd_layers_per_seg)):
        new_seg = []
        new_seg_load_counter = 0
        for layers in range(fwd_layers_per_seg[seg_id]):
            new_seg.append(normalize_inv_counters[layer_id])
            new_seg_load_counter = new_seg_load_counter + normalize_inv_counters[layer_id]
        inv_updated_partition.append(new_seg)
        inv_updated_load_counter_per_seg.append(new_seg_load_counter)
    
    ## check INV partitioning for FWD ##

    #normalize
    normalize_fwd_counters = [item for sublist in fwd_partition for item in sublist]

    #extracting layer per seg in INV partitioning
    inv_layers_per_seg = [len(item) for item in inv_partition]

    #update FWD partitioning according to INV partitioning
    layer_id = 0
    fwd_updated_partition = []
    fwd_updated_load_counter_per_seg = []
    for seg_id in range(len(inv_layers_per_seg)):
        new_seg = []
        new_seg_load_counter = 0
        for layers in range(inv_layers_per_seg[seg_id]):
            new_seg.append(normalize_fwd_counters[layer_id])
            new_seg_load_counter = new_seg_load_counter + normalize_fwd_counters[layer_id]
        fwd_updated_partition.append(new_seg)
        fwd_updated_load_counter_per_seg.append(new_seg_load_counter)
    
    #check the max load counters of updated partitioning
    fwd_based_max_load_counter = max(inv_updated_load_counter_per_seg)
    inv_based_max_load_counter = max(fwd_updated_load_counter_per_seg)

    #select based on the lowest load counter in the updated schedule
    if(fwd_based_max_load_counter<inv_based_max_load_counter): #select fwd
        return fwd_partition, inv_updated_partition
    else:
        return fwd_updated_partition, inv_partition

####
# This function is to verify if the partition is same for both forward and inverse
####
def verifyFwdInvPartitions(fwd_partition, inv_partition):
    
    len1 = len(fwd_partition)
    len2 = len(inv_partition)

    check_success = True

    if(len1==len2): #number of segs equal
        for i in range(len1): #check number of layers in each seg equal
            if( len(fwd_partition[i]) != len(inv_partition[i]) ):
                check_success = False    
    else:
        check_success = False
            
    if(not(check_success)): #if layers in each seg is not equal
        fwd_partition, inv_partition = replacePartitioningSolution(fwd_partition, inv_partition)
    
    return fwd_partition, inv_partition