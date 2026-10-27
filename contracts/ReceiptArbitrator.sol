// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
/**
 * @notice Non-custodial review registry for opt-in receipt processing.
 * @dev This contract does NOT judge crimes, stop external transfers, or seize funds.
 *      Two different, independent guardian accounts must approve pausing THIS registry.
 *      ZK proof verification must be added only after audited verification key and setup.
 *      NOT PRODUCTION READY; never deploy without owner review/audit.
 */
contract ReceiptArbitrator {
    address[3] public guardians;
    mapping(address => bool) public isGuardian;
    mapping(bytes32 => mapping(address => bool)) public approvals;
    mapping(bytes32 => uint8) public approvalCount;
    bool public paused;
    uint256 public epoch;
    event PauseProposed(bytes32 indexed action, address indexed guardian);
    event PauseChanged(bool paused, uint256 epoch);
    modifier onlyGuardian() { require(isGuardian[msg.sender], "NOT_GUARDIAN"); _; }
    constructor(address[3] memory members) {
        for (uint256 i=0;i<3;i++) {
            require(members[i]!=address(0) && !isGuardian[members[i]], "BAD_GUARDIANS");
            guardians[i]=members[i]; isGuardian[members[i]]=true;
        }
    }
    function approvePause(bool nextPaused) external onlyGuardian {
        require(nextPaused != paused, "NO_CHANGE");
        bytes32 action=keccak256(abi.encode(address(this),block.chainid,epoch,nextPaused));
        require(!approvals[action][msg.sender], "ALREADY_APPROVED");
        approvals[action][msg.sender]=true;
        approvalCount[action]++;
        emit PauseProposed(action,msg.sender);
        if(approvalCount[action]>=2) {
            paused=nextPaused;
            epoch++;
            emit PauseChanged(nextPaused,epoch);
        }
    }
}

