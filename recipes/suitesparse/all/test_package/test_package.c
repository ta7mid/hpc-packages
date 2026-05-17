#include <amd.h>
#include <cholmod.h>

#include <stdio.h>

int main(void)
{
    double control[AMD_CONTROL];
    amd_defaults(control);

    cholmod_common c;
    if (!cholmod_start(&c)) {
        fprintf(stderr, "cholmod_start failed\n");
        return 1;
    }

    printf("SuiteSparse test_package OK: AMD %d.%d.%d, CHOLMOD %d.%d.%d\n",
           AMD_MAIN_VERSION, AMD_SUB_VERSION, AMD_SUBSUB_VERSION,
           CHOLMOD_MAIN_VERSION, CHOLMOD_SUB_VERSION, CHOLMOD_SUBSUB_VERSION);

    if (!cholmod_finish(&c)) {
        fprintf(stderr, "cholmod_finish failed\n");
        return 1;
    }
    return 0;
}
