#include <amd.h>
#include <cholmod.h>
#include <umfpack.h>

int main() {
    cholmod_common common;
    cholmod_start(&common);
    cholmod_finish(&common);
    return 0;
}
