#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "XGBoost_Optimized_split.h"

static void print_usage(const char *prog) {
    fprintf(stderr,
            "Usage:\n"
            "  %s <discharge_capacity_ah> <avg_voltage_v> <end_voltage_v> <discharge_time_s> <cv_charge_time_s>\n"
            "  %s    (then type 5 numbers on stdin)\n"
            "\n"
            "Feature order (must match training):\n"
            "  0 discharge_capacity (Ah)\n"
            "  1 avg_voltage (V)\n"
            "  2 end_voltage (V)\n"
            "  3 discharge_time (s)\n"
            "  4 cv_charge_time (s)\n",
            prog, prog);
}

static int parse_double_arg(const char *s, double *out) {
    char *end = NULL;
    errno = 0;
    double v = strtod(s, &end);
    if (errno != 0 || end == s || *end != '\0') {
        return 0;
    }
    *out = v;
    return 1;
}

int main(int argc, char **argv) {
    if (argc == 2 && (strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0)) {
        print_usage(argv[0]);
        return 0;
    }

    double x[5];

    if (argc == 6) {
        for (int i = 0; i < 5; i++) {
            if (!parse_double_arg(argv[i + 1], &x[i])) {
                fprintf(stderr, "Invalid number at position %d: '%s'\n", i + 1, argv[i + 1]);
                print_usage(argv[0]);
                return 2;
            }
        }
    } else if (argc == 1) {
        int n = scanf("%lf %lf %lf %lf %lf", &x[0], &x[1], &x[2], &x[3], &x[4]);
        if (n != 5) {
            fprintf(stderr, "Expected 5 numbers on stdin, got %d.\n", n);
            print_usage(argv[0]);
            return 2;
        }
    } else {
        print_usage(argv[0]);
        return 2;
    }

    double y = score(x);
    printf("%.6f\n", y);
    return 0;
}
