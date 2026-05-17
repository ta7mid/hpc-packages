#include <petsc.h>

#include <stdio.h>

int main(int argc, char **argv)
{
    PetscErrorCode ierr = PetscInitialize(&argc, &argv, NULL, NULL);
    if (ierr) {
        fprintf(stderr, "PetscInitialize failed: %d\n", (int)ierr);
        return 1;
    }

    PetscMPIInt rank = 0;
    MPI_Comm_rank(PETSC_COMM_WORLD, &rank);

    if (rank == 0) {
        printf("PETSc test_package OK: version %d.%d.%d\n",
               PETSC_VERSION_MAJOR,
               PETSC_VERSION_MINOR,
               PETSC_VERSION_SUBMINOR);
    }

    ierr = PetscFinalize();
    if (ierr) {
        fprintf(stderr, "PetscFinalize failed: %d\n", (int)ierr);
        return 1;
    }
    return 0;
}
