// Visual two-parent DAG status propagation only. Does NOT verify SMT, hashes, or signatures.
// Each topological depth is dispatched in a separate ordered GPU submission.
struct DagNode {
    pos: vec4<f32>,
    local_verdict: u32, // 1=pass, 2=refuted, 0 or 3 = undetermined
    effective: u32,     // 1 pass, 2 refuted, 3 blocked, 4 unknown, 5 invalid topology
    parent_a: i32,
    parent_b: i32,
    depth: u32,
    padding0: u32,
    padding1: u32,
    padding2: u32,
};
struct DepthControl {
    current_depth: u32,
    reserved1: u32,
    reserved2: u32,
    reserved3: u32,
};
@group(0) @binding(0) var<storage, read_write> nodes: array<DagNode>;
@group(0) @binding(1) var<uniform> ctl: DepthControl;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let idx = id.x;
    if (idx >= arrayLength(&nodes)) { return; }
    if (nodes[idx].depth != ctl.current_depth) { return; }

    let a = nodes[idx].parent_a;
    let b = nodes[idx].parent_b;
    // Indexed, append-only parent ordering, no duplicate edges or self-parent.
    if (a < -1 || b < -1 ||
        (a >= 0 && (u32(a) >= idx || u32(a) >= arrayLength(&nodes))) ||
        (b >= 0 && (u32(b) >= idx || u32(b) >= arrayLength(&nodes))) ||
        (a >= 0 && a == b)) {
        nodes[idx].effective = 5u;
        return;
    }
    if (a >= 0) {
        let parent = nodes[u32(a)];
        if (parent.depth >= ctl.current_depth) {
            nodes[idx].effective = 5u;
            return;
        }
        if (parent.effective != 1u) {
            nodes[idx].effective = 3u;
            return;
        }
    }
    if (b >= 0) {
        let parent = nodes[u32(b)];
        if (parent.depth >= ctl.current_depth) {
            nodes[idx].effective = 5u;
            return;
        }
        if (parent.effective != 1u) {
            nodes[idx].effective = 3u;
            return;
        }
    }
    if (nodes[idx].local_verdict == 1u) {
        nodes[idx].effective = 1u;
    } else if (nodes[idx].local_verdict == 2u) {
        nodes[idx].effective = 2u;
    } else {
        nodes[idx].effective = 4u;  // unknown never maps to pass
    }
}
