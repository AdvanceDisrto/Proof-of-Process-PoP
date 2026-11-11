"""Assesses scoped Z3 policy only; does not fake an attached Linux device."""
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
src=ROOT/"hardware/strmkrd-node/observer.py"
spec=spec_from_file_location("strmkrd_observer_rev0",src)
sys.modules[spec.name]=mod=module_from_spec(spec)
spec.loader.exec_module(mod)

class TestStrmkrdObserver(unittest.TestCase):
    def observation(self,unit=392,bus_v="5.00000"):
        return {"source_tier":"UNAUTHENTICATED_I2C_OBSERVATION",
         "temperature":{"temperature_sixteenths_c":unit,
                         "source_tier":"UNAUTHENTICATED_I2C_OBSERVATION"},
         "power_meter":{"bus_v":bus_v,"power_w":"4.5",
                        "source_tier":"UNAUTHENTICATED_I2C_OBSERVATION"}}
    def test_nominal(self):
        r=mod.check_observation(self.observation())
        self.assertEqual(r["verdict"],"PROVEN_TRUE")
        self.assertEqual(r["source_tier"],"UNAUTHENTICATED_I2C_OBSERVATION")
    def test_cold_out_of_range(self):
        self.assertEqual(mod.check_observation(self.observation(unit=-641))["verdict"],"REFUTED_FALSE")
    def test_bus_over_range(self):
        self.assertEqual(mod.check_observation(self.observation(bus_v="36.00125"))["verdict"],"REFUTED_FALSE")
    def test_invalid_rounding(self):
        with self.assertRaises(ValueError):mod.check_observation(self.observation(bus_v="4.00001"))
    def test_no_spoofed_source(self):
        obs=self.observation();obs["source_tier"]="REAL_AUTHENTICATED_DEVICE"
        with self.assertRaises(ValueError):mod.check_observation(obs)
    def test_no_nan(self):
        with self.assertRaises(ValueError):mod.check_observation(self.observation(bus_v="NaN"))

if __name__=="__main__":unittest.main()
