// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TruthRegistry
 * @dev On-chain reputation registry for AEGIS AI Guardian.
 */
contract TruthRegistry {
    enum Status { Unknown, Safe, Malicious }
    
    mapping(address => Status) public registry;
    address public admin;

    event AddressUpdated(address indexed target, Status status);

    constructor() {
        admin = msg.sender;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not authorized");
        _;
    }

    // Admin updates the registry based on community audits or AI feedback
    function updateStatus(address _target, Status _status) external onlyAdmin {
        registry[_target] = _status;
        emit AddressUpdated(_target, _status);
    }

    // Read-only function: 0 GAS cost
    function checkAddress(address _target) external view returns (Status) {
        return registry[_target];
    }
}