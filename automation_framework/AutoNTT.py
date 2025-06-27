from inputs.user_inputs import get_user_inputs

from dse.dse_config import DSEParams
from dse.dse import invoke_DSE

from code_generators.code_gen import code_gen

def main():

    DSEParamsVar = DSEParams()
    
    # Take user inputs and validate
    get_user_inputs(DSEParamsVar)

    # Start DSE for all 3/respective architectures and select the best
    bestConfig = invoke_DSE(DSEParamsVar)

    # Code generator
    code_gen(bestConfig)


if __name__ == "__main__":
    main()