"""iNNOVULIS hardware readiness v0.2: honest physical gate diagnostics.

A matching device register or valid signature does not independently attest hardware.
This software NEVER locks secure-element slots, writes I2C configuration, prints,
programs an FPGA, or asserts that a real device is present in GitHub CI.
"""
from __future__ import annotations
import hashlib, json, math, secrets, subprocess
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

class GatePending(RuntimeError): pass

def ina226_word(raw):
    if type(raw) is not int or not 0 <= raw <= 65535:
        raise GatePending("invalid INA226 register word")
    return ((raw & 255) << 8) | (raw >> 8)

def identify_ina226(bus, address=0x40):
    if type(address) is not int or not 0x40 <= address <= 0x4f:
        raise GatePending("invalid INA226 address")
    # Texas Instruments SBOS547B: 0xFE = 0x5449, 0xFF = 0x2260.
    vendor=ina226_word(bus.read_word_data(address,0xfe))
    die=ina226_word(bus.read_word_data(address,0xff))
    if (vendor, die) != (0x5449, 0x2260):
        raise GatePending("INA226 register identity mismatch")
    return {"registers":"PASS_UNATTESTED","vendor_id":"5449","die_id":"2260",
            "source":"LIVE_BUS_READ_IF_REAL_BUS_SUPPLIED",
            "hardware_authenticated":False,
            "does_not_prove":["genuine device","calibrated shunt","computation performed"]}

def verify_p256_digest(public_key_pem,digest,signature):
    if type(digest) is not bytes or len(digest)!=32 or type(signature) is not bytes:
        return False
    try:
        key=serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key,ec.EllipticCurvePublicKey) or not isinstance(key.curve,ec.SECP256R1):
            return False
        if len(signature)==64:
            signature=utils.encode_dss_signature(int.from_bytes(signature[:32],"big"),
                                                int.from_bytes(signature[32:],"big"))
        key.verify(signature,digest,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except (ValueError,TypeError,InvalidSignature):
        return False

def challenge_signer(public_key_pem,sign,random_bytes=secrets.token_bytes):
    nonce=random_bytes(32)
    if type(nonce) is not bytes or len(nonce)!=32:
        raise GatePending("cryptographic challenge unavailable")
    digest=hashlib.sha256(b"iNNOVULIS/ATECC608C/challenge/v1\x00"+nonce).digest()
    signature=sign(digest)
    if not verify_p256_digest(public_key_pem,digest,signature):
        raise GatePending("ECDSA P256 signature invalid")
    return {"challenge_signature":"PASS","algorithm":"ECDSA_P256_SHA256",
            "challenge_sha256":digest.hex(),
            "hardware_private_key_provenance":"UNVERIFIED",
            "gate":"PENDING_INDEPENDENT_HARDWARE_ATTESTATION"}

def signer_command(binary,pinned_public_key_pem):
    if type(binary) is not str or not binary.startswith("/") or any(x in binary for x in ("\x00","\n")):
        raise GatePending("signer binary must be absolute operator-reviewed path")
    def sign(digest):
        try:
            proc=subprocess.run([binary,"--digest-hex",digest.hex()],capture_output=True,
                                timeout=10,check=False,text=True)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise GatePending("physical signer unavailable") from exc
        line=proc.stdout.strip()
        if (proc.returncode!=0 or len(line)>512 or not line or
                any(ch not in "0123456789abcdefABCDEF" for ch in line)):
            raise GatePending("signer returned invalid signature bytes")
        return bytes.fromhex(line)
    return challenge_signer(pinned_public_key_pem,sign)

def readiness(i2c="/dev/i2c-1"):
    return {"schema":"iNNOVULIS/physical-readiness/v0.2",
            "i2c_path_exists":Path(i2c).exists(),
            "physical_printer":"NOT_TESTED","real_ina226_measurement":"NOT_TESTED",
            "atecc608c_hardware_signing":"NOT_TESTED",
            "fpga_programming":"NOT_ATTEMPTED",
            "amd_gpu":"NOT_EXECUTED",
            "physical_acceptance":"ACTION_REQUIRED"}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    sub.add_parser("readiness")
    ina=sub.add_parser("ina226",help="read-only live sensor probe")
    ina.add_argument("--approved",action="store_true")
    ina.add_argument("--bus",type=int,default=1)
    ina.add_argument("--address",type=lambda x:int(x,0),default=0x40)
    ina.add_argument("--shunt-ohms",type=float,required=True)
    ina.add_argument("--calibration-id",required=True)
    ina.add_argument("--device-id",required=True)
    sig=sub.add_parser("p256-challenge",help="external operator-owned secure-element signer")
    sig.add_argument("--approved",action="store_true")
    sig.add_argument("--binary",required=True)
    sig.add_argument("--trusted-pem",required=True)
    args=p.parse_args(argv)
    try:
        if args.mode=="readiness":
            result=readiness()
        elif not args.approved:
            raise GatePending("physical device access requires explicit --approved")
        elif args.mode=="ina226":
            if not 0 < args.shunt_ohms <= 1 or not args.device_id or not args.calibration_id:
                raise GatePending("operator must supply actual shunt and calibration metadata")
            from smbus2 import SMBus
            from paper_console.energy import INA226, JouleIntegrator
            with SMBus(args.bus) as bus:
                ids=identify_ina226(bus,args.address)
                meter=INA226(bus_number=args.bus,address=args.address,
                            shunt_ohms=args.shunt_ohms,calibration_id=args.calibration_id,
                            device_id=args.device_id,bus=bus)
                integ=JouleIntegrator()
                import time
                sample1=meter.sample();integ.add(sample1)
                time.sleep(.25)
                sample2=meter.sample();integ.add(sample2)
                result={"reported_device":ids,"energy_estimate":integ.receipt(),
                       "hardware_attestation":"NOT_ESTABLISHED"}
        else:
            result=signer_command(args.binary,Path(args.trusted_pem).read_bytes())
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except (GatePending,OSError,ImportError,ValueError) as exc:
        print(json.dumps({"physical_gate":"NOT_CLEARED","reason":str(exc)},sort_keys=True))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
