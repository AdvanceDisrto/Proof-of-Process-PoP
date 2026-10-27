pragma circom 2.1.9;
include "circomlib/circuits/bitify.circom";
include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/poseidon.circom";

// This proves a private *heuristic score* comparison, NOT an actual crime,
// liability, entitlement to funds, or validity of underlying evidence.
// Public commitment must be externally authenticated and linked to a signed receipt.
template EvidenceBoundHeuristicV1() {
    // Private integer inputs; no floating-point tokens / negative log probabilities.
    signal input penaltyBps;
    signal input entropyBps;
    signal input chargeStackCount;
    signal input witnessSalt;
    // Public inputs; threshold must be defined by external, versioned policy.
    signal input publicCommitment;
    signal input thresholdProduct;
    // Public output exposes only whether the fixed-point heuristic exceeds threshold.
    signal output thresholdExceeded;

    component penaltyRange = Num2Bits(14);
    component entropyRange = Num2Bits(14);
    component countRange = Num2Bits(8);
    penaltyRange.in <== penaltyBps;
    entropyRange.in <== entropyBps;
    countRange.in <== chargeStackCount;

    component pBound = LessThan(14);
    component eBound = LessThan(14);
    pBound.in[0] <== penaltyBps;
    pBound.in[1] <== 10001;
    pBound.out === 1;
    eBound.in[0] <== entropyBps;
    eBound.in[1] <== 10001;
    eBound.out === 1;

    // Range checked product is <= 10,000*10,000*255 = 25,500,000,000 < 2^35.
    signal pair;
    pair <== penaltyBps * entropyBps;
    signal product;
    product <== pair * chargeStackCount;
    component productBits = Num2Bits(36);
    component thresholdBits = Num2Bits(36);
    productBits.in <== product;
    thresholdBits.in <== thresholdProduct;

    // Poseidon commitment is binding to private witness + secret salt.
    component bind = Poseidon(4);
    bind.inputs[0] <== penaltyBps;
    bind.inputs[1] <== entropyBps;
    bind.inputs[2] <== chargeStackCount;
    bind.inputs[3] <== witnessSalt;
    bind.out === publicCommitment;

    component gt = GreaterThan(36);
    gt.in[0] <== product;
    gt.in[1] <== thresholdProduct;
    thresholdExceeded <== gt.out;
}

component main {public [publicCommitment, thresholdProduct]} = EvidenceBoundHeuristicV1();

