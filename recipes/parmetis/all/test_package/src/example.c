#include <mpi.h>
#include <parmetis.h>

#include <stdio.h>

int main(int argc, char **argv)
{
    int (*part_kway)(idx_t *, idx_t *, idx_t *, idx_t *, idx_t *, idx_t *, idx_t *, idx_t *,
                     idx_t *, real_t *, real_t *, idx_t *, idx_t *, idx_t *, MPI_Comm *) =
        &ParMETIS_V3_PartKway;
    MPI_Comm comm = MPI_COMM_WORLD;

    if (PARMETIS_MAJOR_VERSION != 4 || PARMETIS_MINOR_VERSION != 0 || PARMETIS_SUBMINOR_VERSION != 3) {
        fputs("Unexpected ParMETIS version macros\n", stderr);
        return 1;
    }

    if (part_kway == NULL) {
        fputs("ParMETIS symbol resolution failed\n", stderr);
        return 2;
    }

    (void)argc;
    (void)argv;
    (void)comm;
    return 0;
}
