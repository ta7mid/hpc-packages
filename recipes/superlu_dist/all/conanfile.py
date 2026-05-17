import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir

required_conan_version = ">=2.0.9"


class SuperLUDistConan(ConanFile):
    name = "superlu_dist"
    description = (
        "SuperLU_DIST is a distributed-memory parallel direct solver for "
        "large sparse nonsymmetric systems of linear equations, supporting "
        "real and complex matrices in single and double precision."
    )
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/xiaoyeli/superlu_dist"
    topics = ("sparse-direct-solver", "linear-algebra", "mpi", "parallel", "hpc")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared":         [True, False],
        "fPIC":           [True, False],
        "with_openmp":    [True, False],
        "index64":        [True, False],
        "with_single":    [True, False],
        "with_double":    [True, False],
        "with_complex16": [True, False],
    }
    default_options = {
        "shared":         False,
        "fPIC":           True,
        "with_openmp":    True,
        "index64":        False,
        "with_single":    True,
        "with_double":    True,
        "with_complex16": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # SuperLU_DIST's public API is C; the internal C++ TUs don't leak via
        # installed headers. Keep compiler.libcxx (we still build C++) but
        # cppstd is not constrained by the public surface.
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Local parmetis recipe — symbols link in but parmetis.h is not in
        # SuperLU_DIST's public headers.
        self.requires(
            "parmetis/4.0.3",
            transitive_headers=False,
            transitive_libs=True,
        )
        # superlu_defs.h does #include <mpi.h>; MPI_Comm types are in the
        # public API.
        self.requires(
            "openmpi/[>=4.1.0 <5]",
            transitive_headers=True,
            transitive_libs=True,
        )
        # OpenBLAS provides BLAS; not in public headers.
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
                f"{self.ref} does not support Windows. SuperLU_DIST targets POSIX systems."
            )
        if not (self.options.with_single or self.options.with_double
                or self.options.with_complex16):
            raise ConanInvalidConfiguration(
                f"{self.ref}: enable at least one of with_single, with_double, with_complex16."
            )
        # If index64 is on, the (transitive) metis must also be 64-bit indexed.
        if self.options.index64:
            try:
                metis_64 = bool(self.dependencies["metis"].options.with_64bit_types)
            except (KeyError, AttributeError):
                metis_64 = False
            if not metis_64:
                raise ConanInvalidConfiguration(
                    f"{self.ref} index64=True requires the transitive metis to be "
                    "built with with_64bit_types=True. Pass "
                    "`-o metis/*:with_64bit_types=True` and rebuild parmetis."
                )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        cv = tc.cache_variables

        cv["enable_single"]    = bool(self.options.with_single)
        cv["enable_double"]    = bool(self.options.with_double)
        cv["enable_complex16"] = bool(self.options.with_complex16)
        cv["enable_openmp"]    = bool(self.options.with_openmp)

        cv["XSDK_INDEX_SIZE"]    = 64 if self.options.index64 else 32
        cv["XSDK_ENABLE_Fortran"] = False
        cv["enable_python"]       = False
        cv["enable_tests"]        = False
        cv["enable_examples"]     = False
        cv["enable_doc"]          = False

        cv["TPL_ENABLE_CUDALIB"]    = False
        cv["TPL_ENABLE_HIPLIB"]     = False
        cv["TPL_ENABLE_NVSHMEM"]    = False
        cv["TPL_ENABLE_COMBBLASLIB"]= False
        cv["TPL_ENABLE_COLAMDLIB"]  = False
        cv["TPL_ENABLE_LAPACKLIB"]  = False

        # External BLAS via OpenBLAS — point at the actual library file.
        cv["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        ob = self.dependencies["openblas"].cpp_info.aggregated_components()
        ob_libdir  = ob.libdirs[0]
        ob_libname = ob.libs[0]
        if self.dependencies["openblas"].options.get_safe("shared"):
            ob_ext = ".dylib" if self.settings.os == "Macos" else ".so"
        else:
            ob_ext = ".a"
        cv["TPL_BLAS_LIBRARIES"] = os.path.join(ob_libdir, f"lib{ob_libname}{ob_ext}")

        # External ParMETIS — bypass the bundled FindParMETIS.cmake.
        cv["TPL_ENABLE_PARMETISLIB"] = True
        pm = self.dependencies["parmetis"].cpp_info.aggregated_components()
        pm_libdir  = pm.libdirs[0]
        pm_libname = pm.libs[0]
        if self.dependencies["parmetis"].options.get_safe("shared"):
            pm_ext = ".dylib" if self.settings.os == "Macos" else ".so"
        else:
            pm_ext = ".a"
        cv["TPL_PARMETIS_LIBRARIES"] = os.path.join(pm_libdir, f"lib{pm_libname}{pm_ext}")
        pm_includes = list(pm.includedirs)
        # parmetis.h #includes metis.h; pass both header roots.
        pm_includes.extend(self.dependencies["metis"].cpp_info.aggregated_components().includedirs)
        cv["TPL_PARMETIS_INCLUDE_DIRS"] = ";".join(pm_includes)

        cv["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        cv["BUILD_STATIC_LIBS"] = not bool(self.options.shared)

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "License.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        # Drop upstream's pkg-config (absolute build paths); Conan regenerates
        # a correct one via pkg_config_name.
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if os.path.isdir(os.path.join(self.package_folder, "bin")):
            rmdir(self, os.path.join(self.package_folder, "bin"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Honor upstream branding.
        self.cpp_info.set_property("cmake_file_name", "SuperLU_DIST")
        self.cpp_info.set_property("cmake_target_name", "SuperLU_DIST::superlu_dist")
        self.cpp_info.set_property("pkg_config_name", "superlu_dist")

        self.cpp_info.libs = ["superlu_dist"]

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
            if self.options.with_openmp:
                self.cpp_info.system_libs.append("pthread")

        if self.options.index64:
            self.cpp_info.defines.append("XSDK_INDEX_SIZE=64")
