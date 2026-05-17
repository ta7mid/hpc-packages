import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir

required_conan_version = ">=2.0.9"


class GlobalArraysConan(ConanFile):
    name = "global-arrays"
    description = (
        "Global Arrays (GA) is a portable shared-memory programming model "
        "for distributed-memory MPI computers. It provides one-sided "
        "communication and globally accessible multi-dimensional arrays, "
        "with the underlying ARMCI and ComEx runtimes."
    )
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/GlobalArrays/ga"
    topics = (
        "global-arrays", "armci", "comex", "mpi", "one-sided",
        "parallel", "hpc", "shared-memory",
    )

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared":       [True, False],
        "fPIC":         [True, False],
        "with_fortran": [True, False],
        "with_cxx":     [True, False],
        "with_blas":    [True, False],
        "with_i8":      [True, False],
    }
    default_options = {
        "shared":       False,
        "fPIC":         True,
        "with_fortran": False,
        "with_cxx":     False,
        "with_blas":    False,
        "with_i8":      False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C unless with_cxx is on; strip C++ settings when not building C++.
        if not self.options.with_cxx:
            self.settings.rm_safe("compiler.cppstd")
            self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # ga.h #include <mpi.h>; MPI types are part of GA's public API.
        self.requires(
            "openmpi/[>=4.1.0 <5]",
            transitive_headers=True,
            transitive_libs=True,
        )
        if self.options.with_blas:
            # OpenBLAS supplies BLAS and LAPACK; consumed only at link time.
            self.requires(
                "openblas/[>=0.3.27 <1]",
                transitive_headers=False,
                transitive_libs=True,
            )

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18 <4]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} does not support Windows. Global Arrays targets POSIX systems."
            )
        if self.options.with_blas and not self.options.with_fortran:
            raise ConanInvalidConfiguration(
                f"{self.ref} with_blas=True requires with_fortran=True "
                "(upstream constraint: ENABLE_BLAS depends on Fortran bindings)."
            )
        if self.options.with_i8 and not self.options.with_fortran:
            raise ConanInvalidConfiguration(
                f"{self.ref} with_i8=True requires with_fortran=True "
                "(the I8 macro switches Fortran integer width)."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        cv = tc.cache_variables

        # GA's own options.
        cv["ENABLE_FORTRAN"]   = bool(self.options.with_fortran)
        cv["ENABLE_CXX"]       = bool(self.options.with_cxx)
        cv["ENABLE_BLAS"]      = bool(self.options.with_blas)
        cv["ENABLE_SCALAPACK"] = False  # no ScaLAPACK Conan dep available
        cv["ENABLE_I8"]        = bool(self.options.with_i8)
        cv["ENABLE_TESTS"]     = False
        cv["ENABLE_PROFILING"] = False
        cv["ENABLE_COVERAGE"]  = False
        cv["ENABLE_DPCPP"]     = False
        cv["ENABLE_DEV_MODE"]  = False
        cv["ENABLE_CUDA_MEM"]  = False

        # MPI 2-sided is the safest, most portable transport.
        cv["GA_RUNTIME"]    = "MPI_2SIDED"
        cv["MSG_COMMS_MPI"] = True

        cv["BUILD_SHARED_LIBS"] = bool(self.options.shared)

        if self.options.with_blas:
            # Upstream's ga-linalg.cmake recognizes LINALG_VENDOR=OpenBLAS and
            # locates the library under LINALG_PREFIX via the bundled
            # cmake/linalg-modules/FindOpenBLAS.cmake.
            ob = self.dependencies["openblas"].package_folder
            cv["LINALG_VENDOR"] = "OpenBLAS"
            cv["LINALG_PREFIX"] = ob.replace("\\", "/")
            cv["BLAS_PREFIX"]   = ob.replace("\\", "/")
            cv["LAPACK_PREFIX"] = ob.replace("\\", "/")

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        # Strip upstream's CMake config; Conan regenerates one with correct
        # transitive deps and the components we declare in package_info.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if os.path.isdir(os.path.join(self.package_folder, "bin")):
            rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GlobalArrays")

        # Upstream installs all public headers under include/ga/ (including
        # armci.h, comex.h). Expose both forms — flat #include <ga.h> via
        # include/ga, and #include <ga/ga.h> via include — so consumers can
        # use either style.
        ga_includedirs = ["include/ga", "include"]

        # Main library — includes ARMCI+ComEx symbols as object libraries.
        c_ga = self.cpp_info.components["ga"]
        c_ga.set_property("cmake_target_name", "GlobalArrays::ga")
        c_ga.libs = ["ga"]
        c_ga.includedirs = list(ga_includedirs)
        c_ga.requires = ["openmpi::openmpi"]
        if self.settings.os in ("Linux", "FreeBSD"):
            c_ga.system_libs = ["m", "pthread", "dl"]
        if self.options.with_blas:
            c_ga.requires.append("openblas::openblas")

        # Standalone ARMCI library (parallel to libga).
        c_armci = self.cpp_info.components["armci"]
        c_armci.set_property("cmake_target_name", "GlobalArrays::armci")
        c_armci.libs = ["armci"]
        c_armci.includedirs = list(ga_includedirs)
        c_armci.requires = ["openmpi::openmpi"]
        if self.settings.os in ("Linux", "FreeBSD"):
            c_armci.system_libs = ["m", "pthread", "dl"]

        # Standalone ComEx library.
        c_comex = self.cpp_info.components["comex"]
        c_comex.set_property("cmake_target_name", "GlobalArrays::comex")
        c_comex.libs = ["comex"]
        c_comex.includedirs = list(ga_includedirs)
        c_comex.requires = ["openmpi::openmpi"]
        if self.settings.os in ("Linux", "FreeBSD"):
            c_comex.system_libs = ["m", "pthread", "dl"]

        # C++ bindings — only when built.
        if self.options.with_cxx:
            c_cxx = self.cpp_info.components["gapp"]
            c_cxx.set_property("cmake_target_name", "GlobalArrays::ga++")
            c_cxx.libs = ["ga++"]
            c_cxx.includedirs = list(ga_includedirs)
            c_cxx.requires = ["ga"]
