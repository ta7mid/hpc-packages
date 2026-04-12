from glob import glob
from os import path

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.1"


class SuitesparseConan(ConanFile):
    name = "suitesparse"
    description = "Suite of sparse matrix algorithms"
    license = ("BSD-3-Clause", "LGPL-2.1-or-later", "GPL-2.0-or-later")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/DrTimothyAldenDavis/SuiteSparse"
    topics = ("sparse-matrix", "linear-algebra", "factorization", "solver")
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
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openblas/0.3.30")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

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
            raise ValueError(f"Unable to determine library paths for dependency '{dependency_name}'")

        return library_paths

    def _dependency_include_dirs(self, dependency_name):
        dependency = self.dependencies[dependency_name]
        include_dirs = []

        def append_dirs(directories):
            for directory in directories:
                absolute_directory = directory if path.isabs(directory) else path.join(dependency.package_folder, directory)
                if absolute_directory not in include_dirs:
                    include_dirs.append(absolute_directory)

        append_dirs(dependency.cpp_info.includedirs)
        for component in dependency.cpp_info.components.values():
            append_dirs(component.includedirs or dependency.cpp_info.includedirs)

        return include_dirs

    def generate(self):
        openblas_libraries = self._dependency_library_paths("openblas")
        openblas_include_dirs = self._dependency_include_dirs("openblas")

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["BLA_VENDOR"] = "OpenBLAS"
        tc.cache_variables["BLAS_LIBRARIES"] = ";".join(openblas_libraries)
        tc.cache_variables["LAPACK_LIBRARIES"] = ";".join(openblas_libraries)
        tc.cache_variables["SUITESPARSE_ENABLE_PROJECTS"] = ";".join([
            "suitesparse_config",
            "amd",
            "btf",
            "camd",
            "ccolamd",
            "colamd",
            "cholmod",
            "cxsparse",
            "ldl",
            "klu",
            "umfpack",
        ])
        tc.cache_variables["SUITESPARSE_DEMOS"] = False
        tc.cache_variables["SUITESPARSE_REQUIRE_BLAS"] = True
        tc.cache_variables["SUITESPARSE_USE_CUDA"] = False
        tc.cache_variables["SUITESPARSE_USE_FORTRAN"] = False
        tc.cache_variables["SUITESPARSE_USE_OPENMP"] = False
        tc.cache_variables["CHOLMOD_GPL"] = False
        tc.cache_variables["CHOLMOD_MATRIXOPS"] = False
        tc.cache_variables["CHOLMOD_MODIFY"] = False
        tc.cache_variables["CHOLMOD_PARTITION"] = False
        tc.cache_variables["CHOLMOD_SUPERNODAL"] = False
        tc.cache_variables["KLU_USE_CHOLMOD"] = False
        tc.cache_variables["UMFPACK_USE_CHOLMOD"] = False
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
        if openblas_include_dirs:
            joined_include_dirs = ";".join(openblas_include_dirs)
            tc.cache_variables["BLAS_INCLUDE_DIRS"] = joined_include_dirs
            tc.cache_variables["LAPACK_INCLUDE_DIRS"] = joined_include_dirs
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        for license_file in (
            "LICENSE.txt",
            "AMD/Doc/License.txt",
            "BTF/Doc/License.txt",
            "CAMD/Doc/License.txt",
            "CCOLAMD/Doc/License.txt",
            "COLAMD/Doc/License.txt",
            "CHOLMOD/Doc/License.txt",
            "CXSparse/Doc/License.txt",
            "LDL/Doc/License.txt",
            "KLU/Doc/License.txt",
            "UMFPACK/Doc/License.txt",
        ):
            copy(self, license_file, self.source_folder, path.join(self.package_folder, "licenses"))

        rmdir(self, path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, path.join(self.package_folder, "lib64", "cmake"))
        rmdir(self, path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, path.join(self.package_folder, "lib64", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def _add_component(self, name, library_name, target_name, pkg_config_name, requires=None):
        component = self.cpp_info.components[name]
        component.libs = [library_name]
        component.includedirs = [path.join("include", "suitesparse")]
        component.requires = requires or []
        component.set_property("cmake_target_name", target_name)
        component.set_property("pkg_config_name", pkg_config_name)
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SuiteSparse")
        self.cpp_info.builddirs = []

        suitesparse_config = self._add_component(
            "suitesparse_config",
            "suitesparseconfig",
            "SuiteSparse::SuiteSparseConfig",
            "SuiteSparse_config",
        )

        if self.settings.os in ["Linux", "FreeBSD"]:
            suitesparse_config.system_libs.append("m")
        if self.settings.os == "Linux":
            suitesparse_config.system_libs.append("rt")

        self._add_component("amd", "amd", "SuiteSparse::AMD", "AMD", ["suitesparse_config"])
        self._add_component("btf", "btf", "SuiteSparse::BTF", "BTF", ["suitesparse_config"])
        self._add_component("camd", "camd", "SuiteSparse::CAMD", "CAMD", ["suitesparse_config"])
        self._add_component("ccolamd", "ccolamd", "SuiteSparse::CCOLAMD", "CCOLAMD", ["suitesparse_config"])
        self._add_component("colamd", "colamd", "SuiteSparse::COLAMD", "COLAMD", ["suitesparse_config"])
        self._add_component("cholmod", "cholmod", "SuiteSparse::CHOLMOD", "CHOLMOD", [
            "suitesparse_config",
            "amd",
            "camd",
            "ccolamd",
            "colamd",
        ])
        self._add_component("cxsparse", "cxsparse", "SuiteSparse::CXSparse", "CXSparse", ["suitesparse_config"])
        self._add_component("ldl", "ldl", "SuiteSparse::LDL", "LDL", ["suitesparse_config"])
        self._add_component("klu", "klu", "SuiteSparse::KLU", "KLU", [
            "suitesparse_config",
            "amd",
            "btf",
            "colamd",
        ])
        self._add_component("umfpack", "umfpack", "SuiteSparse::UMFPACK", "UMFPACK", [
            "suitesparse_config",
            "amd",
            "openblas::openblas_component",
        ])
