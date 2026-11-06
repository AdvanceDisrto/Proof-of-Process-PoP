"""Deterministic register-level validation; must not claim external sensor presence."""
import csv
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/"hardware/strmkrd-node/bringup.py"
SPEC=spec_from_file_location("strmkrd_bringup_rev0", TARGET)
sys.modules[SPEC.name]=mod=module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

class FakeBus:
    def __init__(self, registers):
        self.registers=dict(registers)
        self.writes=[]
    def read_i2c_block_data(self,address,register,count):
        if (address,register) not in self.registers:
            raise OSError("absent physical register")
        raw=self.registers[(address,register)]
        return [raw>>8, raw&255]
    def write_i2c_block_data(self,address,register,data):
        self.writes.append((address,register,list(data)))
        self.registers[address,register]=(data[0]<<8)|data[1]

class TestNodeRev0(unittest.TestCase):
    def sensor_bus(self,temperature=0x0188,cal=2560):
        regs={(0x18,0x05):temperature,
            (0x40,0xFE):0x5449, (0x40,0x05):cal,
            (0x40,0x02):4000, (0x40,0x04):1000,
            (0x40,0x03):200}
        return FakeBus(regs)

    def test_mcp9808_24p5(self):
        r=mod.read_mcp9808(self.sensor_bus())
        self.assertEqual(r["temperature_c"],"24.5")
        self.assertEqual(r["temperature_sixteenths_c"],392)
    def test_mcp9808_negative(self):
        self.assertEqual(Decimal(mod.read_mcp9808(self.sensor_bus(0x1FF0))["temperature_c"]), Decimal(-1))
    def test_mcp9808_flags_mask(self):
        self.assertEqual(Decimal(mod.read_mcp9808(self.sensor_bus(0xE188))["temperature_c"]),Decimal("24.5"))
    def test_mcp9808_outside_range(self):
        with self.assertRaises(ValueError):mod.read_mcp9808(self.sensor_bus(0x0FFF))
    def test_ina226_calibration(self):
        self.assertEqual(mod.Ina226Config().calibration(),2560)
    def test_ina226_calibration_fail(self):
        with self.assertRaises(ValueError):mod.Ina226Config(shunt_ohms=Decimal(0)).calibration()
    def test_ina226_bus_and_power(self):
        r=mod.read_ina226(self.sensor_bus(),mod.Ina226Config())
        self.assertEqual(Decimal(r["bus_v"]),Decimal("5"))
        self.assertEqual(Decimal(r["current_a"]),Decimal("1"))
        self.assertEqual(Decimal(r["power_w"]),Decimal("5"))
    def test_ina226_missing_manufacturer(self):
        b=self.sensor_bus();b.registers[0x40,0xFE]=0x1234
        with self.assertRaises(ValueError):mod.read_ina226(b,mod.Ina226Config())
    def test_ina226_mismatched_calibration(self):
        with self.assertRaises(ValueError):mod.read_ina226(self.sensor_bus(cal=0),mod.Ina226Config())
    def test_explicit_calibration_write(self):
        b=self.sensor_bus(cal=0)
        mod.read_ina226(b,mod.Ina226Config(),initialize=True)
        self.assertEqual(b.writes,[(0x40,0x05,[0x0a,0x00])])
    def test_read_only_default(self):
        b=self.sensor_bus()
        mod.read_ina226(b,mod.Ina226Config())
        self.assertEqual(b.writes,[])
    def test_raw_i2c_observation_not_promoted(self):
        b=self.sensor_bus()
        r=mod.build_unsigned_observation(mod.read_mcp9808(b),
                  mod.read_ina226(b,mod.Ina226Config()),10000)
        self.assertEqual(r["source_tier"],"UNAUTHENTICATED_I2C_OBSERVATION")
        self.assertEqual(r["silicon_signature"],"NOT_PRESENT")
        self.assertEqual(r["physical_device_authentication"],"NOT_VERIFIED")
    def test_energy_integration(self):
        e=mod.EnergyIntegrator()
        self.assertEqual(e.observe(Decimal(0),Decimal(2)),Decimal(0))
        self.assertEqual(e.observe(Decimal(1),Decimal(4)),Decimal(3))
        self.assertEqual(e.intervals,1)
    def test_energy_stale_sample(self):
        e=mod.EnergyIntegrator()
        e.observe(Decimal(0),Decimal(2))
        with self.assertRaises(ValueError):e.observe(Decimal(10),Decimal(2))
    def test_energy_time_regression(self):
        e=mod.EnergyIntegrator()
        e.observe(Decimal(1),Decimal(2))
        with self.assertRaises(ValueError):e.observe(Decimal(1),Decimal(2))
    def test_self_test_cli(self):
        p=subprocess.run([sys.executable,str(TARGET),"--self-test"],
           capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("NOT_VERIFIED",p.stdout)
    def test_no_hardware_simulated_promotion(self):
        class AbsentBus:
            def read_i2c_block_data(self,*args): raise OSError("No attached sensor")
        with self.assertRaises(OSError):mod.read_mcp9808(AbsentBus())
    def test_nets_i2c_physical_pin(self):
        with (ROOT/"hardware/strmkrd-node/NETS_rev0.csv").open() as f:
            d={r["Signal"]:r for r in csv.DictReader(f)}
        self.assertEqual(d["SDA1"]["Pi_40pin_Physical"],"3")
        self.assertEqual(d["SCL1"]["Pi_40pin_Physical"],"5")
        self.assertEqual(d["SPU_INTERFACE_TBD"]["Review"],"HOLD")
    def test_bom_no_false_fab_ready(self):
        with (ROOT/"hardware/strmkrd-node/BOM_rev0.csv").open() as f:
            d=list(csv.DictReader(f))
        self.assertTrue(any("TBD" in r["MPN_or_development_part"] for r in d))
        self.assertTrue((ROOT/"hardware/strmkrd-node/MANUFACTURING_HOLD.md").exists())

if __name__=="__main__":
    unittest.main()
