/* spherepop_stack.c
   Nested bubbles as recursive admissibility shells */

#include <stdio.h>
#include <math.h>

#define DEPTH 8

typedef struct {
    double density;
    double entropy;
    double shell_pressure;
} Shell;

double shell_kernel(Shell s) {
    return s.density / (1.0 + s.entropy + s.shell_pressure);
}

double stack_admissibility(Shell shells[DEPTH]) {
    double product = 1.0;

    for (int i = 0; i < DEPTH; i++) {
        product *= shell_kernel(shells[i]);
    }

    return product;
}

int main(void) {
    Shell shells[DEPTH];

    for (int i = 0; i < DEPTH; i++) {
        shells[i].density = 0.9 - 0.04 * i;
        shells[i].entropy = 0.1 + 0.03 * i;
        shells[i].shell_pressure = 0.05 * i;
    }

    printf("recursive admissibility: %.8f\n",
           stack_admissibility(shells));

    return 0;
}
