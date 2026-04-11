#include <stdio.h>

#include "umfpack.h"
#include "cholmod.h"
#include "amd.h"
#include "SuiteSparse_config.h"

int main(void) {
    int v[3];
    SuiteSparse_version(v);
    printf("SuiteSparse version: %d.%d.%d\n", v[0], v[1], v[2]);

    /* Test CHOLMOD: create and free a simple common struct */
    cholmod_common c;
    cholmod_start(&c);
    printf("CHOLMOD started successfully\n");
    cholmod_finish(&c);

    /* Test AMD: get version */
    printf("AMD version: %d.%d.%d\n",
           AMD_MAIN_VERSION, AMD_SUB_VERSION, AMD_SUBSUB_VERSION);

    /* Test UMFPACK: get version */
    printf("UMFPACK version: %d.%d.%d\n",
           UMFPACK_MAIN_VERSION, UMFPACK_SUB_VERSION, UMFPACK_SUBSUB_VERSION);

    return 0;
}
