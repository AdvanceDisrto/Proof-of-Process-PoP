#ifndef AMBIENT_HARVESTER_H
#define AMBIENT_HARVESTER_H
#include "sha256.h"
typedef struct{double barometric_mw_per_m2,teg_uw_per_cm2,radiative_uw_per_cm2,piezo_uw_per_cm2;}HarvesterDensities;
typedef struct{double barometric_m2,teg_cm2,radiative_cm2,piezo_cm2;}HarvesterInstallation;
typedef struct{double idle_power_w,useful_load_w;}HarvesterLoad;
typedef struct{double harvested_w,self_sustaining,can_power_load,coverage_ratio;}HarvesterBudget;
int harvester_compute(const HarvesterDensities*,const HarvesterInstallation*,const HarvesterLoad*,HarvesterBudget*);
int harvester_emit_receipt(const HarvesterBudget*,uint8_t out_hash[32]);
#endif
