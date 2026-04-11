import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir

required_conan_version = ">=2.0.9"


class SuperluDistConan(ConanFile):
    name = "superlu-dist"
    description = (
        "Distributed-memory sparse direct solver using MPI, "
        "OpenMP, and optional GPU acceleration"
    )
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/xiaoyeli/superlu_dist"
    topics = ("sparse-solver", "linear-algebra", "mpi", "parallel-computing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_parmetis": [True, False],
        "with_lapack": [True, False],
        "with_openmp": [True, False],
        "enable_single": [True, False],
        "enable_double": [True, False],
        "enable_complex16": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_parmetis": True,
        "with_lapack": False,
        "with_openmp": True,
        "enable_single": True,
        "enable_double": True,
        "enable_complex16": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("openblas/0.3.25")
        if self.options.with_parmetis:
            self.requires("parmetis/4.0.3")
            self.requires("metis/5.2.1")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Windows")
        if not any([self.options.enable_single, self.options.enable_double,
                    self.options.enable_complex16]):
            raise ConanInvalidConfiguration("At least one precision must be enabled")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _collect_tpl_paths(self, dep_name):
        """Collect include dirs and library file paths for a dependency."""
        dep = self.dependencies[dep_name]
        include_dirs = []
        libraries = []
        for inc in dep.cpp_info.includedirs:
            if os.path.isabs(inc):
                include_dirs.append(inc)
            else:
                include_dirs.append(os.path.join(dep.package_folder, inc))
        for libdir in dep.cpp_info.libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(dep.package_folder, libdir)
            for lib in dep.cpp_info.libs:
                for ext in (".a", ".so", ".dylib", ".lib"):
                    candidate = os.path.join(libdir, f"lib{lib}{ext}")
                    if os.path.exists(candidate):
                        libraries.append(candidate)
                        break
                    candidate = os.path.join(libdir, f"{lib}{ext}")
                    if os.path.exists(candidate):
                        libraries.append(candidate)
                        break
        return include_dirs, libraries

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["enable_tests"] = False
        tc.variables["enable_examples"] = False
        tc.variables["enable_doc"] = False
        tc.variables["enable_python"] = False
        tc.variables["XSDK_ENABLE_Fortran"] = False
        tc.variables["TPL_ENABLE_CUDALIB"] = False
        tc.variables["TPL_ENABLE_HIPLIB"] = False
        tc.variables["TPL_ENABLE_COMBBLASLIB"] = False
        tc.variables["TPL_ENABLE_COLAMDLIB"] = False

        tc.variables["enable_single"] = self.options.enable_single
        tc.variables["enable_double"] = self.options.enable_double
        tc.variables["enable_complex16"] = self.options.enable_complex16

        if not self.options.with_openmp:
            tc.variables["enable_openmp"] = False

        # BLAS
        tc.variables["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        blas_inc, blas_libs = self._collect_tpl_paths("openblas")
        tc.variables["TPL_BLAS_LIBRARIES"] = ";".join(blas_libs)

        # LAPACK
        if self.options.with_lapack:
            tc.variables["TPL_ENABLE_LAPACKLIB"] = True
            tc.variables["TPL_LAPACK_LIBRARIES"] = ";".join(blas_libs)
        else:
            tc.variables["TPL_ENABLE_LAPACKLIB"] = False

        # ParMETIS
        if self.options.with_parmetis:
            tc.variables["TPL_ENABLE_PARMETISLIB"] = True
            pm_inc, pm_libs = self._collect_tpl_paths("parmetis")
            mt_inc, mt_libs = self._collect_tpl_paths("metis")
            tc.variables["TPL_PARMETIS_INCLUDE_DIRS"] = ";".join(pm_inc + mt_inc)
            tc.variables["TPL_PARMETIS_LIBRARIES"] = ";".join(pm_libs + mt_libs)
            # metis.h requires IDXTYPEWIDTH/REALTYPEWIDTH defines to resolve
            # idx_t/real_t types; propagate all metis defines to the build
            for define in self.dependencies["metis"].cpp_info.defines:
                key, _, value = define.partition("=")
                tc.preprocessor_definitions[key] = value
        else:
            tc.variables["TPL_ENABLE_PARMETISLIB"] = False

        # Prevent -march=native type flags from upstream
        tc.cache_variables["CMAKE_C_FLAGS_RELEASE"] = "-O3 -DNDEBUG"
        tc.cache_variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O3 -DNDEBUG"

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        # The upstream CMakeLists links MPI::MPI_CXX which may not exist
        # when MPI is provided via Conan's openmpi (only MPI::MPI_C).
        src_cmake = os.path.join(self.source_folder, "SRC", "CMakeLists.txt")
        replace_in_file(self, src_cmake,
                        "target_link_libraries(superlu_dist MPI::MPI_CXX MPI::MPI_C MPI::MPI_Fortran)",
                        "target_link_libraries(superlu_dist MPI::MPI_C)")
        replace_in_file(self, src_cmake,
                        "target_link_libraries(superlu_dist MPI::MPI_CXX MPI::MPI_C)",
                        "target_link_libraries(superlu_dist MPI::MPI_C)")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "License.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # Remove the generated make.inc (not needed for consumers)
        for f in ("make.inc", "make.inc_tmp"):
            path = os.path.join(self.source_folder, f)
            if os.path.exists(path):
                os.remove(path)

    def package_info(self):
        self.cpp_info.libs = ["superlu_dist"]
        self.cpp_info.set_property("cmake_file_name", "superlu_dist")
        self.cpp_info.set_property("cmake_target_name", "superlu_dist::superlu_dist")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "rt"])

        if self.options.with_openmp:
            if self.settings.compiler in ("gcc", "clang"):
                self.cpp_info.system_libs.append("gomp")
