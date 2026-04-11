#include <stdio.h>
#include <petsc.h>

int main(int argc, char **argv) {
    PetscInt major, minor, subminor;
    PetscErrorCode ierr;

    ierr = PetscInitialize(&argc, &argv, NULL, NULL);
    if (ierr) return 1;

    ierr = PetscGetVersionNumber(&major, &minor, &subminor, NULL);
    if (ierr) return 1;
    printf("PETSc version: %d.%d.%d\n", (int)major, (int)minor, (int)subminor);

    ierr = PetscFinalize();
    if (ierr) return 1;

    return 0;
}
