#include "ibare.h"
#include "sha256.h"

#include <stdio.h>

const char *ibare_architecture(void) {
#if defined(__x86_64__) || defined(_M_X64)
    return "x86_64";
#elif defined(__aarch64__) || defined(_M_ARM64)
    return "arm64";
#elif defined(__riscv)
    return "riscv";
#elif defined(__arm__)
    return "arm32";
#else
    return "unknown";
#endif
}

int ibare_make_payload(
    const ibare_observation *observation,
    char *out,
    size_t out_size
) {
    if (observation == NULL || out == NULL || out_size == 0U) {
        return -1;
    }

    int written = snprintf(
        out,
        out_size,
        "{\"spec\":\"innovulis-ibare/1.0\",\"arch\":\"%s\","
        "\"timestamp_utc\":%llu,\"tpm_device_present\":%s}",
        observation->architecture != NULL
            ? observation->architecture
            : "unknown",
        (unsigned long long)observation->timestamp_utc,
        observation->tpm_device_present ? "true" : "false"
    );

    if (written < 0 || (size_t)written >= out_size) {
        return -1;
    }
    return written;
}

int ibare_receipt_hash(const char *payload, uint8_t hash[32]) {
    if (payload == NULL || hash == NULL) {
        return -1;
    }
    ibare_sha256_string(payload, hash);
    return 0;
}

int ibare_hex(const uint8_t hash[32], char *out, size_t out_size) {
    static const char digits[] = "0123456789abcdef";
    if (hash == NULL || out == NULL || out_size < 65U) {
        return -1;
    }

    for (size_t i = 0; i < 32U; ++i) {
        out[i * 2U] = digits[hash[i] >> 4U];
        out[i * 2U + 1U] = digits[hash[i] & 0x0fU];
    }
    out[64] = '\0';
    return 0;
}
