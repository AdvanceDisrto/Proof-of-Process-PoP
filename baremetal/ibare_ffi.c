#include "ibare_ffi.h"
#include "sha256.h"

static void put_u32_be(uint8_t *out, uint32_t value) {
    out[0] = (uint8_t)(value >> 24U);
    out[1] = (uint8_t)(value >> 16U);
    out[2] = (uint8_t)(value >> 8U);
    out[3] = (uint8_t)value;
}

static void put_u64_be(uint8_t *out, uint64_t value) {
    for (size_t i = 0U; i < 8U; ++i) {
        out[7U - i] = (uint8_t)(value >> (i * 8U));
    }
}

uint32_t ibare_detect_architecture_flags(void) {
#if defined(__x86_64__) || defined(_M_X64)
    return IBARE_FLAG_ARCH_X86_64;
#elif defined(__aarch64__) || defined(_M_ARM64)
    return IBARE_FLAG_ARCH_ARM64;
#elif defined(__riscv)
    return IBARE_FLAG_ARCH_RISCV;
#elif defined(__arm__)
    return IBARE_FLAG_ARCH_ARM32;
#else
    return 0U;
#endif
}

int ibare_hash_bytes(const uint8_t *data, size_t len, uint8_t out[32]) {
    ibare_sha256_ctx ctx;
    if ((data == NULL && len != 0U) || out == NULL) return -1;
    ibare_sha256_init(&ctx);
    if (len != 0U) ibare_sha256_update(&ctx, data, len);
    ibare_sha256_final(&ctx, out);
    return 0;
}

int ibare_generate_deterministic_receipt(
    const ibare_receipt_manifest *manifest,
    uint8_t out[IBARE_FFI_RECEIPT_SIZE]
) {
    uint8_t encoded[52];
    if (manifest == NULL || out == NULL) return -1;
    put_u64_be(encoded, manifest->sequence_id);
    put_u64_be(encoded + 8U, manifest->timestamp_utc);
    for (size_t i = 0U; i < 32U; ++i) encoded[16U + i] = manifest->payload_hash[i];
    put_u32_be(encoded + 48U, manifest->platform_flags);
    return ibare_hash_bytes(encoded, sizeof(encoded), out);
}
