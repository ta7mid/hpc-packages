#include <petsc.h>
#include <stdio.h>

/*
 * Verify compilation and linkage against PETSc.
 * MPI runtime is not started because the MPI daemon (orted) may not
 * be available in all Conan build environments.
 */

/* Force linker to resolve PETSc symbols */
void (*volatile petsc_sym)(void) =
    (void (*volatile)(void))PetscInitialize;

int main(void) {
    printf("PETSc %d.%d.%d\n",
           PETSC_VERSION_MAJOR,
           PETSC_VERSION_MINOR,
           PETSC_VERSION_SUBMINOR);

    if (petsc_sym) {
        printf("PETSc linkage OK\n");
    }
    return 0;
}
