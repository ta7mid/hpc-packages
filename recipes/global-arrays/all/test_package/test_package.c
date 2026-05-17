#include <ga.h>
#include <mpi.h>

#include <stdio.h>

int main(int argc, char **argv)
{
    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        fprintf(stderr, "MPI_Init failed\n");
        return 1;
    }

    GA_Initialize();

    if (GA_Nodeid() == 0) {
        printf("Global Arrays test_package OK: %d processes\n", GA_Nnodes());
    }

    GA_Terminate();
    MPI_Finalize();
    return 0;
}
