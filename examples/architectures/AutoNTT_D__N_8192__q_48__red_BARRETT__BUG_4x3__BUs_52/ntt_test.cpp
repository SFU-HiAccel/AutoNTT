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
    tapa::mmap<TF_WIDE_DATA> TFArr_G1,
    tapa::mmap<TF_WIDE_DATA> TFArr_G2,
    tapa::mmap<TF_WIDE_DATA> TFArr_G3,
    tapa::mmap<TF_WIDE_DATA> TFArr_G4,
    tapa::mmap<POLY_WIDE_DATA> polyVectorOut_G0,
    WORD q0,
    WORD twoInverse0,
    WORD_PLUS3 factor0,
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
Generate NTT friendly moduls.
NTT friendly modulus is in the form of M = 2*n+1, n being the size of the input
*/
WORD find_NTT_friendly_modulus(WORD size, WORD minMod){

  if ((size<1) | (minMod<1)){
    printf("[Error]::Double check your parameters\n");
    exit(1);
  }

  WORD start = (WORD)((minMod -1 + size -1)/size);

  WORD multiplier = (start>((WORD)1))?start:(WORD)1;

  while(true){
    WORD workModulus = size * multiplier + 1;
    if(workModulus<minMod){
      printf("[Error]::Something wrong. Double check.\n");
      exit(1);
    }

    if(is_prime(workModulus)){
      return workModulus;
    }
    multiplier++;
  }
}

/*
Generate NTT friendly moduls array.
NTT friendly modulus is in the form of M = 2*n+1, n being the size of the input
*/
void find_NTT_friendly_modulus_array(WORD size, WORD minMod, std::vector<WORD>& modulusArray, VAR_TYPE_32 limbCount){

  VAR_TYPE_32 limbCounter = 0;
  for(VAR_TYPE_32 i=0; i<limbCount; i++){
    modulusArray[i] = 0;
  }

  if ((size<1) | (minMod<1)){
    printf("[Error]::Double check your parameters.\n");
  }

  WORD start = (WORD)((minMod -1 + size -1)/size);

  WORD multiplier = (start>((WORD)1))?start:(WORD)1;

  while(limbCounter < limbCount){
    WORD workModulus = size * multiplier + 1;
    if(workModulus<minMod){
      printf("[Error]::Something wrong. Double check.\n");
      exit(1);
    }

    if(is_prime(workModulus)){
      // std::cout << "modulusArray[" << limbCounter << "] = " << workModulus << std::endl;
      modulusArray[limbCounter] = workModulus;
      limbCounter++;
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
Compute NTT using radix-2 Pease FFT
Input is provided in bit reversed order. Hence, TF are used in ascending power order.
*/
void radix2PeaseTransformRToN(std::vector<WORD>& boInvec, std::vector<WORD>& noTFArr, WORD mod, VAR_TYPE_32 N, WORD NUMPE){
  WORD stages = myLog2(N);//log2(((VAR_TYPE_32)N));
  if((1<<stages)!=N){
    printf("[Error]::Size is not a 2 to the power number\n");
    exit(0);
  }

  WORD temp[N];

  WORD beta = (1<<(stages-1))/NUMPE;
  
  for(WORD l=stages; l>0; l--){
    for(WORD j=0; j<beta; j++){
      for(WORD i=0; i<NUMPE; i++){
        WORD delta = i*beta + j;
        WORD pow = (((2*delta + 1)>>l) << (l-1));
      
        WORD tfVal = noTFArr[pow];

        WORD left = boInvec[delta<<1];

        WORD right = (WORD)((((DWORD)boInvec[(delta<<1) + 1]) * ((DWORD)tfVal)) % ((DWORD)mod));

        temp[delta] = (WORD)((((DWORD)left) + ((DWORD)right)) % ((DWORD)mod));
        
        if(left >= right){
          temp[delta + (1<<(stages-1))] = (WORD)((((DWORD)left) - ((DWORD)right)) % ((DWORD)mod)); //probably, we can remove this last mod(%) operation
        }
        else{
          temp[delta + (1<<(stages-1))] = (WORD)((((DWORD)mod) - (((DWORD)right) - ((DWORD)left))) % ((DWORD)mod));  //probably, we can remove this last mod(%) operation
        }
      }
    }
    
    for(WORD h=0; h<N; h++){
      boInvec[h] = temp[h];
    }
  }
}


// /********************************************************************************************
// * Polynomial rearrangements *
// ********************************************************************************************/

void reorganize_para_limbs_to_ports_poly(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){
  int num_of_data = (N/CONCAT_FACTOR);

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

void reorganize_ports_to_para_limbs_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB]){
  int num_of_data = (N/CONCAT_FACTOR);

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

void cyclicDivideData(std::vector<WORD>& inVec, std::vector<WORD> (&outVec)[CONCAT_FACTOR]){
  for(int i=0; i<N; i++){
    outVec[i%CONCAT_FACTOR].push_back(inVec[i]);
  }
}
void fwd_reorganize_in_poly_per_para_limb(std::vector<WORD>& inVec, std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[HBM_PORT_NUM]){
  std::vector<WORD> blockInData[CONCAT_FACTOR];
  cyclicDivideData(inVec, blockInData);

    for(int i=0; i<(N/CONCAT_FACTOR); i++){
      POLY_WIDE_DATA_PER_PARA_LIMB val[HBM_PORT_NUM] = {0};   // G0, G1, G2, G3 -> val[0], val[1], val[2], val[3],
      for(int s=0; s<HBM_PORT_NUM; s++) {
        for(int j=HBM_PORT_SIZE-1; j>=0; j--){
          val[s] <<= DRAM_WORD_SIZE;
          val[s] |= ((POLY_WIDE_DATA_PER_PARA_LIMB)blockInData[s*HBM_PORT_SIZE+j][i]);
        }
        outVec[s].push_back((POLY_WIDE_DATA_PER_PARA_LIMB)val[s]);
      }
    }

}
void fwd_reorganize_out_poly_per_para_limb(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[HBM_PORT_NUM], std::vector<WORD>& outVec){

  int index[CONCAT_FACTOR];
  for(int i = 0; i < CONCAT_FACTOR/2; i++) {
    index[i] = i*2;
    index[i+CONCAT_FACTOR/2] = i*2+1;
  }

    for(int j = 0; j < CONCAT_FACTOR; j++) {
      for(int i = 0; i < (N/CONCAT_FACTOR); i++) { //0 - 64
        int inVec_index_1_dimen = index[j]/HBM_PORT_SIZE;
        int inVec_index_2_dimen = index[j]%HBM_PORT_SIZE;
        
        POLY_WIDE_DATA_PER_PARA_LIMB val = inVec[inVec_index_1_dimen][i];
        
        WORD smallVal = (WORD)(val.range((inVec_index_2_dimen*DRAM_WORD_SIZE)+(WORD_SIZE-1),(inVec_index_2_dimen*DRAM_WORD_SIZE)));
        outVec.push_back(smallVal); 
      }
    }
}

void fwd_reorganize_input_poly_to_ports(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){
  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseInPolyData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];
  
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    fwd_reorganize_in_poly_per_para_limb(inVec[paraLimbCounter], limbWiseInPolyData[paraLimbCounter]);
  }

  reorganize_para_limbs_to_ports_poly(limbWiseInPolyData, outVec);
}

void fwd_reorganize_ports_to_output_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<WORD> (&outVec)[PARA_LIMBS]){
  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseOutData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];
  reorganize_ports_to_para_limbs_poly(inVec, limbWiseOutData);

  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    //outVec[paraLimbCounter].resize(N); // Values are getting added instead assign
    fwd_reorganize_out_poly_per_para_limb(limbWiseOutData[paraLimbCounter], outVec[paraLimbCounter]);
  }
}

void inv_reorganize_out_poly_per_para_limb(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[HBM_PORT_NUM], std::vector<WORD>& outVec){

    for(int i=0; i<(N/CONCAT_FACTOR); i++)
    {
      for(int s=0; s<HBM_PORT_NUM; s++) {
        POLY_WIDE_DATA_PER_PARA_LIMB val = inVec[s][i];
        for(int j=0; j<HBM_PORT_SIZE; j++)
        {
          int val_index = (j);
          WORD smallVal = (WORD)(val.range((val_index*DRAM_WORD_SIZE)+(WORD_SIZE-1),(val_index*DRAM_WORD_SIZE)));

          outVec.push_back(smallVal);
        }
      }
    }
}
void inv_reorganize_ports_to_output_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<WORD> (&outVec)[PARA_LIMBS]){
  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseOutData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];
  reorganize_ports_to_para_limbs_poly(inVec, limbWiseOutData);

  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    //outVec[paraLimbCounter].resize(N); // Values are getting added instead assign
    inv_reorganize_out_poly_per_para_limb(limbWiseOutData[paraLimbCounter], outVec[paraLimbCounter]);
  }
}

/* This function is to initialize output DRAM ports to 0 */
void init_kernerl_output_ports(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS]){
  for(int i=0; i<(N/CONCAT_FACTOR); i++){
    for(int j=0; j<POLY_LS_PORTS; j++){
      inVec[j].push_back(0);
    }
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

void reorganize_para_limbs_to_ports_tf(std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[PARA_LIMBS][TF_PORTS_PER_PARA_LIMB], std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> (&outVec)[TF_PORTS]){

  for(int h_port_idx=0; h_port_idx<H_TF_PORTS_PER_PARA_LIMB; h_port_idx++){
    for(int port_counter=0; port_counter<V_TF_PORTS; port_counter++){
      //init
      int target_per_limb_port_start = port_counter*V_PARA_LIMB_PORTS_PER_TF_PORT;
      int target_limb_idx = target_per_limb_port_start/V_TF_PORTS_PER_PARA_LIMB;
      int target_limb_port_idx = h_port_idx*V_TF_PORTS_PER_PARA_LIMB;
      int target_actual_port_idx = h_port_idx*V_TF_PORTS + port_counter;

      int num_of_data = inVec[target_limb_idx][target_limb_port_idx].size(); // This could be = inVec[0][target_limb_port_idx].size()
      outVec[target_actual_port_idx].resize(num_of_data);

      //assign
      for(int data_counter=0; data_counter<num_of_data; data_counter++){
        TF_WIDE_DATA val = 0;
        for(int per_limb_port_counter=V_PARA_LIMB_PORTS_PER_TF_PORT-1; per_limb_port_counter>=0; per_limb_port_counter--){
          int total_per_limb_ports = port_counter*V_PARA_LIMB_PORTS_PER_TF_PORT + per_limb_port_counter;
          int limb_idx = total_per_limb_ports/V_TF_PORTS_PER_PARA_LIMB;
          int limb_port_idx = h_port_idx*V_TF_PORTS_PER_PARA_LIMB + total_per_limb_ports%V_TF_PORTS_PER_PARA_LIMB;

          TF_WIDE_DATA_PER_PARA_LIMB limbVal;
          if(limb_idx<PARA_LIMBS){ 
            limbVal = inVec[limb_idx][limb_port_idx][data_counter];
          }
          else{//In case, PARA_LIMBS is not perfectly divisible by PARA_LIMB_PORTS_PER_TF_PORT
            limbVal = 0;
          }
          val = val << TF_DRAM_PORT_WIDTH_PER_PARA_LIMB;
          val |= (TF_WIDE_DATA)limbVal;
        }
        outVec[target_actual_port_idx][data_counter] = val;
      }
    }
  }
}


void fwd_organizeTFData(std::vector<WORD>& inp1, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inp1_512b)[DB_TF_PORT_NUM]) 
{
  int sum_tf_per_stage = 1;

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    for(int l=0;l<tf_depth;l++)
    {
      int idx = 0;
      if ((LEN_0<=i) && (i<LEN_1)) {
        idx = 0;                
      }
      else if ((LEN_1<=i) && (i<LEN_2)) {
        idx = 1;                
      }
      else if ((LEN_2<=i) && (i<LEN_3)) {
        idx = 2;                
      }
      else if ((LEN_3<=i) && (i<LEN_4)) {
        idx = 3;                
      }
      else {
        idx = 4;
      }

      inp1_512b[idx].push_back(0);

    }
    sum_tf_per_stage <<= 1;
  }

  sum_tf_per_stage = 1;
  int distance_stage = halfN;
  int outer = V_BU_NUM, inner = 1;
  int previous_cycle = 0;
  int idx_before = 0, idx_after = 0;

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    int inp1_idx = 0;
    if ((i%H_BU_NUM) == 0)
    {
      outer = V_BU_NUM;
      inner = 1;
    }
    if (((logN % H_BU_NUM) == LAST_H_BU_NUM) && (i == (logN-LAST_H_BU_NUM))) {  // change by forward, partial group's TF initialization when LAST_H_BU_NUM==4
      int shift = H_BU_NUM-LAST_H_BU_NUM;
      outer = V_BU_NUM >> shift;
      inner = 1 << shift;
    }

    if ((LEN_0<=i) && (i<LEN_1)) {
      idx_before = idx_after;
      idx_after = 0;              
    }
    else if ((LEN_1<=i) && (i<LEN_2)) {
      idx_before = idx_after;
      idx_after = 1;              
    }
    else if ((LEN_2<=i) && (i<LEN_3)) {
      idx_before = idx_after;
      idx_after = 2;              
    }
    else if ((LEN_3<=i) && (i<LEN_4)) {
      idx_before = idx_after;
      idx_after = 3;              
    }
    else {
      idx_before = idx_after;
      idx_after = 4;
    }
    if (idx_before != idx_after) {
      previous_cycle = 0;
    }

    for(int k=0;k<inner;k++)
    {
      for(int l=0;l<tf_depth;l++)
      {
        TF_WIDE_DATA_PER_PARA_LIMB packTF = inp1_512b[idx_after][previous_cycle+l];
        for(int j=0;j<outer;j++)
        {
          packTF <<= DRAM_WORD_SIZE;
          packTF |= (TF_WIDE_DATA_PER_PARA_LIMB)inp1[inp1_idx];
          
          inp1_idx += (((i<H_BU_NUM)&&(j!=(outer-1)))?0:distance_stage);
        }
        inp1_512b[idx_after][previous_cycle+l]=(TF_WIDE_DATA_PER_PARA_LIMB)packTF;
      }
    }
    outer>>=1;
    inner<<=1;  
    sum_tf_per_stage <<= 1;
    distance_stage >>= 1;
    previous_cycle += tf_depth;
  }
}


void inv_organizeTFData(std::vector<WORD>& inp1, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&inp1_512b)[DB_TF_PORT_NUM]) 
{
  int sum_tf_per_stage = 1;
  int new_tf_depth[3] = {};

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    for(int l=0;l<tf_depth;l++)
    {
      int idx = 0;
      if ((LEN_0<=i) && (i<LEN_1)) {
        idx = 0;                
      }
      else if ((LEN_1<=i) && (i<LEN_2)) {
        idx = 1;                
      }
      else if ((LEN_2<=i) && (i<LEN_3)) {
        idx = 2;                
      }
      else if ((LEN_3<=i) && (i<LEN_4)) {
        idx = 3;                
      }
      else {
        idx = 4;
      }

      inp1_512b[idx].push_back(0);
    }
    sum_tf_per_stage <<= 1;
  }

    sum_tf_per_stage = 1;
  int outer = V_BU_NUM, inner = 1;
  int previous_cycle = 0;
  int idx_before = 0, idx_after = 0;

  for(int i=0;i<logN;i++)
  {
    int tf_depth = ((sum_tf_per_stage/V_BU_NUM)==0)?1:(sum_tf_per_stage/V_BU_NUM);
    int inp1_idx = 0;
    if ((i == 0) || (((i+(H_BU_NUM-LAST_H_BU_NUM)) % H_BU_NUM) == 0))   // change by inverse
    {
      outer = V_BU_NUM;
      inner = 1;
    } 

    if ((LEN_0<=i) && (i<LEN_1)) {
      idx_before = idx_after;
      idx_after = 0;              
    }
    else if ((LEN_1<=i) && (i<LEN_2)) {
      idx_before = idx_after;
      idx_after = 1;              
    }
    else if ((LEN_2<=i) && (i<LEN_3)) {
      idx_before = idx_after;
      idx_after = 2;              
    }
    else if ((LEN_3<=i) && (i<LEN_4)) {
      idx_before = idx_after;
      idx_after = 3;              
    }
    else {
      idx_before = idx_after;
      idx_after = 4;
    }
    if (idx_before != idx_after) {
      previous_cycle = 0;
    }

    for(int k=0;k<inner;k++)
    {
      inp1_idx = k;
      for(int l=0;l<tf_depth;l++)
      {
        TF_WIDE_DATA_PER_PARA_LIMB packTF = inp1_512b[idx_after][previous_cycle+l];
        for(int j=0;j<outer;j++)
        {
          packTF <<= DRAM_WORD_SIZE;
          packTF |= (TF_WIDE_DATA_PER_PARA_LIMB)inp1[inp1_idx%sum_tf_per_stage];
          
          inp1_idx += inner;
        }
        inp1_512b[idx_after][previous_cycle+l]=(TF_WIDE_DATA_PER_PARA_LIMB)packTF;
      }
    }
    outer>>=1;
    inner<<=1;  
    sum_tf_per_stage <<= 1;
    previous_cycle += tf_depth;
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

void pre_computation_barrett_factor(WORD mod, WORD_PLUS3 *factor)
{
  *factor = (WORD_PLUS3)(((DWORD_PLUS3(1))<<(2*(WORD_SIZE+1)))/mod);
}

void pre_computation_barrett_factor_arr(std::vector<WORD>& workingModulus_arr, std::vector<WORD_PLUS3>& factor){
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    WORD workingModulus = workingModulus_arr[paraLimbCounter];
    WORD_PLUS3 factor_val;
    pre_computation_barrett_factor(workingModulus, &factor_val);
    factor[paraLimbCounter] = factor_val;
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
  find_NTT_friendly_modulus_array(size, minMod, workingModulus_arr, PARA_LIMBS);

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

  // Calculating TFs - INV
  vector<WORD> inv_tfArr[PARA_LIMBS];
  generateTFsForMultipleLimbs(PARA_LIMBS, size, workingModulus_arr, rootInverse_arr, inv_tfArr);
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    bitReverseVect(inv_tfArr[paraLimbCounter], size/2);
  }

  // NTT in host
  vector<WORD> fwdVec_ref[PARA_LIMBS];
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    fwdVec_ref[paraLimbCounter].resize(size);
    fwdVec_ref[paraLimbCounter] = invec[paraLimbCounter];
    bitReverseVect(fwdVec_ref[paraLimbCounter], size);
    WORD workingModulus = workingModulus_arr[paraLimbCounter];
    radix2PeaseTransformRToN(fwdVec_ref[paraLimbCounter], tfArr[paraLimbCounter], workingModulus, size, 1);
  }
  printf("\nHost NTT computation completed\n");

  // Perform modulo reduction related pre computations
  vector<WORD_PLUS3> factor(PARA_LIMBS);
  pre_computation_barrett_factor_arr(workingModulus_arr, factor);

  bool direction;
  int64_t kernel_time_ns;
  bool status;
  VAR_TYPE_16 iter = 1;
  printf("\nNumber of iterations=%d\n\n",(int)iter);

  // FWD
  direction = true;

  // Poly data rearrangements
  vector<WORD> fwdVec_test[PARA_LIMBS];
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    fwdVec_test[paraLimbCounter].resize(size);
    fwdVec_test[paraLimbCounter] = invec[paraLimbCounter];
    bitReverseVect(fwdVec_test[paraLimbCounter], size);
  }
  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> portWiseInPolyData[POLY_LS_PORTS];
  fwd_reorganize_input_poly_to_ports(fwdVec_test, portWiseInPolyData);

  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> portWiseOutData[POLY_LS_PORTS];
  init_kernerl_output_ports(portWiseOutData);
  // TF data rearrangements
  std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> portWiseInTFData[TF_PORTS];
  reorganize_input_tfs_to_ports(tfArr, portWiseInTFData, direction);

  printf("\n====Forward Computation====\n");

  kernel_time_ns = tapa::invoke(
      NTT_kernel, FLAGS_bitstream, 
      tapa::read_write_mmap<POLY_WIDE_DATA>(portWiseInPolyData[0]),
      tapa::read_only_mmap<TF_WIDE_DATA>(portWiseInTFData[0]),
      tapa::read_only_mmap<TF_WIDE_DATA>(portWiseInTFData[1]),
      tapa::read_only_mmap<TF_WIDE_DATA>(portWiseInTFData[2]),
      tapa::read_only_mmap<TF_WIDE_DATA>(portWiseInTFData[3]),
      tapa::read_only_mmap<TF_WIDE_DATA>(portWiseInTFData[4]),
      tapa::read_write_mmap<POLY_WIDE_DATA>(portWiseOutData[0]),
      workingModulus_arr[0],
      twoInverse_arr[0],
      factor[0],
      direction,
      iter
      );
  clog << "kernel time: " << kernel_time_ns * 1e-9 << " s\n" << endl;

  std::vector<WORD> kernelOutArr[PARA_LIMBS];
  fwd_reorganize_ports_to_output_poly(portWiseOutData, kernelOutArr);

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

  printf("\n");

  // INV
  direction = false;

  // Poly data rearrangements
  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> inv_portWiseOutData[POLY_LS_PORTS];
  init_kernerl_output_ports(inv_portWiseOutData);

  // TF data rearrangements
  std::vector<TF_WIDE_DATA, tapa::aligned_allocator<TF_WIDE_DATA>> inv_portWiseInTFData[TF_PORTS];
  reorganize_input_tfs_to_ports(inv_tfArr, inv_portWiseInTFData, direction);

  printf("\n===Inverse Computation===\n");

  kernel_time_ns = tapa::invoke(
      NTT_kernel, FLAGS_bitstream, 
      tapa::read_write_mmap<POLY_WIDE_DATA>(inv_portWiseOutData[0]),
      tapa::read_only_mmap<TF_WIDE_DATA>(inv_portWiseInTFData[0]),
      tapa::read_only_mmap<TF_WIDE_DATA>(inv_portWiseInTFData[1]),
      tapa::read_only_mmap<TF_WIDE_DATA>(inv_portWiseInTFData[2]),
      tapa::read_only_mmap<TF_WIDE_DATA>(inv_portWiseInTFData[3]),
      tapa::read_only_mmap<TF_WIDE_DATA>(inv_portWiseInTFData[4]),
      tapa::read_write_mmap<POLY_WIDE_DATA>(portWiseOutData[0]),
      workingModulus_arr[0],
      twoInverse_arr[0],
      factor[0],
      direction,
      iter
      );
  clog << "kernel time: " << kernel_time_ns * 1e-9 << " s\n" << endl;

  std::vector<WORD> inv_kernelOutArr[PARA_LIMBS];
  inv_reorganize_ports_to_output_poly(inv_portWiseOutData, inv_kernelOutArr);

  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    bitReverseVect(inv_kernelOutArr[paraLimbCounter], size);
  }

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

