/* admissibility_kernel.c
   Spherepop-style admissibility kernels in C */

#include <stdio.h>
#include <math.h>
#include <stdbool.h>

typedef struct {
    double density;
    double entropy;
    double curvature;
    double pressure;
    double salience;
} Bubble;

double admissibility_kernel(Bubble b) {
    double constraint =
        1.0 + fabs(b.curvature) + b.entropy + b.pressure;

    return (b.density * b.salience) / constraint;
}

bool is_admissible(Bubble b, double threshold) {
    return admissibility_kernel(b) >= threshold;
}

Bubble relax_bubble(Bubble b, double dt) {
    double k = admissibility_kernel(b);

    b.entropy   *= 1.0 - dt * k;
    b.pressure  *= 1.0 - dt * 0.5 * k;
    b.curvature *= 1.0 - dt * 0.25 * k;
    b.salience  += dt * k;

    if (b.entropy < 0.0) b.entropy = 0.0;
    if (b.pressure < 0.0) b.pressure = 0.0;

    return b;
}

int main(void) {
    Bubble b = {
        .density = 0.9,
        .entropy = 0.4,
        .curvature = 0.2,
        .pressure = 0.3,
        .salience = 0.8
    };

    for (int t = 0; t < 20; t++) {
        double k = admissibility_kernel(b);

        printf(
            "t=%02d kernel=%.4f entropy=%.4f pressure=%.4f curvature=%.4f admissible=%s\n",
            t,
            k,
            b.entropy,
            b.pressure,
            b.curvature,
            is_admissible(b, 0.25) ? "yes" : "no"
        );

        b = relax_bubble(b, 0.1);
    }

    return 0;
}
