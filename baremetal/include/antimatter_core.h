#ifndef IPOP_ANTIMATTER_CORE_H
#define IPOP_ANTIMATTER_CORE_H

#include <stdint.h>
#include "../sha256.h"

/* Exact physical constants used by this reference model. */
#define ANTIMATTER_C 299792458.0
#define ANTIMATTER_G 9.80665
#define ANTIMATTER_SEC_PER_YEAR 31557600.0

/*
 * Effective exhaust fraction beta_e = v_e/c.
 *
 * This is a MODEL INPUT, not a measured property of an antimatter engine.
 * 0.60 is an intentionally explicit engineering assumption for the
 * charged-pion beamed-core scenario; it is not a claim that a nozzle exists.
 */
#define ANTIMATTER_BETA_EFF 0.60

typedef struct {
    double delta_v_c;
    double effective_beta;
    double mass_ratio_one_way;
    double mass_ratio_round_trip;
    double mass_fraction_round_trip;
    double proper_time_accel_years;
    double coordinate_time_accel_years;
} AntimatterBurn;

int antimatter_compute_burn(double delta_v_c, double effective_beta,
                            AntimatterBurn *out_burn);

int antimatter_emit_receipt(const AntimatterBurn *burn, uint8_t out_hash[32]);

#endif
