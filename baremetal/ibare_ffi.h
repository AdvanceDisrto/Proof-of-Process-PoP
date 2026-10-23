#ifndef IBARE_FFI_H
#define IBARE_FFI_H

#include <stddef.h>
#include <stdint.h>

#define IBARE_FFI_RECEIPT_SIZE 32U

typedef struct {
    uint64_t sequence_id;
    uint64_t timestamp_utc;
    uint8_t payload_hash[32];
    uint32_t platform_flags;
} ibare_receipt_manifest;

enum {
    IBARE_FLAG_ARCH_X86_64 = 1U << 0,
    IBARE_FLAG_ARCH_ARM64 = 1U << 1,
    IBARE_FLAG_ARCH_RISCV = 1U << 2,
    IBARE_FLAG_ARCH_ARM32 = 1U << 3,
    IBARE_FLAG_TPM_NODE_PRESENT = 1U << 8
};

uint32_t ibare_detect_architecture_flags(void);
int ibare_hash_bytes(const uint8_t *data, size_t len, uint8_t out[32]);
int ibare_generate_deterministic_receipt(
    const ibare_receipt_manifest *manifest,
    uint8_t out[IBARE_FFI_RECEIPT_SIZE]
);

#endif
