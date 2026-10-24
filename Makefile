.PHONY: install test test-ibare test-polyglot test-e2e test-daemon build-ibare build-rtl build-daemon build-all

CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror -pedantic
IBARE_SRC = baremetal/ibare.c baremetal/sha256.c baremetal/ibare_ffi.c
IBARE_HEADERS = baremetal/ibare.h baremetal/sha256.h baremetal/ibare_ffi.h

install:
	python -m pip install -r requirements.txt

test-ibare: build-ibare
	./build/ibare_selftest

build-ibare: $(IBARE_SRC) $(IBARE_HEADERS) baremetal/ibare_host.c baremetal/test_ibare.c
	mkdir -p build
	$(CC) $(CFLAGS) -ffreestanding -fno-builtin -c baremetal/sha256.c -o build/sha256-freestanding.o
	$(CC) $(CFLAGS) -ffreestanding -fno-builtin -c baremetal/ibare.c -o build/ibare-freestanding.o
	$(CC) $(CFLAGS) -ffreestanding -fno-builtin -c baremetal/ibare_ffi.c -o build/ibare-ffi-freestanding.o
	$(CC) $(CFLAGS) -fPIC -shared baremetal/sha256.c baremetal/ibare_ffi.c -o build/libibare.so
	$(CC) $(CFLAGS) baremetal/ibare.c baremetal/sha256.c baremetal/ibare_host.c -o build/ibare_host
	$(CC) $(CFLAGS) baremetal/ibare.c baremetal/sha256.c baremetal/test_ibare.c -o build/ibare_selftest

build-render: build-ibare baremetal/render_combo.c
	$(CC) $(CFLAGS) -O2 baremetal/render_combo.c baremetal/sha256.c baremetal/ibare_ffi.c -o build/render_combo -lm

test-render: build-render
	python tools/generate_render_receipt.py
	python -m pytest -q tests/test_render_combo.py

test-polyglot:
	python -m polyglot.adapter --self-test
	python -m polyglot.adapter --root . --output POLYGLOT_PROCESS_RECEIPT.json

test: test-ibare test-render test-polyglot
	python -m pytest -q

build-all: test
	python -m proof.parallel_pop
	python -m proof.universe_manifest

build-daemon:
	mkdir -p build
	$(CXX) -std=c++20 -O3 -Wall -Wextra -Werror -pthread daemon/system_core.cpp -o build/ibare_daemon
	@if [ "$$(uname -m)" = "x86_64" ]; then $(CXX) -std=c++20 -O3 -Wall -Wextra -Werror -pthread -mavx2 daemon/system_core.cpp -o build/ibare_daemon_avx2; fi

test-daemon: build-daemon
	./build/ibare_daemon --self-test
	@if [ -x build/ibare_daemon_avx2 ] && grep -qw avx2 /proc/cpuinfo; then ./build/ibare_daemon_avx2 --self-test; else echo "AVX2 runtime skipped: CPU support not advertised"; fi
