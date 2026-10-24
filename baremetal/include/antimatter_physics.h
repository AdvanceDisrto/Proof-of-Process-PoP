#ifndef ANTIMATTER_PHYSICS_H
#define ANTIMATTER_PHYSICS_H
#include "sha256.h"
#define AM_C 299792458.0
#define AM_MP 1.67262192369e-27
#define AM_CHEM_JKG 4.4e7
typedef struct{double e_per_collision_j,energy_density_j_per_kg,ratio_vs_chemical;}AntimatterPhysics;
int am_compute_physics(AntimatterPhysics*);
int am_emit_receipt(const AntimatterPhysics*,uint8_t out_hash[32]);
#endif
