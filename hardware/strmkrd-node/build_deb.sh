#!/usr/bin/env bash
# Packaging does NOT activate the service, program silicon or prove physical identity.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
if [ "$#" -lt 2 ]; then echo 'usage: build_deb.sh amd64|arm64 ELF_PATH [OUT]' >&2; exit 2; fi
ARCH="$1"; BIN="$2"; OUT="$REPO/out/strmkrd-deb"
if [ "$#" -ge 3 ]; then OUT="$3"; fi
case "$ARCH" in amd64|arm64) ;; *) echo "Unsupported architecture $ARCH" >&2; exit 2;; esac
command -v dpkg-deb >/dev/null
command -v file >/dev/null
test -f "$BIN"
case "$ARCH" in
  amd64) file "$BIN" | grep -Eq 'ELF 64-bit.*x86-64' ;;
  arm64) file "$BIN" | grep -Eq 'ELF 64-bit.*ARM aarch64' ;;
esac || { echo 'ELF architecture mismatch: refusing package' >&2; exit 2; }
mkdir -p "$OUT"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/lib/strmkrd" "$STAGE/usr/bin" \
         "$STAGE/lib/systemd/system" "$STAGE/usr/share/doc/strmkrd-rev0"
install -m 0755 "$BIN" "$STAGE/usr/bin/strmkrd-i2c-driver"
install -m 0644 "$ROOT/observer.py" "$STAGE/usr/lib/strmkrd/observer.py"
install -m 0644 "$ROOT/bringup.py" "$STAGE/usr/lib/strmkrd/bringup.py"
install -m 0644 "$ROOT/strmkrd-observer.service" "$STAGE/lib/systemd/system/strmkrd-observer.service"
install -m 0644 "$ROOT/MANUFACTURING_HOLD.md" "$STAGE/usr/share/doc/strmkrd-rev0/MANUFACTURING_HOLD.md"
install -m 0644 "$ROOT/DEVICE_KEY_PROVISIONING_PROTOCOL.md" "$STAGE/usr/share/doc/strmkrd-rev0/DEVICE_KEY_PROVISIONING_PROTOCOL.md"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: strmkrd-rev0
Version: 0.1.0-1
Architecture: $ARCH
Maintainer: STRMKRD Engineering <noreply@strmkrd.com>
Depends: python3 (>= 3.11), python3-smbus2, python3-z3, adduser, systemd, libc6, libstdc++6
Section: electronics
Priority: optional
Homepage: https://github.com/AdvanceDisrto/Proof-of-Process-PoP
Description: STRMKRD Rev0 unsigned I2C observation and software Z3 checks
 No automatic services or silicon programming. Engineering prototype only.
 Hardware authentication and printed ipQR remain NOT VERIFIED.
EOF
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
  if ! getent passwd strmkrd >/dev/null; then
    adduser --system --group --no-create-home --home /nonexistent --disabled-login strmkrd
  fi
  # DO NOT grant I2C access or enable/start service without physical approval.
fi
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/postinst"
cat > "$STAGE/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = remove ] && command -v systemctl >/dev/null 2>&1; then
  systemctl stop strmkrd-observer.service >/dev/null 2>&1 || true
  systemctl disable strmkrd-observer.service >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/prerm"
NAME="strmkrd-rev0_0.1.0-1_$ARCH.deb"
dpkg-deb --build --root-owner-group "$STAGE" "$OUT/$NAME" >&2
dpkg-deb --info "$OUT/$NAME" >&2
dpkg-deb --contents "$OUT/$NAME" >&2
printf '%s\n' "$OUT/$NAME"
