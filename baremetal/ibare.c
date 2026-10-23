#include "ibare.h"
#include "sha256.h"

static int append_text(
    char *out,
    size_t out_size,
    size_t *used,
    const char *text
) {
    size_t i = 0U;

    while (text[i] != '\0') {
        if (*used + 1U >= out_size) {
            return -1;
        }
        out[*used] = text[i];
        ++(*used);
        ++i;
    }
    return 0;
}

static int append_u64(
    char *out,
    size_t out_size,
    size_t *used,
    uint64_t value
) {
    char digits[20];
    size_t count = 0U;

    do {
        digits[count++] = (char)('0' + (value % 10U));
        value /= 10U;
    } while (value != 0U && count < sizeof(digits));

    while (count > 0U) {
        if (*used + 1U >= out_size) {
            return -1;
        }
        out[*used] = digits[--count];
        ++(*used);
    }
    return 0;
}

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
    size_t used = 0U;

    if (observation == NULL || out == NULL || out_size == 0U) {
        return -1;
    }

    if (append_text(
            out, out_size, &used,
            "{\"spec\":\"innovulis-ibare/1.0\",\"arch\":\"") < 0 ||
        append_text(
            out, out_size, &used,
            observation->architecture != NULL
                ? observation->architecture
                : "unknown") < 0 ||
        append_text(
            out, out_size, &used,
            "\",\"timestamp_utc\":") < 0 ||
        append_u64(out, out_size, &used, observation->timestamp_utc) < 0 ||
        append_text(
            out, out_size, &used,
            ",\"tpm_device_present\":") < 0 ||
        append_text(
            out, out_size, &used,
            observation->tpm_device_present ? "true" : "false") < 0 ||
        append_text(out, out_size, &used, "}") < 0) {
        return -1;
    }

    out[used] = '\0';
    return (int)used;
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
