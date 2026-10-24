#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "../baremetal/include/secure_enclave.h"
int main(void){IPOP_SharedMemoryRingBuffer m={0};IPOP_EnclaveContext c;IPOP_StateMutation o;uint8_t b=0xA5;assert(ipop_enclave_init(&c,&m)==0);assert(ipop_agent_mutate_state(&c,1,&b,1,1)==0);assert(ipop_agent_mutate_state(&c,2,&b,1,2)==0);assert(ipop_hardware_read_state(&c,&o)==0&&o.opcode==1);assert(ipop_hardware_read_state(&c,&o)==0&&o.opcode==2);assert(ipop_hardware_read_state(&c,&o)!=0);assert(ipop_agent_mutate_state(&c,3,&b,IPOP_MAX_MUTATION_PAYLOAD+1,3)==-1);return 0;}
