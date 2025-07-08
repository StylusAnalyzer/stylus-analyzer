// Example contract that demonstrates locked Ether vulnerability
// This contract can receive Ether but has no way to withdraw it

#![cfg_attr(not(feature = "export-abi"), no_main)]
extern crate alloc;

use stylus_sdk::{alloy_primitives::U256, evm, msg, prelude::*};

#[storage]
#[entrypoint]
pub struct LockedEtherContract {
    balance: U256,
    owner: Address,
}

#[public]
impl LockedEtherContract {
    // Constructor
    pub fn new() -> Self {
        Self {
            balance: U256::ZERO,
            owner: msg::sender(),
        }
    }

    // Function that accepts Ether - VULNERABLE: payable but no withdrawal
    #[payable]
    pub fn deposit(&mut self) -> Result<(), Vec<u8>> {
        let value = evm::msg_value();
        self.balance += value;
        Ok(())
    }

    // Another function that accepts Ether using msg_value() check
    pub fn receive_payment(&mut self, amount: U256) -> Result<(), Vec<u8>> {
        let sent_value = evm::msg_value();
        if sent_value < amount {
            return Err("Insufficient payment".as_bytes().to_vec());
        }
        
        self.balance += sent_value;
        Ok(())
    }

    // Read-only functions
    pub fn get_balance(&self) -> U256 {
        self.balance
    }

    pub fn get_owner(&self) -> Address {
        self.owner
    }

    // This function checks contract's Ether balance but doesn't withdraw
    pub fn check_contract_balance(&self) -> U256 {
        evm::balance(evm::contract_address())
    }


    pub fn withdraw(&self) -> Result<(), Vec<u8>> {
        let balance = evm::balance(evm::contract_address());
        // evm::transfer_eth(self.owner, balance);
        Ok(())
    }

    // // Function that looks like it might withdraw but doesn't actually transfer Ether
    pub fn withdraw(&mut self, amount: U256) -> Result<(), Vec<u8>> {
        if amount > self.balance {
            return Err("Insufficient balance".as_bytes().to_vec());
        }
        
        // This only updates internal state but doesn't actually transfer Ether!
        self.balance -= amount;
        Ok(())
    }
}

// Note: This contract is vulnerable because:
// 1. It has #[payable] functions that accept Ether
// 2. It uses evm::msg_value() to receive Ether
// 3. It has NO functions that actually transfer Ether out of the contract
// 4. Any Ether sent to this contract becomes permanently locked 
