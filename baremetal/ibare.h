#ifndef IBARE_H
#define IBARE_H

#include <stddef.h>
#include <stdint.h>

#define IBARE_ARCH_MAX 16U
#define IBARE_RECEIPT_MAX 1024U

typedef struct {
    const char *architecture;
    uint64_t timestamp_utc;
    uint8_t tpm_device_present;
} ibare_observation;

const char *ibare_architecture(void);

int ibare_make_payload(
    const ibare_observation *observation,
    char *out,
    size_t out_size
);

int ibare_receipt_hash(
    const char *payload,
    uint8_t hash[32]
);

int ibare_hex(
    const uint8_t hash[32],
    char *out,
    size_t out_size
);

#endif
