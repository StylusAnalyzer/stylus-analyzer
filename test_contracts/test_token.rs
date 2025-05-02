// #![cfg_attr(not(feature = "export-abi"), no_main)]
// #![feature(allocator_api)]

// extern crate alloc;

// use stylus_sdk::{
//     alloy_primitives::{Address, U256},
//     alloy_sol_types::sol,
//     evm, msg,
//     prelude::*,
// };

// sol! {
//     #[sol(name = "SimpleToken")]
//     contract SimpleToken {
//         // Event declarations
//         event Transfer(address indexed from, address indexed to, uint256 value);
//         event Approval(address indexed owner, address indexed spender, uint256 value);

//         // State variables
//         string public name;
//         string public symbol;
//         uint8 public decimals;
//         uint256 public totalSupply;
        
//         mapping(address => uint256) public balanceOf;
//         mapping(address => mapping(address => uint256)) public allowance;

//         // POTENTIAL BUG: Missing owner variable
//         // address public owner;

//         // Constructor
//         constructor(string memory _name, string memory _symbol, uint8 _decimals, uint256 _initialSupply) {
//             name = _name;
//             symbol = _symbol;
//             decimals = _decimals;
//             totalSupply = _initialSupply * 10 ** uint256(_decimals);    
//             balanceOf[msg.sender] = totalSupply;
            
//             emit Transfer(address(0), msg.sender, totalSupply);
//         }

//         // Transfer tokens from sender to recipient
//         function transfer(address to, uint256 value) public returns (bool) {
//             require(to != address(0), "Transfer to zero address");
            
//             // POTENTIAL BUG: No check for sufficient balance
//             // require(balanceOf[msg.sender] >= value, "Insufficient balance");
            
//             balanceOf[msg.sender] -= value;
//             balanceOf[to] += value;
            
//             emit Transfer(msg.sender, to, value);
            
//             return true;
//         }

        
//     }
// }

// // Entry point
// #[cfg(not(feature = "export-abi"))]
// #[alloc_error_handler]
// fn alloc_error(_: core::alloc::Layout) -> ! {
//     evm::revert(b"alloc error")
// }

// #[no_mangle]
// extern "C" fn deploy() {
//     let name = "Simple Token";
//     let symbol = "STK";
//     let decimals = 18;
//     let initial_supply = U256::from(1000);
    
//     let contract = SimpleToken::constructor(name, symbol, decimals, initial_supply);
//     evm::deploy(contract);
// }

// #[no_mangle]
// extern "C" fn main() {
//     let contract = SimpleToken::dispatcher();
//     evm::dispatch(contract);
// } 
