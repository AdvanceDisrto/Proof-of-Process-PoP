"""Candidate netlist semantic checks. This is NOT KiCad ERC, DRC or a Gerber."""
from __future__ import annotations
import json
from pathlib import Path

class LayoutNotValidated(ValueError):pass

REQUIRED_NETS={
 "USB_VBUS_5V", "USB_D_PLUS", "USB_D_MINUS", "GND", "PWR_3V3", "I2C_SDA_3V3", "I2C_SCL_3V3"}
EXPECTED={
 "USB_D_PLUS":{"USB_C.DP","MCU.USB_DP"},
 "USB_D_MINUS":{"USB_C.DM","MCU.USB_DM"},
 "PWR_3V3":{"REG.VOUT","MCU.VDD","ATECC.VCC","MCP9808.VDD"},
 "I2C_SDA_3V3":{"MCU.SDA","ATECC.SDA","MCP9808.SDA","R_SDA.UPPER"},
 "I2C_SCL_3V3":{"MCU.SCL","ATECC.SCL","MCP9808.SCL","R_SCL.UPPER"},
 "GND":{"USB_C.GND","MCU.GND","REG.GND","ATECC.GND","MCP9808.GND"},
}

def audit_candidate(d):
    if type(d) is not dict or d.get("schema")!="i-istick-electrical-candidate/v1":
        raise LayoutNotValidated("wrong schema")
    if d.get("processor",{}).get("usb_controller") is not True or d.get("processor",{}).get("i2c_controller") is not True:
        raise LayoutNotValidated("CH340E USB-UART cannot run host programs or native I2C")
    if d.get("manufacturing_state")!="NOT_ROUTED_NOT_FAB_READY":
        raise LayoutNotValidated("cannot claim production route/DFM without physical CAD files")
    nets=d.get("nets")
    if type(nets) is not dict or set(nets)!=REQUIRED_NETS:
        raise LayoutNotValidated("incomplete candidate netlist")
    for n,pins in EXPECTED.items():
        if not pins.issubset(set(nets[n])):
            raise LayoutNotValidated("missing essential connection on "+n)
    if any(net=="USB_VBUS_5V" and "MCU.VDD" in pins for net,pins in nets.items()):
        raise LayoutNotValidated("USB 5V must not be tied straight to 3.3V MCU VDD")
    if d.get("vcc_sensor_volts")!=3.3 or d.get("vcc_secure_element_volts")!=3.3:
        raise LayoutNotValidated("3.3 V domain explicitly required")
    caps=d.get("decoupling_caps")
    if type(caps) is not list or len(caps)<4 or {x["target"] for x in caps}!={"MCU","REG","ATECC","MCP9808"}:
        raise LayoutNotValidated("each IC needs decoupling")
    if any(x["cap_nf"]<100 for x in caps):
        raise LayoutNotValidated("required local high-frequency decoupling absent")
    return {"net_connections_present":True,"schema_checked":True,
            "pcb_is_manufacturable":False,"gerber_exists":False,"erc_drc": "NOT_RUN",
            "usb_signal_integrity":"NOT_MEASURED","esd_qualification":"NOT_PERFORMED",
            "side_channel_resistance":"NOT_ESTABLISHED"}


def audit_file(path):
    return audit_candidate(json.loads(Path(path).read_text()))
