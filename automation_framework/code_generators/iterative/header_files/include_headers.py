def include_kernel_headers():
    line = ""
    line += "#include <cstdint>" + "\n"
    line += "" + "\n"
    line += "#include <tapa.h>" + "\n"
    line += "#include \"ntt.h\"" + "\n"
    return line

def include_host_headers():
    line = ""
    line += "#include <iostream>" + "\n"
    line += "#include <vector>" + "\n"
    line += "" + "\n"
    line += "#include <gflags/gflags.h>" + "\n"
    line += "#include <tapa.h>" + "\n"
    line += "" + "\n"
    line += "#include \"ntt.h\"" + "\n"
    line += "" + "\n"
    line += "using std::clog;" + "\n"
    line += "using std::endl;" + "\n"
    line += "using std::vector;" + "\n"
    line += "\n"
    line += "DEFINE_string(bitstream, \"\", \"path to bitstream file, run csim if empty\");" + "\n"
    line += "\n"
    return line