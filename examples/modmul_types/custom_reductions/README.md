# Supporting Custom Modulo Reduction Methods

Custom prime-specific modulo reduction methods are commonly used in NTT implementations. To support this, our framework provides an interface to integrate a custom reduction method and perform design space exploration (DSE) across various architectures and resource budgets.

---

## System Requirements

**Important**: Ensure that TAPA/Pasta, Vitis, and Vivado are loaded in the terminal before running DSE with a custom reduction method.

---

## Examples:

### Example1: 

In this example, our own WLM modulo reduction method is modified to serve as a custom reduction method. Please note the following changes in the corresponding input files:

- **Kernel code** contains both the relevant function declarations and function calls, with the return type expected to be `WORD`.
- **Host function modifications** include the generation of a custom modulus.
- **Twiddle factor (TF) and constant values** are generated within the host function.
- **Header file** includes necessary type and constant definitions.
- An **interface variable** is passed and the same name is used in both:
  - The `// === BEGIN CALL ===` section of the kernel code, and  
  - The `// === BEGIN REDUCTION CALL ===` section of the host code.

Example command to run:
```bash
python3 AutoNTT.py \
--poly_size 4096 \
--mod_size 48 \
--resources fpga_resources.json \
--modmul_type C \
--custom_mod_kernel ../examples/modmul_types/custom_reductions/example1_pass_WLM_as_custom/custom_red_kernel.txt \
--custom_mod_host ../examples/modmul_types/custom_reductions/example1_pass_WLM_as_custom/custom_red_host.txt \
--custom_mod_header ../examples/modmul_types/custom_reductions/example1_pass_WLM_as_custom/custom_red_header.txt \
--custom_mod_interface ../examples/modmul_types/custom_reductions/example1_pass_WLM_as_custom/custom_red_interface.txt \
--platform xilinx_u50_gen3x16_xdma_5_202210_1
```

### Example2: 

In this example as well, our WLM modulo reduction method is modified to function as a custom reduction method. However, note the following differences:

- The **host function modifications do not** include custom modulus generation.
- All other definitions and structures are similar to those in Example 1.

Example command to run:
```bash
python3 AutoNTT.py \
--poly_size 4096 \
--mod_size 48 \
--resources fpga_resources.json \
--modmul_type C \
--custom_mod_kernel ../examples/modmul_types/custom_reductions/example2_pass_WLM_as_custom/custom_red_kernel.txt \
--custom_mod_host ../examples/modmul_types/custom_reductions/example2_pass_WLM_as_custom/custom_red_host.txt \
--custom_mod_header ../examples/modmul_types/custom_reductions/example2_pass_WLM_as_custom/custom_red_header.txt \
--custom_mod_interface ../examples/modmul_types/custom_reductions/example2_pass_WLM_as_custom/custom_red_interface.txt
```

### Example3: 

In this example, a prime-specific reduction method is implemented as a custom reduction method. Please note the following in the respective files:

- The **kernel function** includes both the function definition and the function call. The return type is `WORD`, and no additional input arguments are used.
- The **host function** includes a custom modulus generation function and its corresponding function call. No other functions are involved.
- There are **no definitions** required in the header file.
- Since no additional constant values are used in the kernel code, **no interface arguments** are needed.

Example command to run:
```bash
python3 AutoNTT.py \
--poly_size 1024 \
--mod_size 52 \
--resources fpga_resources.json \
--modmul_type C \
--custom_mod_kernel ../examples/modmul_types/custom_reductions/example3_prime_specific_example/custom_red_kernel.txt \
--custom_mod_host ../examples/modmul_types/custom_reductions/example3_prime_specific_example/custom_red_host.txt
```

---

## Input Arguments

A custom reduction method may require code changes in multiple locations. We accommodate this through several dedicated command-line switches.

### Mandatory arguments:

#### Enable Custom Reduction Method with `--modmul_type`

- It is mandatory to pass --modmul_type C to enable the use of a custom modulo reduction method during DSE.

#### Passing Kernel Changes with `--custom_mod_kernel`

- The file passed to this switch must contain two sections, as shown below:

```cpp
// === BEGIN DEFS ===
<All kernel function definitions related to the custom reduction method>
// === END DEFS ===

// === BEGIN CALL ===
WORD reducedProduct = <custom reduction function call in BU>;
// === END CALL ===
```

- Under `// === BEGIN DEFS ===`, include all kernel function definitions related to your custom reduction logic. Ensure that the final function returns a value of type `WORD` (WORD = ap_uint<log_q>)
- Under `// === BEGIN CALL ===`, specify how the final reduction function should be called within the Butterfly Unit (BU). You will have access to the following variables:
  - `WORD right` : The right polynomial value in the Cooley-Tukey BU.
  - `WORD tfVal` : The twiddle factor value.
  - `WORD q` : The modulus (i.e., prime value).
  - Other arguments: If additional arguments are required from the host, you can declare them separately using the `--custom_mod_interface` switch and use them here.

### Optional arguments:

#### Passing Host Changes with `--custom_mod_host`

- The file passed to this switch must contain four sections, as shown below:

```cpp
// === BEGIN MOD_GEN DEFS ===
<Functions related to custom modulus generation logic if needed>
// === END MOD_GEN DEFS ===

// === BEGIN REDUCTION DEFS ===
<Other host functions related to custom modulo reduction: This may include constant value(s) generation, TF modification etc.>
// === END REDUCTION DEFS ===

// === BEGIN MOD_GEN CALL ===
<Function call of custom modulus generation if one was defined>
// === END MOD_GEN CALL ===

// === BEGIN REDUCTION CALL ===
<Other host function variable definitions and custom modulo reduction related function call(s)>
// === END REDUCTION CALL ===
```

- A custom modulo reduction method may require generating specific prime modulus values. If so, the definition for modulus generation should be included under the section `// === BEGIN MOD_GEN DEFS ===`. If not passed, default modulus generation is used. Ensure that this function takes the following arguments and the function generate one prime modulus per parallel limb, even if only a single limb is required.
  - `std::vector<WORD>& modulusArray`: This vector should be taken as input and updated for the output modulu values for each parallel limb.
  - `VAR_TYPE_32 limbCount` : Input value with the count of parallel limbs.
 
- A custom modulo reduction method may require generating specific constants values and change TFs. If so, the definition for such functions must be included under the section `// === BEGIN REDUCTION DEFS ===`. If you generate constant(s) that should be passed to the kernel make sure you generate them for all the parallel limbs. These functions can take the following arguments if required.
  - `std::vector<WORD>& modulusArray`: Input vector containing modulus related to all parallel limbs.
  - `VAR_TYPE_32 limbCount`: Input value with the count of parallel limbs.
  - `vector<WORD>& tfArr[PARA_LIMBS];` : Input array of vectors containing FWD TFs related to each limb.
  - `vector<WORD>& inv_tfArr[PARA_LIMBS];` : Input array of vectors containing INV TFs related to each limb.
 
- If you have defined a custom modulus generation, the function call (to be included in the main) should be included under the section `// === BEGIN MOD_GEN CALL ===`. If not passed, default modulus generation function call is used. Make sure to pass following two as arguments:
  - `vector<WORD> workingModulus_arr(PARA_LIMBS);` : The vector to be updated with new modulus values
  - `VAR_TYPE_32 PARA_LIMBS`: This is the variable in main function containing parallel limb count.

- If you have defined other functions to generate some constants or modify TFs, the related `main` function content should be added under the section `// === BEGIN REDUCTION CALL ===`. Following defintions of main function should be used to pass relevant arguments if used.
  - `vector<WORD> workingModulus_arr(PARA_LIMBS);` : The vector containing modulus values to all parallel limbs.
  - `VAR_TYPE_32 PARA_LIMBS`: This is the variable in main function containing parallel limb count.
  - `vector<WORD> tfArr[PARA_LIMBS];` : The vector containing FWD TFs related to each limb.
  - `vector<WORD> inv_tfArr[PARA_LIMBS];` : The vector containing INV TFs related to each limb.
 
#### Passing Header File Changes with `--custom_mod_header`

- If you need to include custom definitions in the generated header file, place them in a separate file and pass it using this switch. An example of such a file might look like:
```cpp
const unit32_t CUSTOM_RED_CONST = 5;
#define CUSTOM_WORD ap_uint<CUSTOM_RED_CONST>
```

#### Passing Interface Arguments with `--custom_mod_interface`

- If your custom reduction method requires passing constant variables to the Butterfly Unit (BU), list them as comma-separated entries in a separate file and provide it via this switch. An example of such a file:
```
ap_uint<32> arg1,ap_uint<35> arg2
```
- Ensure that the same variable names are used in the host code when generating these constants. For example, under the `// === BEGIN REDUCTION CALL ===` section of the host code, you might define:
```
vector<ap_uint<32>> arg1(PARA_LIMBS);
vector<ap_uint<35>> arg2(PARA_LIMBS);
```

#### Passing Platform File with `--platform`

- When a custom reduction method is passed, the tool automatically creates a test design with it and synthesis the design to extract BU details with the custom reduction.
- Hence, if you have a specific device target, you should provide the platform with this switch. If not provided, tool default is set to `xilinx_u280_gen3x16_xdma_1_202211_1` and it will try to extract details with U280 FPGA.
- An example input may looks like:
`--platform xilinx_u50_gen3x16_xdma_5_202210_1`
`--platform xilinx_u200_gen3x16_xdma_2_202110_1`

---

## Debug

If you encounter issues while enabling custom reduction methods, consider using `--verbose 2` to enable full trace logging and help identify the problem.
