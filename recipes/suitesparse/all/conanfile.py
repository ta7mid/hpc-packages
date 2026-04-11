import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.0.9"

# Components built by this recipe (topologically ordered, leaves first)
_SUITESPARSE_PROJECTS = (
    "suitesparse_config;amd;btf;camd;ccolamd;colamd"
    ";cholmod;cxsparse;klu;ldl;umfpack;rbio;spqr"
)

# Installed library names in link order (dependents before dependencies)
_LIBS = [
    "spqr",
    "umfpack",
    "klu",
    "cholmod",
    "cxsparse",
    "rbio",
    "ldl",
    "ccolamd",
    "colamd",
    "camd",
    "btf",
    "amd",
    "suitesparseconfig",
]


class SuitesparseConan(ConanFile):
    name = "suitesparse"
    description = (
        "Suite of sparse matrix algorithms: CHOLMOD, UMFPACK, "
        "SPQR, KLU, AMD, COLAMD, and more"
    )
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later AND BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/DrTimothyAldenDavis/SuiteSparse"
    topics = ("sparse-matrix", "linear-algebra", "cholmod", "umfpack", "klu")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openblas/0.3.25")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Windows")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _openblas_lib_path(self):
        dep = self.dependencies["openblas"]
        libdirs = list(dep.cpp_info.libdirs)
        libs = list(dep.cpp_info.libs)
        # OpenBLAS uses components; aggregate component info
        if hasattr(dep.cpp_info, "components"):
            for comp in dep.cpp_info.components.values():
                libdirs.extend(comp.libdirs)
                libs.extend(comp.libs)
        for libdir in libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(dep.package_folder, libdir)
            for lib in libs:
                for ext in (".a", ".so", ".dylib"):
                    path = os.path.join(libdir, f"lib{lib}{ext}")
                    if os.path.exists(path):
                        return path
        return ""

    def generate(self):
        tc = CMakeToolchain(self)

        # Select which SuiteSparse sub-projects to build
        tc.variables["SUITESPARSE_ENABLE_PROJECTS"] = _SUITESPARSE_PROJECTS

        # Disable features we don't need
        tc.variables["SUITESPARSE_USE_CUDA"] = False
        tc.variables["SUITESPARSE_USE_FORTRAN"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["SUITESPARSE_DEMOS"] = False

        # OpenMP
        if not self.options.with_openmp:
            tc.variables["SUITESPARSE_USE_OPENMP"] = False

        # BLAS/LAPACK: point to openblas library directly
        blas_lib = self._openblas_lib_path()
        tc.variables["BLAS_LIBRARIES"] = blas_lib
        tc.variables["BLAS_FOUND"] = True
        tc.variables["BLA_VENDOR"] = "OpenBLAS"
        tc.variables["LAPACK_LIBRARIES"] = blas_lib
        tc.variables["LAPACK_FOUND"] = True

        # Use bundled METIS inside CHOLMOD (SuiteSparse_metis)
        tc.variables["CHOLMOD_CAMD"] = True

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # Also copy individual component licenses
        for subdir in ("AMD", "BTF", "CAMD", "CCOLAMD", "CHOLMOD", "COLAMD",
                       "CXSparse", "KLU", "LDL", "RBio", "SPQR",
                       "SuiteSparse_config", "UMFPACK"):
            for pattern in ("LICENSE*", "COPYING*", "Doc/License*"):
                copy(self, pattern,
                     os.path.join(self.source_folder, subdir),
                     os.path.join(self.package_folder, "licenses", subdir))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = _LIBS
        self.cpp_info.set_property("cmake_file_name", "SuiteSparse")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::SuiteSparse")

        self.cpp_info.includedirs = [
            os.path.join("include", "suitesparse"),
            "include",
        ]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "rt"])

        if self.options.with_openmp:
            if self.settings.compiler in ("gcc", "clang"):
                self.cpp_info.system_libs.append("gomp")
