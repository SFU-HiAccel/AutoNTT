#data type classes used to keep all config variables

# iterative
class iterativeDesignParams:
    def __init__(self):
        self.ARCH_IDENTITY = "I"
        self.WORD_SIZE = 0

        self.REDUCTION_TYPE = 0
        self.WLM_WORD_SIZE = 0
        self.CUSTOM_REDUCTION_CONTENT = None
        
        self.logN = 0
        self.POLY_SIZE = 0

        self.logBU = 0
        self.NUM_BU = 0

        self.DOUBLE_BUF_EN = True

        self.PARA_LIMBS = 0
        self.para_limb_idx = 0

        self.bufParamsVar = None

        self.PLATFORM_FILE = None

        self.DRAM_TYPE = ""
        self.DEFAULT_DRAM_PORT_WIDTH = 0

        self.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0
        self.POLY_LS_PORTS_PER_PARA_LIMB = 0
        self.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = 0
        self.NUM_BUF_PER_PARA_LIMB_POLY_PORT = 0
        self.NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT = 0
        self.POLY_LS_PORTS = 0

        self.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0
        self.TF_PORTS_PER_PARA_LIMB = 0
        self.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = 0
        self.NUM_BUF_PER_PARA_LIMB_TF_PORT = 0
        self.NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT = 0
        self.TF_PORTS = 0

        self.beta = 0
        self.logBeta = 0

        self.FWD_sizeArr = None
        self.INV_sizeArr = None

        self.output_dir_name = ""

class iterativeBufParams:
    def __init__(self):
        self.BUFIDX0 = 0
        self.BUFIDX1 = 0
        self.BETA = 0
        self.TF_ARR_SIZE = 0
        self.LOAD_STORE_DATA_LOOP_COUNTER = 0
        self.LOAD_STORE_THIS_BUF_DATA_END = 0
        self.FWD_LOAD_TF_LOOP_COUNTER = 0
        self.INV_LOAD_TF_LOOP_COUNTER = 0
        self.THIS_BUF_TF_END_FWD = 0
        self.THIS_BUF_TF_END_INV = 0
        self.TF_FORWARDING_START_FWD = 0
        self.TF_FORWARDING_START_INV = 0
        self.FWD_TF_GROUP_IDX0 = ""
        self.FWD_TF_GROUP_IDX1 = ""
        self.INV_TF_GROUP_IDX0 = ""
        self.INV_TF_GROUP_IDX1 = ""

# dataflow
class dataflowDesignParams:
    def __init__(self):
        self.ARCH_IDENTITY = "D"

        self.WORD_SIZE = 0

        self.REDUCTION_TYPE = 0
        self.WLM_WORD_SIZE = 0
        self.CUSTOM_REDUCTION_CONTENT = None

        self.logN = 0
        self.POLY_SIZE = 0

        self.V_BU_NUM = 0
        self.H_BU_NUM = 0

        self.LAST_H_BU_NUM = 0

        self.PARTIAL_COUNT = 0
        self.partial_group = False

        self.CONCAT_FACTOR = 0
        self.LAST_CONCAT_FACTOR = 0

        self.WORD_SIZE = 0

        self.PLATFORM_FILE = None

        self.DRAM_WORD_SIZE = 0

        DEFAULT_DRAM_PORT_WIDTH = 0

        self.mmap_count = 0

        self.tf_mmap_count = 0
        self.multi_ports_tf_mmap_count = 0

        # TF loading related
        self.arr_TFToTF_idx = None
        self.arr_tfArr_length_val = None
        self.is_last_TFGen = None
        self.tfArr_length = 0
        self.tfArr_length_list = None

        # track whether shuffler are split or not
        self.check_spilt = None

        self.PARA_LIMBS = 0
        self.para_limb_idx = 0

# hybrid
class hybridDesignParams:
    def __init__(self):
        self.ARCH_IDENTITY = "H"

        self.WORD_SIZE = 0

        self.REDUCTION_TYPE = 0
        self.WLM_WORD_SIZE = 0
        self.CUSTOM_REDUCTION_CONTENT = None

        self.logN = 0
        self.POLY_SIZE = 0

        self.V_BUG_SIZE = 0
        self.H_BUG_SIZE = 0
        self.logV_BUG_SIZE = 0
        self.BUG_CONCAT_FACTOR = 0
        self.logBUG_CONCAT_FACTOR = 0
        self.V_TOTAL_DATA = 0
        self.log_V_TOTAL_DATA = 0

        self.IS_SPLIT_SHUFFLER = False
        self.IS_SPLIT_BUFFER = False
        self.IS_INTER_BUG_CONNECTIONS = False
        self.NUM_INTER_BUG_COM = 0

        self.PLATFORM_FILE = None

        self.DRAM_TYPE = 0
        self.DEFAULT_DRAM_PORT_WIDTH = 0

        self.PARA_LIMBS = 0
        self.para_limb_idx = 0

        self.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0
        self.POLY_LS_PORTS_PER_PARA_LIMB = 0
        self.POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT = 0
        self.BUG_PER_PARA_LIMB_POLY_PORT = 0
        self.BUG_PER_PARA_LIMB_POLY_WIDE_DATA = 0
        self.SEQ_BUG_PER_PARA_LIMB_POLY_PORT = 0
        self.PARA_LIMB_PORTS_PER_POLY_PORT = 0
        self.POLY_LS_PORTS = 0

        self.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0
        self.TF_PORTS_PER_PARA_LIMB = 0
        self.TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT = 0
        self.TF_LOAD_V_SEGS_PER_PARA_LIMB = 0
        self.TF_LOAD_H_SEGS_PER_PARA_LIMB = 0
        self.PARA_LIMB_PORTS_PER_TF_PORT = 0
        self.TF_PORTS = 0

        self.TFBuffersParamsVar = None
        
        self.LS_FIFO_BUF_SIZE = 0

