#include <superlu_ddefs.h>

#include <stdio.h>

extern int superlu_dist_GetVersionNumber(int *major, int *minor, int *bugfix);

int main(void)
{
    int major = 0;
    int minor = 0;
    int patch = 0;

    if (SUPERLU_DIST_MAJOR_VERSION != 9 || SUPERLU_DIST_MINOR_VERSION != 2 || SUPERLU_DIST_PATCH_VERSION != 1) {
        fputs("Unexpected SuperLU_DIST version macros\n", stderr);
        return 1;
    }

    if (superlu_dist_GetVersionNumber(&major, &minor, &patch) != 0) {
        fputs("superlu_dist_GetVersionNumber failed\n", stderr);
        return 2;
    }

    if (major != 9 || minor != 2 || patch != 1) {
        fputs("Unexpected SuperLU_DIST runtime version\n", stderr);
        return 3;
    }

    return 0;
}
