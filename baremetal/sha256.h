#ifndef IBARE_SHA256_H
#define IBARE_SHA256_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint8_t data[64];
    uint32_t datalen;
    uint64_t bitlen;
    uint32_t state[8];
} ibare_sha256_ctx;

void ibare_sha256_init(ibare_sha256_ctx *ctx);
void ibare_sha256_update(ibare_sha256_ctx *ctx, const uint8_t *data, size_t len);
void ibare_sha256_final(ibare_sha256_ctx *ctx, uint8_t hash[32]);
void ibare_sha256_string(const char *text, uint8_t hash[32]);

#endif
