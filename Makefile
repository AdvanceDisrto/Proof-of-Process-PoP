.PHONY: install test test-ibare build-ibare build-all

CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror -pedantic
IBARE_SRC = baremetal/ibare.c baremetal/sha256.c
IBARE_HEADERS = baremetal/ibare.h baremetal/sha256.h

install:
	python -m pip install -r requirements.txt

test-ibare: build-ibare
	./build/ibare_selftest

build-ibare: $(IBARE_SRC) $(IBARE_HEADERS) baremetal/ibare_host.c baremetal/test_ibare.c
	mkdir -p build
	$(CC) $(CFLAGS) -ffreestanding -fno-builtin -c baremetal/sha256.c -o build/sha256-freestanding.o
	$(CC) $(CFLAGS) -ffreestanding -fno-builtin -c baremetal/ibare.c -o build/ibare-freestanding.o
	$(CC) $(CFLAGS) baremetal/ibare.c baremetal/sha256.c baremetal/ibare_host.c -o build/ibare_host
	$(CC) $(CFLAGS) baremetal/ibare.c baremetal/sha256.c baremetal/test_ibare.c -o build/ibare_selftest

test: test-ibare
	python -m pytest -q

build-all: test
	python -m proof.parallel_pop
	python -m proof.universe_manifest
