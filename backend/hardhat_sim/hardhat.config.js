require("@nomicfoundation/hardhat-ethers");

// Reads the RPC from the env var injected by Python.
// Default: Moonbase Alpha.  Swap CHAIN_RPC env to point at Westend Hub for submission.
const CHAIN_RPC =
  process.env.CHAIN_RPC || "https://rpc.api.moonbase.moonbeam.network";

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.24",   // required by Hardhat even when we have no .sol files
  networks: {
    hardhat: {
      forking: {
        url: CHAIN_RPC,
        // blockNumber omitted → always forks from the latest block
      },
      mining: {
        auto: true,
        interval: 0,
      },
      // Give impersonated accounts a clean gas environment
      blockGasLimit: 30_000_000,
    },
  },
};