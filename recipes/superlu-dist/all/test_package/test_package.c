#include <superlu_defs.h>
#include <superlu_dist_config.h>
#include <mpi.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    MPI_Init(&argc, &argv);

    superlu_dist_GetVersionNumber(NULL, NULL, NULL);

    int v_major, v_minor, v_bugfix;
    superlu_dist_GetVersionNumber(&v_major, &v_minor, &v_bugfix);
    printf("SuperLU_DIST version: %d.%d.%d\n", v_major, v_minor, v_bugfix);

    /* Verify a basic grid can be initialized */
    gridinfo_t grid;
    superlu_gridinit(MPI_COMM_SELF, 1, 1, &grid);
    printf("SuperLU_DIST grid initialized successfully\n");
    superlu_gridexit(&grid);

    MPI_Finalize();
    return 0;
}
