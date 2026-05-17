import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir

required_conan_version = ">=2.0.9"


# Component key (Conan-side) -> (upstream project token used in
# SUITESPARSE_ENABLE_PROJECTS, installed library OUTPUT_NAME, namespaced
# CMake target, per-component config name).
_PROJECT_TOKEN = {
    "suitesparseconfig": "suitesparse_config",
    "amd":               "amd",
    "colamd":            "colamd",
    "camd":              "camd",
    "ccolamd":           "ccolamd",
    "btf":               "btf",
    "cholmod":           "cholmod",
    "umfpack":           "umfpack",
    "klu":               "klu",
    "ldl":               "ldl",
    "cxsparse":          "cxsparse",
    "spqr":              "spqr",
    "paru":              "paru",
    "rbio":              "rbio",
    "spex":              "spex",
    "graphblas":         "graphblas",
    "lagraph":           "lagraph",
    "mongoose":          "mongoose",
}

_LIB_NAME = {
    "suitesparseconfig": "suitesparseconfig",
    "amd":               "amd",
    "colamd":            "colamd",
    "camd":              "camd",
    "ccolamd":           "ccolamd",
    "btf":               "btf",
    "cholmod":           "cholmod",
    "umfpack":           "umfpack",
    "klu":               "klu",
    "ldl":               "ldl",
    "cxsparse":          "cxsparse",
    "spqr":              "spqr",
    "paru":              "paru",
    "rbio":              "rbio",
    "spex":              "spex",
    "graphblas":         "graphblas",
    "lagraph":           "lagraph",
    "mongoose":          "suitesparse_mongoose",
}

_TARGET_NAME = {
    "suitesparseconfig": "SuiteSparse::SuiteSparseConfig",
    "amd":               "SuiteSparse::AMD",
    "colamd":            "SuiteSparse::COLAMD",
    "camd":              "SuiteSparse::CAMD",
    "ccolamd":           "SuiteSparse::CCOLAMD",
    "btf":               "SuiteSparse::BTF",
    "cholmod":           "SuiteSparse::CHOLMOD",
    "umfpack":           "SuiteSparse::UMFPACK",
    "klu":               "SuiteSparse::KLU",
    "ldl":               "SuiteSparse::LDL",
    "cxsparse":          "SuiteSparse::CXSparse",
    "spqr":              "SuiteSparse::SPQR",
    "paru":              "SuiteSparse::ParU",
    "rbio":              "SuiteSparse::RBio",
    "spex":              "SuiteSparse::SPEX",
    "graphblas":         "SuiteSparse::GraphBLAS",
    "lagraph":           "SuiteSparse::LAGraph",
    "mongoose":          "SuiteSparse::Mongoose",
}

_CMAKE_FILE_NAME = {
    "suitesparseconfig": "SuiteSparse_config",
    "amd":               "AMD",
    "colamd":            "COLAMD",
    "camd":              "CAMD",
    "ccolamd":           "CCOLAMD",
    "btf":               "BTF",
    "cholmod":           "CHOLMOD",
    "umfpack":           "UMFPACK",
    "klu":               "KLU",
    "ldl":               "LDL",
    "cxsparse":          "CXSparse",
    "spqr":              "SPQR",
    "paru":              "ParU",
    "rbio":              "RBio",
    "spex":              "SPEX",
    "graphblas":         "GraphBLAS",
    "lagraph":           "LAGraph",
    "mongoose":          "Mongoose",
}

_LICENSE_DIR = {
    "suitesparseconfig": "SuiteSparse_config",
    "amd":               "AMD",
    "colamd":            "COLAMD",
    "camd":              "CAMD",
    "ccolamd":           "CCOLAMD",
    "btf":               "BTF",
    "cholmod":           "CHOLMOD",
    "umfpack":           "UMFPACK",
    "klu":               "KLU",
    "ldl":               "LDL",
    "cxsparse":          "CXSparse",
    "spqr":              "SPQR",
    "paru":              "ParU",
    "rbio":              "RBio",
    "spex":              "SPEX",
    "graphblas":         "GraphBLAS",
    "lagraph":           "LAGraph",
    "mongoose":          "Mongoose",
}

# Intra-package direct link deps. Transitive closure is handled by Conan.
_INTERNAL_REQUIRES = {
    "suitesparseconfig": [],
    "amd":               ["suitesparseconfig"],
    "colamd":            ["suitesparseconfig"],
    "camd":              ["suitesparseconfig"],
    "ccolamd":           ["suitesparseconfig"],
    "btf":               ["suitesparseconfig"],
    "ldl":               ["suitesparseconfig", "amd"],
    "cxsparse":          ["suitesparseconfig"],
    "cholmod":           ["suitesparseconfig", "amd", "colamd", "camd", "ccolamd"],
    "umfpack":           ["suitesparseconfig", "amd", "cholmod"],
    "klu":               ["suitesparseconfig", "amd", "colamd", "btf", "cholmod"],
    "spqr":              ["suitesparseconfig", "amd", "colamd", "cholmod"],
    "paru":              ["suitesparseconfig", "amd", "colamd", "cholmod", "umfpack"],
    "rbio":              ["suitesparseconfig"],
    "spex":              ["suitesparseconfig", "amd", "colamd"],
    "graphblas":         ["suitesparseconfig"],
    "lagraph":           ["suitesparseconfig", "graphblas"],
    "mongoose":          ["suitesparseconfig"],
}

# Components that link BLAS/LAPACK (openblas brings both).
_BLAS_USERS = {"cholmod", "umfpack", "spqr", "paru", "spex"}

_DEFAULT_COMPONENTS = (
    "suitesparseconfig",
    "amd", "colamd", "camd", "ccolamd", "btf",
    "cholmod", "umfpack", "klu", "ldl", "cxsparse",
)


class SuiteSparseConan(ConanFile):
    name = "suitesparse"
    description = (
        "SuiteSparse is a suite of sparse-matrix algorithms (AMD, CHOLMOD, "
        "UMFPACK, KLU, SPQR, and more) for direct factorization, ordering, "
        "and graph algorithms on sparse linear systems."
    )
    # SuiteSparse is multi-licensed: AMD/COLAMD/CAMD/CCOLAMD are BSD-3-Clause;
    # BTF/LDL/CXSparse/KLU/CHOLMOD-core are LGPL-2.1+; UMFPACK/SPQR/ParU/RBio/
    # Mongoose plus CHOLMOD Modify+Supernodal are GPL-2.0+; GraphBLAS is
    # Apache-2.0. Per-subproject LICENSE files are copied into licenses/.
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later AND BSD-3-Clause AND Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/DrTimothyAldenDavis/SuiteSparse"
    topics = (
        "sparse-matrix", "linear-algebra", "factorization", "cholmod",
        "umfpack", "amd", "klu", "spqr", "hpc",
    )

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared":         [True, False],
        "fPIC":           [True, False],
        "with_openmp":    [True, False],
        "with_cuda":      [True, False],
        "with_fortran":   [True, False],
        "index64":        [True, False],
        "with_spqr":      [True, False],
        "with_paru":      [True, False],
        "with_rbio":      [True, False],
        "with_spex":      [True, False],
        "with_graphblas": [True, False],
        "with_lagraph":   [True, False],
        "with_mongoose":  [True, False],
    }
    default_options = {
        "shared":         False,
        "fPIC":           True,
        "with_openmp":    True,
        "with_cuda":      False,
        "with_fortran":   False,
        "index64":        False,
        "with_spqr":      False,
        "with_paru":      False,
        "with_rbio":      False,
        "with_spex":      False,
        "with_graphblas": False,
        "with_lagraph":   False,
        "with_mongoose":  False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Only strip C++ settings if no C++ subproject is enabled.
        if not (self.options.with_spqr or self.options.with_paru
                or self.options.with_mongoose):
            self.settings.rm_safe("compiler.cppstd")
            self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # CHOLMOD's installed headers reference cblas.h, so headers propagate.
        self.requires(
            "openblas/[>=0.3.27 <1]",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <4]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} does not support Windows. SuiteSparse targets POSIX systems."
            )
        if self.options.with_cuda:
            raise ConanInvalidConfiguration(
                f"{self.ref} option with_cuda=True is not yet supported "
                "(no Conan CUDA toolchain dependency wired)."
            )
        if self.options.with_lagraph and not self.options.with_graphblas:
            raise ConanInvalidConfiguration(
                f"{self.ref} option with_lagraph=True requires with_graphblas=True."
            )
        if self.options.with_paru and not self.options.with_openmp:
            raise ConanInvalidConfiguration(
                f"{self.ref} option with_paru=True requires with_openmp=True."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _enabled_components(self):
        comps = list(_DEFAULT_COMPONENTS)
        for opt_key, comp_key in (
            ("with_spqr",      "spqr"),
            ("with_paru",      "paru"),
            ("with_rbio",      "rbio"),
            ("with_spex",      "spex"),
            ("with_graphblas", "graphblas"),
            ("with_lagraph",   "lagraph"),
            ("with_mongoose",  "mongoose"),
        ):
            if self.options.get_safe(opt_key):
                comps.append(comp_key)
        return comps

    def _enable_projects_value(self):
        return ";".join(_PROJECT_TOKEN[c] for c in self._enabled_components())

    def generate(self):
        tc = CMakeToolchain(self)
        cv = tc.cache_variables

        cv["SUITESPARSE_ENABLE_PROJECTS"] = self._enable_projects_value()

        cv["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        cv["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        cv["GRAPHBLAS_BUILD_STATIC_LIBS"] = (
            bool(self.options.with_graphblas) and not bool(self.options.shared)
        )

        cv["SUITESPARSE_USE_OPENMP"]      = bool(self.options.with_openmp)
        cv["SUITESPARSE_USE_CUDA"]        = bool(self.options.with_cuda)
        cv["SUITESPARSE_USE_FORTRAN"]     = bool(self.options.with_fortran)
        cv["SUITESPARSE_USE_64BIT_BLAS"]  = bool(self.options.index64)

        cv["SUITESPARSE_DEMOS"] = False

        cv["CHOLMOD_CAMD"]        = True
        cv["CHOLMOD_SUPERNODAL"]  = True
        cv["KLU_USE_CHOLMOD"]     = True
        cv["UMFPACK_USE_CHOLMOD"] = True

        # Never let upstream substitute a system copy of a sibling subproject.
        for tok in ("BTF", "CHOLMOD", "AMD", "COLAMD", "CAMD", "CCOLAMD",
                    "GRAPHBLAS", "SUITESPARSE_CONFIG", "UMFPACK"):
            cv[f"SUITESPARSE_USE_SYSTEM_{tok}"] = False

        if self.options.with_graphblas:
            cv["GRAPHBLAS_USE_JIT"] = False

        # Short-circuit upstream FindBLAS/FindLAPACK by injecting absolute paths.
        # OpenBLAS's Conan recipe ships OpenBLASConfig.cmake but no FindBLAS shim;
        # setting BLAS_LIBRARIES/LAPACK_LIBRARIES tells upstream's own
        # SuiteSparseBLAS.cmake / SuiteSparseLAPACK.cmake to skip find_module.
        ob = self.dependencies["openblas"].cpp_info.aggregated_components()
        ob_libdir  = ob.libdirs[0]
        ob_incdir  = ob.includedirs[0]
        ob_libname = ob.libs[0]
        if self.dependencies["openblas"].options.get_safe("shared"):
            ob_lib_ext = ".dylib" if self.settings.os == "Macos" else ".so"
        else:
            ob_lib_ext = ".a"
        ob_lib = os.path.join(ob_libdir, f"lib{ob_libname}{ob_lib_ext}")

        cv["BLAS_LIBRARIES"]      = ob_lib
        cv["BLAS_INCLUDE_DIRS"]   = ob_incdir
        cv["LAPACK_LIBRARIES"]    = ob_lib  # OpenBLAS bundles LAPACK
        cv["LAPACK_INCLUDE_DIRS"] = ob_incdir

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Each subproject ships its own LICENSE; preserve them all.
        for comp in self._enabled_components():
            subdir = _LICENSE_DIR[comp]
            copy(
                self,
                "LICENSE*",
                src=os.path.join(self.source_folder, subdir),
                dst=os.path.join(self.package_folder, "licenses", subdir),
            )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        cmake = CMake(self)
        cmake.install()

        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if os.path.isdir(os.path.join(self.package_folder, "bin")):
            rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SuiteSparse")

        enabled = self._enabled_components()
        for comp in enabled:
            c = self.cpp_info.components[comp]
            c.set_property("cmake_target_name", _TARGET_NAME[comp])
            c.set_property("cmake_file_name", _CMAKE_FILE_NAME[comp])
            c.libs = [_LIB_NAME[comp]]

            requires = [r for r in _INTERNAL_REQUIRES[comp] if r in enabled]
            if comp in _BLAS_USERS:
                requires.append("openblas::openblas")
            c.requires = requires

            if self.settings.os in ("Linux", "FreeBSD"):
                c.system_libs = ["m", "dl", "pthread"]
