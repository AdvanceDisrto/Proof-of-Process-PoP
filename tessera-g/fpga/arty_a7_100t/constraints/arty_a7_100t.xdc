# Digilent Arty A7-100T, Rev. D, xc7a100tcsg324-1
# Board pin mapping checked against Digilent/Arty-A7-100-GPIO Arty_Master.xdc.
# DO NOT use this XDC on a different board variant or revision without verifying.
set_property -dict { PACKAGE_PIN E3 IOSTANDARD LVCMOS33 } [get_ports {clk100}]
create_clock -name sys_clk_pin -period 10.000 -waveform {0 5} [get_ports {clk100}]

set_property -dict { PACKAGE_PIN D9 IOSTANDARD LVCMOS33 } [get_ports {btn_reset}]

set_property -dict { PACKAGE_PIN H5 IOSTANDARD LVCMOS33 } [get_ports {led[0]}]
set_property -dict { PACKAGE_PIN J5 IOSTANDARD LVCMOS33 } [get_ports {led[1]}]
set_property -dict { PACKAGE_PIN T9 IOSTANDARD LVCMOS33 } [get_ports {led[2]}]
set_property -dict { PACKAGE_PIN T10 IOSTANDARD LVCMOS33 } [get_ports {led[3]}]

set_property -dict { PACKAGE_PIN G6 IOSTANDARD LVCMOS33 } [get_ports {rgb0_r}]
set_property -dict { PACKAGE_PIN F6 IOSTANDARD LVCMOS33 } [get_ports {rgb0_g}]
set_property -dict { PACKAGE_PIN E1 IOSTANDARD LVCMOS33 } [get_ports {rgb0_b}]
