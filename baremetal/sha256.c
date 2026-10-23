#include "sha256.h"

#include <string.h>

static const uint32_t k[64] = {
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
    0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
    0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
    0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
    0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
    0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
    0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
    0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
    0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
    0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
    0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
    0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
    0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
    0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
    0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
    0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U
};

static uint32_t rotr(uint32_t x, unsigned n) {
    return (x >> n) | (x << (32U - n));
}

static uint32_t ch(uint32_t x, uint32_t y, uint32_t z) {
    return (x & y) ^ (~x & z);
}

static uint32_t maj(uint32_t x, uint32_t y, uint32_t z) {
    return (x & y) ^ (x & z) ^ (y & z);
}

static uint32_t ep0(uint32_t x) {
    return rotr(x, 2U) ^ rotr(x, 13U) ^ rotr(x, 22U);
}

static uint32_t ep1(uint32_t x) {
    return rotr(x, 6U) ^ rotr(x, 11U) ^ rotr(x, 25U);
}

static uint32_t sig0(uint32_t x) {
    return rotr(x, 7U) ^ rotr(x, 18U) ^ (x >> 3U);
}

static uint32_t sig1(uint32_t x) {
    return rotr(x, 17U) ^ rotr(x, 19U) ^ (x >> 10U);
}

static uint32_t load_be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24U) |
           ((uint32_t)p[1] << 16U) |
           ((uint32_t)p[2] << 8U) |
           (uint32_t)p[3];
}

static void store_be32(uint8_t *p, uint32_t x) {
    p[0] = (uint8_t)(x >> 24U);
    p[1] = (uint8_t)(x >> 16U);
    p[2] = (uint8_t)(x >> 8U);
    p[3] = (uint8_t)x;
}

static void transform(ibare_sha256_ctx *ctx, const uint8_t data[64]) {
    uint32_t m[64];
    uint32_t a, b, c, d, e, f, g, h;

    for (unsigned i = 0; i < 16U; ++i) {
        m[i] = load_be32(data + (i * 4U));
    }
    for (unsigned i = 16U; i < 64U; ++i) {
        m[i] = sig1(m[i - 2U]) + m[i - 7U] +
               sig0(m[i - 15U]) + m[i - 16U];
    }

    a = ctx->state[0];
    b = ctx->state[1];
    c = ctx->state[2];
    d = ctx->state[3];
    e = ctx->state[4];
    f = ctx->state[5];
    g = ctx->state[6];
    h = ctx->state[7];

    for (unsigned i = 0; i < 64U; ++i) {
        uint32_t t1 = h + ep1(e) + ch(e, f, g) + k[i] + m[i];
        uint32_t t2 = ep0(a) + maj(a, b, c);
        h = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
    }

    ctx->state[0] += a;
    ctx->state[1] += b;
    ctx->state[2] += c;
    ctx->state[3] += d;
    ctx->state[4] += e;
    ctx->state[5] += f;
    ctx->state[6] += g;
    ctx->state[7] += h;
}

void ibare_sha256_init(ibare_sha256_ctx *ctx) {
    ctx->datalen = 0U;
    ctx->bitlen = 0U;
    ctx->state[0] = 0x6a09e667U;
    ctx->state[1] = 0xbb67ae85U;
    ctx->state[2] = 0x3c6ef372U;
    ctx->state[3] = 0xa54ff53aU;
    ctx->state[4] = 0x510e527fU;
    ctx->state[5] = 0x9b05688cU;
    ctx->state[6] = 0x1f83d9abU;
    ctx->state[7] = 0x5be0cd19U;
}

void ibare_sha256_update(ibare_sha256_ctx *ctx, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        ctx->data[ctx->datalen++] = data[i];
        if (ctx->datalen == 64U) {
            transform(ctx, ctx->data);
            ctx->bitlen += 512U;
            ctx->datalen = 0U;
        }
    }
}

void ibare_sha256_final(ibare_sha256_ctx *ctx, uint8_t hash[32]) {
    uint32_t i = ctx->datalen;

    if (ctx->datalen < 56U) {
        ctx->data[i++] = 0x80U;
        while (i < 56U) {
            ctx->data[i++] = 0U;
        }
    } else {
        ctx->data[i++] = 0x80U;
        while (i < 64U) {
            ctx->data[i++] = 0U;
        }
        transform(ctx, ctx->data);
        memset(ctx->data, 0, 56U);
    }

    ctx->bitlen += (uint64_t)ctx->datalen * 8U;
    for (unsigned j = 0; j < 8U; ++j) {
        ctx->data[63U - j] = (uint8_t)(ctx->bitlen >> (j * 8U));
    }
    transform(ctx, ctx->data);

    for (unsigned j = 0; j < 8U; ++j) {
        store_be32(hash + (j * 4U), ctx->state[j]);
    }
}

void ibare_sha256_string(const char *text, uint8_t hash[32]) {
    ibare_sha256_ctx ctx;
    size_t len = 0U;
    while (text[len] != '\0') {
        ++len;
    }
    ibare_sha256_init(&ctx);
    ibare_sha256_update(&ctx, (const uint8_t *)text, len);
    ibare_sha256_final(&ctx, hash);
}
