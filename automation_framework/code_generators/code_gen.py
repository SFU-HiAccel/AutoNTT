from code_generators.iterative.codeGen_iterative import gen_iterative
from code_generators.dataflow.codeGen_dataflow import gen_dataflow
from code_generators.hybrid.codeGen_hybrid import gen_hybrid

def code_gen(bestConfig):

    if(bestConfig.ARCH_IDENTITY == "I"):
        gen_iterative(bestConfig)
    elif(bestConfig.ARCH_IDENTITY == "D"):
        gen_dataflow(bestConfig)
    elif(bestConfig.ARCH_IDENTITY == "H"):
        gen_hybrid(bestConfig)

    