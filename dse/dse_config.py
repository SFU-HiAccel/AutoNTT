# Input parameters
class DSEParams:
    def __init__(self):
        self.WORD_SIZE = 0

        self.POLY_SIZE = 0
        self.logN = 0

        self.DEVICE_RESOURCES = None
        self.PLATFORM_FILE = None
        
        self.TARGET_LATENCY_MS = None
        self.TARGET_THROUGHPUT = None

        self.TARGET_ARCH_TYPE = None

        self.PARA_LIMBS = 0

        self.REDUCTION_TYPE = 0
        self.WLM_WORD_SIZE = 0
        self.CUSTOM_REDUCTION_CONTENT = None

        self.BU_PIPELINE_DEPTH_CYCLES = 0
        self.BU_RESOURCE = {
        "LUT" : 0,
        "FF" : 0,
        "DSP" : 0
        }
        self.NUM_BU_BUDGET = 0

        self.BEST_ARCH_CONFIG = None

        self.DRAM_BW_PER_PORT = 0
        self.NUM_DRAM_PORTS = 0
        self.DRAM_PORT_WIDTH = 0
        self.DRAM_WORD_SIZE = 0

# Required iterative architecture parameters based on the iterative arch code generator
class iterativeConfigs:
    def __init__(self, DSEParamsVar_ref):
        self.ARCH_IDENTITY = "I"
        self.ARCH_VALID = False

        self.DSEParamsVar = DSEParamsVar_ref

        self.NUM_BU = 0

        self.DOUBLE_BUF_EN = False

        self.DESIGN_RESOURCES = {
        "LUT" : 0,
        "FF" : 0,
        "DSP" : 0,
        "BRAM" : 0,
        "URAM" : 0,
        "offchip_ports" : 0
        }

        self.POLY_LS_PORTS_PER_PARA_LIMB = 0
        self.TF_PORTS_PER_PARA_LIMB = 0
        self.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0
        self.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0

        self.COMPUTE_LATECY_CYCLES = 0
        self.POLY_LOAD_OR_STORE_LATENCY_CYCLES = 0
        self.TF_LOAD_LATENCY_CYCLES = 0
        self.EXPECTED_LATENCY_MS = float("inf")
        self.EXPECTED_THROUGHPUT = 0

# Required dataflow architecture parameters based on the dataflow arch code generator
class dataflowConfigs:
    def __init__(self, DSEParamsVar_ref):
        self.ARCH_IDENTITY = "D"
        self.ARCH_VALID = False

        self.DSEParamsVar = DSEParamsVar_ref

        self.NUM_BU = 0

        self.COMPUTE_LATECY_CYCLES = 0

        self.V_BUG_SIZE = 0
        self.H_BUG_SIZE = 0
        self.V_TOTAL_DATA = 0

        self.POLY_LS_PORTS_PER_PARA_LIMB = 0
        self.V_TF_PORTS_PER_PARA_LIMB = 0
        self.H_TF_PORTS_PER_PARA_LIMB = 0
        self.TF_PORTS_PER_PARA_LIMB = 0
        self.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0
        self.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0

        self.DESIGN_RESOURCES = {
        "LUT" : 0,
        "FF" : 0,
        "DSP" : 0,
        "BRAM" : 0,
        "URAM" : 0,
        "offchip_ports" : 0
        }

        self.TF_FIFO_DEPTH = 0

        self.EXPECTED_LATENCY_MS = float("inf")
        self.EXPECTED_THROUGHPUT = 0

# Required hybrid architecture parameters based on the hybrid arch code generator
class hybridConfigs:
    def __init__(self, DSEParamsVar_ref):
        self.ARCH_IDENTITY = "H"
        self.ARCH_VALID = False

        self.DSEParamsVar = DSEParamsVar_ref

        self.NUM_BU = 0

        self.COMPUTE_LATECY_CYCLES = 0

        self.V_BUG_SIZE = 0
        self.H_BUG_SIZE = 0
        self.BUG_CONCAT_FACTOR = 0
        self.V_TOTAL_DATA = 0
        self.logV_BUG_SIZE = 0
        self.logBUG_CONCAT_FACTOR = 0
        self.log_V_TOTAL_DATA = 0

        self.POLY_LS_PORTS_PER_PARA_LIMB = 0
        self.TF_PORTS_PER_PARA_LIMB = 0
        self.POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0
        self.TF_DRAM_PORT_WIDTH_PER_PARA_LIMB = 0

        self.DESIGN_RESOURCES = {
        "LUT" : 0,
        "FF" : 0,
        "DSP" : 0,
        "BRAM" : 0,
        "URAM" : 0,
        "offchip_ports" : 0
        }

        self.LS_FIFO_BUF_SIZE = 0

        self.EXPECTED_LATENCY_MS = float("inf")
        self.EXPECTED_THROUGHPUT = 0

class linearModelArgs:
    m = 0
    c = 0

# Target frequency in MHz
GLOBAL_TARGET_FREQ_MHZ = 250

# DRAM port BW values
# These values are taken from Alec's paper (https://www.sfu.ca/~zhenman/files/J9-TRETS2022-uBench.pdf: Fig. 4) for 250 MHz
HBM_PORT_BW = 13.18
DDR_PORT_BW = 13.73 # (14.84+12.62)

# Set default DRAM port width
DEFAULT_DRAM_PORT_WIDTH = 512

# Set (off-chip access time)/(compute time) ratio for double buffering
OFF_CHIP_ACC_TO_COMP_THRESHOLD = 0.25

# LUT and FF resource estimation adjustment percentage
LUT_FF_MODEL_ADJUST_PERCENTAGE  = 5

# Default DSP data widths
DSP_DATA_WIDTHS = [18, 27]

# Default BRAM 18k parameters
BRAM_WIDTH = 18
BRAM_DEPTH = 1024

# Default URAM parameters
URAM_WIDTH = 72
URAM_DEPTH = 4096

# AXI resources. For each port AXI interconnect takes some resources. These numbers are taken to align with Aubridge reports.
AXI_INTERCONNECT_RESOURCES = {
        "LUT" : 5000,
        "FF" : 6500,
        "DSP" : 0,
        "BRAM" : 0,
        "URAM" : 0
        }