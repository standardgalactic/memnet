/* spherepop_boundary.c
   Boundary admissibility between neighboring bubbles */

#include <stdio.h>
#include <math.h>
#include <stdbool.h>

typedef struct {
    double phase;
    double entropy;
    double salience;
    double radius;
} Bubble;

double boundary_alignment(Bubble a, Bubble b) {
    double phase_gap = fabs(a.phase - b.phase);
    double radius_gap = fabs(a.radius - b.radius);

    return (a.salience * b.salience) /
           (1.0 + phase_gap + radius_gap + a.entropy + b.entropy);
}

bool can_merge(Bubble a, Bubble b) {
    return boundary_alignment(a, b) > 0.25;
}

int main(void) {
    Bubble a = {0.10, 0.20, 0.90, 1.00};
    Bubble b = {0.16, 0.25, 0.85, 1.05};

    double k = boundary_alignment(a, b);

    printf("boundary kernel: %.4f\n", k);
    printf("merge admissible: %s\n", can_merge(a, b) ? "yes" : "no");

    return 0;
}
