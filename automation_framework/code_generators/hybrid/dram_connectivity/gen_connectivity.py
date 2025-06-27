###### DRAM Types ######
HBM=0
DDR=1
#########################

# Currently assign DRAM ports to design ports in ascending order.
# This is ok as we later user TAPA's HBM binding enable which will find better assignment according to the floorplan.
def gen_ntt_connectivity_code(designParamsVar):

    DRAM_TYPE = designParamsVar.DRAM_TYPE

    if(DRAM_TYPE==HBM):
        port_name = "HBM"
    else:
        port_name = "DDR"

    line = ""

    dram_port_idx = 0
    line += "[connectivity]" + "\n"
    
    for port_idx in range(designParamsVar.POLY_LS_PORTS):
        line += "sp=NTT_kernel.polyVectorInOut_G" + str(port_idx) + ":" + port_name + "[" + str(dram_port_idx) + "]" + "\n"
        dram_port_idx += 1

    for port_idx in range(designParamsVar.TF_PORTS):
        line += "sp=NTT_kernel.TFArr_G" + str(port_idx) + ":" + port_name + "[" + str(dram_port_idx) + "]" + "\n"
        dram_port_idx += 1

    for port_idx in range(designParamsVar.POLY_LS_PORTS):
        line += "sp=NTT_kernel.polyVectorInOut_G" + str(designParamsVar.POLY_LS_PORTS + port_idx) + ":" + port_name + "[" + str(dram_port_idx) + "]" + "\n"
        dram_port_idx += 1
    
    return line