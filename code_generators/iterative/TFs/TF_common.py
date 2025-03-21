#This function generates how many TF groups each buffer carries for forward computation in all the buffer modules which carry TFs.
#The supported BUs by one buf is NUM_BU/2 BUs. i.e. for 256 BUs, (0,128) , (1,129), (2,130), (3,131),...
def fwd_bufWiseTFGroupSizeGen_halfPEsDistBufTogether(designParamsVar):

    NUM_BU = designParamsVar.NUM_BU
    logBU = designParamsVar.logBU
    
    FWD_sizeArr = []

    for BufIdx in range(NUM_BU//2):
        TFSetPerBUf = []
        for i in range(2):
            BUIdx = BufIdx + i*(NUM_BU//2)
            # for stage in range(0, logN):
            for stage in range(0, logBU+1):    #identified that logN(i.e, polynomial size) does not have any impact, but only the #PEs
                # baseTFIdx = ((BUIdx*beta) & ((1<<(stage)) - 1));
                # tfGrpIdx = baseTFIdx//beta;
                tfGrpIdx = ((BUIdx) & ((1<<(stage)) - 1))   #identified that beta has no impact in the equation and it is only the BUIdx has impact on it.
                if(tfGrpIdx not in TFSetPerBUf):
                    TFSetPerBUf.append(tfGrpIdx)
        TFSetPerBUf.sort()
        FWD_sizeArr.append(len(TFSetPerBUf))
        # print("Buf: " + str(BufIdx) + ", size:" + str(len(TFSetPerBUf)))
        # print(TFSetPerBUf)
    
    return FWD_sizeArr

#This function generates how many TF groups each buffer carries for inverse computation in all the buffer modules which carry TFs.
#The supported BUs by one buf is NUM_BU/2 BUs. i.e. for 256 BUs, (0,128) , (1,129), (2,130), (3,131),...
def inv_bufWiseTFGroupSizeGen_halfPEsDistBufTogether(designParamsVar):

    NUM_BU = designParamsVar.NUM_BU
    logBU = designParamsVar.logBU

    INV_sizeArr = []

    for BufIdx in range(NUM_BU//2):
        TFSetPerBUf = []
        for i in range(2):
            BUIdx = BufIdx + i*(NUM_BU//2)
            # for stage in range(0, logN):
            for stage in range(logBU+1, -1, -1):    #identified that logN(i.e, polynomial size) does not have any impact, but only the #PEs
                # baseTFIdx = ((BUIdx*beta) & ((1<<(stage)) - 1));
                # tfGrpIdx = baseTFIdx//beta;
                tfGrpIdx = ((BUIdx) & (~((1<<(stage)) - 1)))   #identified that beta has no impact in the equation and it is only the BUIdx has impact on it.
                if(tfGrpIdx not in TFSetPerBUf):
                    TFSetPerBUf.append(tfGrpIdx)
        TFSetPerBUf.sort()
        INV_sizeArr.append(len(TFSetPerBUf))
        # print("Buf: " + str(BufIdx) + ", size:" + str(len(TFSetPerBUf)))
        # print(TFSetPerBUf)
    return INV_sizeArr

