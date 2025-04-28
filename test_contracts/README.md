# Simple Token Contract

This is a basic ERC-20 like token implementation for the Stylus framework. The contract allows for:

- Token transfers between addresses
- Delegation of spending through approvals
- Minting new tokens
- Burning existing tokens

## Features

- **Name**: Simple Token
- **Symbol**: STK
- **Decimals**: 18
- **Initial Supply**: 1,000 tokens

## Contract Functions

- `transfer(address to, uint256 value)`: Transfer tokens from sender to recipient
- `approve(address spender, uint256 value)`: Approve spender to use tokens on behalf of the sender
- `transferFrom(address from, address to, uint256 value)`: Transfer tokens on behalf of another address
- `mint(address to, uint256 value)`: Create new tokens and assign to an address
- `burn(address from, uint256 value)`: Destroy tokens from an address

## Purpose

This token contract is designed for demonstration purposes. It is not audited and should not be used in production without a thorough security review.

## Technical Notes

The contract is implemented using the Stylus SDK, which allows Rust to target the Arbitrum Stylus platform. 
