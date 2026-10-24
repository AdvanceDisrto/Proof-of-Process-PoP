#include <stdio.h>
#include <stdlib.h>
#include "antimatter_core.h"

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <delta_v_c> <beta_eff>\n", argv[0]);
        return 1;
    }

    char *end_dv = NULL;
    char *end_beta = NULL;
    double delta_v_c = strtod(argv[1], &end_dv);
    double beta_eff = strtod(argv[2], &end_beta);

    if (end_dv == argv[1] || *end_dv != '\0' ||
        end_beta == argv[2] || *end_beta != '\0') {
        fprintf(stderr, "invalid numeric input\n");
        return 1;
    }

    AntimatterBurn burn;
    int rc = antimatter_compute_burn(delta_v_c, beta_eff, &burn);
    if (rc != 0) {
        fprintf(stderr, "compute failed: %d\n", rc);
        return 2;
    }

    printf("{\n");
    printf("  \"delta_v_c\": %.17g,\n", burn.delta_v_c);
    printf("  \"effective_beta\": %.17g,\n", burn.effective_beta);
    printf("  \"mass_ratio_one_way\": %.17g,\n", burn.mass_ratio_one_way);
    printf("  \"mass_ratio_round_trip\": %.17g,\n", burn.mass_ratio_round_trip);
    printf("  \"mass_fraction_round_trip\": %.17g,\n", burn.mass_fraction_round_trip);
    printf("  \"proper_time_accel_years\": %.17g,\n", burn.proper_time_accel_years);
    printf("  \"coordinate_time_accel_years\": %.17g\n", burn.coordinate_time_accel_years);
    printf("}\n");
    return 0;
}
