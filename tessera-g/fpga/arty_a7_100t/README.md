# Tessera-G Arty A7-100T hardware bring-up — v0.13 preparatory build

**Scope: a real Vivado-ready physical-board wrapper, not an actual bitstream or programmed FPGA.**

## What runs

- `tessera_g_arty_top.sv` instantiates the actual synthesized
  `tessera_g_dag_tile` SystemVerilog from `../../rtl/`.
- Four locally generated, synthetic nodes exercise: accepted genesis,
  locally refuted rogue, blocked descendant, and valid independent sibling.
- After the four checks complete, the four discrete board LEDs illuminate;
  RGB0 **green** is the hardware test-sequence outcome, **red** marks a
  sequence failure, **blue** marks unfinished setup. This indicator DOES NOT
  prove external Z3 receipts, sensor authenticity, or physical human intent.
- BTN0 resets the demonstration. Synchronization handles reset release,
  not an independently verified clock or button debounce protocol.

Board: **Digilent Arty A7-100T, XC7A100T-CSG324-1**, not Arty A7-35T.
Pin mapping from official
[Digilent Arty A7-100 GPIO master XDC](https://github.com/Digilent/Arty-A7-100-GPIO/blob/master/src/constraints/Arty_Master.xdc).
Verify the silkscreen variant and board revision before programming.

## 1. Headless logic-only preflight — tested on GitHub CPU runner

```bash
sudo apt-get update
sudo apt-get install -y iverilog verilator yosys python3
bash tessera-g/fpga/arty_a7_100t/ci/run_board_preflight.sh
```

Runs XDC pin lint, Icarus board-top simulation + reset tests, warning-fatal
Verilator lint and full generic Yosys synthesis. A pass **is not a .bit file**.

## 2. Real bitstream generation — requires installed AMD/Xilinx Vivado

```bash
bash tessera-g/fpga/arty_a7_100t/build_on_vivado_host.sh
```

Vivado runs synthesis → place → route → timing check → write_bitstream using
`xc7a100tcsg324-1`. Expected output:

`tessera-g/fpga/arty_a7_100t/output/tessera_g_arty_a7_100t.bit`

An accompanying SHA-256 file, timing report, utilization report and DRC
report are produced. The script **refuses to claim success without Vivado**
and fails on missing/nonpositive timing evidence. This step is
not possible on ordinary GitHub-hosted runners without the toolchain.

GitHub workflow `Tessera-G Arty A7-100T board prep` optionally supports
manual `mode=vivado` **on reviewed main only**, using a protected
`fpga-hardware` environment and an operator-controlled runner carrying
the `vivado` label. That job NEVER programs physical hardware.

## 3. Optional temporary SRAM programming — requires connected physical board

**Check that the board is idle and the target silicon is exactly A7-100T,
not A7-35T, before executing.** The script uses SRAM (volatile) and does
not modify persistent SPI flash:

```bash
export TESSERA_CONFIRM_PHYSICAL_BOARD=ARTY_A7_100T_CONNECTED_AND_IDLE
bash tessera-g/fpga/arty_a7_100t/flash_volatile_confirmed.sh
```

Requires `openFPGALoader`, the actual Vivado-produced bitstream, and matching
sha256 file. The tool must detect the hardware over Digilent JTAG. After
programming, the operator must physically observe the green RGB0 plus
four discrete LEDs, press BTN0 and observe the reset/test sequence again,
and capture the board ID/bitstream hash/readback evidence.

OpenFPGALoader confirms `arty_a7_100t` is a supported board profile:
https://trabucayre.github.io/openFPGALoader/compatibility/board.html

## Explicit status boundaries

- `HDL_SIMULATION / LINT / GENERIC_SYNTH` may PASS in headless CI.
- `VIVADO_BITSTREAM`: NOT BUILT until the real Vivado build succeeds.
- `SRAM_PROGRAMMING`: NOT PERFORMED until board is connected and command runs.
- `PHYSICAL_FPGA_ACCEPTANCE`: NOT VERIFIED without board readback +
  independent observation. A green LED shows only its programmed demo path.
- `ATECC608C_SIGNING`: NOT CONNECTED (ECDSA P-256, not Ed25519).
- `BCI`: NOT CONNECTED. Any raw EEG commands require opt-in, confirmation,
  calibration and independent validation; this demo has no neural interface.
- `RUNPOD_AMD_GPU`: NOT USED.
- `SILICON_MANUFACTURABLE`: NOT ESTABLISHED by Yosys generic synthesis.
  RTL portability also requires target timing/constraints/technology mapping.
- `MEMORY_LEAK_FREE`: not a meaningful property established by HDL synthesis.

No PR is merged without direct owner instruction. No hardware is programmed
automatically, and the scripts will not create a production deployment.
