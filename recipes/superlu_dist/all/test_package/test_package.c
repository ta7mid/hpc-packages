#include <mpi.h>
#include <superlu_ddefs.h>

#include <stdio.h>

int main(int argc, char **argv)
{
    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        fprintf(stderr, "MPI_Init failed\n");
        return 1;
    }

    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    /* Force the linker to resolve a real SuperLU_DIST symbol without invoking it. */
    void (*sym)(void) = (void (*)(void))pdgssvx;
    (void)sym;

    if (rank == 0) {
        printf("SuperLU_DIST test_package OK: version %d.%d.%d\n",
               SUPERLU_DIST_MAJOR_VERSION,
               SUPERLU_DIST_MINOR_VERSION,
               SUPERLU_DIST_PATCH_VERSION);
    }

    MPI_Finalize();
    return 0;
}
