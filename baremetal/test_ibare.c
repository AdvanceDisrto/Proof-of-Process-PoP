#include "ibare.h"
#include "sha256.h"

#include <stdio.h>
#include <string.h>

static int test_sha256(void) {
    uint8_t hash[32];
    char hex[65];
    const char *expected =
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad";

    ibare_sha256_string("abc", hash);
    if (ibare_hex(hash, hex, sizeof(hex)) != 0) {
        return 1;
    }
    return strcmp(hex, expected) != 0;
}

static int test_payload(void) {
    ibare_observation observation = {
        .architecture = "test",
        .timestamp_utc = 1234567890ULL,
        .tpm_device_present = 0U
    };
    char payload[IBARE_RECEIPT_MAX];

    if (ibare_make_payload(&observation, payload, sizeof(payload)) < 0) {
        return 1;
    }

    return strcmp(
        payload,
        "{\"spec\":\"innovulis-ibare/1.0\",\"arch\":\"test\","
        "\"timestamp_utc\":1234567890,\"tpm_device_present\":false}"
    ) != 0;
}

int main(void) {
    if (test_sha256() != 0 || test_payload() != 0) {
        fputs("iBare self-test: FAIL\n", stderr);
        return 1;
    }
    puts("iBare self-test: PASS");
    return 0;
}
