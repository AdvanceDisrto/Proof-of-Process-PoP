#include "antimatter_physics.h"
int am_compute_physics(AntimatterPhysics*p){if(!p)return -1;p->e_per_collision_j=2.0*AM_MP*AM_C*AM_C;p->energy_density_j_per_kg=AM_C*AM_C;p->ratio_vs_chemical=p->energy_density_j_per_kg/AM_CHEM_JKG;return 0;}
int am_emit_receipt(const AntimatterPhysics*p,uint8_t out[32]){if(!p||!out)return -1;ibare_sha256_ctx c;ibare_sha256_init(&c);ibare_sha256_update(&c,(const uint8_t*)p,sizeof(*p));ibare_sha256_final(&c,out);return 0;}
