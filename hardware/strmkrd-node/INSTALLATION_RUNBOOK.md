# STRMKRD Rev0 — Operator Installation and Manufacturing Handoff

**Safety classification: Engineering prototype.** These packages build and inspect on GitHub CI; they have NOT been installed on a physical Raspberry Pi, have NOT signed with an ATECC608C, and have NOT been certified by FIPS, NATO or any defense standards. The service remains disabled after installing the package.

## Releases

The CI artifact contains two architecture-specific packages: strmkrd-rev0_0.1.0-1_amd64.deb and strmkrd-rev0_0.1.0-1_arm64.deb, a SHA256SUMS.txt file, and ACCEPTANCE.json with unverified gates. amd64 is compiled and executed in GitHub's Linux x86-64 runner. arm64 is **cross-compiled, inspected, but NOT executed on an ARM64 host**.

The package installs a Linux native I2C register reader and a Python sensor/Z3 observer daemon. No permanent chip provisioning, no fake silicon key creation, and no FIPS validation are performed.

## Before any real hardware operation

1. Inspect real regulated supply rails with a multimeter and verify the external MCP9808 and INA226 module pinouts. Only use 3.3 V logic on the Raspberry expansion interface; do not place the INA226 sense pins directly in the load-current path.
2. Confirm INA226 actual address straps (Python supports --ina-address 0x40 or 0x41) and calibrate the shunt using a physically reviewed reference (calibration changes register state). Native C++ read-only probe currently targets 0x40.
3. Confirm Linux device tree, the presence of /dev/i2c-1, no conflicting kernel hwmon driver that already claims the INA226, and system Python visibility of apt-installed python3-z3 and python3-smbus2.
4. Confirm module package architecture matches dpkg --print-architecture. Verify SHA256SUMS.txt against the downloaded package files. SHA checks verify bytes, **not factory authenticity**.
5. Confirm cryptographic provisioning protocol review is complete **before** any future hardware locking command. This distribution contains none.

## Manual install (operator only)

On a physically tested Ubuntu Server 24.04/Debian host, choose the matching architecture package:

    sha256sum -c SHA256SUMS.txt
    sudo apt update
    sudo apt install ./strmkrd-rev0_0.1.0-1_arm64.deb
    /usr/bin/strmkrd-i2c-driver --self-test

Without real hardware, the following command MUST return a failure:

    /usr/bin/strmkrd-i2c-driver --hardware /dev/i2c-999

Read-only physical probe **after inspecting wiring**:

    /usr/bin/strmkrd-i2c-driver --hardware /dev/i2c-1
    sudo /usr/bin/python3 /usr/lib/strmkrd/observer.py --bus 1 --ina-address 0x40 --once

Grant group access only after physical inspection and approval:

    getent group i2c
    sudo usermod -aG i2c strmkrd
    sudo systemctl daemon-reload
    sudo systemctl enable --now strmkrd-observer.service
    systemctl status strmkrd-observer.service

To stop and disable:

    sudo systemctl disable --now strmkrd-observer.service

By design, the installer itself does **not** enable or start the service; the observer does not generate any hardware signature or mint QoW/PoP. The C++ binary only reads I2C and does not program permanent secure element configuration.

## Exact acceptance boundaries

- Compilation and Debian archive inspection do NOT establish a tested Pi boot or real device.
- Successful raw register reads prove a Linux I2C exchange, but no factory identity or calibration.
- Correct ECDSA P-256 verification proves only key possession; secure-element key origin requires a genuine manufacturer-signed trust path.
- PCB interposer Gerber previews have not cleared full DRC/ERC and are not a release for fabrication.
- Full 2000-pixel radial ipQR print+camera scanning has not been accepted.
- Any patent claim amendments require counsel and original-disclosure support.

## Build from checkout

    g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic hardware/strmkrd-node/strmkrd_driver.cpp -o strmkrd-i2c-driver-amd64
    bash hardware/strmkrd-node/build_deb.sh amd64 ./strmkrd-i2c-driver-amd64 ./out
    python -m unittest discover -s tests -p test_strmkrd_p256_protocol.py -v

Final release requires a separately signed manufacturing record, actual silicon/board acceptance, service authorization, and operator approval to merge.
