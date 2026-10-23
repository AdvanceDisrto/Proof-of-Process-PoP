#include "ibare.h"

#include <stdio.h>
#include <time.h>

#if defined(__unix__) || defined(__APPLE__)
#include <unistd.h>
#endif

static int tpm_device_present(void) {
#if defined(__unix__) || defined(__APPLE__)
    return access("/dev/tpm0", F_OK) == 0 ||
           access("/dev/tpmrm0", F_OK) == 0;
#else
    return 0;
#endif
}

int main(void) {
    ibare_observation observation = {
        .architecture = ibare_architecture(),
        .timestamp_utc = (uint64_t)time(NULL),
        .tpm_device_present = (uint8_t)tpm_device_present()
    };
    char payload[IBARE_RECEIPT_MAX];
    uint8_t hash[32];
    char hex[65];

    if (ibare_make_payload(&observation, payload, sizeof(payload)) < 0 ||
        ibare_receipt_hash(payload, hash) < 0 ||
        ibare_hex(hash, hex, sizeof(hex)) < 0) {
        fprintf(stderr, "iBare: receipt generation failed\n");
        return 1;
    }

    puts("=========================================");
    puts("i™ BARE-METAL RECEIPT");
    puts("=========================================");
    printf("Architecture: %s\n", observation.architecture);
    printf("TPM Device Presence: %s\n",
           observation.tpm_device_present ? "PRESENT" : "NOT_PRESENT");
    printf("Payload: %s\n", payload);
    printf("Hash: sha256:%s\n", hex);
    puts("State: VERIFIED_PROCESS (Software)");
    puts("Physical Gate: ACTION_REQUIRED");
    puts("Note: device presence is not TPM attestation.");
    puts("Truth is Processing Made Permanent.");
    return 0;
}
