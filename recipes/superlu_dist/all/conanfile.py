from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get, rm, replace_in_file, rmdir
from conan.tools.microsoft import is_msvc
import glob
import os


required_conan_version = ">=2.0"


class SuperLUDistConan(ConanFile):
    name = "superlu_dist"
    version = "9.2.1"
    description = "Distributed-memory sparse direct solver using MPI"
    license = "BSD-3-Clause"
    homepage = "https://github.com/xiaoyeli/superlu_dist"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("sparse-matrix", "linear-algebra", "mpi", "superlu")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_fortran": [True, False],
        "with_openmp": [True, False],
        "with_lapack": [True, False],
        "with_parmetis": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_fortran": False,
        "with_openmp": True,
        "with_lapack": True,
        "with_parmetis": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("SuperLU_DIST's upstream CMake build is not supported by this recipe with MSVC")
        if self.options.with_fortran and not self.conf.get("tools.build:compiler_executables", default={}).get("fortran"):
            raise ConanInvalidConfiguration("with_fortran=True requires a configured Fortran compiler")

    def requirements(self):
        self.requires("openblas/0.3.30", transitive_headers=True, transitive_libs=True)
        self.requires("openmpi/4.1.8", transitive_headers=True, transitive_libs=True)
        if self.options.with_parmetis:
            self.requires("parmetis/4.0.3", transitive_headers=True, transitive_libs=True)
            self.requires("metis/5.2.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        self._create_openmpi_build_environment()

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["BUILD_STATIC_LIBS"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.cache_variables["enable_tests"] = False
        tc.cache_variables["enable_examples"] = False
        tc.cache_variables["enable_python"] = False
        tc.cache_variables["enable_openmp"] = bool(self.options.with_openmp)
        tc.cache_variables["XSDK_ENABLE_Fortran"] = bool(self.options.with_fortran)
        tc.cache_variables["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        tc.cache_variables["TPL_BLAS_LIBRARIES"] = ";".join(self._dep_libraries("openblas"))
        tc.cache_variables["TPL_ENABLE_LAPACKLIB"] = bool(self.options.with_lapack)
        tc.cache_variables["TPL_ENABLE_COLAMDLIB"] = False
        tc.cache_variables["TPL_ENABLE_COMBBLASLIB"] = False
        tc.cache_variables["TPL_ENABLE_CUDALIB"] = False
        tc.cache_variables["TPL_ENABLE_HIPLIB"] = False
        tc.cache_variables["TPL_ENABLE_MAGMALIB"] = False
        tc.cache_variables["TPL_ENABLE_NVSHMEM"] = False
        tc.cache_variables["TPL_ENABLE_ROCSHMEM"] = False
        openmpi_bin = os.path.join(self.dependencies["openmpi"].package_folder, "bin").replace("\\", "/")
        tc.cache_variables["MPI_C_COMPILER"] = os.path.join(openmpi_bin, "mpicc").replace("\\", "/")
        tc.cache_variables["MPIEXEC_EXECUTABLE"] = os.path.join(openmpi_bin, "mpiexec").replace("\\", "/")
        if self.options.with_lapack:
            tc.cache_variables["TPL_LAPACK_LIBRARIES"] = ";".join(self._dep_libraries("openblas"))
        tc.cache_variables["TPL_ENABLE_PARMETISLIB"] = bool(self.options.with_parmetis)
        if self.options.with_parmetis:
            tc.cache_variables["TPL_PARMETIS_LIBRARIES"] = ";".join(
                self._dep_libraries("parmetis") + self._dep_libraries("metis")
            )
            tc.cache_variables["TPL_PARMETIS_INCLUDE_DIRS"] = ";".join(
                self._dep_include_dirs("parmetis") + self._dep_include_dirs("metis")
            )
        if not self.options.with_openmp:
            tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
        tc.generate()

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "License.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pc", os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pc", os.path.join(self.package_folder, "lib64", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib64", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SuperLU_DIST")
        self.cpp_info.set_property("cmake_target_name", "SuperLU_DIST::superlu_dist")
        self.cpp_info.set_property("cmake_target_aliases", ["superlu_dist::superlu_dist"])
        self.cpp_info.set_property("pkg_config_name", "superlu_dist")
        self.cpp_info.libs = ["superlu_dist"]
        self.cpp_info.requires = ["openblas::openblas", "openmpi::openmpi"]
        if self.options.with_parmetis:
            self.cpp_info.requires.extend(["parmetis::parmetis", "metis::metis"])
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]

    def _dep_include_dirs(self, name):
        dep = self.dependencies[name]
        result = []
        for include_dir in dep.cpp_info.aggregated_components().includedirs:
            path = include_dir if os.path.isabs(include_dir) else os.path.join(dep.package_folder, include_dir)
            path = path.replace("\\", "/")
            if path not in result:
                result.append(path)
        return result

    def _dep_libraries(self, name):
        dep = self.dependencies[name]
        cpp_info = dep.cpp_info.aggregated_components()
        paths = []
        for lib in cpp_info.libs:
            found = self._find_library(cpp_info.libdirs, dep.package_folder, lib)
            paths.append(found if found else lib)
        return paths

    @staticmethod
    def _find_library(libdirs, package_folder, lib):
        candidates = (
            f"lib{lib}.a",
            f"lib{lib}.so",
            f"lib{lib}.so.*",
            f"lib{lib}.dylib",
            f"{lib}.lib",
        )
        for libdir in libdirs:
            abs_libdir = libdir if os.path.isabs(libdir) else os.path.join(package_folder, libdir)
            for candidate in candidates:
                matches = sorted(glob.glob(os.path.join(abs_libdir, candidate)))
                if matches:
                    return matches[0].replace("\\", "/")
        return None

    def _create_openmpi_build_environment(self):
        openmpi_root = self.dependencies["openmpi"].package_folder
        env = Environment()
        env.define("OPAL_PREFIX", openmpi_root)
        env.prepend_path("PATH", os.path.join(openmpi_root, "bin"))
        runtime_path_var = "DYLD_LIBRARY_PATH" if self.settings.os == "Macos" else "LD_LIBRARY_PATH"
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                env.prepend_path(runtime_path_var, path)
        env.vars(self).save_script("conanbuild_mpi")

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "SRC", "CMakeLists.txt")
        if not self.options.with_fortran:
            replace_in_file(
                self,
                cmakelists,
                "target_link_libraries(superlu_dist MPI::MPI_CXX MPI::MPI_C)",
                "target_link_libraries(superlu_dist MPI::MPI_C)",
                strict=False,
            )
