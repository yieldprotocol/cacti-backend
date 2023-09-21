# Cacti Chatbot Usage Guide

## Introduction
* This guide showcases some example prompts to use from the UI to interact with the chatbot and perform Web3 actions across different protocols.
* The prompts cover wide range of Web3 use-cases such as ETH transfers, DeFi, NFTs and ENS.
* The prompts can be synthesized by looking at the [widget commands file](./knowledge_base/widgets.yaml)

## Example Prompts

### Wallet

* Send ETH amount to an address 
    - `Send 0.01 ETH to 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045`
* Check ETH balance 
    - `What is my ETH balance?`

### DeFI
* Get price of any token 
    - `What is the price of BTC?`

* Get top yields on any chain for any token 
    - `What are the top yields on Ethereum?`
    - `What are the top yields on Polygon?`
    - `What are the top USDC yields on Arbitrum?`

* Lending/Borrowing on Yield Protocol
    - `Lend 100 DAI using yield protocol`
    - `Close 100 DAI lend position on yield protocol`
    - `Borrow 2000 USDC using 3 ETH on yield protocol`
    - `Close my USDC yield protocol borrow position`

* Swap on Uniswap
    - `Swap 0.01 ETH for USDC`

### NFTs
* Search for NFTs in a collection by trait
    - Use sequence of prompts
        - `Load Pudgy Penguin NFTs`
        - `Show me NFTs with yellow background`

* Buy NFTs in a collection
    - Use sequence of prompts
        - `Load Pudgy Penguin NFTs`
        - `Show me NFTs for sale`
        - `Buy NFT #1234`

* View NFTs you own
    - `Show me my NFTs`

### ENS
* Register an ENS domain
    - `Register <ENS DOMAIN>` 

* Set ENS Primary Name
    - `Set <ENS DOMAIN> as ENS primary name`

* Set one of your NFTs as ENS avatar
    - Use sequence of prompts
        - `Set <ENS DOMAIN> as ENS primary name`
        - `Show me NFTs I own`
        - `Set NFT #1234 from Pudgy Penguin as my ENS avatar`


