// Visual dependency propagation only. No signatures or cryptographic hashes are checked on GPU.
// Each generation is dispatched separately; no workgroup execution-order assumptions.
struct DagNode {
    pos: vec4<f32>,
    local_ok: u32,
    effective: u32,
    parent_index: i32,
    depth: u32,
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
    let parent = nodes[idx].parent_index;
    if (parent >= 0) {
        if (u32(parent) >= arrayLength(&nodes)) {
            nodes[idx].effective = 3u;
            return;
        }
        if (nodes[u32(parent)].effective != 1u) {
            nodes[idx].effective = 3u;
            return;
        }
    }
    if (nodes[idx].local_ok == 1u) {
        nodes[idx].effective = 1u;
    } else {
        nodes[idx].effective = 2u;
    }
}
