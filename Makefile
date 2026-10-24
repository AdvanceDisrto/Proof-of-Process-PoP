.PHONY: install test test-cce test-platform-architecture test-buddy-liveness test-inetty test-signal-proof test-omnipresent test-ambient test-am-tiered build-omnipresent build-ambient build-am-physics test-antimatter test-tee-scrape test-on-silicon test-iska test-imcp test-ledger test-truth test-attestation-router test-physical-merkle test-ibare test-polyglot test-e2e test-daemon test-mmr test-hardened test-spu test-spu-reference test-spu-rtl test-spu-custody test-spu-materialization test-spu-ml-dsa test-spu-orfs test-spu-source-policy build-ibare build-rtl build-daemon build-hardened build-spu-reference build-all

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

test-iska:
	python -m pytest -q tests/test_iska.py

test-ledger:
	python -m pytest -q test_ledger_persistence.py

test-platform-architecture:
	python tools/platform_architecture_check.py
	python -m pytest -q tests/test_platform_architecture.py


test: test-platform-architecture test-ibare test-render test-polyglot test-iska test-imcp test-ledger test-tee-scrape test-antimatter test-am-tiered test-ambient test-omnipresent test-buddy-liveness test-inetty test-mmr
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

build-hardened:
	mkdir -p build
	$(CXX) -std=c++20 -O3 -Wall -Wextra -Werror -pthread daemon/omnibus_hardened.cpp -o build/omnibus_hardened -lcrypto
	@if [ "$$(uname -m)" = "x86_64" ]; then $(CXX) -std=c++20 -O3 -Wall -Wextra -Werror -pthread -mavx2 daemon/omnibus_hardened.cpp -o build/omnibus_hardened_avx2 -lcrypto; fi

test-hardened: build-hardened
	./build/omnibus_hardened
	@if [ -x build/omnibus_hardened_avx2 ] && grep -qw avx2 /proc/cpuinfo; then ./build/omnibus_hardened_avx2; else echo "AVX2 hardened runtime skipped: CPU support not advertised"; fi

build-spu-reference:
	cmake -S . -B build/spu -DCMAKE_BUILD_TYPE=Release
	cmake --build build/spu --parallel

test-spu-reference: build-spu-reference
	ctest --test-dir build/spu --output-on-failure

test-spu-rtl:
	mkdir -p build/spu
	iverilog -g2012 -Wall -o build/spu/route_tb rtl/route_partition_1024.sv rtl/tb_route_partition_1024.sv
	vvp build/spu/route_tb
	iverilog -g2012 -Wall -o build/spu/ispu10240_tb rtl/ispu10240/*.sv rtl/tb_ispu10240.sv
	vvp build/spu/ispu10240_tb

test-spu-custody:
	python tools/validate_spu_custody.py

test-spu-materialization:
	python tools/validate_materialization_topology.py materialization/topology.pending.json --expect-blocked

test-spu-ml-dsa:
	python -m pytest -q tests/test_ml_dsa.py

test-spu: test-spu-reference test-spu-rtl test-spu-custody test-spu-materialization test-spu-ml-dsa
	@echo "SPU software/RTL verification complete; physical gate remains ACTION_REQUIRED"

test-spu-orfs:
	bash physical/native-orfs/preflight.sh

test-spu-source-policy:
	python tools/validate_spu_source_policy.py

build-truth:
	mkdir -p build
	$(CXX) -std=c++20 -O2 -Wall -Wextra -Werror truth/truth_engine.cpp -o build/truth_engine

test-truth: build-truth
	./build/truth_engine
	python -m pytest -q tests/test_truth_engine.py


test-attestation-router:
	python physical/attestation_router.py
	python -m pytest -q tests/test_attestation_router.py


test-physical-merkle:
	python -m pytest -q tests/test_physical_merkle.py


test-on-silicon:
	mkdir -p build
	$(CC) $(CFLAGS) -Ibaremetal -o build/on_silicon_agency baremetal/test_on_silicon.c baremetal/core_kernel.c baremetal/sha256.c
	./build/on_silicon_agency
	$(CC) $(CFLAGS) -Ibaremetal -o build/on_silicon_safety tests/test_on_silicon.c baremetal/core_kernel.c baremetal/sha256.c
	./build/on_silicon_safety
	@echo "On-Silicon Agency reference verification complete; physical TEE gate remains ACTION_REQUIRED"


test-tee-scrape:
	python -m pytest tests/test_tee_scrape.py -v

build-antimatter:
	mkdir -p build
	$(CC) $(CFLAGS) -Ibaremetal -Ibaremetal/include \
		baremetal/antimatter_core.c baremetal/sha256.c baremetal/test_antimatter.c \
		-o build/antimatter_kernel

test-antimatter: build-antimatter
	python -m pytest -q tests/test_antimatter.py
	python tools/antimatter_simulator.py evidence/antimatter_evidence_receipt.json

build-omnipresent:
	mkdir -p build
	$(CC) $(CFLAGS) -Ibaremetal -Ibaremetal/include baremetal/omnipresent_mesh.c baremetal/sha256.c baremetal/test_omnipresent_mesh.c -o build/mesh_test
	./build/mesh_test

test-omnipresent: build-omnipresent
	python -m pytest -q tests/test_omnipresent_mesh.py
	python tools/omnipresent_mesh_verifier.py

build-ambient:
	mkdir -p build
	$(CC) $(CFLAGS) -Ibaremetal -Ibaremetal/include -c baremetal/ambient_harvester.c -o build/ambient_harvester.o

test-ambient: build-ambient
	python -m pytest -q tests/test_ambient_harvester.py
	python tools/ambient_harvester_verifier.py

build-am-physics:
	mkdir -p build
	$(CC) $(CFLAGS) -Ibaremetal -Ibaremetal/include -c baremetal/antimatter_physics.c -o build/antimatter_physics.o

test-am-tiered: build-am-physics
	python -m pytest -q tests/test_antimatter_tiered.py
	python tools/antimatter_tiered_receipt.py

# Sovereign signal / iNetty proof-of-process surfaces. These are cryptographic software proofs;
# physical radio and TEE gates remain ACTION_REQUIRED.
test-buddy-liveness:
	python -m pytest -q tests/test_buddy_liveness.py
	python tools/buddy_liveness_proof.py self-test

test-inetty:
	python -m pytest -q tests/test_inetty_smallest_proof.py
	python tools/inetty_smallest_proof.py

test-cce:
	mkdir -p "${RUN_ALL_OUT:-evidence}"
	python -m pytest -q tests/test_cce.py
	python -m tools.cce_prototype > "${RUN_ALL_OUT:-evidence}/cce_prototype_receipt.json"
	python tools/epistemic_tier_map.py > "${RUN_ALL_OUT:-evidence}/epistemic_tier_map.json"

test-signal-proof: test-buddy-liveness test-inetty
	@echo "Signal proof-of-process complete; physical gate remains ACTION_REQUIRED"

.PHONY: test-ci-receipts status

test-ci-receipts:
	python -m pytest tests/test_ci_receipts.py -v

status:
	python tools/status_monitor.py


test-mmr:
	python -m pytest -q tests/test_mmr_pipeline.py
	python tools/mmr_pipeline.py 5000 evidence/mmr_5000.json
	python tools/mmr_artifact_seal.py evidence/mmr_5000.json local-run evidence/mmr_artifact_seal.json
