#![cfg_attr(not(feature = "export-abi"), no_main)]

extern crate alloc;

use stylus_sdk::{
    alloy_primitives::{Address, U256},
    abi::Bytes,
    evm, msg,
    prelude::*,
};
use alloc::string::String;
use alloc::vec::Vec;
use alloy_sol_types::{sol_data::{Address as SOLAddress, String as SOLString, Bytes as SOLBytes, Uint}, SolType};
use sha3::{Digest, Keccak256};

#[storage]
#[entrypoint]
pub struct EncodePackedExample;

#[public]
impl EncodePackedExample {
    // UNSAFE: Collision risk because encode_packed("a", "bc") == encode_packed("ab", "c")
    pub fn unsafe_encode_packed_collision(&self) -> [u8; 32] {
        // First set of values that will collide
        let string1 = "a".to_string();
        let string2 = "bc".to_string();
        
        // Encode the first set
        let result1 = self.encode_packed_strings(string1, string2);
        
        // Second set of values that will collide
        let string3 = "ab".to_string();
        let string4 = "c".to_string();
        
        // Encode the second set
        let result2 = self.encode_packed_strings(string3, string4);
        
        // Hash the results - these will be identical!
        result1 
    }
    
    // Helper function to demonstrate encode_packed
    fn encode_packed_strings(&self, a: String, b: String) -> [u8; 32] {
        // This is the potentially dangerous encode_packed operation
        // Both ("a", "bc") and ("ab", "c") will result in the same packed value
        let packed_data = [a.as_bytes(), b.as_bytes()].concat();
        
        // Hash the packed data
        let mut hasher = Keccak256::new();
        hasher.update(&packed_data);
        let result = hasher.finalize();
        
        // Convert to fixed size array
        let mut output = [0u8; 32];
        output.copy_from_slice(&result);
        output
    }
    
    // UNSAFE: Using encode_packed with dynamically sized strings
    pub fn unsafe_encode_packed_with_dynamic_types(&self, a: String, b: String) -> Vec<u8> {
        type PackedType = (SOLString, SOLString);
        let values = (a, b);
        
        // This could lead to collisions if there's no delimiter between values
        PackedType::abi_encode_packed(&values)
    }
    
    // SAFE: Using regular encode to avoid collisions
    pub fn safe_encode(&self, a: String, b: String) -> Vec<u8> {
        type EncodeType = (SOLString, SOLString);
        let values = (a, b);
        
        // Safe because it adds padding for each value
        EncodeType::abi_encode_params(&values)
    }
    
    // SAFE: Using encode_packed but with fixed-size types
    pub fn safe_encode_packed_fixed_types(&self, addr: Address, amount: U256) -> Vec<u8> {
        type FixedPackedType = (SOLAddress, Uint<256>);
        let values = (addr, amount);
        
        // Less risk with fixed-size types
        FixedPackedType::abi_encode_packed(&values)
    }
    
    // SAFE: Using delimiters between dynamic types
    pub fn safe_encode_packed_with_delimiter(&self, a: String, b: String) -> Vec<u8> {
        // Add a delimiter (0 byte) between strings to avoid collisions
        let delimiter = [0u8];
        let packed_data = [a.as_bytes(), &delimiter, b.as_bytes()].concat();
        packed_data
    }
}

// Entry point
#[no_mangle]
extern "C" fn main() {
    let contract = EncodePackedExample::dispatcher();
    evm::dispatch(contract);
} 
