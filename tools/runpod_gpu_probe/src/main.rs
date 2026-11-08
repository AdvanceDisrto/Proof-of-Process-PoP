//! Minimal REAL GPU integration gate for iNNOVULIS DAGE.
//! CPU Z3 verifies declared integer policy; GPU propagates dependency states.
//! DOES NOT establish physically accurate sensors, signature trust, or mathematical
//! proof on the GPU. AMD-only to honor i™ non-NVIDIA DAGE acceptance.
use bytemuck::{Pod, Zeroable};
use std::{error::Error, sync::mpsc};
use wgpu::util::DeviceExt;
use z3::{ast::{Ast, Int}, Config, Context, SatResult, Solver};

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
struct GpuNode {
    pos: [f32; 4],
    local_verdict: u32,
    effective: u32,
    parent_a: i32,
    parent_b: i32,
    depth: u32,
    padding: [u32; 3],
}
const _: [(); 48] = [(); std::mem::size_of::<GpuNode>()];

fn z3_under_limit(observed: i64, maximum: i64) -> bool {
    let mut cfg = Config::new();
    cfg.set_timeout_msec(5_000);
    let ctx = Context::new(&cfg);
    let s = Solver::new(&ctx);
    let reading = Int::new_const(&ctx, "reading");
    s.assert(&reading._eq(&Int::from_i64(&ctx, observed)));
    // Prove reading <= maximum by finding NO model with reading > maximum.
    s.assert(&reading.gt(&Int::from_i64(&ctx, maximum)));
    matches!(s.check(), SatResult::Unsat)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn z3_accepts_in_bound_observation() {
        assert!(z3_under_limit(45_000, 50_000));
        assert!(z3_under_limit(50_000, 50_000));
    }
    #[test]
    fn z3_refutes_over_limit_observation() {
        assert!(!z3_under_limit(500_000, 50_000));
    }
    #[test]
    fn node_storage_layout_is_48_bytes() {
        assert_eq!(std::mem::size_of::<GpuNode>(), 48);
    }
    #[test]
    fn wgsl_shader_parses_and_validates_without_a_gpu() {
        let shader = naga::front::wgsl::parse_str(include_str!("propagate.wgsl")).unwrap();
        naga::valid::Validator::new(
            naga::valid::ValidationFlags::all(),
            naga::valid::Capabilities::all()
        ).validate(&shader).unwrap();
    }
}

async fn gpu_smoke() -> Result<(), Box<dyn Error>> {
    // CPU Z3 determines ONLY bounded integer claims; GPU displays lineage status.
    // Two-parent joins, unknown inputs and future/cyclic references are distinct.
    let as_local = |observed, limit| if z3_under_limit(observed, limit) { 1 } else { 2 };
    let mk = |local_verdict, parent_a, parent_b, depth| GpuNode {
        pos: [0.0, 0.0, 0.0, 1.0], local_verdict, effective: 0,
        parent_a, parent_b, depth, padding: [0; 3],
    };
    let nodes: [GpuNode; 9] = [
        mk(as_local(45_000, 50_000), -1, -1, 0), // 0 genesis pass
        mk(as_local(500_000, 50_000), 0, -1, 1), // 1 local refuted
        mk(as_local(30_000, 50_000), 1, -1, 2),  // 2 blocked descendant
        mk(as_local(30_000, 50_000), 0, -1, 1),  // 3 passing sibling
        mk(as_local(30_000, 50_000), 0, 3, 2),   // 4 two-parent valid join
        mk(as_local(30_000, 50_000), 3, 1, 2),   // 5 two-parent blocked join
        mk(as_local(30_000, 50_000), 7, -1, 1),  // 6 future parent invalid
        mk(0, -1, -1, 0),                         // 7 undetermined
        mk(as_local(30_000, 50_000), 7, -1, 1),  // 8 blocked by unknown
    ];
    let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
        backends: wgpu::Backends::VULKAN,
        ..Default::default()
    });
    let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions {
        power_preference: wgpu::PowerPreference::HighPerformance,
        compatible_surface: None,
        force_fallback_adapter: false,
    }).await.ok_or("no Vulkan adapter detected")?;
    let info = adapter.get_info();
    // A software Vulkan implementation (llvmpipe) is not a physical GPU PASS.
    if info.vendor != 0x1002 || !matches!(info.device_type,
        wgpu::DeviceType::DiscreteGpu | wgpu::DeviceType::IntegratedGpu) {
        return Err(format!(
            "AMD GPU REQUIRED: Vulkan adapter name={:?} vendor={:#x} device_type={:?}",
            info.name, info.vendor, info.device_type,
        ).into());
    }
    let (device, queue) = adapter.request_device(
        &wgpu::DeviceDescriptor {
            label: Some("iNNOVULIS AMD DAGE"),
            required_features: wgpu::Features::empty(),
            required_limits: wgpu::Limits::downlevel_defaults(),
        },
        None,
    ).await?;
    let graph_buf = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("VRAM proof-node states"),
        contents: bytemuck::cast_slice(&nodes),
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
    });
    let out_buf = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("GPU readback"),
        size: std::mem::size_of_val(&nodes) as u64,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    let depth_buf = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("depth uniform"),
        contents: bytemuck::cast_slice(&[0u32; 4]),
        usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
    });
    let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("DAGE propagation"),
        source: wgpu::ShaderSource::Wgsl(include_str!("propagate.wgsl").into()),
    });
    let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("DAGE bindings"),
        entries: &[
            wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::COMPUTE,
                ty: wgpu::BindingType::Buffer {
                    ty: wgpu::BufferBindingType::Storage { read_only: false },
                    has_dynamic_offset: false, min_binding_size: None,
                },
                count: None,
            },
            wgpu::BindGroupLayoutEntry {
                binding: 1,
                visibility: wgpu::ShaderStages::COMPUTE,
                ty: wgpu::BindingType::Buffer {
                    ty: wgpu::BufferBindingType::Uniform,
                    has_dynamic_offset: false, min_binding_size: None,
                },
                count: None,
            },
        ],
    });
    let group = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("DAGE group"), layout: &layout,
        entries: &[
            wgpu::BindGroupEntry { binding: 0, resource: graph_buf.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 1, resource: depth_buf.as_entire_binding() },
        ],
    });
    let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("DAGE compute pipeline layout"),
        bind_group_layouts: &[&layout], push_constant_ranges: &[],
    });
    let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: Some("DAGE compute"),
        layout: Some(&pipeline_layout),
        module: &shader, entry_point: "main",
    });
    // DEPENDENCY ORDER: separate submissions, never race a parent and child.
    for depth in 0u32..3u32 {
        queue.write_buffer(&depth_buf, 0, bytemuck::cast_slice(&[depth, 0, 0, 0]));
        let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("DAGE depth iteration"),
        });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("dependency propagator"), timestamp_writes: None,
            });
            pass.set_pipeline(&pipeline);
            pass.set_bind_group(0, &group, &[]);
            pass.dispatch_workgroups(1, 1, 1);
        }
        queue.submit(Some(encoder.finish()));
    }
    let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
        label: Some("DAGE readback"),
    });
    encoder.copy_buffer_to_buffer(&graph_buf, 0, &out_buf, 0, std::mem::size_of_val(&nodes) as u64);
    queue.submit(Some(encoder.finish()));
    let slice = out_buf.slice(..);
    let (tx, rx) = mpsc::channel();
    slice.map_async(wgpu::MapMode::Read, move |result| { let _ = tx.send(result); });
    device.poll(wgpu::Maintain::Wait);
    rx.recv()??;
    let mapped = slice.get_mapped_range();
    let result: Vec<GpuNode> = bytemuck::cast_slice::<u8, GpuNode>(&mapped).to_vec();
    drop(mapped);
    out_buf.unmap();
    let observed: Vec<u32> = result.iter().map(|v| v.effective).collect();
    let expected = [1, 2, 3, 1, 1, 3, 5, 4, 3];
    if observed != expected {
        return Err(format!("GPU propagation mismatch: {observed:?}; expected {expected:?}").into());
    }
    println!("DAGE_GPU_SMOKE=PASS vendor=AMD adapter={:?} states={observed:?} (signed/physical gates NOT proven)", info.name);
    Ok(())
}

/// Emit an untrusted but independently recheckable typed input fixture from real CPU Z3.
/// Only a formal bounded integer relation is evaluated; sensors and signer trust remain absent.
fn emit_tessera_vectors() {
    let cases: [(Option<i64>, i64, i32, i32); 8] = [
        (Some(45_000), 50_000, -1, -1), // 0 bounded genesis
        (Some(50_000), 50_000, 0, -1),  // 1 bounded child
        (Some(90_000), 50_000, 0, -1),  // 2 refuted locally
        (Some(20_000), 50_000, 2, -1),  // 3 valid arithmetic, dependency blocked
        (Some(20_000), 50_000, 0, 1),   // 4 two-parent valid join
        (Some(20_000), 50_000, 1, 2),   // 5 two-parent blocked join
        (None, 50_000, -1, -1),         // 6 UNKNOWN, not proven
        (Some(20_000), 50_000, 10, -1),// 7 future index invalid topology
    ];
    for (index, (reading, limit, pa, pb)) in cases.into_iter().enumerate() {
        let verdict = match reading {
            None => 0u32,
            Some(value) if z3_under_limit(value, limit) => 1u32,
            Some(_) => 2u32,
        };
        println!("TESSERA_VECTOR {index} {verdict} {pa} {pb}");
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|x| x == "--gpu-smoke") {
        pollster::block_on(gpu_smoke())
    } else if args.iter().any(|x| x == "--tessera-vector") {
        emit_tessera_vectors();
        Ok(())
    } else {
        println!("DAGE_GPU_SMOKE=NOT_RUN; use --gpu-smoke on a physical AMD Vulkan GPU");
        Ok(())
    }
}
