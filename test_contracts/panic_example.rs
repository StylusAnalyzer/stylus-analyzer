#![cfg_attr(not(feature = "export-abi"), no_main)]

extern crate alloc;

use stylus_sdk::{
    alloy_primitives::{Address, U256},
    evm, msg,
    prelude::*,
};

#[public]
impl PanicExample {
    // Example 1: Direct use of panic!() macro
    pub fn unsafe_direct_panic(&self) -> Result<(), Vec<u8>> {
        let condition = true;
        if condition {
            panic!("This will cause immediate termination");
        }
        Ok(())
    }

    // Example 2: Using panic!() with formatting
    pub fn unsafe_formatted_panic(&self, value: U256) -> Result<(), Vec<u8>> {
        if value == U256::ZERO {
            panic!("Invalid value: {}", value);
        }
        Ok(())
    }

    // Example 3: Safe alternative using Result type
    pub fn safe_error_handling(&self, value: U256) -> Result<(), Vec<u8>> {
        if value == U256::ZERO {
            return Err("Invalid value".into());
        }
        Ok(())
    }

    // Example 4: Safe alternative using Option and pattern matching
    pub fn safe_option_handling(&self, address: Address) -> Result<U256, Vec<u8>> {
        let balance = if address == Address::ZERO {
            None
        } else {
            Some(U256::from(100))
        };

        match balance {
            Some(value) => Ok(value),
            None => Err("Invalid address".into())
        }
    }
}

// Entry point
#[no_mangle]
extern "C" fn main() {
    let contract = PanicExample::dispatcher();
    evm::dispatch(contract);
} 
