#ifndef IPOP_SECURE_ENCLAVE_H
#define IPOP_SECURE_ENCLAVE_H
#include <stdint.h>
#include "../sha256.h"
#define IPOP_RING_BUFFER_SIZE 1024U
#define IPOP_MAX_MUTATION_PAYLOAD 256U
#define IPOP_OPCODE_VALIDATE_SILICON 0x01U
typedef struct { uint32_t mutation_id; uint32_t opcode; uint64_t timestamp_ns; uint16_t payload_len; uint8_t payload[IPOP_MAX_MUTATION_PAYLOAD]; } IPOP_StateMutation;
typedef struct { uint32_t head; uint32_t tail; IPOP_StateMutation buffer[IPOP_RING_BUFFER_SIZE]; } IPOP_SharedMemoryRingBuffer;
typedef struct { IPOP_SharedMemoryRingBuffer *ring_buffer; uint8_t tee_measurement_hash[32]; uint32_t physical_attestation_verified; } IPOP_EnclaveContext;
int ipop_enclave_init(IPOP_EnclaveContext *, IPOP_SharedMemoryRingBuffer *);
int ipop_agent_mutate_state(IPOP_EnclaveContext *, uint32_t, const uint8_t *, uint16_t, uint64_t);
int ipop_hardware_read_state(IPOP_EnclaveContext *, IPOP_StateMutation *);
int ipop_seal_memory_state(const IPOP_EnclaveContext *, uint8_t out_receipt[32]);
#endif
