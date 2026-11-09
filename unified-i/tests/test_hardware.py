from __future__ import annotations
import json
import copy
from pathlib import Path
import pytest
from unified_i.hardware import MCP9808ReadOnly,SensorUnavailable
from unified_i.board import audit_file,audit_candidate,LayoutNotValidated
from unified_i.physical import baseline,record_report,assert_no_upgrade,PhysicalClaimRejected,REQUIRED

ROOT=Path(__file__).parents[1]

class Bus:
 def __init__(self,reg=None):
  self.reg=reg or {0x06:0x0054,0x07:0x0400,0x05:0x0190}
  self.calls=[]
 def read_word_data(self,a,reg):
  self.calls.append((a,reg))
  v=self.reg[reg]
  return ((v&255)<<8)|(v>>8)

def test_mcp9808_25_degrees():
 b=Bus();s=MCP9808ReadOnly(b).read()
 assert s.temperature_milli_celsius==25000 and s.source_tier=="HARDWARE_UNATTESTED"
 assert b.calls==[(0x18,0x06),(0x18,0x07),(0x18,0x05)]

def test_mcp9808_negative_16_degrees():
 assert MCP9808ReadOnly(Bus({0x06:0x54,0x07:0x400,0x05:0x1f00})).read().temperature_milli_celsius == -16000

@pytest.mark.parametrize("addr",[0x00,0x17,0x20,0xff,True])
def test_bad_sensor_address(addr):
 with pytest.raises(ValueError):MCP9808ReadOnly(Bus(),address=addr)

@pytest.mark.parametrize("register,value",[(0x06,0x1234),(0x07,0x1234),(0x05,0x0fff)])
def test_sensor_identity_or_range_fails(register,value):
 b=Bus();b.reg[register]=value
 if register==0x05:
  # 255.9375 deg C should be invalid
  pass
 with pytest.raises(SensorUnavailable):MCP9808ReadOnly(b).read()

def test_i2c_exception_fails_closed():
 class Disconnected:
  def read_word_data(self,a,b):raise OSError("no device")
 with pytest.raises(SensorUnavailable):MCP9808ReadOnly(Disconnected()).read()

def test_reference_audit_not_fab():
 result=audit_file(ROOT/"hardware"/"istick_reference.json")
 assert result["net_connections_present"] and result["gerber_exists"] is False

@pytest.mark.parametrize("field,bad_value",[
 ("processor",{"usb_controller":False,"i2c_controller":True}),
 ("manufacturing_state","GERBERS_READY"),
 ("vcc_sensor_volts",5.0),
 ("vcc_secure_element_volts",5.0),
 ("decoupling_caps",[]),
])
def test_bad_candidate_refused(field,bad_value):
 d=json.loads((ROOT/"hardware"/"istick_reference.json").read_text());d[field]=bad_value
 with pytest.raises(LayoutNotValidated):audit_candidate(d)

def test_5v_mcu_short_rejected():
 d=json.loads((ROOT/"hardware"/"istick_reference.json").read_text())
 d["nets"]["USB_VBUS_5V"].append("MCU.VDD")
 with pytest.raises(LayoutNotValidated):audit_candidate(d)

def test_sda_disconnect_rejected():
 d=json.loads((ROOT/"hardware"/"istick_reference.json").read_text())
 d["nets"]["I2C_SDA_3V3"].remove("ATECC.SDA")
 with pytest.raises(LayoutNotValidated):audit_candidate(d)

def test_all_physical_gates_accounted():
 d=record_report();assert assert_no_upgrade(d)
 assert len(REQUIRED)>=15 and all(x["status"]=="PENDING" for x in d["gates"].values())

@pytest.mark.parametrize('field',('physical_acceptance','production_ready'))
def test_unauthorized_upgrading_rejected(field):
 d=record_report();d[field]=True
 with pytest.raises(PhysicalClaimRejected):assert_no_upgrade(d)

def test_no_auto_upgrade_from_physical_log():
 with pytest.raises(PhysicalClaimRejected):record_report({"PHYSICAL_PRINTER":{"status":"PASSED","log_sha256":"0"*64}})

def test_requiring_valid_hdl_evidence():
 with pytest.raises(PhysicalClaimRejected):record_report({"RTL_SIMULATION":{"status":"PASSED","log_sha256":"garbage"}})

def test_hdl_pass_still_not_physical():
 d=record_report({"RTL_SIMULATION":{"status":"PASSED","log_sha256":"0"*64}})
 assert d["gates"]["RTL_SIMULATION"]["status"]=="PASSED_SOFTWARE_ONLY"
 assert d["physical_acceptance"] is False
