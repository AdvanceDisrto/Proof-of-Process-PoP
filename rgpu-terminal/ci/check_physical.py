"""Read-only physical discovery. Presence is NOT authentication or acceptance."""
import glob,json,shutil,sys
from pathlib import Path
status={
 'i2c_device_nodes':glob.glob('/dev/i2c-*'),
 'tpm_device_nodes':glob.glob('/dev/tpm*'),
 'usb_printer_nodes':glob.glob('/dev/usb/lp*'),
 'vivado_cli_available':bool(shutil.which('vivado')),
 'tpm2_getrandom_available':bool(shutil.which('tpm2_getrandom')),
 'i2cdetect_available':bool(shutil.which('i2cdetect')),
 'hardware_signatures_verified':False,
 'physical_energy_measurement_verified':False,
 'physical_receipt_printed':False,
 'comment':'Read-only host checks cannot certify device identities or physical observations.'
}
print(json.dumps(status,sort_keys=True,indent=2))
