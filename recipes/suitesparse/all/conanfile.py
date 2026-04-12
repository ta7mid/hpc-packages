import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.1"

# Components to build (order does not matter; CMake resolves deps internally)
_PROJECTS = (
    "suitesparse_config;amd;btf;camd;ccolamd;colamd;"
    "cholmod;cxsparse;klu;ldl;umfpack;rbio;spqr"
)

# Installed library names in link order (dependents before dependencies)
_LIBS = [
    "spqr",
    "umfpack",
    "klu_cholmod",
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

    # SPQR is C++, so keep compiler.cppstd/libcxx

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openblas/0.3.27")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Windows")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _dep_lib_files(self, dep_name):
        """Collect absolute library file paths for a Conan dependency.

        Handles both flat and component-based package_info layouts.
        """
        dep = self.dependencies[dep_name]
        pkg = dep.package_folder

        # Aggregate libs and libdirs from top level and components
        libs = list(dep.cpp_info.libs)
        libdirs = list(dep.cpp_info.libdirs)
        for comp in dep.cpp_info.components.values():
            libs.extend(comp.libs)
            libdirs.extend(comp.libdirs)

        files = []
        for libdir in libdirs:
            abs_dir = libdir if os.path.isabs(libdir) else os.path.join(pkg, libdir)
            for lib in libs:
                for prefix, ext in [("lib", ".a"), ("lib", ".so"), ("lib", ".dylib"),
                                    ("", ".lib")]:
                    candidate = os.path.join(abs_dir, f"{prefix}{lib}{ext}")
                    if os.path.exists(candidate) and candidate not in files:
                        files.append(candidate)
                        break
        return files

    def generate(self):
        tc = CMakeToolchain(self)

        # Select sub-projects
        tc.variables["SUITESPARSE_ENABLE_PROJECTS"] = _PROJECTS

        # Disable unneeded features
        tc.variables["SUITESPARSE_USE_CUDA"] = False
        tc.variables["SUITESPARSE_USE_FORTRAN"] = False
        tc.variables["SUITESPARSE_USE_PYTHON"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["SUITESPARSE_DEMOS"] = False

        # OpenMP
        if not self.options.with_openmp:
            tc.variables["SUITESPARSE_USE_OPENMP"] = False

        # CHOLMOD options
        tc.variables["CHOLMOD_CAMD"] = True

        # BLAS/LAPACK: bypass FindBLAS by pre-setting result variables
        blas_libs = self._dep_lib_files("openblas")
        blas_str = ";".join(blas_libs)
        tc.cache_variables["BLAS_LIBRARIES"] = blas_str
        tc.cache_variables["BLAS_FOUND"] = "TRUE"
        tc.cache_variables["LAPACK_LIBRARIES"] = blas_str
        tc.cache_variables["LAPACK_FOUND"] = "TRUE"
        tc.cache_variables["BLA_VENDOR"] = "OpenBLAS"

        # Ensure openblas headers are findable
        dep = self.dependencies["openblas"]
        inc_dirs = [
            d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
            for d in dep.cpp_info.includedirs
        ]
        tc.cache_variables["BLAS_INCLUDE_DIRS"] = ";".join(inc_dirs)

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        # Copy per-component licenses
        for subdir in ("AMD", "BTF", "CAMD", "CCOLAMD", "CHOLMOD", "COLAMD",
                       "CXSparse", "KLU", "LDL", "RBio", "SPQR",
                       "SuiteSparse_config", "UMFPACK"):
            for pattern in ("LICENSE*", "COPYING*"):
                copy(
                    self,
                    pattern,
                    os.path.join(self.source_folder, subdir),
                    os.path.join(self.package_folder, "licenses", subdir),
                )
                copy(
                    self,
                    pattern,
                    os.path.join(self.source_folder, subdir, "Doc"),
                    os.path.join(self.package_folder, "licenses", subdir),
                )
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
