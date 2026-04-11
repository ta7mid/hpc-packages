#include <parmetis.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    MPI_Init(&argc, &argv);

    printf("ParMETIS version: %d.%d.%d\n",
           PARMETIS_MAJOR_VERSION,
           PARMETIS_MINOR_VERSION,
           PARMETIS_SUBMINOR_VERSION);

    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    /* Minimal ParMETIS call to verify linkage */
    idx_t vtxdist[] = {0, 3};
    idx_t xadj[]    = {0, 2, 3, 4};
    idx_t adjncy[]  = {1, 2, 0, 0};
    idx_t ncon      = 1;
    idx_t nparts    = 1;
    idx_t wgtflag   = 0;
    idx_t numflag   = 0;
    idx_t options[] = {0, 0, 0};
    idx_t edgecut;
    idx_t part[]    = {0, 0, 0};
    real_t tpwgts[] = {1.0};
    real_t ubvec[]  = {1.05};

    MPI_Comm comm = MPI_COMM_SELF;
    ParMETIS_V3_PartKway(vtxdist, xadj, adjncy, NULL, NULL,
                         &wgtflag, &numflag, &ncon, &nparts,
                         tpwgts, ubvec, options, &edgecut, part, &comm);

    printf("ParMETIS test passed (edgecut=%d)\n", (int)edgecut);

    MPI_Finalize();
    return 0;
}
