#include <gridpack/environment/environment.hpp>

#include <mpi.h>

#include <iostream>

int main(int argc, char **argv)
{
    // gridpack::Environment initializes MPI, GA, and PETSc in one go, and
    // finalizes them in the destructor. This single-symbol use is enough to
    // validate the full transitive link (gridpack + Boost.MPI + GA + PETSc
    // + OpenMPI).
    gridpack::Environment env{argc, argv};

    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    if (rank == 0) {
        std::cout << "GridPACK test_package OK\n";
    }

    return 0;
}
