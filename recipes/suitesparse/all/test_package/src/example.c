#include <SuiteSparse_config.h>
#include <amd.h>
#include <btf.h>
#include <camd.h>
#include <ccolamd.h>
#include <cholmod.h>
#include <colamd.h>
#include <cs.h>
#include <klu.h>
#include <ldl.h>
#include <umfpack.h>

#include <stdio.h>

static int check_version(const char *name, const int version[3], int major, int minor, int patch)
{
    if (version[0] != major || version[1] != minor || version[2] != patch) {
        fprintf(stderr, "Unexpected %s version: %d.%d.%d\n", name, version[0], version[1], version[2]);
        return 1;
    }
    return 0;
}

int main(void)
{
    int version[3] = {0, 0, 0};
    cholmod_common common;

    if (check_version(
            "SuiteSparse",
            (int[3]){SUITESPARSE_MAIN_VERSION, SUITESPARSE_SUB_VERSION, SUITESPARSE_SUBSUB_VERSION},
            7,
            12,
            2)) {
        return 1;
    }

    SuiteSparse_version(version);
    if (check_version("SuiteSparse", version, 7, 12, 2)) {
        return 2;
    }

    amd_version(version);
    if (check_version("AMD", version, AMD_MAIN_VERSION, AMD_SUB_VERSION, AMD_SUBSUB_VERSION)) {
        return 3;
    }

    btf_version(version);
    if (check_version("BTF", version, BTF_MAIN_VERSION, BTF_SUB_VERSION, BTF_SUBSUB_VERSION)) {
        return 4;
    }

    camd_version(version);
    if (check_version("CAMD", version, CAMD_MAIN_VERSION, CAMD_SUB_VERSION, CAMD_SUBSUB_VERSION)) {
        return 5;
    }

    ccolamd_version(version);
    if (check_version("CCOLAMD", version, CCOLAMD_MAIN_VERSION, CCOLAMD_SUB_VERSION, CCOLAMD_SUBSUB_VERSION)) {
        return 6;
    }

    colamd_version(version);
    if (check_version("COLAMD", version, COLAMD_MAIN_VERSION, COLAMD_SUB_VERSION, COLAMD_SUBSUB_VERSION)) {
        return 7;
    }

    cxsparse_version(version);
    if (check_version("CXSparse", version, CS_VER, CS_SUBVER, CS_SUBSUB)) {
        return 8;
    }

    ldl_version(version);
    if (check_version("LDL", version, LDL_MAIN_VERSION, LDL_SUB_VERSION, LDL_SUBSUB_VERSION)) {
        return 9;
    }

    klu_version(version);
    if (check_version("KLU", version, KLU_MAIN_VERSION, KLU_SUB_VERSION, KLU_SUBSUB_VERSION)) {
        return 10;
    }

    if (cholmod_start(&common) == 0) {
        fputs("cholmod_start failed\n", stderr);
        return 11;
    }
    if (cholmod_version(version) != CHOLMOD_VERSION) {
        fputs("Unexpected CHOLMOD version code\n", stderr);
        cholmod_finish(&common);
        return 12;
    }
    if (check_version("CHOLMOD", version, CHOLMOD_MAIN_VERSION, CHOLMOD_SUB_VERSION, CHOLMOD_SUBSUB_VERSION)) {
        cholmod_finish(&common);
        return 13;
    }
    cholmod_finish(&common);

    umfpack_version(version);
    if (check_version("UMFPACK", version, UMFPACK_MAIN_VERSION, UMFPACK_SUB_VERSION, UMFPACK_SUBSUB_VERSION)) {
        return 14;
    }

    return 0;
}
