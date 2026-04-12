#include <parmetis.h>
#include <stdio.h>

/*
 * Verify compilation (parmetis.h includes mpi.h) and linkage.
 * We reference ParMETIS_V3_PartKway to force the linker to resolve
 * ParMETIS symbols. MPI_Init is not called because the MPI runtime
 * may not be available in all build environments.
 */

/* Prevent the compiler from optimizing away the symbol reference */
void (*volatile parmetis_sym)(void) =
    (void (*volatile)(void))ParMETIS_V3_PartKway;

int main(void) {
    printf("ParMETIS %d.%d.%d\n",
           PARMETIS_MAJOR_VERSION,
           PARMETIS_MINOR_VERSION,
           PARMETIS_SUBMINOR_VERSION);

    if (parmetis_sym) {
        printf("ParMETIS linkage OK\n");
    }
    return 0;
}
