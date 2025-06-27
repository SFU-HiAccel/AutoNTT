#include <iostream>
#include <vector>

#include <gflags/gflags.h>
#include <tapa.h>

#include "ntt.h"

using std::clog;
using std::endl;
using std::vector;

DEFINE_string(bitstream, "", "path to bitstream file, run csim if empty");


void NTT_kernel(
    tapa::mmap<POLY_WIDE_DATA> polyVectorIn_G0,
    tapa::mmap<TF_WIDE_DATA> TFArr_G0,
    tapa::mmap<POLY_WIDE_DATA> polyVectorOut_G0,
    WORD q0,
    WORD twoInverse0,
    WLM_MULTIPLIER_WORD multiplier0,
    bool direction,
    VAR_TYPE_16 iter
    )
;

// /********************************************************************************************
// * Supporting functions *
// ********************************************************************************************/

/* Return x^p */
WORD myPow(WORD x, WORD p, WORD mod)
{
  if (p == 0) return 1;
  if (p == 1) return x % mod;
  
  WORD tmp = myPow(x, p/2, mod);
  WORD tmpSquare = (WORD)(((DWORD)(tmp) * (DWORD)(tmp)) % ((DWORD)mod));  //It is important to control the growth of values when multiplying. Hence, squaring is computed separately like this and used in later.
  if (p%2 == 0){
    return tmpSquare;
  } 
  else{
    WORD res = (WORD)(((DWORD)(x) * (DWORD)(tmpSquare)) % ((DWORD)mod));
    return res;
  }
}

/* calculate log2(NUM) */
VAR_TYPE_8 myLog2(WORD mod) {
    WORD result = 0;
    while (mod > 1) {
        mod >>= 1;
        result++;
    }
    return result;
}

/* Extended Euclidean algorithm to find modular inverse */
long extendedGCD(long a, long b, long &x, long &y) {
    if (b == 0) {
        x = 1;
        y = 0;
        return a;
    }
    long x1, y1;
    long gcd = extendedGCD(b, a % b, x1, y1);
    x = y1;
    y = x1 - (long)((a / b) * y1);
    return gcd;
}

/* Function to find modular inverse of 'a' modulo 'm' */
long mod_inverse(long a, long m) {
  
    long x, y;
    long gcd = extendedGCD(a, m, x, y);
    if (gcd != 1) {
        return 0; // Modular inverse does not exist
    } else {
        // Adjusting for negative result
        long res = (long)(x + (long)m);
        return ((res % m) + m) % m;
    }
}

/* Function to help finding inverse of Nth root of unity modulo m using specific 
characteristics of primitive root of unity.
Rules:
1. r^N mod m = 1
2. r^(N/2+k) mod m = -(r^k)
Idea:
* r^N mod m = 1 (rule 1)
* r^(N-1).r mod m = 1 -> Hence r^(N-1) = r^(-1)
* r^(N/2 + N/2 - 1).r mod m = 1
* r^(N/2 + N/2 - 1).r mod m = 1
* -r^(N/2 - 1).r mod m = 1 (rule 2) -> hence -r^(N/2 - 1) = r^(-1) */
WORD mod_inverse_root(WORD r, WORD m, VAR_TYPE_32 size){
  WORD inv = 1;
  for(int i=0; i<(size/2)-1; i++){
    inv = (WORD)((((DWORD)inv) * ((DWORD)r)) % ((DWORD)m));
  }
  inv = (WORD)(m - inv);
  return inv;
}

/* Function to help finding inverse of power of 2 numbers using the fact that n = 2^x.
Idea:
* n^(-1) = (2^x)^(-1) = (2^(-1))^(x) */
WORD mod_inverse_pow2Num(VAR_TYPE_32 logx, WORD m){
  WORD inv = 1;
  WORD twoInverse = (m+1)/2;
  for(int i=0; i<logx; i++){
    inv = (WORD)((((DWORD)inv) * ((DWORD)twoInverse)) % ((DWORD)m));
  }
  return inv;
}

/* Get the length of mod number */
VAR_TYPE_8 bit_length(WORD mod) {
    VAR_TYPE_8 result = 0;
    while (mod > 0) { //works for mod as it is an odd number(prime).
        mod >>= 1;
        result++;
    }
    return result;
}

/* Initialize array to 0 for given size */
void initializeArr(std::vector<WORD>& vec, WORD size){
  for(int i=0; i<size; i++){
    vec[i] = 0;
  }
}

/* Generate an input for the ntt computation
seed - Seed for random number generator
minMod -  minimum working modulus
size -  Size of the input. Has to be some 2 to the power number(need to add a check)
invec - Generated polynomial
*/
void gen_random_arr(VAR_TYPE_32 seed, WORD minMod, WORD size, std::vector<WORD>& invec){
  
  std::srand(seed);

  for (int i=0; i < size; i++){
    invec[i] = std::rand() % minMod;
  }
}

/* Return floor(sqrt(num)) */
WORD floor_sqrt(WORD num){
  VAR_TYPE_64 val = (VAR_TYPE_64)(floor(sqrt((VAR_TYPE_64)num)));
  WORD returnVal = *(WORD*)(&val);
  return returnVal;
}

/* Test whether the given integer is a prime */
bool is_prime(WORD num){
  if (num <= 1){
    printf("[Error]::Value is less than 1.\n");
    exit(1);
  }

  WORD limit = floor_sqrt(num) + 1;

  for (VAR_TYPE_64 i=2; i<limit; i++){
    if(num%i==0){
      return false;
    }
  }
  return true;

}

/*
Generate NTT and WLM friendly moduls.
NTT friendly modulus is in the form of M = 2*N+1, N is the polynomial size.
If WORD size for WLM is WLM_WORD_SIZE, for WLM (M-1)%(2^WLM_WORD_SIZE)=0 should satisfy.
Since usually (2^WLM_WORD_SIZE) could be much larger than 2*N, we take specific measures to 
find NTT and WLM friendly moduls here by making initial multiplier larger.
*/
WORD find_NTT_and_WLM_friendly_modulus(WORD size, WORD minMod){

  if ((size<1) | (minMod<1)){
    printf("[Error]::Double check your parameters\n");
    exit(1);
  }

  WORD start = (WORD)((minMod -1 + size -1)/size);

  WORD multiplier = (((WORD_PLUS1)1)<<(WORD_SIZE-1))/(((WORD_PLUS1)1)<<WLM_WORD_SIZE);

  while(true){
    WORD workModulus = (((WORD_PLUS1)1)<<WLM_WORD_SIZE) * multiplier + 1;
    if(workModulus<minMod){
      printf("[Error]::Something wrong. Double check.\n");
      exit(1);
    }

    if(( ( (workModulus-1)%size ) == 0 ) ){
      if( is_prime(workModulus) ){
        return workModulus;
      }
    }

    multiplier++;
  }
}

/*
Generate NTT friendly and WLM friendly moduls array.
NTT friendly modulus is in the form of M = 2*N+1, N is the polynomial size.
If WORD size for WLM is WLM_WORD_SIZE, for WLM (M-1)%(2^WLM_WORD_SIZE)=0 should satisfy.
Since usually (2^WLM_WORD_SIZE) could be much larger than 2*N, we take specific measures to 
find NTT and WLM friendly moduls here by making initial multiplier larger.
*/
void find_NTT_and_WLM_friendly_modulus_array(WORD size, WORD minMod, std::vector<WORD>& modulusArray, VAR_TYPE_32 limbCount){

  VAR_TYPE_32 limbCounter = 0;
  for(VAR_TYPE_32 i=0; i<limbCount; i++){
    modulusArray[i] = 0;
  }

  if ((size<1) | (minMod<1)){
    printf("[Error]::Double check your parameters.\n");
  }

  WORD start = (WORD)((minMod -1 + size -1)/size);

  WORD multiplier = (((WORD_PLUS1)1)<<(WORD_SIZE-1))/(((WORD_PLUS1)1)<<WLM_WORD_SIZE);

  while(limbCounter < limbCount){
    WORD workModulus = (((WORD_PLUS1)1)<<WLM_WORD_SIZE) * multiplier + 1;
    if(workModulus<minMod){
      printf("[Error]::Something wrong. Double check.\n");
      exit(1);
    }

    if(( ( (workModulus-1)%size ) == 0 ) ){
      if(is_prime(workModulus)){
        //std::cout << "modulusArray[" << limbCounter << "] = " << workModulus << std::endl;
        modulusArray[limbCounter] = workModulus;
        limbCounter++;
      }
    }
    multiplier++;
  }
}

/*
Returns a list of unique prime factors of the given integer in
ascending order. For example, unique_prime_factors(60) = [2, 3, 5].
*/
void unique_prime_factors(WORD val, std::vector<WORD>& unique_factors){
  if(val<1){
    printf("[Error]::Invalid number to find unique primes\n");
    exit(1);
  }

  WORD factor = 2;
  WORD fact_end = floor_sqrt(val);

  while(factor <= fact_end){
    if(val % factor == 0){
      unique_factors.push_back(factor);
      val = (WORD)(val/factor);
      
      while(val % factor == 0){
        val = (WORD)(val/factor);
      }
      fact_end = floor_sqrt(val);
    }
    factor++;
  }
  if(val>1){
    unique_factors.push_back(val);
  }
}

/*
Check if the passed values is a degreeth primitive root of unity in modulo mod.
Conditions for primitive root: val^degree % mod = 1 and for all 1 <= k < degree, val^k % mod != 1
*/
bool is_primitive_root(WORD val, WORD degree, WORD mod){
  if ((val < 0) | (val > mod)){
    printf("[Error]::Check the passed value\n");
  }
  if ((degree<1) | (degree>mod)){
    printf("[Error]::Check the passed value\n");
  }

  std::vector<WORD> prime_factors;
  unique_prime_factors(degree, prime_factors);

  if((myPow(val, degree, mod)) == 1){
    for(int i=0; i<prime_factors.size(); i++){
      WORD newDeg = (WORD)(degree/prime_factors[i]);
      if((myPow(val, newDeg, mod)) == 1){
        return false;
      }
    }
    return true;
  }
  else{
    return false;
  }

}

/* Returns an arbitrary generator of the multiplicative group of integers modulo mod.
totient must equal the Euler phi function of mod. If mod is prime, an answer must exist. */
WORD find_generator(WORD totient, WORD mod){
  if((totient<1) | (totient>=mod)){
    printf("[Error]::Issue in inputs to find_generator\n");
    exit(1);
  }

  for(WORD i=1; i<mod; i++){
    if(is_primitive_root(i, totient, mod)){
      return i;
    }
  }
  printf("[Error]::No generators found\n");
  exit(1);
  return 0;
}

/* Provide the bit reveresed value.
i.e., bitReverseNumber(3,3) = 6 = 110 (= reverse(011) = reverse(3)))
*/
WORD bitReverseNumber(WORD num, WORD bits){
  WORD temp = 0;
  for(int i=0; i<bits; i++){
    temp = (temp<<1) | (num & 1);
    num >>= 1;
  }
  return temp;
}

/* Generate the bit reveresed array */
void bitReverseVect(std::vector<WORD>& vec, WORD size){
  WORD levels = myLog2(size);
  if((1<<levels) != size){
    printf("[Error]::Length is not a power of 2.\n");
    exit(1);
  }

  for(WORD i=0; i<size; i++){
    WORD j = bitReverseNumber(i,levels);
    if(j>i){
      WORD temp = vec[i];
      vec[i] = vec[j];
      vec[j] = temp;
    }
  }
}

/* Returns an arbitrary primitive degree-th root of unity modulo mod.
totient must be a multiple of degree. If mod is prime, an answer must exist.
*/
WORD find_primitive_root(WORD degree, WORD totient, WORD mod){
  if((degree<1) | (totient<1) | (totient<degree) | (mod<degree) | (mod<totient)) {
    printf("[Error]::Error in the inputs in find_primitive_root\n");
    exit(1);
  }
  if(totient%degree!=0){
    printf("[Error]::Invalid totient or degree passed to find_primitive_root\n");
    exit(1);
  }
  WORD gen = find_generator(totient, mod);
  WORD root = myPow(gen, (WORD)(totient/degree), mod);

  if((root<0) | (root>mod)){
    printf("[Error]::Error in generated root\n");
    exit(1);
  }

  return root;
}

/* Compare values of two arrays and check correctness */
bool compareResults(std::vector<WORD>& ref, std::vector<WORD>& test, WORD size){
  for(int i=0; i<size; i++){
    if(ref[i]!=test[i]){
      std::cout << "Error detected at idx=" << i << ", ref=" << ref[i] << ", test=" << test[i] << std::endl;
      return false;
    }
  }
  return true;
}

/* Generate polynomials with random values. Each coefficient is within log(q) range*/
void generate_random_polynomials_array(VAR_TYPE_32 seed, VAR_TYPE_64 minMod, VAR_TYPE_32 size, VAR_TYPE_32 para_limbs, std::vector<WORD> (&invec)[PARA_LIMBS]){
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<para_limbs; paraLimbCounter++){
    invec[paraLimbCounter].resize(size);
    initializeArr(invec[paraLimbCounter], size);
    gen_random_arr((seed+paraLimbCounter), minMod, size, invec[paraLimbCounter]);
  }
}

// Generate the primitive root of unity, inverse root and two inverse (used in INTT)
void generate_NTT_variables(std::vector<WORD>& workingModulus_arr, VAR_TYPE_32 size, VAR_TYPE_32 para_limbs, std::vector<WORD>& root_arr, std::vector<WORD>& rootInverse_arr, std::vector<WORD>& twoInverse_arr){
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<para_limbs; paraLimbCounter++){
    WORD workingModulus = workingModulus_arr[paraLimbCounter];
    
    WORD root = find_primitive_root(size, workingModulus-1, workingModulus);
    WORD rootInverse = (WORD)(mod_inverse_root((long)root, (long)workingModulus, size));
    WORD twoInverse = (workingModulus+1)/2;
    
    root_arr[paraLimbCounter] = root;
    rootInverse_arr[paraLimbCounter] = rootInverse;
    twoInverse_arr[paraLimbCounter] = twoInverse;
  }
}

// /********************************************************************************************
// * Cooley-Tukey based NTT computations *
// ********************************************************************************************/

/*
Compute NTT using radix-2 tensor product based implementation
Input is provided in normal order and output is given in bit reversed order.
TFs are actually required in bit reversed order. But we use bit reverse function to 
convert.
*/
void tensorProd_NToR_fwd_NTT(std::vector<WORD>& noInvec, std::vector<WORD>& boTFArr, WORD mod, VAR_TYPE_32 N, WORD NUM_BU){
  WORD stages = myLog2(N);//log2(((VAR_TYPE_32)N));
  if((1<<stages)!=N){
    printf("[Error]::Size is not a 2 to the power number");
    exit(0);
  }

  WORD temp[N];

  WORD beta = (1<<(stages-1))/NUM_BU;
  
  for(WORD l=stages; l>0; l--){
    for(WORD j=0; j<beta; j++){
      for(WORD i=0; i<NUM_BU; i++){
        WORD delta = j*NUM_BU + i;
        WORD tfIdx = (delta & ((1<<(logN-l)) - 1));
        //WORD br_tfIdx = bitReverseNumber(tfIdx, stages-1);

        WORD tfVal = boTFArr[tfIdx];

        WORD left = noInvec[delta];
        WORD right = (WORD)((((DWORD)noInvec[delta + NUM_BU*beta]) * ((DWORD)tfVal)) % ((DWORD)mod));

        temp[2*delta] = (WORD)((((DWORD)left) + ((DWORD)right)) % ((DWORD)mod));
        
        if(left >= right){
          temp[2*delta+1] = (WORD)((((DWORD)left) - ((DWORD)right)) % ((DWORD)mod)); //probably, we can remove this last mod(%) operation
        }
        else{
          temp[2*delta+1] = (WORD)((((DWORD)mod) - (((DWORD)right) - ((DWORD)left))) % ((DWORD)mod));  //probably, we can remove this last mod(%) operation
        }
      }
    }
    
    for(WORD h=0; h<N; h++){
      noInvec[h] = temp[h];
    }
  }
}


// /********************************************************************************************
// * Polynomial rearrangements *
// ********************************************************************************************/

void blockWiseDivideData(std::vector<WORD>& inVec, std::vector<WORD> (&outVec)[NUM_BU]){
  for(int i=0; i<N; i++){
    outVec[i>>(logN-logBU)].push_back(inVec[i]);
  }
}

void reorganize_in_poly_per_para_limb(std::vector<WORD>& inVec, std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[POLY_LS_PORTS_PER_PARA_LIMB]){
  std::vector<WORD> blockInData[NUM_BU];
  blockWiseDivideData(inVec, blockInData);

  for(int k=0; k<POLY_LS_PORTS_PER_PARA_LIMB; k++){    // Number of DRAM ports
    for(int s=0; s<NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT; s++){                     // How many 'Bufs groups' being supported by a DRAM prot. A single 'Buf group' is 8/16 Bufs(DRAM port width).
      for(int i=0; i<N/NUM_BU; i++){                   // How many values are being gone to a buf
        POLY_WIDE_DATA_PER_PARA_LIMB val = 0;
        for(int j=POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1; j>=0; j--){                // combine values in one buf group(8/16 bufs based on HBM width)
          val <<= DRAM_WORD_SIZE;
          val |= ((POLY_WIDE_DATA_PER_PARA_LIMB)blockInData[((k*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT+s)*POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT) + j][i]);
        }
        outVec[k].push_back(val);
      }
    }
  }
}

void reorganize_para_limbs_to_ports_poly(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){
  int num_of_data = ((N*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)/NUM_BU);

  //check
  if(num_of_data!=(inVec[0][0].size())){
    printf("[ERROR]::Size mismatch detected in reorganize_para_limbs_to_ports_poly. expected = %d, received=%d\n", num_of_data, (int)(inVec[0][0].size()));
    exit(1);
  }

  //init
  for(int port_idx=0; port_idx<POLY_LS_PORTS; port_idx++){
    outVec[port_idx].resize(num_of_data);
  }

  for(int data_counter=0; data_counter<num_of_data; data_counter++){
    for(int port_counter=0; port_counter<POLY_LS_PORTS; port_counter++){
      POLY_WIDE_DATA val = 0;
      for(int per_limb_port_counter=PARA_LIMB_PORTS_PER_POLY_PORT-1; per_limb_port_counter>=0; per_limb_port_counter--){
        int total_per_limb_ports = port_counter*PARA_LIMB_PORTS_PER_POLY_PORT + per_limb_port_counter;
        int limb_idx = total_per_limb_ports/POLY_LS_PORTS_PER_PARA_LIMB;
        int limb_port_idx = total_per_limb_ports%POLY_LS_PORTS_PER_PARA_LIMB;
        
        POLY_WIDE_DATA_PER_PARA_LIMB limbVal;
        if(limb_idx<PARA_LIMBS){ 
          limbVal = inVec[limb_idx][limb_port_idx][data_counter];
        }
        else{ //In case, PARA_LIMBS is not perfectly divisible by PARA_LIMB_PORTS_PER_POLY_PORT
          limbVal = 0;
        }
        val = val << POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB;
        val |= (POLY_WIDE_DATA)limbVal;
      }
      outVec[port_counter][data_counter] = val;
    }
  }
}

void reorganize_input_poly_to_ports(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){
  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseInPolyData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];
  
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    reorganize_in_poly_per_para_limb(inVec[paraLimbCounter], limbWiseInPolyData[paraLimbCounter]);
  }

  reorganize_para_limbs_to_ports_poly(limbWiseInPolyData, outVec);
}

void init_kernerl_output_ports(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS]){
  for(int i=0; i<((N*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)/NUM_BU); i++){
    for(int j=0; j<POLY_LS_PORTS; j++){
      inVec[j].push_back(0);
    }
  }
}

void blockWiseCombineData(std::vector<WORD> (&inVec)[NUM_BU], std::vector<WORD>& outVec){
  for(int i=0; i<N; i++){
      outVec[i] = inVec[i >> (logN-logBU)][i & ((1U<<(logN-logBU))-1)];
  }
}

void reorganize_out_poly_per_para_limb(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[POLY_LS_PORTS_PER_PARA_LIMB], std::vector<WORD>& outVec){
  std::vector<WORD> blockOutData[NUM_BU];

  for(int k=0; k<POLY_LS_PORTS_PER_PARA_LIMB; k++){
    for(int s=0; s<NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT; s++){
      for(int i=0; i<N/NUM_BU; i++){
        POLY_WIDE_DATA_PER_PARA_LIMB val = inVec[k][(s*(N/NUM_BU)) + i];
        for(int j=0; j<POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT; j++){
          WORD smallVal = (WORD)(val & ((((POLY_WIDE_DATA_PER_PARA_LIMB)1)<<WORD_SIZE)-1));
          blockOutData[((k*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT+s)*POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT) + j].push_back(smallVal);
          val >>= DRAM_WORD_SIZE;
        }
      }
    }
  }
  
  blockWiseCombineData(blockOutData, outVec);
}

void reorganize_ports_to_para_limbs_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB]){
  int num_of_data = ((N*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)/NUM_BU);

  //check
  if(num_of_data!=(inVec[0].size())){
    printf("[ERROR]::Size mismatch detected in reorganize_para_limbs_to_ports_poly. expected = %d, received=%d\n", num_of_data, (int)(inVec[0].size()));
  }

  //init
  for(int limb_counter=0; limb_counter<PARA_LIMBS; limb_counter++){
    for(int port_counter=0; port_counter<POLY_LS_PORTS_PER_PARA_LIMB; port_counter++){
      outVec[limb_counter][port_counter].resize(num_of_data);
    }
  }

  for(int data_counter=0; data_counter<num_of_data; data_counter++){
    for(int port_counter=0; port_counter<POLY_LS_PORTS; port_counter++){
      POLY_WIDE_DATA val = inVec[port_counter][data_counter];
      for(int per_limb_port_counter=0; per_limb_port_counter<PARA_LIMB_PORTS_PER_POLY_PORT; per_limb_port_counter++){
        int total_per_limb_ports = port_counter*PARA_LIMB_PORTS_PER_POLY_PORT + per_limb_port_counter;
        int limb_idx = total_per_limb_ports/POLY_LS_PORTS_PER_PARA_LIMB;
        int limb_port_idx = total_per_limb_ports%POLY_LS_PORTS_PER_PARA_LIMB;
        
        POLY_WIDE_DATA_PER_PARA_LIMB limbVal = val & (((POLY_WIDE_DATA)1 << POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB)-1);
        val = val >> POLY_DRAM_PORT_WIDTH_PER_PARA_LIMB;
        if(limb_idx<PARA_LIMBS){  //In case, PARA_LIMBS is not perfectly divisible by PARA_LIMB_PORTS_PER_POLY_PORT(else of this if), we ignore extra data padded.
          outVec[limb_idx][limb_port_idx][data_counter] = limbVal;
        }
      }
    }
  }
}

// In the case of no double buffering, kernel share the same storage to save data with an offset. 
// To streamline the ouput reordering for both double buffer enabled and disable cases,
// this function rearrange the data removing the offset for double buffer disabled case.
void remove_single_buffer_offset_in_output(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS]){
  for(int port_idx=0; port_idx<POLY_LS_PORTS; port_idx++){
    for(int data_idx=0; data_idx<((N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT); data_idx++){
      inVec[port_idx][data_idx] = inVec[port_idx][data_idx+((N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT)];
    }
    inVec[port_idx].resize(((N/NUM_BU)*NUM_CHAIN_GROUPS_PER_PARA_LIMB_POLY_PORT));
  }
}

void reorganize_ports_to_output_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<WORD> (&outVec)[PARA_LIMBS]){
  if(!DOUBLE_BUF_EN){
    remove_single_buffer_offset_in_output(inVec);
  }

  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseOutData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];
  reorganize_ports_to_para_limbs_poly(inVec, limbWiseOutData);

  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    outVec[paraLimbCounter].resize(N);
    reorganize_out_poly_per_para_limb(limbWiseOutData[paraLimbCounter], outVec[paraLimbCounter]);
  }
}


// /********************************************************************************************
// * TF rearrangements *
// ********************************************************************************************/

/* Generate twiddle factors for radix 2 NTT. 
In normal radix-2 case, twiddle factors are used in increasing power order
*/
void generateTFForRadix2NTT(WORD root, WORD size, WORD mod, std::vector<WORD>& TFArr){
  WORD tempTF = 1;
  for(int i=0; i<(size/2); i++){
    TFArr[i] = tempTF;
    tempTF = (WORD)((((DWORD)tempTF) * ((DWORD)root)) % ((DWORD)mod));
  }
}

/* Generate TFs for num_of_limbs when poly size is 'size' */
void generateTFsForMultipleLimbs(VAR_TYPE_32 num_of_limbs, VAR_TYPE_32 size, std::vector<WORD>& workingModulus_arr, std::vector<WORD>& root_arr, std::vector<WORD> (&tfArr)[PARA_LIMBS]){
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<num_of_limbs; paraLimbCounter++){
    WORD root = root_arr[paraLimbCounter];
    WORD workingModulus = workingModulus_arr[paraLimbCounter];
    
    tfArr[paraLimbCounter].resize(size/2);

    generateTFForRadix2NTT(root, size, workingModulus, tfArr[paraLimbCounter]);
  }
}

//This function is used to reorganize TFs for FWD transform in following conditions.
//1. Only required TFs are stored
//2. One TF storage for 2 BUs with a distance of NUM_BU/2
//3. Chain broadcasting is used to load TFs.
//4. Chain is for consecutive BUF modules.
void fwd_organizeTFData(std::vector<WORD>& inpTfArr, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&outTFArr)[TF_PORTS_PER_PARA_LIMB]){
  std::vector<VAR_TYPE_32> TFGroupsPerBuf;
  std::vector<WORD> TFValsPerBuf[NUM_BU/2];
  std::vector<WORD> TFValsPerPort[TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT];

  int beta = (N)/(2*NUM_BU);
  
  for (VAR_TYPE_32 bufIdx=0; bufIdx<NUM_BU/2; bufIdx++){ //loop through the TF buffers(1 Buf for 2 BUs)
    TFGroupsPerBuf.clear();
    //calculate TF group indexes
    for(VAR_TYPE_32 i=0; i<2; i++){ //loop through 2 BUs
      VAR_TYPE_32 BUIdx = bufIdx+(i*(NUM_BU/2)); //recreate target BU index
      for(VAR_TYPE_32 stage=0; stage<=logBU; stage++){  //loop through bit size to extract different numbers created based on the BU index
        VAR_TYPE_32 tfGrpIdx = ((BUIdx) & ((1<<(stage)) - 1));
        TFGroupsPerBuf.push_back(tfGrpIdx);
      }
    }
    //Sort and remove duplicate TF group indexes
    sort( TFGroupsPerBuf.begin(), TFGroupsPerBuf.end() );
    TFGroupsPerBuf.erase( unique( TFGroupsPerBuf.begin(), TFGroupsPerBuf.end() ), TFGroupsPerBuf.end() );

    //adding TFs to respective Buf array based on the TF group index calculated before
    for(int numSets=0; numSets<TFGroupsPerBuf.size(); numSets++){
      int groupIndex = TFGroupsPerBuf[numSets];
      int TF_start_idx = groupIndex*beta;
      for(int idx=0; idx<beta; idx++){
        int tfIdx = TF_start_idx + idx;
        WORD tfVal = inpTfArr[tfIdx];
        TFValsPerBuf[bufIdx].push_back(tfVal);
      }
    }
  }

  //combining data for different DDR ports fascilitating chain broadcasting as well.
  for(int k=0; k<TF_PORTS_PER_PARA_LIMB; k++){    // Number of HBM ports for TF. We use TF_PORTS_PER_PARA_LIMB as we support more buffers per port for TFs compared to polynomials.

    //putting all data that goes to this paerticular port into one vector array. They are inserted according to the chain broadcasting pattern
    for(int s=0; s<NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT; s++){ // How many 'Bufs groups' being supported by a HBM prot. A single 'Buf group' is 8 Bufs(HBM port width).
      
      //cleaning the vector array for new data
      for(int i=0; i<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT; i++){
        TFValsPerPort[i].clear();
      }

      for (int idx=0; idx<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT; idx++){  //loop through a group. A single 'Buf group' is 16 Bufs(HBM port width).
        int bufIdx = k*NUM_BUF_PER_PARA_LIMB_TF_PORT + s*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + idx;
        for(int i=0; i<TFValsPerBuf[bufIdx].size(); i++){ //loop through the values in the respective buf
          TFValsPerPort[idx].push_back(TFValsPerBuf[bufIdx][i]); //append it to respective stream
        }
      }

      //calcualte the max length for this chain group
      int lastBufIdx = k*NUM_BUF_PER_PARA_LIMB_TF_PORT + s*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1;
      int maxlength=FWD_NUM_TF_GRPS_PER_BUF[lastBufIdx]*beta; 

      //combining data into a WIDE stream
      for(int idx=0; idx<maxlength; idx++){
        TF_WIDE_DATA_PER_PARA_LIMB comb_data = 0;
        for(int bufIdx=TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1; bufIdx>=0; bufIdx--){
          comb_data <<= DRAM_WORD_SIZE;
          WORD small_data;
          if((idx+1)<=TFValsPerPort[bufIdx].size()){
            small_data = TFValsPerPort[bufIdx][idx];
          }
          else{
            small_data = 0;
          }
          comb_data |= (TF_WIDE_DATA_PER_PARA_LIMB)small_data;
        }
        outTFArr[k].push_back(comb_data);
      }
    }
  }
}

//This function is used to reorganize TFs for INV transform in following conditions.
//1. Only required TFs are stored
//2. One TF storage for 2 BUs with a distance of NUM_BU/2
//3. Chain broadcasting is used to load TFs.
//4. Chain is for consecutive BUF modules. i.e., not balancing bandwdith
void inv_organizeTFData(std::vector<WORD>& inpTfArr, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&outTFArr)[TF_PORTS_PER_PARA_LIMB]){
  std::vector<VAR_TYPE_32> TFGroupsPerBuf;
  std::vector<WORD> TFValsPerBuf[NUM_BU/2];
  std::vector<WORD> TFValsPerPort[TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT];

  int beta = (N)/(2*NUM_BU);
  
  for (VAR_TYPE_32 bufIdx=0; bufIdx<NUM_BU/2; bufIdx++){ //loop through the TF buffers(1 Buf for 2 BUs)
    TFGroupsPerBuf.clear();
    //calculate TF group indexes
    for(VAR_TYPE_32 i=0; i<2; i++){ //loop through 2 BUs
      VAR_TYPE_32 BUIdx = bufIdx+(i*(NUM_BU/2)); //recreate target BU index
      for(VAR_TYPE_32 stage=logBU+2; stage>0; stage--){  //loop through bit size to extract different numbers created based on the BU index
        VAR_TYPE_32 tfGrpIdx = ((BUIdx) & (~((1<<(stage-1)) - 1)));
        TFGroupsPerBuf.push_back(tfGrpIdx);
      }
    }
    //Sort and remove duplicate TF group indexes
    sort( TFGroupsPerBuf.begin(), TFGroupsPerBuf.end() );
    TFGroupsPerBuf.erase( unique( TFGroupsPerBuf.begin(), TFGroupsPerBuf.end() ), TFGroupsPerBuf.end() );

    //adding TFs to respective Buf array based on the TF group index calculated before
    for(int numSets=0; numSets<TFGroupsPerBuf.size(); numSets++){
      int groupIndex = TFGroupsPerBuf[numSets];
      int TF_start_idx = groupIndex*beta;
      if( (numSets==((TFGroupsPerBuf.size()/2)-1)) || (numSets==(TFGroupsPerBuf.size()-1)) ){ //the middle one or the last one should have full group when supporting half distance BUs
        for(int idx=0; idx<beta; idx++){
          int tfIdx = TF_start_idx + idx;
          WORD tfVal = inpTfArr[tfIdx];
          TFValsPerBuf[bufIdx].push_back(tfVal);
        }
      }
      else{
        int tfIdx = TF_start_idx;
        WORD tfVal = inpTfArr[tfIdx];
        TFValsPerBuf[bufIdx].push_back(tfVal);
      }
    }
  }

  //combining data for different DDR ports fascilitating chain broadcasting as well.
  for(int k=0; k<TF_PORTS_PER_PARA_LIMB; k++){    // Number of HBM ports for TF. We use TF_PORTS_PER_PARA_LIMB as we support more buffers per port for TFs compared to polynomials.

    //putting all data that goes to this paerticular port into one vector array. They are inserted according to the chain broadcasting pattern
    for(int s=0; s<NUM_CHAIN_GROUPS_PER_PARA_LIMB_TF_PORT; s++){ // How many 'Bufs groups' being supported by a HBM prot. A single 'Buf group' is 8 Bufs(HBM port width).
      //cleaning the vector array for new data
      for(int i=0; i<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT; i++){
        TFValsPerPort[i].clear();
      }

      for (int idx=0; idx<TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT; idx++){  //loop through a group. A single 'Buf group' is 16 Bufs(HBM port width).
        int bufIdx = k*NUM_BUF_PER_PARA_LIMB_TF_PORT + s*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + idx;
        for(int i=0; i<TFValsPerBuf[bufIdx].size(); i++){ //loop through the values in the respective buf
          TFValsPerPort[idx].push_back(TFValsPerBuf[bufIdx][i]); //append it to respective stream
        }
      }

      //calcualte the max length for this port
      int lastBufIdx = k*NUM_BUF_PER_PARA_LIMB_TF_PORT + s*TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT + TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1;
      int maxlength = INV_NUM_TF_GRPS_PER_BUF[lastBufIdx]-2 + 2*beta;

      //combining data into a WIDE stream
      for(int idx=0; idx<maxlength; idx++){
        TF_WIDE_DATA_PER_PARA_LIMB comb_data = 0;
        for(int bufIdx=TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT-1; bufIdx>=0; bufIdx--){
          comb_data <<= DRAM_WORD_SIZE;
          WORD small_data;
          if((idx+1)<=TFValsPerPort[bufIdx].size()){
            small_data = TFValsPerPort[bufIdx][idx];
          }
          else{
            small_data = 0;
          }
          comb_data |= (TF_WIDE_DATA_PER_PARA_LIMB)small_data;
        }
        outTFArr[k].push_back(comb_data);
      }
    }
  }
}

void reorganize_para_limbs_to_ports_tf(std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[PARA_LIMBS][TF_PORTS_PER_PARA_LIMB], std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> (&outVec)[TF_PORTS]){

  for(int port_counter=0; port_counter<TF_PORTS; port_counter++){
    //init
    int target_per_limb_port_start = port_counter*PER_LIMB_PORTS_PER_TF_PORT;
    int target_limb_idx = target_per_limb_port_start/TF_PORTS_PER_PARA_LIMB;
    int target_limb_port_idx = target_per_limb_port_start%TF_PORTS_PER_PARA_LIMB;

    int num_of_data = inVec[target_limb_idx][target_limb_port_idx].size();
    outVec[port_counter].resize(num_of_data);

    //assign
    for(int data_counter=0; data_counter<num_of_data; data_counter++){
      TF_WIDE_DATA val = 0;
      for(int per_limb_port_counter=PER_LIMB_PORTS_PER_TF_PORT-1; per_limb_port_counter>=0; per_limb_port_counter--){
        int total_per_limb_ports = port_counter*PER_LIMB_PORTS_PER_TF_PORT + per_limb_port_counter;
        int limb_idx = total_per_limb_ports/TF_PORTS_PER_PARA_LIMB;
        int limb_port_idx = total_per_limb_ports%TF_PORTS_PER_PARA_LIMB;

        TF_WIDE_DATA_PER_PARA_LIMB limbVal;
        if(limb_idx<PARA_LIMBS){ 
          limbVal = inVec[limb_idx][limb_port_idx][data_counter];
        }
        else{//In case, PARA_LIMBS is not perfectly divisible by PER_LIMB_PORTS_PER_TF_PORT
          limbVal = 0;
        }
        val = val << TF_DRAM_PORT_WIDTH_PER_PARA_LIMB;
        val |= (TF_WIDE_DATA)limbVal;
      }
      outVec[port_counter][data_counter] = val;
    }
  }
}

void reorganize_input_tfs_to_ports(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> (&outVec)[TF_PORTS], bool direction){
  
  std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> limbWiseInTFData[PARA_LIMBS][TF_PORTS_PER_PARA_LIMB];
  
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    if(direction){
      fwd_organizeTFData(inVec[paraLimbCounter], limbWiseInTFData[paraLimbCounter]);
    }
    else{
      inv_organizeTFData(inVec[paraLimbCounter], limbWiseInTFData[paraLimbCounter]);
    }
  }
  reorganize_para_limbs_to_ports_tf(limbWiseInTFData, outVec);

}


// /********************************************************************************************
// * Modulo multiplication precomputations *
// ********************************************************************************************/

void pre_computation_montgomery(WORD mod, uint8_t *shift_montgomery, WORD *r, WORD *r_inverse, WORD *k)
{
	if (mod < 3 || mod % 2 == 0) {
    printf("[Error]::Modulus must be an odd number at least 3\n");
    exit(1);
  }

	// reducer
  *shift_montgomery = bit_length(mod);
  WORD_PLUS1 r_tmp = ((WORD_PLUS1)1U)<<(*shift_montgomery);
  *r_inverse = mod_inverse_pow2Num(*shift_montgomery, mod);
    
	// other precomputation
	*k = (WORD)((DWORD)((DWORD)((DWORD)(r_tmp)*(DWORD)(*r_inverse % mod)) - (DWORD)1) / (DWORD)(mod));
  *r = (WORD)((WORD_PLUS1)(r_tmp) - (WORD_PLUS1)(1));
  
  printf("\nMontgomery details:\n");
  std::cout << "r = " << r_tmp << ", inverse of r = " << *r_inverse << std::endl;
  std::cout << "k = " << *k << ", second r = " << *r << std::endl;
}

void pre_computation_montgomery_array(std::vector<WORD>& workingModulus_arr, std::vector<VAR_TYPE_8>& shift_montgomery, std::vector<WORD>& r, std::vector<WORD>& r_inverse, std::vector<WORD>& k){
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    VAR_TYPE_8 shift_montgomery_val;
    WORD r_val, r_inverse_val, k_val;
    pre_computation_montgomery(workingModulus_arr[paraLimbCounter], &shift_montgomery_val, &r_val, &r_inverse_val, &k_val);
    shift_montgomery[paraLimbCounter] = shift_montgomery_val;
    r[paraLimbCounter] = r_val;
    r_inverse[paraLimbCounter] = r_inverse_val;
    k[paraLimbCounter] = k_val;
  }
}

WORD convert_in(WORD x, uint8_t shift_montgomery, WORD modulus) {
    return (WORD)((DWORD)((DWORD)(x) << (DWORD)(shift_montgomery)) % (DWORD)(modulus));  // return ((x << log2(r)) % modulus);
}

void convert_in_array(std::vector<WORD>& inp1, std::vector<WORD>& inp1_montgomery, uint8_t shift_montgomery, WORD modulus) {
  for(int i=0;i<N/2;i++){
    inp1_montgomery.push_back(0);
  }
  for(int i=0; i<N/2; i++){
    inp1_montgomery[i] = convert_in(inp1[i], shift_montgomery, modulus);
  }
}

void convert_tfs_in_limbs_array_to_montgomery_form(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<WORD> (&outVec)[PARA_LIMBS], std::vector<VAR_TYPE_8>& shift_montgomery, std::vector<WORD>& workingModulus_arr){
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    VAR_TYPE_32 size = inVec[paraLimbCounter].size();
    outVec[paraLimbCounter].resize(size);
    convert_in_array(inVec[paraLimbCounter], outVec[paraLimbCounter], shift_montgomery[paraLimbCounter], workingModulus_arr[paraLimbCounter]);
  }
}

WORD WLM_find_multiplier(WORD mod){
  if((mod-1)%(((WORD_PLUS1)1)<<WLM_WORD_SIZE)!=0){
    std::cout << "[ERROR]:: The modulus " << mod << " can not be divided by WLM word size " << WLM_WORD_SIZE << std::endl;
    exit(1);
  }
  WORD multiplier = (mod-1)/(((WORD_PLUS1)1)<<WLM_WORD_SIZE);
  return multiplier;
}

void WLM_find_multiplier_arr(std::vector<WORD>& workingModulus_arr, std::vector<WLM_MULTIPLIER_WORD>& multiplier_arr){
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    multiplier_arr[paraLimbCounter] = WLM_find_multiplier(workingModulus_arr[paraLimbCounter]);
    std::cout << "WLM multiplier[" << paraLimbCounter << "] = " << multiplier_arr[paraLimbCounter] << std::endl;
  }
}


// /********************************************************************************************
// * main *
// ********************************************************************************************/

int main(int argc, char* argv[]) {
  gflags::ParseCommandLineFlags(&argc, &argv, /*remove_flags=*/true);

  VAR_TYPE_32 seed = 7;
  VAR_TYPE_64 minMod = (((VAR_TYPE_64)1U)<<(WORD_SIZE-1))+1;
  VAR_TYPE_32 size = N;

  std::cout << "Polynomial size = " << size << ", Minimum Modulus = " << minMod << std::endl;
  std::cout << "Parallel limb count = " << (VAR_TYPE_32)PARA_LIMBS << std::endl;

  // Generate inputs
  vector<WORD> invec[PARA_LIMBS];
  generate_random_polynomials_array(seed, minMod, size, PARA_LIMBS, invec);

  // Calculate working modulus
  vector<WORD> workingModulus_arr(PARA_LIMBS);
  find_NTT_and_WLM_friendly_modulus_array(size, minMod, workingModulus_arr, PARA_LIMBS);

  // Find the primitive root of unity, inverse and two inverse (used in INTT)
  vector<WORD> root_arr(PARA_LIMBS);
  vector<WORD> rootInverse_arr(PARA_LIMBS);
  vector<WORD> twoInverse_arr(PARA_LIMBS);
  generate_NTT_variables(workingModulus_arr, size, PARA_LIMBS, root_arr, rootInverse_arr, twoInverse_arr);

  // Print parameter summary
  std::cout << "\nParallel limb parameters:" << std::endl;
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    std::cout << "Para limb " << paraLimbCounter << ": Modulus = " << workingModulus_arr[paraLimbCounter] << ", root = " << root_arr[paraLimbCounter] << ", rootInverse = " << rootInverse_arr[paraLimbCounter] << ", twoInverse = " << twoInverse_arr[paraLimbCounter] << std::endl;
  }

  // Calculating TFs - FWD
  vector<WORD> tfArr[PARA_LIMBS];
  generateTFsForMultipleLimbs(PARA_LIMBS, size, workingModulus_arr, root_arr, tfArr);
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    bitReverseVect(tfArr[paraLimbCounter], size/2);
  }

  // Calculating TFs - INV
  vector<WORD> inv_tfArr[PARA_LIMBS];
  generateTFsForMultipleLimbs(PARA_LIMBS, size, workingModulus_arr, rootInverse_arr, inv_tfArr);

  // NTT in host
  vector<WORD> fwdVec_ref[PARA_LIMBS];
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    fwdVec_ref[paraLimbCounter].resize(size);
    fwdVec_ref[paraLimbCounter] = invec[paraLimbCounter];
    WORD workingModulus = workingModulus_arr[paraLimbCounter];
    tensorProd_NToR_fwd_NTT(fwdVec_ref[paraLimbCounter], tfArr[paraLimbCounter], workingModulus, size, NUM_BU);
  }
  printf("Host NTT computation completed\n");

  // Perform modulo reduction related pre computations
  vector<VAR_TYPE_8> shift_montgomery(PARA_LIMBS);
  vector<WORD> r(PARA_LIMBS);
  vector<WORD> r_inverse(PARA_LIMBS);
  vector<WORD> k(PARA_LIMBS);
  pre_computation_montgomery_array(workingModulus_arr, shift_montgomery, r, r_inverse, k);
  vector<WLM_MULTIPLIER_WORD> multiplier(PARA_LIMBS);
  WLM_find_multiplier_arr(workingModulus_arr, multiplier);
  
  //convert TFs into the montgomery form
  vector<WORD> tfArr_montgomery[PARA_LIMBS];
  vector<WORD> inv_tfArr_montgomery[PARA_LIMBS];
  convert_tfs_in_limbs_array_to_montgomery_form(tfArr, tfArr_montgomery, shift_montgomery, workingModulus_arr);
  convert_tfs_in_limbs_array_to_montgomery_form(inv_tfArr, inv_tfArr_montgomery, shift_montgomery, workingModulus_arr);

  bool direction;
  int64_t kernel_time_ns;
  bool status;
  VAR_TYPE_16 iter = 1;
  printf("\nNumber of iterations=%d\n\n",(int)iter);

  // FWD
  direction = true;

  // Poly data rearrangements
  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> portWiseInPolyData[POLY_LS_PORTS];
  reorganize_input_poly_to_ports(invec, portWiseInPolyData);

  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> portWiseOutData[POLY_LS_PORTS];
  init_kernerl_output_ports(portWiseOutData);

  // TF data rearrangements
  std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> portWiseInTFData[TF_PORTS];
  reorganize_input_tfs_to_ports(tfArr_montgomery, portWiseInTFData, direction);

  printf("\n====Forward Computation====\n");

  kernel_time_ns = tapa::invoke(
      NTT_kernel, FLAGS_bitstream, 
      tapa::read_only_mmap<POLY_WIDE_DATA>(portWiseInPolyData[0]),
      tapa::read_only_mmap<TF_WIDE_DATA>(portWiseInTFData[0]),
      tapa::write_only_mmap<POLY_WIDE_DATA>(portWiseOutData[0]),
      workingModulus_arr[0],
      twoInverse_arr[0],
      multiplier[0],
      direction,
      iter
      );
  clog << "kernel time: " << kernel_time_ns * 1e-9 << " s\n" << endl;

  std::vector<WORD> kernelOutArr[PARA_LIMBS];
  reorganize_ports_to_output_poly(portWiseOutData, kernelOutArr);

  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    status = compareResults(fwdVec_ref[paraLimbCounter], kernelOutArr[paraLimbCounter], size);
    if(status){
      printf("[Para limb %d]::Forward Kernel Execution Passed\n", (int)paraLimbCounter);
    }
    else{
      printf("[Para limb %d]::Forward Kernel Execution Failed\n", (int)paraLimbCounter);
      exit (1);
    }
  }

  // INV
  direction = false;

  // Poly data rearrangements
  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> inv_portWiseInPolyData[POLY_LS_PORTS];
  reorganize_input_poly_to_ports(fwdVec_ref, inv_portWiseInPolyData);

  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> inv_portWiseOutData[POLY_LS_PORTS];
  init_kernerl_output_ports(inv_portWiseOutData);

  // TF data rearrangements
  std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> inv_portWiseInTFData[TF_PORTS];
  reorganize_input_tfs_to_ports(inv_tfArr_montgomery, inv_portWiseInTFData, direction);

  printf("\n===Inverse Computation===\n");

  kernel_time_ns = tapa::invoke(
      NTT_kernel, FLAGS_bitstream, 
      tapa::read_only_mmap<POLY_WIDE_DATA>(inv_portWiseInPolyData[0]),
      tapa::read_only_mmap<TF_WIDE_DATA>(inv_portWiseInTFData[0]),
      tapa::write_only_mmap<POLY_WIDE_DATA>(inv_portWiseOutData[0]),
      workingModulus_arr[0],
      twoInverse_arr[0],
      multiplier[0],
      direction,
      iter
      );
  clog << "kernel time: " << kernel_time_ns * 1e-9 << " s\n" << endl;

  std::vector<WORD> inv_kernelOutArr[PARA_LIMBS];
  reorganize_ports_to_output_poly(inv_portWiseOutData, inv_kernelOutArr);

  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    status = compareResults(invec[paraLimbCounter], inv_kernelOutArr[paraLimbCounter], size);
    if(status){
      printf("[Para limb %d]::Inverse Kernel Execution Passed\n", (int)paraLimbCounter);
    }
    else{
      printf("[Para limb %d]::Inverse Kernel Execution Failed\n", (int)paraLimbCounter);
      exit (1);
    }
  }

  printf("\nRun completed\n");

  return 0;
}

