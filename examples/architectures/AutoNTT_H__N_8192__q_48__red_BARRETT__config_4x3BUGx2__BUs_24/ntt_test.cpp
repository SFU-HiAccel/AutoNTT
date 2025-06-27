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
    tapa::mmap<POLY_WIDE_DATA> polyVectorInOut_G0,
    tapa::mmap<TF_WIDE_DATA> TFArr_G0,
    tapa::mmap<POLY_WIDE_DATA> polyVectorInOut_G1,
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

void CT_RToN_fwd_NTT(std::vector<WORD>& inVec, std::vector<WORD>& tfVec, WORD mod, VAR_TYPE_32 size){
  for (VAR_TYPE_32 stage=1; stage<size; stage=stage*2){
    VAR_TYPE_32 distance = stage;
    VAR_TYPE_32 tableStep = size/(2*distance);
    for(VAR_TYPE_32 tableIdx = 0; tableIdx<size; tableIdx+=2*distance){
      VAR_TYPE_32 tfIdx = 0;
      for(VAR_TYPE_32 pairIdx=tableIdx; pairIdx<tableIdx+distance; pairIdx++){
        VAR_TYPE_32 leftIdx = pairIdx;
        VAR_TYPE_32 rightIdx = pairIdx+distance;

        WORD left = inVec[leftIdx];
        WORD right = inVec[rightIdx];
        WORD tfVal = tfVec[tfIdx];

        WORD reducedProduct = (WORD)((((DWORD)right) * ((DWORD)tfVal)) % ((DWORD)mod));
        
        WORD updatedLeft = (WORD)((((DWORD)left) + ((DWORD)reducedProduct)) % ((DWORD)mod));
        
        WORD updatedRight;
        if(left>=reducedProduct){
          updatedRight = left - reducedProduct;
        }
        else{
          updatedRight = mod - (reducedProduct - left);
        }

        inVec[leftIdx] = updatedLeft;
        inVec[rightIdx] = updatedRight;

        tfIdx += tableStep;
      }
    }
  }
}

void CT_NToR_INTT(std::vector<WORD>& inVec, std::vector<WORD>& tfVec, WORD mod, VAR_TYPE_32 size){
  for (VAR_TYPE_32 stage=1; stage<size; stage=stage*2){
    VAR_TYPE_32 distance = size/(2*stage);
    VAR_TYPE_32 tfIdx = 0;
    for(VAR_TYPE_32 tableIdx = 0; tableIdx<size; tableIdx+=2*distance){
      for(VAR_TYPE_32 pairIdx=tableIdx; pairIdx<tableIdx+distance; pairIdx++){
        VAR_TYPE_32 leftIdx = pairIdx;
        VAR_TYPE_32 rightIdx = pairIdx+distance;

        WORD left = inVec[leftIdx];
        WORD right = inVec[rightIdx];
        WORD tfVal = tfVec[tfIdx];

        WORD reducedProduct = (WORD)((((DWORD)right) * ((DWORD)tfVal)) % ((DWORD)mod));
        
        WORD updatedLeft = (WORD)((((DWORD)left) + ((DWORD)reducedProduct)) % ((DWORD)mod));
        
        WORD updatedRight;
        if(left>=reducedProduct){
          updatedRight = left - reducedProduct;
        }
        else{
          updatedRight = mod - (reducedProduct - left);
        }

        inVec[leftIdx] = updatedLeft;
        inVec[rightIdx] = updatedRight;

      }
      tfIdx += 1;
    }
  }

  // multiply with (1/n) mod q, which is required in INTT
  WORD nInverse = (WORD)(mod_inverse_pow2Num(logN, (long)mod));

  for(VAR_TYPE_32 i=0; i<size; i++){
    inVec[i] = (WORD)( (((DWORD)inVec[i]) * ((DWORD)nInverse)) % ((DWORD)mod) );
  }
}

/* This function generates CT data flow exactly same as CT_RToN_fwd_NTT, just without computations. This can be used for debugging purposes */
void dummy_CT_RToN_fwd_NTT(std::vector<WORD>& inVec, std::vector<WORD>& tfVec, WORD mod, VAR_TYPE_32 size){
  for (VAR_TYPE_32 stage=1; stage<size; stage=stage*2){
    VAR_TYPE_32 distance = stage;
    VAR_TYPE_32 tableStep = size/(2*distance);
    for(VAR_TYPE_32 tableIdx = 0; tableIdx<size; tableIdx+=2*distance){
      VAR_TYPE_32 tfIdx = 0;
      for(VAR_TYPE_32 pairIdx=tableIdx; pairIdx<tableIdx+distance; pairIdx++){
        VAR_TYPE_32 leftIdx = pairIdx;
        VAR_TYPE_32 rightIdx = pairIdx+distance;

        WORD left = inVec[leftIdx];
        WORD right = inVec[rightIdx];

        inVec[leftIdx] = left;
        inVec[rightIdx] = right;

        tfIdx += tableStep;
      }
    }
  }
}


// /********************************************************************************************
// * Polynomial rearrangements *
// ********************************************************************************************/

void reorganize_para_limbs_to_ports_poly(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){
  int num_of_data = ((N/V_TOTAL_DATA)*SEQ_BUG_PER_PARA_LIMB_POLY_PORT);

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
  int num_of_data = ((N/V_TOTAL_DATA)*SEQ_BUG_PER_PARA_LIMB_POLY_PORT);

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

void fwd_blockWiseDivideData(std::vector<WORD>& inVec, std::vector<WORD> (&outVec)[V_TOTAL_DATA]){
  for(int i=0; i<N; i++){
    outVec[i%V_TOTAL_DATA].push_back(inVec[i]);
  }
}

void fwd_blockWiseCombineData(std::vector<WORD> (&inVec)[V_TOTAL_DATA], std::vector<WORD>& outVec){

  std::vector<WORD> inputArr(2*V_BUG_SIZE);

  VAR_TYPE_32 lastSupportedStages = ( (logN%H_BUG_SIZE) == 0 ) ? (H_BUG_SIZE) : ( (logN%H_BUG_SIZE) ); 
  VAR_TYPE_32 numOfPairsCombinedForStages = (1<<lastSupportedStages)/2;
  VAR_TYPE_32 numOfIndivCombinations = V_BUG_SIZE/numOfPairsCombinedForStages;

  VAR_TYPE_32 pairDistance = N/(1<<lastSupportedStages);

  for(int i=0; i<N/V_TOTAL_DATA; i++){
    for(int j=0; j<BUG_CONCAT_FACTOR; j++){
      
      for(int k=0; k<2*V_BUG_SIZE; k++){
        inputArr[k] = inVec[j*2*V_BUG_SIZE+k][i];
      }

      for(int grp_id=0; grp_id<numOfIndivCombinations ; grp_id++){
        for(int pair_id=0; pair_id<numOfPairsCombinedForStages; pair_id++){
          int val_addr0 = i*BUG_CONCAT_FACTOR*numOfIndivCombinations + \
                          j + \
                          grp_id*BUG_CONCAT_FACTOR + \
                          pair_id*pairDistance*2;
          int val_addr1 = val_addr0 + pairDistance;

          outVec[val_addr0] = inputArr[grp_id*numOfPairsCombinedForStages*2 + 2*pair_id];
          outVec[val_addr1] = inputArr[grp_id*numOfPairsCombinedForStages*2 + 2*pair_id + 1];
          
        }
      }

    }
  }
}

void fwd_reorganize_in_poly_per_para_limb(std::vector<WORD>& inVec, std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[POLY_LS_PORTS_PER_PARA_LIMB]){
  std::vector<WORD> blockInData[V_TOTAL_DATA];
  fwd_blockWiseDivideData(inVec, blockInData);

  for(int i=0; i<POLY_LS_PORTS_PER_PARA_LIMB; i++){
    for(int j=0; j<(SEQ_BUG_PER_PARA_LIMB_POLY_PORT); j++){
      for(int k=0; k<N/V_TOTAL_DATA; k++){
        POLY_WIDE_DATA_PER_PARA_LIMB val = 0;
        for(int l=BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1; l>=0; l--){
          for(int m=(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA)-1; m>=0; m--){
            int blockIdx = ( ( i * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT) + j ) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + l ) * (POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + m;
            val <<= DRAM_WORD_SIZE;
            val |= ((POLY_WIDE_DATA_PER_PARA_LIMB)blockInData[blockIdx][k]);
          }
        }
        outVec[i].push_back(val);
      }
    }
  }
}

void fwd_reorganize_out_poly_per_para_limb(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[POLY_LS_PORTS_PER_PARA_LIMB], std::vector<WORD>& outVec){
  std::vector<WORD> blockOutData[V_TOTAL_DATA];

  for(int i=0; i<POLY_LS_PORTS_PER_PARA_LIMB; i++){
    for(int j=0; j<(SEQ_BUG_PER_PARA_LIMB_POLY_PORT); j++){
      for(int k=0; k<N/V_TOTAL_DATA; k++){
        POLY_WIDE_DATA_PER_PARA_LIMB val = inVec[i][j*N/V_TOTAL_DATA+k];
        for(int l=0; l<BUG_PER_PARA_LIMB_POLY_WIDE_DATA; l++){
          for(int m=0; m<(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA); m++){
            int blockIdx = ( ( i * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT) + j ) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + l ) * (POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + m;
            WORD smallData = val & ( (((POLY_WIDE_DATA_PER_PARA_LIMB)1) << WORD_SIZE) -1 );
            blockOutData[blockIdx].push_back(smallData);
            val = val >> DRAM_WORD_SIZE;
          }
        }
      }
    }
  }

  fwd_blockWiseCombineData(blockOutData, outVec);
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
    outVec[paraLimbCounter].resize(N);
    fwd_reorganize_out_poly_per_para_limb(limbWiseOutData[paraLimbCounter], outVec[paraLimbCounter]);
  }
}

void inv_blockWiseCombineData(std::vector<WORD> (&inVec)[V_TOTAL_DATA], std::vector<WORD>& outVec){

  for(int i=0; i<N/V_TOTAL_DATA; i++){
    for(int j=0; j<BUG_CONCAT_FACTOR; j++){
      for(int k=0; k<2*V_BUG_SIZE; k++){
        WORD val = inVec[j*2*V_BUG_SIZE+k][i];
        int val_addr = (i*BUG_CONCAT_FACTOR+j)*2*V_BUG_SIZE + k;
        outVec[val_addr] = val;
      }
    }
  }
}

void inv_blockWiseDivideData(std::vector<WORD>& inVec, std::vector<WORD> (&outVec)[V_TOTAL_DATA]){

  std::vector<WORD> inputArr(2*V_BUG_SIZE);

  VAR_TYPE_32 lastSupportedStages = ( (logN%H_BUG_SIZE) == 0 ) ? (H_BUG_SIZE) : ( (logN%H_BUG_SIZE) ); 
  VAR_TYPE_32 numOfPairsCombinedForStages = (1<<lastSupportedStages)/2;
  VAR_TYPE_32 numOfIndivCombinations = V_BUG_SIZE/numOfPairsCombinedForStages;

  VAR_TYPE_32 pairDistance = N/(1<<lastSupportedStages);

  for(int i=0; i<N/V_TOTAL_DATA; i++){
    for(int j=0; j<BUG_CONCAT_FACTOR; j++){
      
      for(int grp_id=0; grp_id<numOfIndivCombinations ; grp_id++){
        for(int pair_id=0; pair_id<numOfPairsCombinedForStages; pair_id++){
          int val_addr0 = i*BUG_CONCAT_FACTOR*numOfIndivCombinations + \
                          j + \
                          grp_id*BUG_CONCAT_FACTOR + \
                          pair_id*pairDistance*2;
          int val_addr1 = val_addr0 + pairDistance;

          inputArr[grp_id*numOfPairsCombinedForStages*2 + 2*pair_id] = inVec[val_addr0];
          inputArr[grp_id*numOfPairsCombinedForStages*2 + 2*pair_id + 1] = inVec[val_addr1];
        }
      }

      for(int k=0; k<2*V_BUG_SIZE; k++){
        outVec[j*2*V_BUG_SIZE+k].push_back(inputArr[k]);
      }

    }
  }
}

// This function is complete inverse of fwd_reorganize_out_poly_per_para_limb.
void inv_reorganize_in_poly_per_para_limb(std::vector<WORD>& inVec, std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[POLY_LS_PORTS_PER_PARA_LIMB]){
  std::vector<WORD> blockInData[V_TOTAL_DATA];

  inv_blockWiseDivideData(inVec, blockInData);

  //init outVec
  for(int i=0; i<POLY_LS_PORTS_PER_PARA_LIMB; i++){
    outVec[i].resize((N/V_TOTAL_DATA)*SEQ_BUG_PER_PARA_LIMB_POLY_PORT);
  }

  for(int i=0; i<POLY_LS_PORTS_PER_PARA_LIMB; i++){
    for(int j=0; j<(SEQ_BUG_PER_PARA_LIMB_POLY_PORT); j++){
      for(int k=0; k<N/V_TOTAL_DATA; k++){
        POLY_WIDE_DATA_PER_PARA_LIMB val = 0;
        for(int l=BUG_PER_PARA_LIMB_POLY_WIDE_DATA-1; l>=0; l--){
          for(int m=(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA)-1; m>=0; m--){
            val = val << DRAM_WORD_SIZE;
            int blockIdx = ( ( i * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT) + j ) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + l ) * (POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + m;
            WORD smallData = blockInData[blockIdx][k];
            val = val | ((POLY_WIDE_DATA_PER_PARA_LIMB)smallData);
          }
        }
        outVec[i][j*N/V_TOTAL_DATA+k] = val;
      }
    }
  }
}

void inv_reorganize_out_poly_per_para_limb(std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> (&inVec)[POLY_LS_PORTS_PER_PARA_LIMB], std::vector<WORD>& outVec){
  std::vector<WORD> blockOutData[V_TOTAL_DATA];

  for(int i=0; i<POLY_LS_PORTS_PER_PARA_LIMB; i++){
    for(int j=0; j<(SEQ_BUG_PER_PARA_LIMB_POLY_PORT); j++){
      for(int k=0; k<N/V_TOTAL_DATA; k++){
        POLY_WIDE_DATA_PER_PARA_LIMB val = inVec[i][j*N/V_TOTAL_DATA+k];
        for(int l=0; l<BUG_PER_PARA_LIMB_POLY_WIDE_DATA; l++){
          for(int m=0; m<(POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA); m++){
            int blockIdx = ( ( i * (SEQ_BUG_PER_PARA_LIMB_POLY_PORT) + j ) * BUG_PER_PARA_LIMB_POLY_WIDE_DATA + l ) * (POLY_CONCAT_FACTOR_PER_PARA_LIMB_PORT/BUG_PER_PARA_LIMB_POLY_WIDE_DATA) + m;
            WORD smallData = val & ( (((POLY_WIDE_DATA_PER_PARA_LIMB)1) << WORD_SIZE) -1 );
            blockOutData[blockIdx].push_back(smallData);
            val = val >> DRAM_WORD_SIZE;
          }
        }
      }
    }
  }

  inv_blockWiseCombineData(blockOutData, outVec);
}

void inv_reorganize_input_poly_to_ports(std::vector<WORD> (&inVec)[PARA_LIMBS], std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&outVec)[POLY_LS_PORTS]){
  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseInPolyData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];
  
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    inv_reorganize_in_poly_per_para_limb(inVec[paraLimbCounter], limbWiseInPolyData[paraLimbCounter]);
  }

  reorganize_para_limbs_to_ports_poly(limbWiseInPolyData, outVec);
}

void inv_reorganize_ports_to_output_poly(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS], std::vector<WORD> (&outVec)[PARA_LIMBS]){
  std::vector<POLY_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<POLY_WIDE_DATA_PER_PARA_LIMB>> limbWiseOutData[PARA_LIMBS][POLY_LS_PORTS_PER_PARA_LIMB];
  reorganize_ports_to_para_limbs_poly(inVec, limbWiseOutData);

  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    outVec[paraLimbCounter].resize(N);
    inv_reorganize_out_poly_per_para_limb(limbWiseOutData[paraLimbCounter], outVec[paraLimbCounter]);
  }
}

/* This function is to initialize output DRAM ports to 0 */
void init_kernerl_output_ports(std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> (&inVec)[POLY_LS_PORTS]){
  for(int i=0; i<(N/V_TOTAL_DATA)*SEQ_BUG_PER_PARA_LIMB_POLY_PORT; i++){
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

  for(int port_counter=0; port_counter<TF_PORTS; port_counter++){
    //init
    int target_per_limb_port_start = port_counter*PARA_LIMB_PORTS_PER_TF_PORT;
    int target_limb_idx = target_per_limb_port_start/TF_PORTS_PER_PARA_LIMB;
    int target_limb_port_idx = target_per_limb_port_start%TF_PORTS_PER_PARA_LIMB;

    int num_of_data = inVec[target_limb_idx][target_limb_port_idx].size();
    outVec[port_counter].resize(num_of_data);

    //assign
    for(int data_counter=0; data_counter<num_of_data; data_counter++){
      TF_WIDE_DATA val = 0;
      for(int per_limb_port_counter=PARA_LIMB_PORTS_PER_TF_PORT-1; per_limb_port_counter>=0; per_limb_port_counter--){
        int total_per_limb_ports = port_counter*PARA_LIMB_PORTS_PER_TF_PORT + per_limb_port_counter;
        int limb_idx = total_per_limb_ports/TF_PORTS_PER_PARA_LIMB;
        int limb_port_idx = total_per_limb_ports%TF_PORTS_PER_PARA_LIMB;

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
      outVec[port_counter][data_counter] = val;
    }
  }
}

void fwd_organizeTFData(std::vector<WORD>& inVec, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[TF_PORTS_PER_PARA_LIMB]){
  //number of TF tasks = vertical BUs/2
  std::vector<WORD> layerWiseTFBuf[H_BUG_SIZE][V_BUG_SIZE/2 * BUG_CONCAT_FACTOR];

  std::vector<int> layerWiseTFBufDepth(H_BUG_SIZE);
  for(int layer=0; layer<H_BUG_SIZE; layer++){
    layerWiseTFBufDepth[layer] = 0;
  }

  //select TFs going into each TFBuf in each layer
  for(int stage=0; stage<logN; stage++){

    //total TFs
    int num_tfs_in_this_stage = 1 << stage;
    int tf_stride_in_this_stage = (N/2)/num_tfs_in_this_stage; //distance between two TF values

    //check partial BUG
    int dataFlowIter = stage/H_BUG_SIZE;
    int numberOfSupportedStages = ( logN-(dataFlowIter*H_BUG_SIZE) > H_BUG_SIZE ) ? (H_BUG_SIZE) : ( logN-(dataFlowIter*H_BUG_SIZE) );
    int tf_grp_size_BUG = 1 << (numberOfSupportedStages-1); //to support remaining layers, how many poly. values are grouped together is (1 << (num_partial_layers)). Since 2 poly val. need 1 TF, this is the eqn for TFs
    int num_tf_grps_per_BUG = V_BUG_SIZE/tf_grp_size_BUG;

    //layer specific dist
    int layer_id = stage % H_BUG_SIZE;
    int per_BUG_diff_num_data = (1 << layer_id); //how many unique TF values are passed from this layer
    int per_BUG_diff_data_dist = ( (N/2)/per_BUG_diff_num_data );

    //per buffer if two unique values are going or not
    //only first layer share values among 2 consec BUs. All the remaining layers always have two different values accessed by the consecutive BUs
    //That does not happen only when partial grp size is 1. i.e., every BU is a partial BU.
    int num_val_accessed_by_consec_BUs;
    if( ( layer_id == 0 ) && ( tf_grp_size_BUG !=1 ) ){ 
      num_val_accessed_by_consec_BUs = 1;
    }
    else{
      num_val_accessed_by_consec_BUs = 2;
    }

    //As # BUGs increases, TFs can be spread accross different buffers. this determines that
    //if total number of TFs only fit into one BUG, duplicates among BUGs. 
    //Else, if number of TFs are larger than a single BUG, hence spread accross BUGs
    //In that case, if number of TFs are less than total number of BUGs, that means, TFs are only spread accross (num of TFs amount/per BUG) of BUGs
    //If number of TFs are more than total number of BUGs, that means, TFs are spread accross BUG_CONCAT_FACTOR
    int BUG_concat_dist_factor = ( num_tfs_in_this_stage <= V_BUG_SIZE ) ? ( 1 ) : ( ( (num_tfs_in_this_stage/per_BUG_diff_num_data) <= BUG_CONCAT_FACTOR ) ? ( num_tfs_in_this_stage/per_BUG_diff_num_data ) : ( BUG_CONCAT_FACTOR ) ); 

    //number of unique tf values going per single iteration
    int unique_tf_per_iter = per_BUG_diff_num_data * num_tf_grps_per_BUG * BUG_concat_dist_factor;

    //Number of total TFs going into a buffer
    //Eqn is: per "num_val_accessed_by_consec_BUs" depth "unique_tf_per_iter" values were stored. Then how much depth for "num_tfs_in_this_stage"
    int num_tfs_per_buf = num_tfs_in_this_stage / ( unique_tf_per_iter/num_val_accessed_by_consec_BUs );
    layerWiseTFBufDepth[layer_id] += num_tfs_per_buf;

    int partial_dist_factor = num_tf_grps_per_BUG;

    for(int BUG_id=0; BUG_id<BUG_CONCAT_FACTOR; BUG_id++){
      for(int buf_id=0; buf_id<V_BUG_SIZE/2; buf_id++){
        
        //intra partial BUG handling
        int tf_grp_idx = (int)( ( buf_id * 1.0 ) / ( ( 1.0 * tf_grp_size_BUG ) / 2 ) );
        int intra_buf_idx = (int)( buf_id % ( (tf_grp_size_BUG+1) / 2 ) ); //ceil division

        //start index of each buffer
        int start_idx = ( ( ( tf_grp_idx * BUG_CONCAT_FACTOR ) + (BUG_id % BUG_concat_dist_factor ) ) * tf_stride_in_this_stage ) + \
                        ( intra_buf_idx * per_BUG_diff_data_dist * 2 ) % (N/2);

        
        for(int tf_count=0; tf_count<num_tfs_per_buf; tf_count++){
          int tf_idx;
          //In the case of partial group only supporting the first layer, it has to store the consec BU TF values far apart to match with the
          //other TFBuf modules(supporting other layers). Also the stride is not consistant in this case.
          //It is like: 0, 2, 32, 34, 64, 66, 96, 98,... So we store 0, 32, 64, 96, ..., 2, 34, 66, 98, ...
          if( num_tf_grps_per_BUG > (V_BUG_SIZE/2) ){ //Hmmm...think if you can make this bit generic
            tf_idx = start_idx + (tf_stride_in_this_stage*BUG_concat_dist_factor)*(tf_count/((num_tfs_per_buf)/2)) + (tf_count % ((num_tfs_per_buf)/2)) * tf_stride_in_this_stage * BUG_concat_dist_factor * partial_dist_factor;
          }
          else{
            tf_idx = start_idx + tf_count*tf_stride_in_this_stage*BUG_concat_dist_factor*partial_dist_factor;
          }
          
          int write_buf = BUG_id*(V_BUG_SIZE/2) + buf_id;
          WORD tfVal = inVec[tf_idx];
          layerWiseTFBuf[layer_id][write_buf].push_back(tfVal);
        }
      }
    }

  }

  //make each depth even as two values going to be packed together
  for(int layer=0; layer<H_BUG_SIZE; layer++){
    if( layerWiseTFBufDepth[layer]%2==1 ){//odd
      layerWiseTFBufDepth[layer]+=1;
      for(int buf_id=0; buf_id<V_BUG_SIZE/2 * BUG_CONCAT_FACTOR; buf_id++){
        layerWiseTFBuf[layer][buf_id].push_back(0);
      }
    }
  }
  
  printf("Layerwise TF depths:\n");
  for(int layer=0; layer<H_BUG_SIZE; layer++){
    printf("layer=%d, depth=%d\n", layer, layerWiseTFBufDepth[layer]);
  }
  printf("\n");

  //coelesce data
  if( (V_BUG_SIZE/2)*BUG_CONCAT_FACTOR > TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT*TF_PORTS_PER_PARA_LIMB ){
    printf("[ERROR][fwd_organizeTFData]:: Not enoght TF ports! Total vertical buffers=%d, Combine factor=%d\n", (int)(V_BUG_SIZE/2)*BUG_CONCAT_FACTOR, (int)TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT*TF_PORTS_PER_PARA_LIMB );
  }

  int cummulative_sum_of_assigned_layers = 0;
  
  //When there is a horizontal split(s) between BUG for TF loading, a balance (in terms of #TFs) between segments is required.
  int layers_per_seg[TF_LOAD_H_SEGS_PER_PARA_LIMB] = {3};
  bool load_direction_per_seg[TF_LOAD_H_SEGS_PER_PARA_LIMB] = {true};

  for(int h_seg_id=0; h_seg_id<TF_LOAD_H_SEGS_PER_PARA_LIMB; h_seg_id++){
    int num_layers = layers_per_seg[h_seg_id]; //remaining layers/remaining segments
    printf("Layers in seg id %d:\n", h_seg_id);

    if(load_direction_per_seg[h_seg_id]){
      for(int layer_id=cummulative_sum_of_assigned_layers; layer_id<(cummulative_sum_of_assigned_layers+num_layers); layer_id++){
        printf("\t%d\n", layer_id);
        for(int tf_count=0; tf_count<layerWiseTFBufDepth[layer_id]/2; tf_count++){ //two values packed together
          for(int v_seg_id=0; v_seg_id<TF_LOAD_V_SEGS_PER_PARA_LIMB; v_seg_id++){
            
            int tf_port_id = h_seg_id * TF_LOAD_V_SEGS_PER_PARA_LIMB + v_seg_id;

            TF_WIDE_DATA_PER_PARA_LIMB val = 0;

            for(int comb_id=TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2-1; comb_id>=0; comb_id--){
              val = val << (DRAM_WORD_SIZE*2);
              int buf_id = v_seg_id*(TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2)+comb_id;
              WORD smallVal_0 = layerWiseTFBuf[layer_id][buf_id][2*tf_count];
              WORD smallVal_1 = layerWiseTFBuf[layer_id][buf_id][2*tf_count+1];
              val = val | ( ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_1 ) << WORD_SIZE ) | ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_0 );
            }
            outVec[tf_port_id].push_back(val);
          }
        }
      }
    }
    else{
      for(int layer_id=(cummulative_sum_of_assigned_layers+num_layers-1); layer_id>=(cummulative_sum_of_assigned_layers); layer_id--){
        printf("\t%d\n", layer_id);
        for(int tf_count=0; tf_count<layerWiseTFBufDepth[layer_id]/2; tf_count++){ //two values packed together
          for(int v_seg_id=0; v_seg_id<TF_LOAD_V_SEGS_PER_PARA_LIMB; v_seg_id++){
            
            int tf_port_id = h_seg_id * TF_LOAD_V_SEGS_PER_PARA_LIMB + v_seg_id;

            TF_WIDE_DATA_PER_PARA_LIMB val = 0;

            for(int comb_id=TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2-1; comb_id>=0; comb_id--){
              val = val << (DRAM_WORD_SIZE*2);
              int buf_id = v_seg_id*(TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2)+comb_id;
              WORD smallVal_0 = layerWiseTFBuf[layer_id][buf_id][2*tf_count];
              WORD smallVal_1 = layerWiseTFBuf[layer_id][buf_id][2*tf_count+1];
              val = val | ( ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_1 ) << WORD_SIZE ) | ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_0 );
            }
            outVec[tf_port_id].push_back(val);
          }
        }
      }
    }
    cummulative_sum_of_assigned_layers+=num_layers;
  }
}

void inv_organizeTFData(std::vector<WORD>& inVec, std::vector<TF_WIDE_DATA_PER_PARA_LIMB, tapa::aligned_allocator<TF_WIDE_DATA_PER_PARA_LIMB>> (&outVec)[TF_PORTS_PER_PARA_LIMB]){
  //number of TF tasks = vertical BUs/2
  std::vector<WORD> layerWiseTFBuf[H_BUG_SIZE][V_BUG_SIZE/2 * BUG_CONCAT_FACTOR];

  std::vector<int> layerWiseTFBufDepth(H_BUG_SIZE);
  for(int layer=0; layer<H_BUG_SIZE; layer++){
    layerWiseTFBufDepth[layer] = 0;
  }

  //select TFs going into each TFBuf in each layer
  for(int stage=0; stage<logN; stage++){
    
    //total TFs
    int num_tfs_in_this_stage = 1 << stage;
    int tf_change_freq = (N/2)/num_tfs_in_this_stage; //distance between two TF values

    //check partial BUG
    int dataFlowIter = (logN - 1 - stage)/H_BUG_SIZE;
    int numberOfSupportedStages = ( logN-(dataFlowIter*H_BUG_SIZE) > H_BUG_SIZE ) ? (H_BUG_SIZE) : ( logN-(dataFlowIter*H_BUG_SIZE) );
    int tf_grp_size_BUG = 1 << (numberOfSupportedStages-1); //to support remaining layers, how many poly. values are grouped together is (1 << (num_partial_layers)). Since 2 poly val. need 1 TF, this is the eqn for TFs
    int num_tf_grps_per_BUG = V_BUG_SIZE/tf_grp_size_BUG;

    //layer specific dist
    int layer_id = (logN - stage - 1) % H_BUG_SIZE;
    int per_BUG_diff_num_data = ( 1 << ( (H_BUG_SIZE - 1) - layer_id ) ); //how many unique TF values are passed from this layer
    // int per_BUG_idx_change_freq = ( (V_BUG_SIZE)/per_BUG_diff_num_data );
    int BUG_buf_val_change_freq = (( (V_BUG_SIZE)/per_BUG_diff_num_data ) + 1)/2;

    //per buffer if two unique values are going or not
    //only first layer need 2 value access for 2 consec BUs. All the remaining layers always share the same value by the consecutive BUs
    //That does not happen only when partial grp size is 1. i.e., every BU is a partial BU. In that case, it has to be 1st stage of NTT and that has only one value.
    int num_val_accessed_by_consec_BUs;
    if( ( layer_id == 0 ) && ( tf_grp_size_BUG !=1 ) ){
      num_val_accessed_by_consec_BUs = 2;
    }
    else{
      num_val_accessed_by_consec_BUs = 1;
    }

    //As # BUGs increases, TFs can be spread accross different buffers. this determines that
    //if TF change frequency is more than one BUG, that means same TF(s) is being used accross multiple BUG. i.e., duplicating
    //Else, if TF change freq is smaller than a single BUG, that means different TFs are send in different BUGs
    int BUG_concat_dist_factor = ( tf_change_freq > V_BUG_SIZE ) ? ( ( ( (BUG_CONCAT_FACTOR*V_BUG_SIZE)/(tf_change_freq*per_BUG_diff_num_data) ) > 0 ) ? ( (BUG_CONCAT_FACTOR*V_BUG_SIZE)/(tf_change_freq*per_BUG_diff_num_data) ) : (1) ) : ( BUG_CONCAT_FACTOR );

    //number of unique tf values going per single iteration
    int unique_tf_per_iter = (per_BUG_diff_num_data/num_tf_grps_per_BUG) * BUG_concat_dist_factor;

    //Number of total TFs going into a buffer
    //Eqn is: per "num_val_accessed_by_consec_BUs" depth "unique_tf_per_iter" values were stored. Then how much depth for "num_tfs_in_this_stage"
    int num_tfs_per_buf = num_tfs_in_this_stage / ( unique_tf_per_iter/num_val_accessed_by_consec_BUs );
    layerWiseTFBufDepth[layer_id] += num_tfs_per_buf;
    
    //Because of partial groups, multiple TF groups can be stored in the same BUG. this variable determines that
    int partial_dist_factor = num_tf_grps_per_BUG;

    for(int BUG_id=0; BUG_id<BUG_CONCAT_FACTOR; BUG_id++){
      for(int buf_id=0; buf_id<V_BUG_SIZE/2; buf_id++){
        
        //start index of each buffer
        int start_idx = ( ( BUG_id / (BUG_CONCAT_FACTOR/BUG_concat_dist_factor) ) * per_BUG_diff_num_data * partial_dist_factor ) + \
                        ( ( (buf_id % ((tf_grp_size_BUG+1)/2)) / BUG_buf_val_change_freq ) * num_val_accessed_by_consec_BUs );

        for(int tf_count=0; tf_count<num_tfs_per_buf; tf_count++){

          int tf_idx = start_idx + (tf_count/num_val_accessed_by_consec_BUs) * per_BUG_diff_num_data * BUG_concat_dist_factor + (tf_count % num_val_accessed_by_consec_BUs);
          int write_buf = BUG_id*(V_BUG_SIZE/2) + buf_id;
          WORD tfVal = inVec[tf_idx];
          layerWiseTFBuf[layer_id][write_buf].push_back(tfVal);
        }
      }
    }

  }

  //make each depth even as two values going to be packed together
  for(int layer=0; layer<H_BUG_SIZE; layer++){
    if( layerWiseTFBufDepth[layer]%2==1 ){ //odd
      layerWiseTFBufDepth[layer]+=1;
      for(int buf_id=0; buf_id<V_BUG_SIZE/2 * BUG_CONCAT_FACTOR; buf_id++){
        layerWiseTFBuf[layer][buf_id].push_back(0);
      }
    }
  }
  
  printf("Layerwise TF depths:\n");
  for(int layer=0; layer<H_BUG_SIZE; layer++){
    printf("layer=%d, depth=%d\n", layer, layerWiseTFBufDepth[layer]);
  }
  printf("\n");

  //coelesce data
  if( (V_BUG_SIZE/2)*BUG_CONCAT_FACTOR > TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT*TF_PORTS_PER_PARA_LIMB ){ // a self check
    printf("[ERROR][inv_organizeTFData]:: Not enoght TF ports! Total vertical buffers=%d, Combine factor=%d\n", (int)(V_BUG_SIZE/2)*BUG_CONCAT_FACTOR, (int)TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT*TF_PORTS_PER_PARA_LIMB );
    exit(1);
  }

  int cummulative_sum_of_assigned_layers = 0;

  //When there is a horizontal split(s) between BUG for TF loading, a balance (in terms of #TFs) between segments is required.
  int layers_per_seg[TF_LOAD_H_SEGS_PER_PARA_LIMB] = {3};
  bool load_direction_per_seg[TF_LOAD_H_SEGS_PER_PARA_LIMB] = {true};

  for(int h_seg_id=0; h_seg_id<TF_LOAD_H_SEGS_PER_PARA_LIMB; h_seg_id++){
    int num_layers = layers_per_seg[h_seg_id]; //remaining layers/remaining segments
    printf("Layers in seg id %d:\n", h_seg_id);

    if(load_direction_per_seg[h_seg_id]){
      for(int layer_id=cummulative_sum_of_assigned_layers; layer_id<(cummulative_sum_of_assigned_layers+num_layers); layer_id++){
        printf("\t%d\n", layer_id);
        for(int tf_count=0; tf_count<layerWiseTFBufDepth[layer_id]/2; tf_count++){
          for(int v_seg_id=0; v_seg_id<TF_LOAD_V_SEGS_PER_PARA_LIMB; v_seg_id++){
            
            int tf_port_id = h_seg_id * TF_LOAD_V_SEGS_PER_PARA_LIMB + v_seg_id;

            TF_WIDE_DATA_PER_PARA_LIMB val = 0;

            for(int comb_id=TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2-1; comb_id>=0; comb_id--){
              val = val << (DRAM_WORD_SIZE*2);
              int buf_id = v_seg_id*(TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2)+comb_id;
              WORD smallVal_0 = layerWiseTFBuf[layer_id][buf_id][2*tf_count];
              WORD smallVal_1 = layerWiseTFBuf[layer_id][buf_id][2*tf_count+1];
              val = val | ( ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_1 ) << WORD_SIZE ) | ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_0 );
            }
            outVec[tf_port_id].push_back(val);
          }
        }
      }
    }
    else{
      for(int layer_id=(cummulative_sum_of_assigned_layers+num_layers-1); layer_id>=(cummulative_sum_of_assigned_layers); layer_id--){
        printf("\t%d\n", layer_id);
        for(int tf_count=0; tf_count<layerWiseTFBufDepth[layer_id]/2; tf_count++){ //two values packed together
          for(int v_seg_id=0; v_seg_id<TF_LOAD_V_SEGS_PER_PARA_LIMB; v_seg_id++){
            
            int tf_port_id = h_seg_id * TF_LOAD_V_SEGS_PER_PARA_LIMB + v_seg_id;

            TF_WIDE_DATA_PER_PARA_LIMB val = 0;

            for(int comb_id=TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2-1; comb_id>=0; comb_id--){
              val = val << (DRAM_WORD_SIZE*2);
              int buf_id = v_seg_id*(TF_CONCAT_FACTOR_PER_PARA_LIMB_PORT/2)+comb_id;
              WORD smallVal_0 = layerWiseTFBuf[layer_id][buf_id][2*tf_count];
              WORD smallVal_1 = layerWiseTFBuf[layer_id][buf_id][2*tf_count+1];
              val = val | ( ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_1 ) << WORD_SIZE ) | ( (TF_WIDE_DATA_PER_PARA_LIMB)smallVal_0 );
            }
            outVec[tf_port_id].push_back(val);
          }
        }
      }
    }
    cummulative_sum_of_assigned_layers+=num_layers;
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
    CT_RToN_fwd_NTT(fwdVec_ref[paraLimbCounter], tfArr[paraLimbCounter], workingModulus, size);
  }
  printf("\nHost NTT computation completed\n");

  // INTT in host
  vector<WORD> invVec_ref[PARA_LIMBS];
  for(VAR_TYPE_32 paraLimbCounter=0; paraLimbCounter<PARA_LIMBS; paraLimbCounter++){
    invVec_ref[paraLimbCounter].resize(size);
    invVec_ref[paraLimbCounter] = fwdVec_ref[paraLimbCounter];
    CT_NToR_INTT(invVec_ref[paraLimbCounter], inv_tfArr[paraLimbCounter], workingModulus_arr[paraLimbCounter], size);
    bitReverseVect(invVec_ref[paraLimbCounter], size);
    bool check_status = compareResults(invec[paraLimbCounter], invVec_ref[paraLimbCounter], size);
    if(check_status){
      printf("[Para limb %d]::Inverse Test Execution Passed\n", (int)paraLimbCounter);
    }
    else{
      printf("[Para limb %d]::Inverse Test Execution Failed\n", (int)paraLimbCounter);
      exit (1);
    }
  }
  printf("Host INTT computation completed\n\n");

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
  std::vector<POLY_WIDE_DATA, tapa::aligned_allocator<POLY_WIDE_DATA>> inv_portWiseInPolyData[POLY_LS_PORTS];
  inv_reorganize_input_poly_to_ports(fwdVec_ref, inv_portWiseInPolyData);

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
      tapa::read_write_mmap<POLY_WIDE_DATA>(inv_portWiseInPolyData[0]),
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

