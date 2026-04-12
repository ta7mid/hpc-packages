#include <stdio.h>

#include "SuiteSparse_config.h"
#include "amd.h"
#include "cholmod.h"
#include "umfpack.h"

int main(void) {
    int v[3];
    SuiteSparse_version(v);
    printf("SuiteSparse %d.%d.%d\n", v[0], v[1], v[2]);

    /* Test CHOLMOD: create and free a common struct */
    cholmod_common c;
    cholmod_start(&c);
    printf("CHOLMOD started\n");
    cholmod_finish(&c);

    /* Test AMD version macros */
    printf("AMD %d.%d.%d\n",
           AMD_MAIN_VERSION, AMD_SUB_VERSION, AMD_SUBSUB_VERSION);

    /* Test UMFPACK version macros */
    printf("UMFPACK %d.%d.%d\n",
           UMFPACK_MAIN_VERSION, UMFPACK_SUB_VERSION, UMFPACK_SUBSUB_VERSION);

    return 0;
}
