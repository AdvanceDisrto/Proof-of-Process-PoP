# Tessera-G v0.1 Arty A7-100T; execute with Vivado batch mode ON a licensed host.
# Does not flash an FPGA, read sensors, check signatures, or claim physical truth.
set script_dir [file dirname [file normalize [info script]]]
set tessera_dir [file normalize [file join $script_dir ../..]]
set out_dir [file normalize [file join $script_dir output]]
file mkdir $out_dir

set tile [file join $tessera_dir rtl tessera_g_dag_tile.sv]
set board_top [file join $script_dir tessera_g_arty_top.sv]
set constraints [file join $script_dir constraints arty_a7_100t.xdc]
foreach required [list $tile $board_top $constraints] {
    if {![file isfile $required]} { error "MISSING_REQUIRED_INPUT: $required" }
}
read_verilog -sv $tile
read_verilog -sv $board_top
read_xdc $constraints
synth_design -top tessera_g_arty_top -part xc7a100tcsg324-1
write_checkpoint -force [file join $out_dir tessera_synth.dcp]
report_utilization -file [file join $out_dir utilization_synth.rpt]
opt_design
place_design
route_design
write_checkpoint -force [file join $out_dir tessera_routed.dcp]
report_drc -file [file join $out_dir drc_routed.rpt]
report_utilization -file [file join $out_dir utilization_routed.rpt]
report_timing_summary -file [file join $out_dir timing_routed.rpt]
set timing_paths [get_timing_paths -delay_type max -max_paths 1]
if {[llength $timing_paths] == 0} {
    error "TIMING_GATE_FAILED: no real maximum-delay path; cannot claim closure"
}
set wns [get_property SLACK [lindex $timing_paths 0]]
if {![string is double -strict $wns] || $wns < 0.0} {
    error "TIMING_GATE_FAILED: worst slack is $wns"
}
set bitstream [file join $out_dir tessera_g_arty_a7_100t.bit]
write_bitstream -force $bitstream
if {![file exists $bitstream] || [file size $bitstream] < 1024} {
    error "BITSTREAM_GATE_FAILED: no valid-size output"
}
puts "TESSERA_ARTY_BITSTREAM=BUILT (unflashed; no board-level acceptance)"
puts "TESSERA_ARTY_BITSTREAM_PATH=$bitstream"
puts "TESSERA_ARTY_TIMING_WNS_NS=$wns"
