#include <petscksp.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    PetscErrorCode (*petsc_initialize)(int *, char ***, const char[], const char[]) = &PetscInitialize;
    PetscErrorCode (*petsc_finalize)(void) = &PetscFinalize;
    PetscErrorCode (*ksp_create)(MPI_Comm, KSP *) = &KSPCreate;
    PetscInt major = 0;
    PetscInt minor = 0;
    PetscInt patch = 0;
    PetscInt release = 0;
    const char *petsc_dir = NULL;
    char replaced_dir[PETSC_MAX_PATH_LEN] = {0};
    char version[256] = {0};

    if (petsc_initialize == NULL || petsc_finalize == NULL || ksp_create == NULL) {
        fputs("PETSc symbol resolution failed\n", stderr);
        return 1;
    }

    if (PetscGetVersion(version, sizeof(version)) != PETSC_SUCCESS) {
        fputs("PetscGetVersion failed\n", stderr);
        return 2;
    }

    if (PetscGetVersionNumber(&major, &minor, &patch, &release) != PETSC_SUCCESS) {
        fputs("PetscGetVersionNumber failed\n", stderr);
        return 3;
    }

    if (major != PETSC_VERSION_MAJOR || minor != PETSC_VERSION_MINOR || patch != PETSC_VERSION_SUBMINOR) {
        fputs("Unexpected PETSc runtime version\n", stderr);
        return 4;
    }

    if (release != PETSC_VERSION_RELEASE) {
        fputs("Unexpected PETSc release flag\n", stderr);
        return 5;
    }

    if (version[0] == '\0') {
        fputs("Empty PETSc version string\n", stderr);
        return 6;
    }

    if (PetscGetPetscDir(&petsc_dir) != PETSC_SUCCESS || petsc_dir == NULL || petsc_dir[0] == '\0') {
        fputs("PetscGetPetscDir failed\n", stderr);
        return 7;
    }

    if (strcmp(petsc_dir, PETSC_DIR) == 0) {
        fputs("PETSc directory was not resolved from the runtime environment\n", stderr);
        return 8;
    }

    if (PetscStrreplace(PETSC_COMM_SELF, "${PETSC_DIR}/include", replaced_dir, sizeof(replaced_dir)) != PETSC_SUCCESS) {
        fputs("PetscStrreplace failed\n", stderr);
        return 9;
    }

    if (strstr(replaced_dir, "${PETSC_DIR}") != NULL) {
        fputs("PETSc directory placeholder was not replaced\n", stderr);
        return 10;
    }

    return 0;
}
