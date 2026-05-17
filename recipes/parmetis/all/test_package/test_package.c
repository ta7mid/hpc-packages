#include <mpi.h>
#include <parmetis.h>

#include <stdio.h>

int main(int argc, char **argv)
{
    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        fprintf(stderr, "MPI_Init failed\n");
        return 1;
    }

    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    /* Force the linker to resolve a real ParMETIS symbol without invoking it. */
    void (*sym)(void) = (void (*)(void))ParMETIS_V3_PartKway;
    (void)sym;

    /* Touch the types from metis.h transported via parmetis.h. */
    idx_t  idx_value  = (idx_t)0;
    real_t real_value = (real_t)0.0;
    (void)idx_value;
    (void)real_value;

    if (rank == 0) {
        printf("ParMETIS test_package OK: version %d.%d.%d\n",
               PARMETIS_MAJOR_VERSION,
               PARMETIS_MINOR_VERSION,
               PARMETIS_SUBMINOR_VERSION);
    }

    MPI_Finalize();
    return 0;
}
