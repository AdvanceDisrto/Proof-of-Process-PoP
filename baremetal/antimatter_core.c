#include "antimatter_core.h"

/*
 * Freestanding-friendly elementary functions for the bounded domain used by
 * this reference kernel. The implementation uses range reduction plus
 * convergent power series and does not call libm.
 */

static double am_atanh_series(double x) {
    double x2 = x * x;
    double term = x;
    double sum = 0.0;

    for (int n = 0; n < 64; ++n) {
        sum += term / (2.0 * (double)n + 1.0);
        term *= x2;
    }
    return sum;
}

static double am_log(double y) {
    if (y <= 0.0) {
        return 0.0;
    }

    /*
     * Reduce y into [1,2) by powers of two:
     * ln(y) = ln(m) + k*ln(2).
     */
    const double ln2 = 0.693147180559945309417232121458176568;
    int k = 0;
    double m = y;

    while (m >= 2.0) {
        m *= 0.5;
        ++k;
    }
    while (m < 1.0) {
        m *= 2.0;
        --k;
    }

    /* ln(m) = 2*atanh((m-1)/(m+1)); |x| < 1/3. */
    double x = (m - 1.0) / (m + 1.0);
    return 2.0 * am_atanh_series(x) + (double)k * ln2;
}

static double am_exp(double y) {
    /* The model domain keeps y comfortably below 1 for supplied scenarios. */
    double sum = 1.0;
    double term = 1.0;

    for (int n = 1; n < 64; ++n) {
        term *= y / (double)n;
        sum += term;
    }
    return sum;
}

static double am_sqrt_unit(double x) {
    if (x <= 0.0) {
        return 0.0;
    }

    double s = 1.0;
    for (int i = 0; i < 12; ++i) {
        s = 0.5 * (s + x / s);
    }
    return s;
}

int antimatter_compute_burn(double delta_v_c, double effective_beta,
                            AntimatterBurn *out_burn) {
    if (out_burn == 0) {
        return -1;
    }
    if (delta_v_c <= 0.0 || delta_v_c >= 0.999) {
        return -2;
    }
    if (effective_beta <= 0.0 || effective_beta >= 1.0) {
        return -3;
    }

    /*
     * Idealized relativistic rocket model:
     *
     *   rapidity = atanh(delta_v/c)
     *   M0/Mf = exp(rapidity / beta_eff)
     *
     * beta_eff is an assumed effective exhaust-velocity fraction, not a
     * measured antimatter-engine result.
     */
    double rapidity = am_atanh_series(delta_v_c);
    double mass_ratio_one = am_exp(rapidity / effective_beta);
    double mass_ratio_round_trip = mass_ratio_one * mass_ratio_one;
    double mass_fraction_round_trip = 1.0 - (1.0 / mass_ratio_round_trip);

    /* Constant 1-g proper acceleration. */
    double c_over_g = ANTIMATTER_C / ANTIMATTER_G;
    double proper_time_years =
        (c_over_g * rapidity) / ANTIMATTER_SEC_PER_YEAR;

    /* Earth-frame coordinate time at the end of acceleration. */
    double gamma_beta = delta_v_c / am_sqrt_unit(
        1.0 - (delta_v_c * delta_v_c));
    double coordinate_time_years =
        (c_over_g * gamma_beta) / ANTIMATTER_SEC_PER_YEAR;

    out_burn->delta_v_c = delta_v_c;
    out_burn->effective_beta = effective_beta;
    out_burn->mass_ratio_one_way = mass_ratio_one;
    out_burn->mass_ratio_round_trip = mass_ratio_round_trip;
    out_burn->mass_fraction_round_trip = mass_fraction_round_trip;
    out_burn->proper_time_accel_years = proper_time_years;
    out_burn->coordinate_time_accel_years = coordinate_time_years;
    return 0;
}

int antimatter_emit_receipt(const AntimatterBurn *burn, uint8_t out_hash[32]) {
    if (burn == 0 || out_hash == 0) {
        return -1;
    }

    /*
     * This hash is an integrity digest of the local model output. It is not
     * a signature and is not physical evidence.
     */
    uint8_t payload[6U * sizeof(double)];
    const double fields[6] = {
        burn->delta_v_c,
        burn->effective_beta,
        burn->mass_ratio_one_way,
        burn->mass_ratio_round_trip,
        burn->mass_fraction_round_trip,
        burn->proper_time_accel_years
    };

    for (int i = 0; i < 6; ++i) {
        const uint8_t *src = (const uint8_t *)&fields[i];
        for (size_t j = 0; j < sizeof(double); ++j) {
            payload[(size_t)i * sizeof(double) + j] = src[j];
        }
    }

    ibare_sha256_ctx ctx;
    ibare_sha256_init(&ctx);
    ibare_sha256_update(&ctx, payload, sizeof(payload));
    ibare_sha256_final(&ctx, out_hash);
    return 0;
}
