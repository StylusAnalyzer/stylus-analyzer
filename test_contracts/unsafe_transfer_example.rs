#![cfg_attr(not(feature = "export-abi"), no_main)]
#![feature(allocator_api)]

extern crate alloc;

use stylus_sdk::{
    alloy_primitives::{Address, U256},
    alloy_sol_types::sol,
    evm, msg,
    prelude::*,
    call::Call,
};

// Define interface for ERC20 tokens
sol_interface! {
    interface IERC20 {
        function transfer(address to, uint256 value) external returns (bool);
        function transferFrom(address from, address to, uint256 value) external returns (bool);
        function balanceOf(address account) external view returns (uint256);
        function approve(address spender, uint256 amount) external returns (bool);
    }
}

sol! {
    #[sol(name = "UncheckedCalls")]
    contract UncheckedCalls {
        // State variables
        address public owner;
        
        // Constructor
        constructor() {
            owner = msg.sender;
        }
        
        // Modifier
        modifier onlyOwner() {
            require(msg.sender == owner, "Not owner");
            _;
        }
        
        // VULNERABILITY 1: Unchecked external ERC20 transfer
        // This function doesn't check the return value of the transfer call
        function unsafeTransferERC20(address token, address to, uint256 amount) public {
            // Low-level call without checking return value
            token.call(abi.encodeWithSignature("transfer(address,uint256)", to, amount));
            
            // The transfer might have failed silently
        }
        
        // Safe version that checks the return value
        function safeTransferERC20(address token, address to, uint256 amount) public {
            // Make call and check return value
            (bool success, bytes memory returnData) = token.call(abi.encodeWithSignature("transfer(address,uint256)", to, amount));
            require(success && (returnData.length == 0 || abi.decode(returnData, (bool))), "ERC20 transfer failed");
        }
        
        // VULNERABILITY 2: Another type of unchecked transfer with transferFrom
        function unsafeTransferFromERC20(address token, address from, address to, uint256 amount) public {
            token.call(abi.encodeWithSignature("transferFrom(address,address,uint256)", from, to, amount));
            // Again, no return value check
        }
        
        // Receive function to handle ETH transfers
        receive() external payable {}
        
        // Fallback function
        fallback() external payable {}
    }
}

// Implementation using the Stylus SDK interface approach
#[public]
impl UncheckedCalls {
    // VULNERABILITY 3: Unchecked transfer using the SDK interface
    pub fn unsafe_transfer_via_interface(&mut self, token: IERC20, to: Address, amount: U256) -> Result<(), Vec<u8>> {
        // Call the transfer method but ignore its boolean return value
        let _ = token.transfer(self, to, amount);
        
        // Did not check if transfer succeeded
        Ok(())
    }
    
    // Safe version using the interface approach
    pub fn safe_transfer_via_interface(&mut self, token: IERC20, to: Address, amount: U256) -> Result<(), Vec<u8>> {
        // Call the transfer method and check its return value
        let success = token.transfer(self, to, amount)?;
        if !success {
            return Err("ERC20 transfer failed".into());
        }
        
        Ok(())
    }
    
    // VULNERABILITY 4: Unexpected revert handling
    pub fn transfer_with_ignored_error(&mut self, token: IERC20, to: Address, amount: U256) -> Result<(), Vec<u8>> {
        // Try to perform the transfer, but ignore any errors
        match token.transfer(self, to, amount) {
            Ok(_) => {} // Don't check the boolean result
            Err(_) => {} // Ignore any errors
        }
        
        // Continue execution even if transfer failed
        Ok(())
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
    let contract = UncheckedCalls::constructor();
    evm::deploy(contract);
}

#[no_mangle]
extern "C" fn main() {
    let contract = UncheckedCalls::dispatcher();
    evm::dispatch(contract);
} 
