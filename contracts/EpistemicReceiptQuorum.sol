// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title iNNOVULIS EpistemicReceiptQuorum (non-custodial governance prototype)
 * @notice 3-of-5 independent EIP-712 node signatures over a receipt root. Five
 *         separate governance signers may rotate keys or pause/resume the registry.
 * @dev No funds, no court powers, no financial authorization, no ZKP verifier,
 *      no assumption that signer keys correspond to distinct hosts or truthful data.
 *      Not audited and NOT approved for production deployment.
 */
contract EpistemicReceiptQuorum {
    bytes32 private constant DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 private constant CONFIRM_TYPEHASH = keccak256("Confirm(bytes32 receiptRoot,uint256 nodeEpoch,uint256 deadline)");
    bytes32 private constant ROTATE_NODE_TYPEHASH = keccak256("RotateNode(address oldNode,address newNode,uint256 nodeEpoch,uint256 governanceEpoch,uint256 nonce,uint256 deadline)");
    bytes32 private constant ROTATE_GOV_TYPEHASH = keccak256("RotateGovernor(address oldGovernor,address newGovernor,uint256 governanceEpoch,uint256 nonce,uint256 deadline)");
    bytes32 private constant PAUSE_TYPEHASH = keccak256("SetPaused(bool paused,uint256 governanceEpoch,uint256 nonce,uint256 deadline)");
    bytes32 private constant NAME_HASH = keccak256("iNNOVULISReceiptQuorum");
    bytes32 private constant VERSION_HASH = keccak256("1");
    uint256 private constant SECP256K1_HALF_N = 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0;
    uint256 public constant QUORUM = 3;
    uint256 public constant MEMBERS = 5;
    uint256 public constant MAX_DEADLINE_AHEAD = 10 minutes;

    mapping(address => bool) public isNode;
    mapping(address => bool) public isGovernor;
    mapping(bytes32 => bool) public confirmedRoot;
    uint256 public nodeEpoch = 1;
    uint256 public governanceEpoch = 1;
    uint256 public governanceNonce;
    bool public paused;
    event ReceiptQuorumReached(bytes32 indexed receiptRoot, uint256 indexed nodeEpoch, uint256 timestamp);
    event NodeRotated(address indexed oldNode, address indexed newNode, uint256 indexed newEpoch);
    event GovernorRotated(address indexed oldGovernor, address indexed newGovernor, uint256 indexed newEpoch);
    event PauseChanged(bool paused, uint256 governanceEpoch);

    constructor(address[5] memory nodes, address[5] memory governors) {
        for (uint256 i; i < MEMBERS; ++i) {
            if (nodes[i] == address(0) || isNode[nodes[i]]) revert InvalidMember();
            if (governors[i] == address(0) || isGovernor[governors[i]]) revert InvalidMember();
            isNode[nodes[i]] = true;
            isGovernor[governors[i]] = true;
        }
    }
    error InvalidMember();
    error InvalidSignature();
    error InsufficientQuorum();
    error InvalidDeadline();
    error AlreadyConfirmed();
    error Paused();
    error AlreadyPaused();

    function domainSeparator() public view returns(bytes32) {
        return keccak256(abi.encode(DOMAIN_TYPEHASH, NAME_HASH, VERSION_HASH, block.chainid, address(this)));
    }
    function _hashTypedData(bytes32 structHash) internal view returns(bytes32) {
        return keccak256(abi.encodePacked(hex"1901", domainSeparator(), structHash));
    }
    function _deadline(uint256 deadline) private view {
        if (deadline < block.timestamp || deadline > block.timestamp + MAX_DEADLINE_AHEAD)
            revert InvalidDeadline();
    }
    function _recover(bytes32 digest, bytes calldata signature) private pure returns(address signer) {
        if (signature.length != 65) revert InvalidSignature();
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (v != 27 && v != 28) revert InvalidSignature();
        if (r == bytes32(0) || uint256(s) == 0 || uint256(s) > SECP256K1_HALF_N) revert InvalidSignature();
        signer = ecrecover(digest, v, r, s);
        if (signer == address(0)) revert InvalidSignature();
    }
    function _check(bytes32 digest, bytes[] calldata signatures, bool governance) private view {
        if (signatures.length < QUORUM || signatures.length > MEMBERS) revert InsufficientQuorum();
        uint160 last = 0;
        for (uint256 i; i < signatures.length; ++i) {
            address signer = _recover(digest, signatures[i]);
            if (uint160(signer) <= last) revert InvalidSignature(); // reject duplicate or unsorted
            if (governance ? !isGovernor[signer] : !isNode[signer]) revert InvalidSignature();
            last = uint160(signer);
        }
    }
    function confirmReceipt(bytes32 root, uint256 deadline, bytes[] calldata signatures) external {
        if (paused) revert Paused();
        if (root == bytes32(0)) revert InvalidMember();
        if (confirmedRoot[root]) revert AlreadyConfirmed();
        _deadline(deadline);
        bytes32 digest = _hashTypedData(keccak256(abi.encode(CONFIRM_TYPEHASH, root, nodeEpoch, deadline)));
        _check(digest, signatures, false);
        confirmedRoot[root] = true; // this is consensus about a root, not a proof of truth
        emit ReceiptQuorumReached(root, nodeEpoch, block.timestamp);
    }
    function rotateNode(address oldNode, address newNode, uint256 deadline, bytes[] calldata signatures) external {
        if (!isNode[oldNode] || newNode == address(0) || isNode[newNode]) revert InvalidMember();
        _deadline(deadline);
        bytes32 digest = _hashTypedData(keccak256(abi.encode(ROTATE_NODE_TYPEHASH, oldNode, newNode,
            nodeEpoch, governanceEpoch, governanceNonce, deadline)));
        _check(digest, signatures, true);
        isNode[oldNode] = false;
        isNode[newNode] = true; // exactly five always, atomic key rotation
        nodeEpoch += 1; // previous epoch attestations are invalid
        governanceNonce += 1;
        emit NodeRotated(oldNode, newNode, nodeEpoch);
    }
    function rotateGovernor(address oldGovernor, address newGovernor, uint256 deadline, bytes[] calldata signatures) external {
        if (!isGovernor[oldGovernor] || newGovernor == address(0) || isGovernor[newGovernor]) revert InvalidMember();
        _deadline(deadline);
        bytes32 digest = _hashTypedData(keccak256(abi.encode(ROTATE_GOV_TYPEHASH, oldGovernor,
            newGovernor, governanceEpoch, governanceNonce, deadline)));
        _check(digest, signatures, true);
        isGovernor[oldGovernor] = false;
        isGovernor[newGovernor] = true;
        governanceEpoch += 1;
        governanceNonce += 1;
        emit GovernorRotated(oldGovernor, newGovernor, governanceEpoch);
    }
    function setPaused(bool next, uint256 deadline, bytes[] calldata signatures) external {
        if (next == paused) revert AlreadyPaused();
        _deadline(deadline);
        bytes32 digest = _hashTypedData(keccak256(abi.encode(PAUSE_TYPEHASH, next,
            governanceEpoch, governanceNonce, deadline)));
        _check(digest, signatures, true);
        paused = next;
        governanceNonce += 1; // no second execution of the same signed governance action
        emit PauseChanged(paused, governanceEpoch);
    }
}

