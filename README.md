# AutoNTT

**Automatic Architecture Design and Exploration for Number Theoretic Transform Acceleration on FPGAs**

AutoNTT is a design automation framework for generating and exploring efficient FPGA architectures for the Number Theoretic Transform (NTT). It enables automatic design space exploration, code generation using HLS, and integration with FPGA toolchains.

---

## System Requirements

- **Python 3**: AutoNTT has been extensively tested with Python 3.6.9.
- **[TAPA](https://github.com/UCLA-VAST/tapa)/[Pasta](https://github.com/SFU-HiAccel/pasta)**: AutoNTT designs are developed using the TAPA framework for task-parallel programming. Users can either [install TAPA](https://github.com/UCLA-VAST/tapa?tab=readme-ov-file#:~:text=Documentation-,Installation,-Hello%20World) or [install Pasta](https://github.com/SFU-HiAccel/pasta#installation), which is an extension of TAPA. AutoNTT has been extensively tested with TAPA version 0.0.20240104.2.
- **AMD/Xilinx Tools**: TAPA relies on AMD/Xilinx Vitis and Vivado. AutoNTT has been tested with Vitis and Vivado version 2023.2.

**Note**: TAPA/Pasta, Vitis, and Vivado are **only required** when:
1. A custom reduction method is passed to the automation framework.
2. You plan to build and run the generated hardware design.
These tools are **not required** for design space exploration (DSE) and code generation using default reduction methods.

---

## Usage

### DSE and code generation

To view all available command-line options:

```bash
python3 AutoNTT.py --help
```

Example command with mandatory inputs:

```bash
python3 AutoNTT.py --poly_size 4096 --mod_size 48 --resources fpga_resources.json
```

Mandatory inputs:

- `--poly_size N`: Specifies the target polynomial size

- `--mod_size log_q` : Specifies the modulus (i.e., prime) bit-width

- `--resources RESOURCE_JSON` : Specifies the target device resources (see the provided `fpga_resources.json` as a template)

Optional inputs:

A detailed description of all supported optional inputs is provided below.

Tool output:

Upon a successful run, the generated design code will be written to the following directory: `tool_outputs/<design_name>/`

### Build the design and run

C simulation:

```bash
make csim
```
Tapa run with floorplanning:

```bash
make tapa_wi_floorplan
```

Build the design using Vivado:

```bash
make build_hw
```

Run design on FPGA:

```bash
make run_hw
```
