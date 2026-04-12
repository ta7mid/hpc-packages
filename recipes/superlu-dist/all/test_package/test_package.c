#include <superlu_defs.h>
#include <stdio.h>

/*
 * Verify compilation (superlu_defs.h includes mpi.h) and linkage.
 * MPI_Init is not called because the MPI runtime may not be
 * available in all build environments.
 */

/* Force linker to resolve SuperLU_DIST symbols */
void (*volatile superlu_sym)(void) =
    (void (*volatile)(void))superlu_gridinit;

int main(void) {
    int v_major, v_minor, v_bugfix;
    superlu_dist_GetVersionNumber(&v_major, &v_minor, &v_bugfix);
    printf("SuperLU_DIST %d.%d.%d\n", v_major, v_minor, v_bugfix);

    if (superlu_sym) {
        printf("SuperLU_DIST linkage OK\n");
    }
    return 0;
}
