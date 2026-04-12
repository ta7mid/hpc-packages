from glob import glob
from os import path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.1"


class SuperluDistConan(ConanFile):
    name = "superlu_dist"
    description = "Distributed-memory direct solver for large sparse linear systems"
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/xiaoyeli/superlu_dist"
    topics = ("linear-algebra", "sparse", "mpi", "blas", "solver")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["openmpi"].enable_cxx = True

    def requirements(self):
        self.requires("openblas/0.3.30")
        self.requires("openmpi/4.1.8")
        self.requires("parmetis/4.0.3")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("SuperLU_DIST does not support Windows in this recipe")
        if cross_building(self):
            raise ConanInvalidConfiguration("Cross-building SuperLU_DIST is not supported")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def _dependency_library_paths(self, dependency_name):
        dependency = self.dependencies[dependency_name]
        entries = []

        if dependency.cpp_info.libs:
            entries.append((dependency.cpp_info.libdirs, dependency.cpp_info.libs))

        for component in dependency.cpp_info.components.values():
            if component.libs:
                libdirs = component.libdirs or dependency.cpp_info.libdirs
                entries.append((libdirs, component.libs))

        library_paths = []
        for libdirs, libs in entries:
            for libdir in libdirs:
                absolute_libdir = libdir if path.isabs(libdir) else path.join(dependency.package_folder, libdir)
                for lib in libs:
                    match = None
                    for pattern in (
                        f"lib{lib}.a",
                        f"lib{lib}.so",
                        f"lib{lib}.so.*",
                        f"lib{lib}.dylib",
                        f"{lib}.lib",
                    ):
                        candidates = sorted(glob(path.join(absolute_libdir, pattern)))
                        if candidates:
                            match = candidates[0]
                            break
                    if match and match not in library_paths:
                        library_paths.append(match)

        if not library_paths:
            raise ConanInvalidConfiguration(f"Unable to determine library paths for dependency '{dependency_name}'")

        return library_paths

    def generate(self):
        tc = CMakeToolchain(self)
        openmpi_root = self.dependencies["openmpi"].package_folder
        parmetis_root = self.dependencies["parmetis"].package_folder

        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["enable_tests"] = False
        tc.cache_variables["enable_examples"] = False
        tc.cache_variables["enable_python"] = False
        tc.cache_variables["XSDK_ENABLE_Fortran"] = False
        tc.cache_variables["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        tc.cache_variables["TPL_ENABLE_PARMETISLIB"] = True
        tc.cache_variables["TPL_ENABLE_COLAMDLIB"] = False
        tc.cache_variables["TPL_ENABLE_LAPACKLIB"] = False
        tc.cache_variables["TPL_ENABLE_COMBBLASLIB"] = False
        tc.cache_variables["TPL_ENABLE_CUDALIB"] = False
        tc.cache_variables["TPL_ENABLE_HIPLIB"] = False
        tc.cache_variables["TPL_ENABLE_NVSHMEM"] = False
        tc.cache_variables["TPL_ENABLE_ROCSHMEM"] = False
        tc.cache_variables["TPL_ENABLE_MAGMALIB"] = False
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
        tc.cache_variables["MPI_C_INCLUDE_PATH"] = path.join(openmpi_root, "include")
        tc.cache_variables["MPI_CXX_INCLUDE_PATH"] = path.join(openmpi_root, "include")
        tc.cache_variables["TPL_BLAS_LIBRARIES"] = ";".join(self._dependency_library_paths("openblas"))
        tc.cache_variables["TPL_PARMETIS_INCLUDE_DIRS"] = path.join(parmetis_root, "include")
        tc.cache_variables["TPL_PARMETIS_LIBRARIES"] = ";".join(self._dependency_library_paths("parmetis"))
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "License.txt", self.source_folder, path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, path.join(self.package_folder, "lib64", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SuperLU_DIST")
        self.cpp_info.set_property("cmake_target_name", "SuperLU_DIST::superlu_dist")
        self.cpp_info.set_property("pkg_config_name", "superlu_dist")
        self.cpp_info.libs = ["superlu_dist"]
        self.cpp_info.requires = ["openblas::openblas_component", "openmpi::openmpi", "parmetis::parmetis"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")

        openmpi_root = self.dependencies["openmpi"].package_folder
        self.cpp_info.includedirs.extend([
            path.join(openmpi_root, "include"),
            path.join(openmpi_root, "include", "openmpi"),
        ])
