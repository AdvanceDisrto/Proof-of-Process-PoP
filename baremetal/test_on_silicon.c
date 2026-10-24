#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "include/secure_enclave.h"
static void dump(const uint8_t *p){for(unsigned i=0;i<32;i++)printf("%02x",p[i]);putchar('\n');}
int main(void){IPOP_SharedMemoryRingBuffer mem={0};IPOP_EnclaveContext ctx;IPOP_StateMutation out;uint8_t receipt[32];const uint8_t p[]="OP_VALIDATE_SILICON: node-h100-prod-04";if(ipop_enclave_init(&ctx,&mem)!=0)return 1;if(ipop_agent_mutate_state(&ctx,IPOP_OPCODE_VALIDATE_SILICON,p,(uint16_t)(sizeof(p)-1),1778035000015000ULL)!=0)return 2;if(ipop_hardware_read_state(&ctx,&out)!=0)return 3;if(out.opcode!=1U||out.payload_len!=sizeof(p)-1||memcmp(out.payload,p,sizeof(p)-1)!=0)return 4;if(ipop_seal_memory_state(&ctx,receipt)!=0)return 5;printf("[PASS] mutation consumed; receipt=");dump(receipt);puts("[BOUNDARY] VERIFIED_PROCESS / physical_gate=ACTION_REQUIRED");return 0;}
