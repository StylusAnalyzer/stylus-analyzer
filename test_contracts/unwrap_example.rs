#![cfg_attr(not(feature = "export-abi"), no_main)]
#![feature(allocator_api)]

extern crate alloc;

use stylus_sdk::{
    alloy_primitives::{Address, U256},
    alloy_sol_types::sol,
    evm, msg,
    prelude::*,
    alloc::string::String,
};

// Contract showing unsafe use of unwrap() in a Stylus Rust contract
#[public]
struct UnwrapExamples {
    // State variables
    owner: Storage<Address>,
    balance: Storage<U256>,
    last_caller: Storage<Address>,
}

#[external]
impl UnwrapExamples {
    // Initialize the contract
    pub fn constructor(initial_balance: U256) -> Self {
        let mut instance = Self {
            owner: Storage::new(),
            balance: Storage::new(),
            last_caller: Storage::new(),
        };
        
        instance.owner.initialize(msg::sender());
        instance.balance.initialize(initial_balance);
        instance.last_caller.initialize(Address::ZERO);
        
        instance
    }
    
    // VULNERABILITY 1: Unsafe unwrap of Option in a public function
    pub fn get_value_at_index(&self, values: Vec<U256>, index: U256) -> Result<U256, Vec<u8>> {
        let idx = index.try_as_usize().unwrap(); // This can panic if index doesn't fit in usize
        let value = values.get(idx).copied().unwrap_or_default(); // This is safer with unwrap_or_default
        
        Ok(value)
    }
    
    // VULNERABILITY 2: Using unwrap on a Result from a fallible operation
    pub fn unsafe_div(&mut self, a: U256, b: U256) -> Result<U256, Vec<u8>> {
        // This will panic if b is zero
        let result = a.checked_div(b).unwrap();
        
        // Store result as the new balance
        self.balance.set(result);
        
        Ok(result)
    }
    
    // Safe version using proper error handling
    pub fn safe_div(&mut self, a: U256, b: U256) -> Result<U256, Vec<u8>> {
        // Properly handle the case where b is zero
        match a.checked_div(b) {
            Some(result) => {
                self.balance.set(result);
                Ok(result)
            },
            None => Err("Division by zero".into())
        }
    }
    
    // VULNERABILITY 3: Using unwrap inside a complex operation
    pub fn process_addresses(&mut self, addresses: Vec<Address>) -> Result<Address, Vec<u8>> {
        // This assumes addresses is non-empty, will panic otherwise
        let first_address = addresses.first().unwrap();
        let last_address = addresses.last().unwrap();
        
        // Store the last address
        self.last_caller.set(*last_address);
        
        Ok(*first_address)
    }
    
    // Safe version using pattern matching
    pub fn safe_process_addresses(&mut self, addresses: Vec<Address>) -> Result<Address, Vec<u8>> {
        if addresses.is_empty() {
            return Err("No addresses provided".into());
        }
        
        let first_address = addresses[0]; // Safe because we checked if empty
        let last_address = addresses[addresses.len() - 1];
        
        self.last_caller.set(last_address);
        
        Ok(first_address)
    }
    
    // VULNERABILITY 4: Using unwrap in a string conversion
    pub fn to_hex_string(&self, value: U256) -> Result<String, Vec<u8>> {
        // This can panic if the string conversion fails
        let hex_string = format!("0x{:x}", value).parse().unwrap();
        
        Ok(hex_string)
    }
}

// Entry point
#[cfg(not(feature = "export-abi"))]
#[alloc_error_handler]
fn alloc_error(_: core::alloc::Layout) -> ! {
    evm::revert(b"alloc error")
}

#[no_mangle]
extern "C" fn deploy() {
    let initial_balance = U256::from(1000);
    let contract = UnwrapExamples::constructor(initial_balance);
    evm::deploy(contract);
}

#[no_mangle]
extern "C" fn main() {
    evm::dispatch(UnwrapExamples::dispatcher());
} 
