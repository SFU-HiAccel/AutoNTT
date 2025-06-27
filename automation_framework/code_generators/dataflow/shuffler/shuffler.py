def generate_start_index_i_base(CONCAT_FACTOR):
    result = []
    # Generate the two series for interleaving
    even_series = [((CONCAT_FACTOR - (i * 2)) % CONCAT_FACTOR) for i in range(CONCAT_FACTOR // 2)]
    odd_series = [((CONCAT_FACTOR - (i * 2) - 1) % CONCAT_FACTOR) for i in range(CONCAT_FACTOR // 2)]
    
    # Interleave the two series
    for i in range(CONCAT_FACTOR // 2):
        result.append(even_series[i])
        
    for i in range(CONCAT_FACTOR // 2):
        result.append(odd_series[i])
    
    return result

def generate_shuffler_function_signature(X, shuffler_num, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR):
    function_signature = f"""
void shuffler_{X + 1}(tapa::istreams<WORD, {CONCAT_FACTOR}>& fwd_in_strm,
            tapa::istreams<WORD, {CONCAT_FACTOR}>& inv_in_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& fwd_out_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& inv_out_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {H_BU_NUM};
    int buffer_size = stride << {H_BU_NUM + 1};
"""
    # Prepare the C++ array as a formatted string
    function_signature += f"""
    int start_index_i_base[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_start_index_i_base(CONCAT_FACTOR)))
    function_signature += "};\n"

    if X != (shuffler_num - 1):
        buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1)
        mod_size_name = "buffer_size"
        last_shuffler = False
    else:
        buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1) >> 1
        mod_size_name = "iteration_size"
        last_shuffler = True
    function_signature += f"""
    WORD buf_poly[CONCAT_FACTOR][{buffer_size}];  // wait {(1 << (X * H_BU_NUM)) << H_BU_NUM}, but double buffer = {((1 << (X * H_BU_NUM)) << H_BU_NUM) << 1}
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram
    #pragma HLS array_partition type=complete dim=1 variable=buf_poly

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {{
            // NTT realted defination
"""
    if last_shuffler == False:
        function_signature += "            int ntt_actual_j = j_read&(buffer_size-1);\n"
    else:
        function_signature += "            int ntt_actual_j = j_read;\n"
    function_signature += f"""
            int ntt_offset_i = (j_read>>log_stride)%CONCAT_FACTOR;  // change in last_shuffler

            bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
                #pragma HLS UNROLL
                fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
            }}


            // iNTT realted defination
            int intt_actual_j = 0;

            // int intt_index = (j_read>>log_stride)%CONCAT_FACTOR;
            int intt_offset_i = start_index_i_base[ntt_offset_i];

            bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
            CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
                #pragma HLS UNROLL
                inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
            }}

            LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
                #pragma HLS UNROLL
                if (fwd_inFIFONotEmpty) {{
                    int offset_plus_i = ntt_offset_i+i;  // change in last_shuffler
                    int actual_i = offset_plus_i%CONCAT_FACTOR;
                    buf_poly[actual_i][ntt_actual_j] = fwd_in_strm[i].read();
                }} else if (inv_inFIFONotEmpty) {{
                    int offset_plus_i = intt_offset_i+i;
                    int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                    // iteration_of_j + offset_of_j + offset_of_i
                    intt_actual_j = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + actual_strm_i*stride)&({mod_size_name}-1);
                    buf_poly[i][intt_actual_j] = inv_in_strm[actual_strm_i].read();
                }}
            }}

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{
                j_read++;
                j_read_all_iter++;
            }}

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {{
                j_read = 0;
            }}
        }}

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {{
            writeEnable = true;
        }}

        /* poly input */
    
        // NTT defination
        int ntt_actual_j = 0;

        int ntt_index = (j_write>>log_stride)%CONCAT_FACTOR;
        int ntt_offset_i = start_index_i_base[ntt_index];


        // iNTT defination
"""
    if last_shuffler == False:
        function_signature += "            int intt_actual_j = j_write&(buffer_size-1);\n"
    else:
        function_signature += "            int intt_actual_j = j_write;\n"
    function_signature += f"""
        // int intt_offset_i = (j_write>>log_stride)%CONCAT_FACTOR;
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL

            if (direction && writeEnable) {{
                int offset_plus_i = ntt_offset_i+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                ntt_actual_j = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + actual_strm_i*stride)&({mod_size_name}-1);
                fwd_out_strm[actual_strm_i].write(buf_poly[i][ntt_actual_j]);
            }} else if ((!direction) && writeEnable) {{
                // int offset_plus_i = intt_offset_i+i;
                int offset_plus_i = ntt_index+i;
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                inv_out_strm[i].write(buf_poly[actual_i][intt_actual_j]);
            }}
        }}

        if (writeEnable) {{
            j_write++;
            j_write_all_iter++;
        }}

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {{
            j_write = 0;
        }}

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {{
            writeEnable = false;
        }}
    }}
}}

"""
    return function_signature

def generate_split_shuffler_function_signature(X, shuffler_num, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR):
    function_signature = f"""
void shuffler_{X + 1}_in(tapa::istreams<WORD, {CONCAT_FACTOR}>& fwd_in_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& inv_out_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& fwd_out_strm,
            tapa::istreams<WORD, {CONCAT_FACTOR}>& inv_in_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {H_BU_NUM};
    int buffer_size = stride << {H_BU_NUM + 1};
"""
    # Prepare the C++ array as a formatted string
    function_signature += f"""
    int start_index_i_base[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_start_index_i_base(CONCAT_FACTOR)))
    function_signature += "};\n"

    function_signature += f"""
    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    LOAD_STORE_POLY_TF:for(int j = 0, j_all = 0; j_all < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        int offset_i = (j>>log_stride)%CONCAT_FACTOR;

        bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
        CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
        }}

        bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
        CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
        }}

        LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL

            int offset_plus_i = offset_i+i;
            int actual_i = offset_plus_i%CONCAT_FACTOR;
            if (fwd_inFIFONotEmpty) {{
                fwd_out_strm[actual_i].write(fwd_in_strm[i].read());
            }}  else if (inv_inFIFONotEmpty) {{
                inv_out_strm[i].write(inv_in_strm[actual_i].read());
            }}
            
        }}

        if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{
            j++;
            j_all++;
        }}

        if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_all&(BUF_SIZE-1)) == 0) {{
            j = 0;
        }}
    }}

}}

"""

    function_signature += f"""
void shuffler_{X + 1}_out(tapa::istreams<WORD, {CONCAT_FACTOR}>& fwd_in_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& inv_out_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& fwd_out_strm,
            tapa::istreams<WORD, {CONCAT_FACTOR}>& inv_in_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {H_BU_NUM};
    int buffer_size = stride << {H_BU_NUM + 1};
"""
    # Prepare the C++ array as a formatted string
    function_signature += f"""
    int start_index_i_base[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_start_index_i_base(CONCAT_FACTOR)))
    function_signature += "};\n"

    function_signature += f"""
    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    LOAD_STORE_POLY_TF:for(int j = 0, j_all = 0; j_all < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        int index = (j>>log_stride)%CONCAT_FACTOR;
        int offset_i = start_index_i_base[index];

        bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
        CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
        }}

        bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
        CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
        }}
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL

            int offset_plus_i = offset_i+i;
            int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
            if (fwd_inFIFONotEmpty) {{
                fwd_out_strm[actual_strm_i].write(fwd_in_strm[i].read());
            }} else if (inv_inFIFONotEmpty) {{
                inv_out_strm[i].write(inv_in_strm[actual_strm_i].read());
            }}
        }}

        if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{
            j++;
            j_all++;
        }}

        if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_all&(BUF_SIZE-1)) == 0) {{
            j = 0;
        }}
    }}

}}
"""

    function_signature += f"""
void shuffler_{X + 1}(tapa::istream<WORD>& fwd_in_strm,
            tapa::ostream<WORD>& inv_out_strm,
            tapa::ostream<WORD>& fwd_out_strm,
            tapa::istream<WORD>& inv_in_strm, VAR_TYPE_8 i, 
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {H_BU_NUM};
    int buffer_size = stride << {H_BU_NUM + 1};
"""
    # Prepare the C++ array as a formatted string
    function_signature += f"""
    int start_index_i_base[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_start_index_i_base(CONCAT_FACTOR)))
    function_signature += "};\n"

    if X != (shuffler_num - 1):
        buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1)
        mod_size_name = "buffer_size"
        last_shuffler = False
    else:
        buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1) >> 1
        mod_size_name = "iteration_size"
        last_shuffler = True
    function_signature += f"""
    WORD buf_poly[{buffer_size}];  // wait {(1 << (X * H_BU_NUM)) << H_BU_NUM}, but double buffer = {((1 << (X * H_BU_NUM)) << H_BU_NUM) << 1}
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {{
            // NTT realted defination
"""
    if last_shuffler == False:
        function_signature += "            int ntt_actual_j_0 = j_read&(buffer_size-1);\n"
    else:
        function_signature += "            int ntt_actual_j_0 = j_read;\n"
    function_signature += f"""
            int ntt_offset_i_0 = (j_read/stride)%CONCAT_FACTOR;

            bool fwd_inFIFONotEmpty = (!fwd_in_strm.empty());


            // iNTT realted defination
            int intt_actual_j_0 = 0;

            int intt_index_0 = (j_read>>log_stride)%CONCAT_FACTOR;
            int intt_offset_i_0 = start_index_i_base[intt_index_0];

            bool inv_inFIFONotEmpty = (!inv_in_strm.empty());


            if (fwd_inFIFONotEmpty) {{
                int offset_plus_i = ntt_offset_i_0+i;
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                // buf_poly[actual_i][ntt_actual_j+0] = fwd_in_strm[i].read();
                buf_poly[ntt_actual_j_0] = fwd_in_strm.read();
            }} else if (inv_inFIFONotEmpty) {{
                int offset_plus_i = intt_offset_i_0+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                intt_actual_j_0 = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + actual_strm_i*stride)&({mod_size_name}-1);
                // buf_poly[i][intt_actual_j_0] = inv_in_strm[actual_strm_i].read();
                buf_poly[intt_actual_j_0] = inv_in_strm.read();
            }}

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{
                j_read++;
                j_read_all_iter++;
            }}

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {{
                j_read = 0;
            }}
        }}

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {{
            writeEnable = true;
        }}

        /* poly input */
    
        // NTT defination
        int ntt_actual_j_1 = 0;

        int ntt_index_1 = (j_write/stride)%CONCAT_FACTOR;
        int ntt_offset_i_1 = start_index_i_base[ntt_index_1];


        // iNTT defination
"""
    if last_shuffler == False:
        function_signature += "            int intt_actual_j_1 = j_write&(buffer_size-1);\n"
    else:
        function_signature += "            int intt_actual_j_1 = j_write;\n"
    function_signature += f"""
        int intt_offset_i_1 = (j_write>>log_stride)%CONCAT_FACTOR;

        if (direction && writeEnable) {{
            int offset_plus_i = ntt_offset_i_1+i;
            int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
            // iteration_of_j + offset_of_j + offset_of_i
            ntt_actual_j_1 = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + actual_strm_i*stride)&({mod_size_name}-1);
            // fwd_out_strm[actual_strm_i].write(buf_poly[i][ntt_actual_j]);
            fwd_out_strm.write(buf_poly[ntt_actual_j_1]);
        }} else if ((!direction) && writeEnable) {{
            int offset_plus_i = intt_offset_i_1+i;
            int actual_i = offset_plus_i%CONCAT_FACTOR;
            // inv_out_strm[i].write(buf_poly[actual_i][intt_actual_j_1]);
            inv_out_strm.write(buf_poly[intt_actual_j_1]);
        }}

        if (writeEnable) {{
            j_write++;
            j_write_all_iter++;
        }}

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {{
            j_write = 0;
        }}

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {{
            writeEnable = false;
        }}
    }}

}}
"""
    return function_signature

def generate_offset_0(LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR):
    result = [0]
    value = CONCAT_FACTOR - 1
    minus = CONCAT_FACTOR // (1 << (LAST_H_BU_NUM - 1)) - 1
    for i in range(LAST_CONCAT_FACTOR - 1):
        result.append(value)
        if i % 2 == 0:  # Even index: decrement by minus
            value -= minus
        else:  # Odd index: decrement by 1
            value -= 1
    return result

def generate_offset_1(CONCAT_FACTOR, start_index):
    return [(CONCAT_FACTOR - num) % CONCAT_FACTOR for num in start_index]

def generate_offset_2(V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR):
    offset = V_BU_NUM // (1 << (LAST_H_BU_NUM - 1))
    indices = []

    # Outer loop for i
    for i in range(CONCAT_FACTOR // (1 << (LAST_H_BU_NUM + 1))):
        base_0 = i * 2
        
        # Middle loop for j
        for j in range((1 << (LAST_H_BU_NUM + 1)) // 4):
            base_1 = j * (CONCAT_FACTOR // (1 << (LAST_H_BU_NUM + 1)) * 4)
            
            # Inner loop for k
            for k in range(4):
                val = base_0 + base_1 + offset * (k % 2) + k // 2
                indices.append(val)

    return indices

def generate_offset_3(LAST_H_BU_NUM, CONCAT_FACTOR):
    base = [0, 1, 0, 1]
    return [x + 2 * (i // (CONCAT_FACTOR // (1 << (LAST_H_BU_NUM - 1)))) for i in range(CONCAT_FACTOR) for x in [base[i % 4]]]


def generate_partial_shuffler_function_signature(logN, X, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR):
    # not split shuffler - partial group
    function_signature = f"""
void shuffler_{X + 1}(tapa::istreams<WORD, {CONCAT_FACTOR}>& fwd_in_strm,
            tapa::istreams<WORD, {CONCAT_FACTOR}>& inv_in_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& fwd_out_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& inv_out_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {LAST_H_BU_NUM};
    int buffer_size = stride << {LAST_H_BU_NUM + 1};
"""
    # Prepare the C++ array as a formatted string
    offset_0 = generate_offset_0(LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR)
    function_signature += f"""
    int start_index_i_base[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, offset_0))
    function_signature += "};"

    function_signature += f"""
    int offset_1[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_1(CONCAT_FACTOR, offset_0)))
    function_signature += "};"

    function_signature += f"""
    int offset_2[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_2(V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};"

    function_signature += f"""
    int offset_3[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_3(LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};\n"

    buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1) >> 1
    function_signature += f"""
    WORD buf_poly[CONCAT_FACTOR][{(1 << logN) // CONCAT_FACTOR}];  // wait {(1 << logN) // CONCAT_FACTOR} = N / CONCAT_FACTOR
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram
    #pragma HLS array_partition type=complete dim=1 variable=buf_poly

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {{
            // iNTT realted defination
            int intt_actual_j = 0;

            int intt_index = (j_read>>log_stride)%LAST_CONCAT_FACTOR;
            int intt_offset_i = start_index_i_base[intt_index];

            bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
            CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
                #pragma HLS UNROLL
                inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
            }}


            // NTT realted defination
            int ntt_actual_j = j_read&(iteration_size-1);  // get j index in buf_poly[][]
            int ntt_offset_i = offset_1[intt_index];  // get the first i index in buf_poly[][]

            bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
            CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
                #pragma HLS UNROLL
                fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
            }}


            LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
                #pragma HLS UNROLL
                if (fwd_inFIFONotEmpty) {{
                    int offset_plus_i = ntt_offset_i+offset_2[i];
                    int actual_i = offset_plus_i%CONCAT_FACTOR;
                    buf_poly[actual_i][ntt_actual_j] = fwd_in_strm[i].read();
                }} else if (inv_inFIFONotEmpty) {{
                    int offset_plus_i = intt_offset_i+i;
                    int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                    // iteration_of_j + offset_of_j + offset_of_i
                    intt_actual_j = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + offset_3[actual_strm_i]*stride)&(iteration_size-1);  //change in last_shuffler
                    buf_poly[i][intt_actual_j] = inv_in_strm[actual_strm_i].read();
                }}
            }}

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{
                j_read++;
                j_read_all_iter++;
            }}

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {{
                j_read = 0;
            }}
        }}

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {{
            writeEnable = true;
        }}

        /* poly input */
    
        // NTT defination
        int ntt_actual_j = 0;

        int ntt_index = (j_write>>log_stride)%LAST_CONCAT_FACTOR;
        int ntt_offset_i = start_index_i_base[ntt_index];

        // iNTT defination
        int intt_actual_j = j_write&(iteration_size-1); 
        int intt_offset_i = offset_1[ntt_index];
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL

            if (direction && writeEnable) {{
                int offset_plus_i = ntt_offset_i+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                ntt_actual_j = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + offset_3[actual_strm_i]*stride)&(iteration_size-1);
                fwd_out_strm[actual_strm_i].write(buf_poly[i][ntt_actual_j]);
            }} else if ((!direction) && writeEnable) {{
                int offset_plus_i = intt_offset_i+offset_2[i];
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                inv_out_strm[i].write(buf_poly[actual_i][intt_actual_j]);
            }}
        }}

        if (writeEnable) {{
            j_write++;
            j_write_all_iter++;
        }}

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {{
            j_write = 0;
        }}

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {{
            writeEnable = false;
        }}
    }}
}}

"""
    return function_signature


def generate_split_partial_shuffler_function_signature(logN, X, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR):
    # split shuffler in - partial group
    function_signature = f"""
void shuffler_{X + 1}_in(tapa::istreams<WORD, {CONCAT_FACTOR}>& fwd_in_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& inv_out_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& fwd_out_strm,
            tapa::istreams<WORD, {CONCAT_FACTOR}>& inv_in_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {LAST_H_BU_NUM};
    int buffer_size = stride << {LAST_H_BU_NUM + 1};
"""
    # Prepare the C++ array as a formatted string
    offset_0 = generate_offset_0(LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR)
    function_signature += f"""
    int start_index_i_base[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, offset_0))
    function_signature += "};"

    function_signature += f"""
    int offset_1[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_1(CONCAT_FACTOR, offset_0)))
    function_signature += "};"

    function_signature += f"""
    int offset_2[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_2(V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};"

    function_signature += f"""
    int offset_3[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_3(LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};\n"

    buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1) >> 1
    function_signature += f"""
    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    LOAD_STORE_POLY_TF:for(int j = 0, j_all = 0; j_all < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        int index = (j>>log_stride)%LAST_CONCAT_FACTOR;
        int offset_i = offset_1[index];

        bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
        CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
        }}

        bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
        CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
        }}

        LOAD_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL

            int offset_plus_i = offset_i+offset_2[i];
            int actual_i = offset_plus_i%CONCAT_FACTOR;
            if (fwd_inFIFONotEmpty) {{
                fwd_out_strm[actual_i].write(fwd_in_strm[i].read());
            }} else if (inv_inFIFONotEmpty) {{
                inv_out_strm[i].write(inv_in_strm[actual_i].read());
            }}
        }}

        if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{
            j++;
            j_all++;
        }}

        if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_all&(BUF_SIZE-1)) == 0) {{
            j = 0;
        }}

    }}
}}

"""

    # split shuffler out - partial group
    function_signature += f"""
void shuffler_{X + 1}_out(tapa::istreams<WORD, {CONCAT_FACTOR}>& fwd_in_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& inv_out_strm,
            tapa::ostreams<WORD, {CONCAT_FACTOR}>& fwd_out_strm,
            tapa::istreams<WORD, {CONCAT_FACTOR}>& inv_in_strm,
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {LAST_H_BU_NUM};
    int buffer_size = stride << {LAST_H_BU_NUM + 1};
"""
    function_signature += f"""
    int start_index_i_base[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, offset_0))
    function_signature += "};"

    function_signature += f"""
    int offset_1[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_1(CONCAT_FACTOR, offset_0)))
    function_signature += "};"

    function_signature += f"""
    int offset_2[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_2(V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};"

    function_signature += f"""
    int offset_3[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_3(LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};\n"

    buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1) >> 1
    function_signature += f"""
    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    LOAD_STORE_POLY_TF:for(int j = 0, j_all = 0; j_all < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        int index = (j>>log_stride)%LAST_CONCAT_FACTOR;
        int offset_i = start_index_i_base[index];

        bool fwd_inFIFONotEmpty = (!fwd_in_strm[0].empty());
        CHECK_FWD_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            fwd_inFIFONotEmpty &= (!fwd_in_strm[i].empty());
        }}

        bool inv_inFIFONotEmpty = (!inv_in_strm[0].empty());
        CHECK_INV_EMPTY:for(VAR_TYPE_8 i = 1; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL
            inv_inFIFONotEmpty &= (!inv_in_strm[i].empty());
        }}
        
        STORE_POLY:for(VAR_TYPE_8 i = 0; i < CONCAT_FACTOR; i++) {{
            #pragma HLS UNROLL

            int offset_plus_i = offset_i+i;
            int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
            if (fwd_inFIFONotEmpty) {{
                fwd_out_strm[actual_strm_i].write(fwd_in_strm[i].read());
            }} else if (inv_inFIFONotEmpty) {{
                inv_out_strm[i].write(inv_in_strm[actual_strm_i].read());
            }}
        }}

        if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{ 
            j++;
            j_all++;
        }}

        if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_all&(BUF_SIZE-1)) == 0) {{
            j = 0;
        }}
    }}
}}

"""

    # split shuffler - partial group
    function_signature += f"""
void shuffler_{X + 1}(tapa::istream<WORD>& fwd_in_strm,
            tapa::ostream<WORD>& inv_out_strm,
            tapa::ostream<WORD>& fwd_out_strm,
            tapa::istream<WORD>& inv_in_strm, VAR_TYPE_8 i, 
            VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter)
{{  
    int stride = 1 << log_stride;
    int iteration_size = stride << {LAST_H_BU_NUM};
    int buffer_size = stride << {LAST_H_BU_NUM + 1};
"""
    function_signature += f"""
    int start_index_i_base[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, offset_0))
    function_signature += "};"

    function_signature += f"""
    int offset_1[{LAST_CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_1(CONCAT_FACTOR, offset_0)))
    function_signature += "};"

    function_signature += f"""
    int offset_2[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_2(V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};"

    function_signature += f"""
    int offset_3[{CONCAT_FACTOR}] = {{"""
    function_signature += ", ".join(map(str, generate_offset_3(LAST_H_BU_NUM, CONCAT_FACTOR)))
    function_signature += "};\n"

    buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1) >> 1
    function_signature += f"""
    WORD buf_poly[{(1 << logN) // CONCAT_FACTOR}];  // wait {(1 << logN) // CONCAT_FACTOR} = N / CONCAT_FACTOR
    #pragma HLS bind_storage variable=buf_poly type=RAM_2P impl=bram

    VAR_TYPE_32 loopIter = BUF_SIZE*(iter+1);
    bool writeEnable = false;
    LOAD_STORE_POLY_TF:for(int j_read = 0, j_write = 0, j_read_all_iter = 0, j_write_all_iter = 0; j_write_all_iter < loopIter; ) {{
        #pragma HLS PIPELINE II = 1

        if (j_read < BUF_SIZE) {{
            // iNTT realted defination
            int intt_actual_j_0 = 0;

            int intt_index = (j_read>>log_stride)%LAST_CONCAT_FACTOR;
            int intt_offset_i_0 = start_index_i_base[intt_index];

            bool inv_inFIFONotEmpty = (!inv_in_strm.empty());

            // NTT realted defination
            int ntt_actual_j_0 = j_read&(iteration_size-1);
            int ntt_offset_i_0 = offset_1[intt_index];

            bool fwd_inFIFONotEmpty = (!fwd_in_strm.empty());


            if (fwd_inFIFONotEmpty) {{
                int offset_plus_i = ntt_offset_i_0+offset_2[i];
                int actual_i = offset_plus_i%CONCAT_FACTOR;
                buf_poly[ntt_actual_j_0] = fwd_in_strm.read();
            }} else if (inv_inFIFONotEmpty) {{
                int offset_plus_i = intt_offset_i_0+i;
                int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
                // iteration_of_j + offset_of_j + offset_of_i
                intt_actual_j_0 = (((j_read>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_read&(stride-1)) + offset_3[actual_strm_i]*stride)&(iteration_size-1);  //change in last_shuffler
                buf_poly[intt_actual_j_0] = inv_in_strm.read();
            }}

            if (fwd_inFIFONotEmpty || inv_inFIFONotEmpty) {{
                j_read++;
                j_read_all_iter++;
            }}

            if ((fwd_inFIFONotEmpty || inv_inFIFONotEmpty) && (j_read_all_iter&(BUF_SIZE-1)) == 0) {{
                j_read = 0;
            }}
        }}

        if((j_write_all_iter + iteration_size) == j_read_all_iter) {{
            writeEnable = true;
        }}

        /* poly input */
    
        // NTT defination
        int ntt_actual_j = 0;

        int ntt_index = (j_write>>log_stride)%LAST_CONCAT_FACTOR;
        int ntt_offset_i = start_index_i_base[ntt_index];

        // iNTT defination
        int intt_actual_j = j_write&(iteration_size-1); 
        int intt_offset_i = offset_1[ntt_index];

        if (direction && writeEnable) {{
            int offset_plus_i = ntt_offset_i+i;
            int actual_strm_i = offset_plus_i%CONCAT_FACTOR;
            // iteration_of_j + offset_of_j + offset_of_i
            ntt_actual_j = (((j_write>>(log_stride+LOG_CONCAT_FACTOR))<<(log_stride+LOG_CONCAT_FACTOR)) + (j_write&(stride-1)) + offset_3[actual_strm_i]*stride)&(iteration_size-1);
            fwd_out_strm.write(buf_poly[ntt_actual_j]);
        }} else if ((!direction) && writeEnable) {{
            int offset_plus_i = intt_offset_i+offset_2[i];
            int actual_i = offset_plus_i%CONCAT_FACTOR;
            inv_out_strm.write(buf_poly[intt_actual_j]);
        }}

        if (writeEnable) {{
            j_write++;
            j_write_all_iter++;
        }}

        if (writeEnable && ((j_write_all_iter&(BUF_SIZE-1)) == 0)) {{
            j_write = 0;
        }}

        if (writeEnable && ((j_write_all_iter&(iteration_size-1)) == 0)) {{
            writeEnable = false;
        }}
    }}
}}
"""
    return function_signature



def generate_top_function_signature(logN, X, partial_group, shuffler_num, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR):
    # print(X)
    if X != (shuffler_num - 1) and partial_group == False:  # previous shuffler
        buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1)
        # print("case 1")
    elif X == (shuffler_num - 1) and partial_group == False:  # last shuffler
        buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1) >> 1
        # print("case 2")
    elif X != (shuffler_num - 1) and partial_group == True:  # partial group's previous shuffler
        buffer_size = (1 << (X * H_BU_NUM)) << (H_BU_NUM + 1)
        # print("case 3")
    else:  # partial group's last shuffler
        buffer_size = (1 << logN) // CONCAT_FACTOR
        # print("case 4")

    split = False
    if H_BU_NUM >= 5 or buffer_size > 8192:  # split shuffler
        split = True
        if partial_group == True and X == (shuffler_num - 1):
            function_signature = generate_split_partial_shuffler_function_signature(logN, X, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR)
        else:
            function_signature = generate_split_shuffler_function_signature(X, shuffler_num, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR)
    else:
        if partial_group == True and X == (shuffler_num - 1):
            function_signature = generate_partial_shuffler_function_signature(logN, X, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR)
        else:
            function_signature = generate_shuffler_function_signature(X, shuffler_num, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR)
    return function_signature, split

def generate_shufflergen_functions(designParamsVar):

    logN = designParamsVar.logN
    H_BU_NUM = designParamsVar.H_BU_NUM
    V_BU_NUM = designParamsVar.V_BU_NUM
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM
    CONCAT_FACTOR = designParamsVar.CONCAT_FACTOR
    LAST_CONCAT_FACTOR = designParamsVar.LAST_CONCAT_FACTOR

    shuffler_num = logN // H_BU_NUM
    partial_group = False
    if LAST_H_BU_NUM != 0: 
        partial_group = True
    else:
        shuffler_num -= 1

    code = ""
    check_spilt = []

    for X in range(shuffler_num):
        # Function signature
        function_signature, split = generate_top_function_signature(logN, X, partial_group, shuffler_num, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, CONCAT_FACTOR, LAST_CONCAT_FACTOR)

        # Start function definition
        code += f"\n{function_signature}\n"
        check_spilt.append(split)

    designParamsVar.check_spilt = check_spilt

    return code