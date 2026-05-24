/* spherepop_lattice.c
   Local bubble-to-bubble admissibility propagation */

#include <stdio.h>
#include <math.h>

#define N 16

typedef struct {
    double density;
    double entropy;
    double curvature;
    double salience;
} Cell;

double kernel(Cell c) {
    return (c.density * c.salience) /
           (1.0 + c.entropy + fabs(c.curvature));
}

void step(Cell field[N]) {
    Cell next[N];

    for (int i = 0; i < N; i++) {
        int left  = (i == 0) ? i : i - 1;
        int right = (i == N - 1) ? i : i + 1;

        double local =
            (kernel(field[left]) +
             kernel(field[i]) +
             kernel(field[right])) / 3.0;

        next[i] = field[i];

        next[i].entropy *= 1.0 - 0.05 * local;
        next[i].density += 0.02 * local;
        next[i].salience += 0.01 * local;
        next[i].curvature *= 0.99;
    }

    for (int i = 0; i < N; i++) {
        field[i] = next[i];
    }
}

int main(void) {
    Cell field[N];

    for (int i = 0; i < N; i++) {
        field[i].density = 0.5 + 0.03 * i;
        field[i].entropy = 0.8;
        field[i].curvature = sin(i * 0.5);
        field[i].salience = 0.4;
    }

    for (int t = 0; t < 10; t++) {
        step(field);

        printf("tick %d: ", t);

        for (int i = 0; i < N; i++) {
            printf("%.2f ", kernel(field[i]));
        }

        printf("\n");
    }

    return 0;
}
