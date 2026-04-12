import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir

required_conan_version = ">=2.1"


class SuperluDistConan(ConanFile):
    name = "superlu-dist"
    description = (
        "Distributed-memory sparse direct solver using MPI, OpenMP, "
        "and optional GPU acceleration"
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
        "with_openmp": [True, False],
        "enable_single": [True, False],
        "enable_double": [True, False],
        "enable_complex16": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_parmetis": True,
        "with_openmp": True,
        "enable_single": True,
        "enable_double": True,
        "enable_complex16": True,
    }
    implements = ["auto_shared_fpic"]

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openmpi/4.1.8", transitive_headers=True, transitive_libs=True)
        self.requires("openblas/0.3.27")
        if self.options.with_parmetis:
            self.requires("parmetis/4.0.3")
            self.requires("metis/5.2.1")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Windows")
        if not any([
            self.options.enable_single,
            self.options.enable_double,
            self.options.enable_complex16,
        ]):
            raise ConanInvalidConfiguration(
                f"{self.ref} requires at least one precision to be enabled"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _dep_lib_files(self, dep_name):
        """Collect absolute library file paths for a Conan dependency.

        Handles both flat and component-based package_info layouts.
        """
        dep = self.dependencies[dep_name]
        pkg = dep.package_folder

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

    def _dep_include_dirs(self, dep_name):
        """Collect absolute include directories for a Conan dependency."""
        dep = self.dependencies[dep_name]
        return [
            d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
            for d in dep.cpp_info.includedirs
        ]

    def generate(self):
        tc = CMakeToolchain(self)

        # Disable unneeded features
        tc.variables["enable_tests"] = False
        tc.variables["enable_examples"] = False
        tc.variables["enable_doc"] = False
        tc.variables["enable_python"] = False
        tc.variables["XSDK_ENABLE_Fortran"] = False
        tc.variables["TPL_ENABLE_CUDALIB"] = False
        tc.variables["TPL_ENABLE_HIPLIB"] = False
        tc.variables["TPL_ENABLE_COMBBLASLIB"] = False
        tc.variables["TPL_ENABLE_COLAMDLIB"] = False
        tc.variables["TPL_ENABLE_NVSHMEM"] = False
        tc.variables["TPL_ENABLE_ROCSHMEM"] = False
        tc.variables["TPL_ENABLE_MAGMALIB"] = False

        # Precision options
        tc.variables["enable_single"] = bool(self.options.enable_single)
        tc.variables["enable_double"] = bool(self.options.enable_double)
        tc.variables["enable_complex16"] = bool(self.options.enable_complex16)

        # OpenMP
        if not self.options.with_openmp:
            tc.variables["enable_openmp"] = False

        # BLAS (external via openblas)
        tc.variables["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        blas_libs = self._dep_lib_files("openblas")
        tc.variables["TPL_BLAS_LIBRARIES"] = ";".join(blas_libs)

        # LAPACK (openblas includes LAPACK routines)
        tc.variables["TPL_ENABLE_LAPACKLIB"] = True
        tc.variables["TPL_LAPACK_LIBRARIES"] = ";".join(blas_libs)

        # ParMETIS
        if self.options.with_parmetis:
            tc.variables["TPL_ENABLE_PARMETISLIB"] = True
            pm_inc = self._dep_include_dirs("parmetis")
            mt_inc = self._dep_include_dirs("metis")
            pm_libs = self._dep_lib_files("parmetis")
            mt_libs = self._dep_lib_files("metis")
            tc.variables["TPL_PARMETIS_INCLUDE_DIRS"] = ";".join(pm_inc + mt_inc)
            tc.variables["TPL_PARMETIS_LIBRARIES"] = ";".join(pm_libs + mt_libs)
            # METIS headers need index/real type width defines
            for define in self.dependencies["metis"].cpp_info.defines:
                key, _, value = define.partition("=")
                tc.preprocessor_definitions[key] = value
        else:
            tc.variables["TPL_ENABLE_PARMETISLIB"] = False

        # Prevent -march=native or aggressive flags from upstream
        tc.cache_variables["CMAKE_C_FLAGS_RELEASE"] = "-O3 -DNDEBUG"
        tc.cache_variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O3 -DNDEBUG"

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        # Upstream links MPI::MPI_CXX and MPI::MPI_Fortran which may not
        # exist when MPI is provided by Conan's openmpi package.
        src_cmake = os.path.join(self.source_folder, "SRC", "CMakeLists.txt")
        replace_in_file(
            self, src_cmake,
            "target_link_libraries(superlu_dist MPI::MPI_CXX MPI::MPI_C MPI::MPI_Fortran)",
            "target_link_libraries(superlu_dist MPI::MPI_C)",
            strict=False,
        )
        replace_in_file(
            self, src_cmake,
            "target_link_libraries(superlu_dist MPI::MPI_CXX MPI::MPI_C)",
            "target_link_libraries(superlu_dist MPI::MPI_C)",
            strict=False,
        )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "License.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["superlu_dist"]
        self.cpp_info.set_property("cmake_file_name", "superlu_dist")
        self.cpp_info.set_property("cmake_target_name", "superlu_dist::superlu_dist")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "rt"])

        if self.options.with_openmp:
            if self.settings.compiler in ("gcc", "clang"):
                self.cpp_info.system_libs.append("gomp")
