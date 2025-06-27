def validate_inputs(logN, H_BU_NUM, V_BU_NUM):
    # Validate inputs
    if not (1 <= logN <= 17):
        raise ValueError("logN must be between 1 and 17")
    if not (V_BU_NUM == (1 << (H_BU_NUM - 1))):
        raise ValueError("V_BU_NUM must be (1 << (H_BU_NUM - 1))")
    if not (1 <= H_BU_NUM <= 6):
        raise ValueError("H_BU_NUM must be between 1 and 6")


def compute_tf_total(X):
    tf_total = 1 << X

    return tf_total


def compute_initial_values(is_last_TFGen, arr_tfArr_length_val, tfArr_length_list, V_BU_NUM, tfArr_length, logN):
    current_tfArr_length_arr = []
    fwd_tfArr_length_arr = []

    idx = 0
    temp = arr_tfArr_length_val[idx]
    for X in range(logN):
        tf_total = 1 << X

        if is_last_TFGen[X] == 1:
            if (idx + 1) < len(arr_tfArr_length_val):
                idx += 1
        temp -= tfArr_length_list[X]
        fwd_tfArr_length = temp
        fwd_tfArr_length_arr.append(fwd_tfArr_length)

        if is_last_TFGen[X] == 1:
            temp = arr_tfArr_length_val[idx]

    return fwd_tfArr_length_arr


def generate_inline_tf_array(tf_total, V_BU_NUM):
    function_signature = ""
    if V_BU_NUM == 1:
        # function_signature += f"                    WORD TFArr[{tf_total}]) {{\n"
        function_signature += f"                    WORD *TFArr) {{\n"
        tfarr_dimension = 1
    else:
        if tf_total <= (V_BU_NUM // 2):
            tfarr_size = V_BU_NUM // 2
            # function_signature += f"                    WORD TFArr[{tf_total}]) {{\n"
            function_signature += f"                    WORD *TFArr) {{\n"
            tfarr_dimension = 1
        else:
            tfarr_dim1 = V_BU_NUM // 2
            tfarr_dim2 = tf_total // (V_BU_NUM // 2) if (tf_total // (V_BU_NUM // 2)) != 0 else 1
            # function_signature += f"                    WORD TFArr[{tfarr_dim1}][{tfarr_dim2}]) {{\n"
            function_signature += f"                    WORD TFArr[][{tfarr_dim2}]) {{\n"
            tfarr_dimension = 2
    return function_signature, tfarr_dimension

def generate_tf_load_fwd_signature(is_last_TFGen, tf_total, X, logN, V_BU_NUM, H_BU_NUM):
    if H_BU_NUM == 1:
        function_signature = f"""void tf_load_forward_{X}(tapa::istreams<WORD, {V_BU_NUM}>& tfToTfs,\n"""
    elif is_last_TFGen[X] == 0:  # if X < logN - 1:
        # For functions 0 to N-2
        function_signature = f"""void tf_load_forward_{X}(tapa::istreams<WORD, {V_BU_NUM}>& tfToTfs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& tfToNextTfs, bool direction,\n"""
    else:
        # For function N-1
        function_signature = f"""void tf_load_forward_{X}(tapa::istreams<WORD, {V_BU_NUM}>& tfToTfs, bool direction, \n"""

    function_signature_temp, tfarr_dimension = generate_inline_tf_array(tf_total, V_BU_NUM)
    function_signature += function_signature_temp
    function_signature += "    #pragma HLS inline off\n"

    return function_signature, tfarr_dimension

def generate_TFArr_loading_code(is_last_TFGen, tfArr_length, current_tfArr_length, fwd_tfArr_length, tf_total, logN, tfarr_dimension, fwd_flag, inv_flag, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, X):
    code = f"""
    VAR_TYPE_32 sum_tfArr_length = {current_tfArr_length + fwd_tfArr_length}, current_tfArr_length = {current_tfArr_length};
    VAR_TYPE_32 tf_counter = 0;
"""
    
    if V_BU_NUM == 1:
        code += f"""
    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {{
        #pragma HLS PIPELINE II=1

        WORD read_val = tfToTfs[0].read();
        if (tf_counter < current_tfArr_length) {{
            TFArr[tf_counter] = read_val;"""
    elif tfarr_dimension == 1 and ((LAST_H_BU_NUM == 0) or ((LAST_H_BU_NUM != 0) and (X < LAST_H_BU_NUM))):
        code += f"""
    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {{
        #pragma HLS PIPELINE II=1
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < {V_BU_NUM}; ++j) {{
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {{
               TFArr[j / {V_BU_NUM // tf_total}] = read_val;
            }}"""
    elif tfarr_dimension == 1 and ((LAST_H_BU_NUM != 0) and (X >= LAST_H_BU_NUM)):
        code += f"""
    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {{
        #pragma HLS PIPELINE II=1
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < {V_BU_NUM}; ++j){{
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if ((tf_counter < current_tfArr_length) && direction) {{
                TFArr[j / {V_BU_NUM // tf_total}] = read_val;
            }} else if ((tf_counter < current_tfArr_length) && (!direction)) {{
                TFArr[j % {1 << LAST_H_BU_NUM} + (j / {V_BU_NUM >> (inv_flag % H_BU_NUM)}) * {1 << LAST_H_BU_NUM}] = read_val;
            }}"""
    else:
        code += f"""
    LOAD_TF_OUTER:for(; tf_counter < sum_tfArr_length; ++tf_counter) {{
        #pragma HLS PIPELINE II=1
        #pragma HLS DEPENDENCE variable=TFArr intra WAW false
        LOAD_TF_INNER:for(VAR_TYPE_8 j = 0; j < {V_BU_NUM}; ++j){{
            #pragma HLS UNROLL

            WORD read_val = tfToTfs[j].read();
            if (tf_counter < current_tfArr_length) {{
                int tfArr_idx = tf_counter * 2;
                int tfArr_idx_offset = (j % 2);
                int sum_idx = tfArr_idx + tfArr_idx_offset;
                TFArr[j / 2][sum_idx] = read_val;
            }}"""
    # if X < logN - 1:
    if is_last_TFGen[X] == 0:
        code += f""" else {{
                tfToNextTfs[j].write(read_val);
            }}
        }}
    }}
}}

"""
    else:
        code += """
        }
    }
}


"""

    return code


def generate_tf_com_signature(is_last_TFGen, tf_total, X, logN, V_BU_NUM, H_BU_NUM):
    if H_BU_NUM == 1:
        function_signature = f"""void tf_comp_{X}(tapa::ostreams<WORD, {V_BU_NUM}>& fwd_tfToBUs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& inv_tfToBUs,
                    bool direction, \n"""
    elif is_last_TFGen[X] == 0:  # if X < logN - 1:
        # For functions 0 to N-2
        function_signature = f"""void tf_comp_{X}(tapa::ostreams<WORD, {V_BU_NUM}>& fwd_tfToBUs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, \n"""
    else:
        # For function N-1
        function_signature = f"""void tf_comp_{X}(tapa::ostreams<WORD, {V_BU_NUM}>& fwd_tfToBUs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, \n"""

    function_signature_temp, tfarr_dimension = generate_inline_tf_array(tf_total, V_BU_NUM)
    function_signature += function_signature_temp
    function_signature += "    #pragma HLS inline off\n"

    return function_signature


def generate_iteration_loops(logN, tf_total, tfarr_dimension, fwd_flag, inv_flag, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, X, singleLoopIter_value):
    code = f"""
    STORE_TF_OUTER:for(VAR_TYPE_32 i_per_iter = 0; i_per_iter < singleLoopIter; i_per_iter++) {{
        #pragma HLS PIPELINE II=1
"""
    # Compute temp array sizes
    if H_BU_NUM == 1:
        temp_array_name = "fwd_inv_temp"
    elif fwd_flag == inv_flag and (X < H_BU_NUM or X >= (logN - LAST_H_BU_NUM)):
        temp_size = 1 << (fwd_flag % H_BU_NUM)
        temp_array_name = "fwd_inv_temp"
    else:
        fwd_temp_size = 1 << (fwd_flag % H_BU_NUM)
        inv_temp_size = 1 << (inv_flag % H_BU_NUM)  # 1, 2, 4

    # Generate code based on conditions
    # Case when fwd_flag == inv_flag
    if H_BU_NUM == 1:
        code += f"""
        // Assign values to fwd_inv_temp when H_BU_NUM == 1
        if (direction) {{
            fwd_inv_temp = TFArr[i_per_iter % {1 << X}];
            fwd_tfToBUs[0].write(fwd_inv_temp);
        }} else {{
            fwd_inv_temp = TFArr[i_per_iter / {(1 << (logN-1)) // (1 << X)}];
            inv_tfToBUs[0].write(fwd_inv_temp);
        }}
"""
    elif fwd_flag == inv_flag and (X < H_BU_NUM or X >= (logN - LAST_H_BU_NUM)):
        if X < H_BU_NUM:
            if tfarr_dimension == 1:
                # Generate code for temp[idx] = TFArr[idx * step]
                code += f"""
        // Assign values to {temp_array_name} when fwd_flag == inv_flag and X < H_BU_NUM and tfarr_dimension == 1
        ASSIGN_TEMP:for(int idx = 0; idx < {temp_size}; ++idx) {{
            #pragma HLS UNROLL
            {temp_array_name}[idx] = TFArr[idx];
        }}
"""
            else:
                # For H_BU_NUM - 1 case
                code += f"""
        // Assign values to {temp_array_name} when fwd_flag == inv_flag aand X < H_BU_NUM and tfarr_dimension == 2
        ASSIGN_TEMP:for(int idx = 0; idx < {temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int tfarr_row = idx / 2;
            int tfarr_col = idx % 2;
            {temp_array_name}[idx] = TFArr[tfarr_row][tfarr_col];
        }}
"""
        else:
            # For X >= H_BU_NUM
            step = (V_BU_NUM // 2) // temp_size
            fwd_shift_amount = X - H_BU_NUM + 1
            offset_multiplier = 1 << fwd_shift_amount
            if (fwd_flag % H_BU_NUM) != (H_BU_NUM - 1):
                # Precompute expressions
                fwd_flag_mod_V_BU_NUM = fwd_flag % H_BU_NUM
                V_BU_NUM_shift_fwd = V_BU_NUM >> fwd_flag_mod_V_BU_NUM
                
                code += f"""
        // Assign values to {temp_array_name} when fwd_flag == inv_flag and X >= H_BU_NUM
        ASSIGN_TEMP:for(int idx = 0; idx < {temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int index = (i_per_iter % {V_BU_NUM_shift_fwd}) / 2 + idx * {step};
            int offset = (i_per_iter % 2) + ((i_per_iter / {V_BU_NUM_shift_fwd}) % {offset_multiplier}) * 2;
            {temp_array_name}[idx] = TFArr[index][offset];
        }}
"""
            else:
                half_temp_size = temp_size // 2

                code += f"""
        // Assign values to {temp_array_name} when fwd_flag == inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_TEMP:for(int idx = 0; idx < {half_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int base_offset = (i_per_iter % {offset_multiplier}) * 2;
            {temp_array_name}[idx * 2] = TFArr[idx][base_offset];
            {temp_array_name}[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }}
"""
    else:
        # fwd_temp assignments
        if X < H_BU_NUM:
            if tfarr_dimension == 1:
                code += f"""
        // Assign values to fwd_temp when fwd_flag != inv_flag and X < H_BU_NUM and tfarr_dimension == 1
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < {fwd_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            fwd_temp[idx] = TFArr[idx];
        }}
"""
            else:
                code += f"""
        // Assign values to fwd_temp when fwd_flag != inv_flag and X < H_BU_NUM and tfarr_dimension == 2
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < {fwd_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int tfarr_row = idx / 2;
            int tfarr_col = idx % 2;
            fwd_temp[idx] = TFArr[tfarr_row][tfarr_col];
        }}
"""
        else:
            # For X >= H_BU_NUM
            step = (V_BU_NUM // 2) // fwd_temp_size
            fwd_shift_amount = X - H_BU_NUM + 1
            offset_multiplier = 1 << fwd_shift_amount
            if (fwd_flag % H_BU_NUM) != (H_BU_NUM - 1):
                fwd_flag_mod_V_BU_NUM = fwd_flag % H_BU_NUM
                V_BU_NUM_shift_fwd = V_BU_NUM >> fwd_flag_mod_V_BU_NUM

                code += f"""
        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < {fwd_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int index = (i_per_iter % {V_BU_NUM_shift_fwd}) / 2 + idx * {step};
            int offset = (i_per_iter % 2) + ((i_per_iter / {V_BU_NUM_shift_fwd}) % {offset_multiplier}) * 2;
            fwd_temp[idx] = TFArr[index][offset];
        }}
"""
            else:
                half_fwd_temp_size = fwd_temp_size // 2

                code += f"""
        // Assign values to fwd_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_FWD_TEMP:for(int idx = 0; idx < {half_fwd_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int base_offset = (i_per_iter % {offset_multiplier}) * 2;
            fwd_temp[idx * 2] = TFArr[idx][base_offset];
            fwd_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }}
"""
        # inv_temp assignments
        if X < LAST_H_BU_NUM:
            if tfarr_dimension == 1:
                code += f"""
        // Assign values to inv_temp when fwd_flag != inv_flag and X < LAST_H_BU_NUM and tfarr_dimension == 1
        ASSIGN_INV_TEMP:for(int idx = 0; idx < {inv_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            inv_temp[idx] = TFArr[idx];
        }}
"""
            else:
                code += f"""
        // Assign values to inv_temp when fwd_flag != inv_flag and X < LAST_H_BU_NUM and tfarr_dimension == 2
        ASSIGN_INV_TEMP:for(int idx = 0; idx < {inv_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int tfarr_row = idx / 2;
            int tfarr_col = idx % 2;
            inv_temp[idx] = TFArr[tfarr_row][tfarr_col];
        }}
"""
        elif LAST_H_BU_NUM <= X < H_BU_NUM:
            inv_step = (V_BU_NUM // 2) // inv_temp_size
            inv_flag_mod = inv_flag % H_BU_NUM
            reuse = singleLoopIter_value // (tf_total // (1 << inv_flag_mod))
            if reuse == 0:
                reuse = 1  # Ensure reuse is at least 1 to avoid division by zero

            if tfarr_dimension == 1:
                inv_flag_mod_V_BU_NUM = inv_flag % H_BU_NUM
                V_BU_NUM_shift_inv = V_BU_NUM >> inv_flag_mod_V_BU_NUM
                code += f"""
        // Assign values to inv_temp when fwd_flag != inv_flag and LAST_H_BU_NUM <= X < H_BU_NUM and tfarr_dimension == 1
        ASSIGN_INV_TEMP:for(int idx = 0; idx < {inv_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int offset = i_per_iter / {reuse};
            inv_temp[idx] = TFArr[idx * {1 << LAST_H_BU_NUM} + offset];
        }}
"""
            else:
                step = (V_BU_NUM // 2) // inv_temp_size
                if (inv_flag % H_BU_NUM) != (H_BU_NUM - 1):
                    inv_flag_mod_V_BU_NUM = inv_flag % H_BU_NUM
                    V_BU_NUM_shift_inv = V_BU_NUM >> inv_flag_mod_V_BU_NUM
                    inv_shift_amount = inv_flag - H_BU_NUM + 1
                    offset_multiplier = 1 << inv_shift_amount

                    code += f"""
        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < {inv_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / {reuse};
            int index = i_per_iter_div_reuse / 2 + idx * {step};
            int offset = i_per_iter_div_reuse % 2;
            inv_temp[idx] = TFArr[index][offset];
        }}
"""
                else:
                    half_inv_temp_size = inv_temp_size // 2
                    inv_shift_amount = inv_flag - H_BU_NUM + 1
                    base_offset_multiplier = 1 << inv_shift_amount

                    code += f"""
        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_INV_TEMP:for(int idx = 0; idx < {half_inv_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / {reuse};
            int base_offset = (i_per_iter_div_reuse % {base_offset_multiplier}) * 2;
            inv_temp[idx * 2] = TFArr[idx][base_offset];
            inv_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }}
"""
        else:
            # For X >= H_BU_NUM
            step = (V_BU_NUM // 2) // inv_temp_size
            # inv_flag_div = (inv_flag // H_BU_NUM) * H_BU_NUM - 1
            # if inv_flag_div <= 0:
            #     raise ValueError("inv_flag_div must be larger than 0")
            # reuse = singleLoopIter_value // (1 << inv_flag_div)
            inv_flag_mod = inv_flag % H_BU_NUM
            reuse = singleLoopIter_value // (tf_total // (1 << inv_flag_mod))
            if reuse == 0:
                reuse = 1  # Ensure reuse is at least 1 to avoid division by zero

            if (inv_flag % H_BU_NUM) != (H_BU_NUM - 1):
                inv_flag_mod_V_BU_NUM = inv_flag % H_BU_NUM
                V_BU_NUM_shift_inv = V_BU_NUM >> inv_flag_mod_V_BU_NUM
                inv_shift_amount = inv_flag - H_BU_NUM + 1
                offset_multiplier = 1 << inv_shift_amount

                code += f"""
        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM
        ASSIGN_INV_TEMP:for(int idx = 0; idx < {inv_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / {reuse};
            int index = (i_per_iter_div_reuse % {V_BU_NUM_shift_inv}) / 2 + idx * {step};
            int offset = (i_per_iter_div_reuse % 2) + ((i_per_iter_div_reuse / {V_BU_NUM_shift_inv}) % {offset_multiplier}) * 2;
            inv_temp[idx] = TFArr[index][offset];
        }}
"""
            else:
                half_inv_temp_size = inv_temp_size // 2
                inv_shift_amount = inv_flag - H_BU_NUM + 1
                base_offset_multiplier = 1 << inv_shift_amount

                code += f"""
        // Assign values to inv_temp when fwd_flag != inv_flag and X >= H_BU_NUM (H_BU_NUM - 1 case)
        ASSIGN_INV_TEMP:for(int idx = 0; idx < {half_inv_temp_size}; ++idx) {{
            #pragma HLS UNROLL
            int i_per_iter_div_reuse = i_per_iter / {reuse};
            int base_offset = (i_per_iter_div_reuse % {base_offset_multiplier}) * 2;
            inv_temp[idx * 2] = TFArr[idx][base_offset];
            inv_temp[idx * 2 + 1] = TFArr[idx][base_offset + 1];
        }}
"""
    # Now create the loop to use the temp array
    if H_BU_NUM != 1: 
        code += f"""
        STORE_TF_INNER:for(VAR_TYPE_8 j = 0; j < {V_BU_NUM}; ++j) {{
            #pragma HLS UNROLL
"""
        # Compute fwd_mod and inv_div
        fwd_mod = 1 << (fwd_flag % H_BU_NUM)
        inv_div = V_BU_NUM // (1 << (inv_flag % H_BU_NUM))

        if fwd_flag == inv_flag and (X < H_BU_NUM or X >= (logN - LAST_H_BU_NUM)):
            code += f"""
            if (direction) {{
                fwd_tfToBUs[j].write({temp_array_name}[j % {fwd_mod}]);
            }} else if (!direction) {{
                inv_tfToBUs[j].write({temp_array_name}[j / {inv_div}]);
            }}
"""
        else:
            code += f"""
            if (direction) {{
                fwd_tfToBUs[j].write(fwd_temp[j % {fwd_mod}]);
            }} else if (!direction) {{
                inv_tfToBUs[j].write(inv_temp[j / {inv_div}]);
            }}
"""
        code += f"""
        }}"""

    code += f"""
    }}
}}

"""
    return code


def generate_tf_function_signature(is_last_TFGen, X, logN, V_BU_NUM, H_BU_NUM):
    if H_BU_NUM == 1:
        function_signature = f"""void TFGen{X}(tapa::istreams<WORD, {V_BU_NUM}>& tfToTfs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& fwd_tfToBUs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& inv_tfToBUs,
                    bool direction, VAR_TYPE_32 iter) {{

"""
    elif is_last_TFGen[X] == 0:  # if X < logN - 1:
        # For functions 0 to N-2
        function_signature = f"""void TFGen{X}(tapa::istreams<WORD, {V_BU_NUM}>& tfToTfs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& tfToNextTfs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& fwd_tfToBUs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {{

"""
    else:
        # For function N-1
        function_signature = f"""void TFGen{X}(tapa::istreams<WORD, {V_BU_NUM}>& tfToTfs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& fwd_tfToBUs,
                    tapa::ostreams<WORD, {V_BU_NUM}>& inv_tfToBUs,
                    VAR_TYPE_8 log_stride, bool direction, VAR_TYPE_32 iter) {{

"""

    return function_signature

def generate_double_buffer_TFArr_declaration(tf_total, V_BU_NUM):
    code = ""
    if V_BU_NUM == 1:
        for i in range(2):
            code += f"    WORD TFArr_{i}[{tf_total}];\n"
            if(tf_total < 32):
                code += f"#pragma HLS array_partition type=complete variable=TFArr_{i} dim=1\n"
            else:
                code += f"#pragma HLS bind_storage variable=TFArr_{i} type=RAM_1P impl=URAM\n"
    else:
        if tf_total <= (V_BU_NUM // 2):
            for i in range(2):
                tfarr_size = V_BU_NUM // 2
                code += f"    WORD TFArr_{i}[{tf_total}];\n"
                code += f"#pragma HLS array_partition type=complete variable=TFArr_{i} dim=1\n"
        else:
            for i in range(2):
                tfarr_dim1 = V_BU_NUM // 2
                tfarr_dim2 = tf_total // (V_BU_NUM // 2) if (tf_total // (V_BU_NUM // 2)) != 0 else 1
                code += f"    WORD TFArr_{i}[{tfarr_dim1}][{tfarr_dim2}];\n"
                if tfarr_dim2 >= 32:
                    # code += f"#pragma HLS bind_storage variable=TFArr_{i} type=RAM_T2P impl=BRAM\n"
                    code += f"#pragma HLS bind_storage variable=TFArr_{i} type=RAM_T2P impl=URAM\n"
                    code += f"#pragma HLS array_partition type=complete variable=TFArr_{i} dim=1\n"
                else:
                    code += f"#pragma HLS array_partition type=complete variable=TFArr_{i} dim=1\n"
                    code += f"#pragma HLS array_partition type=cyclic variable=TFArr_{i} factor=2 dim=2\n"
    return code


def generate_tfgen_functions(designParamsVar):

    is_last_TFGen = designParamsVar.is_last_TFGen
    tfArr_length = designParamsVar.tfArr_length
    arr_tfArr_length_val = designParamsVar.arr_tfArr_length_val
    tfArr_length_list = designParamsVar.tfArr_length_list
    logN = designParamsVar.logN
    H_BU_NUM = designParamsVar.H_BU_NUM
    V_BU_NUM = designParamsVar.V_BU_NUM
    LAST_H_BU_NUM = designParamsVar.LAST_H_BU_NUM

    validate_inputs(logN, H_BU_NUM, V_BU_NUM)

    # Compute POLY_SIZE and CONCAT_FACTOR
    POLY_SIZE = 1 << logN
    CONCAT_FACTOR = V_BU_NUM << 1
    singleLoopIter_value = POLY_SIZE // CONCAT_FACTOR


    # Compute initial values
    fwd_tfArr_length_arr = compute_initial_values(is_last_TFGen, arr_tfArr_length_val, tfArr_length_list, V_BU_NUM, tfArr_length, logN)

    code = ""

    for X in range(logN):
        # Compute fwd_flag and inv_flag
        if LAST_H_BU_NUM == 0:
            fwd_flag = X
            inv_flag = X
        else:
            if X < (logN - LAST_H_BU_NUM):
                fwd_flag = X
            else:
                fwd_flag = X + (H_BU_NUM - LAST_H_BU_NUM)
            if X < LAST_H_BU_NUM:
                inv_flag = X
            else:
                inv_flag = X + (H_BU_NUM - LAST_H_BU_NUM)
        
        tf_total = compute_tf_total(X)
        code_temp, tfarr_dimension = generate_tf_load_fwd_signature(is_last_TFGen, tf_total, X, logN, V_BU_NUM, H_BU_NUM)
        code += code_temp
        code += generate_TFArr_loading_code(is_last_TFGen, tfArr_length, tfArr_length_list[X], fwd_tfArr_length_arr[X], tf_total, logN, tfarr_dimension, fwd_flag, inv_flag, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, X)
        code += generate_tf_com_signature(is_last_TFGen, tf_total, X, logN, V_BU_NUM, H_BU_NUM)

        code += f"\n    VAR_TYPE_32 singleLoopIter = {singleLoopIter_value};\n"

        # Compute sizes for temp arrays
        fwd_size = 1 << (fwd_flag % H_BU_NUM)
        inv_size = 1 << (inv_flag % H_BU_NUM)

        # Generate temp arrays based on fwd_flag and inv_flag
        if H_BU_NUM == 1:
            code += f"    WORD fwd_inv_temp;\n"
        elif fwd_flag == inv_flag and (X < H_BU_NUM or X >= (logN - LAST_H_BU_NUM)):
            code += f"    WORD fwd_inv_temp[{fwd_size}];\n"
        else:
            code += f"    WORD fwd_temp[{fwd_size}];\n"
            code += f"    WORD inv_temp[{inv_size}];\n"

        code += generate_iteration_loops(logN, tf_total, tfarr_dimension, fwd_flag, inv_flag, H_BU_NUM, V_BU_NUM, LAST_H_BU_NUM, X, singleLoopIter_value)
 
        # Function signature
        code += generate_tf_function_signature(is_last_TFGen, X, logN, V_BU_NUM, H_BU_NUM)

        # Generate TFArr declaration and pragmas
        tfarr_decl_code = generate_double_buffer_TFArr_declaration(tf_total, V_BU_NUM)
        code += tfarr_decl_code

        if H_BU_NUM == 1:
            code += f"""
        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {{
            if ((iteration_idx % 2) == 0) {{
                tf_load_forward_{X}(tfToTfs, TFArr_0);
                tf_comp_{X}(fwd_tfToBUs, inv_tfToBUs, direction, TFArr_1);
            }} else {{
                tf_load_forward_{X}(tfToTfs, TFArr_1);
                tf_comp_{X}(fwd_tfToBUs, inv_tfToBUs, direction, TFArr_0);
            }}
        }}
    """
        elif is_last_TFGen[X] == 0:  # if X < logN - 1:
            code += f"""
        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {{
            if ((iteration_idx % 2) == 0) {{
                tf_load_forward_{X}(tfToTfs, tfToNextTfs, direction, TFArr_0);
                tf_comp_{X}(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            }} else {{
                tf_load_forward_{X}(tfToTfs, tfToNextTfs, direction, TFArr_1);
                tf_comp_{X}(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }}
        }}
    """
        else:
            code += f"""
        ITER_OUTER:for(VAR_TYPE_32 iteration_idx = 0; iteration_idx < (iter+1); iteration_idx++) {{
            if ((iteration_idx % 2) == 0) {{
                tf_load_forward_{X}(tfToTfs, direction, TFArr_0);
                tf_comp_{X}(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_1);
            }} else {{
                tf_load_forward_{X}(tfToTfs, direction, TFArr_1);
                tf_comp_{X}(fwd_tfToBUs, inv_tfToBUs, log_stride, direction, TFArr_0);
            }}
        }}
    """

        # Close the function
        code += "}\n\n\n"

    return code