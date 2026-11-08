"""Check exact Digilent Arty A7-100T bank-appropriate pin mapping, NOT actual bitstream."""
import pathlib, re
xdc=pathlib.Path(__file__).resolve().parents[1]/"constraints"/"arty_a7_100t.xdc"
data=xdc.read_text()
mapping=dict(re.findall(
    r"PACKAGE_PIN ([A-Z][0-9]+) IOSTANDARD LVCMOS33 } \[get_ports \{([^}]+)\}\]",
    data))
expected={
    "E3":"clk100","D9":"btn_reset",
    "H5":"led[0]","J5":"led[1]","T9":"led[2]","T10":"led[3]",
    "G6":"rgb0_r","F6":"rgb0_g","E1":"rgb0_b",
}
assert mapping==expected,(mapping,expected)
assert 'create_clock -name sys_clk_pin -period 10.000' in data
print("ARTY_A7_100T_XDC_STATIC_MAPPING=PASS pin_count=9 (not actual board detection)")
