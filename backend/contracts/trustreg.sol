// SPDX-License-Identifier: GPL-3.0

pragma solidity ^ 0.8.0

contract TrustRegistry{
    // note: hindi pa sure to, wala pa akong naisip na specific na status, so pwede pa magbago
    enum Status {
        Unknown,
        Safe,
        Suspicious,
        Malicious
    }

    struct Entry {
        Status status;
        uint256 timestamp;
        bytes32 evidenceHash;
    }
    // maybe wala nang evidence hash, pero para sa sim report yan.
}
