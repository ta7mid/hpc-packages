from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir
from conan.tools.microsoft import is_msvc
import glob
import os


required_conan_version = ">=2.0"


class SuiteSparseConan(ConanFile):
    name = "suitesparse"
    version = "7.12.2"
    description = "Suite of sparse matrix algorithms"
    license = "LGPL-2.1-or-later AND GPL-2.0-or-later AND Apache-2.0 AND BSD-3-Clause"
    homepage = "https://github.com/DrTimothyAldenDavis/SuiteSparse"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("sparse-matrix", "linear-algebra", "cholmod", "umfpack", "spqr")
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

    _projects = (
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
        "spqr",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("This SuiteSparse recipe currently supports Unix-like toolchains")

    def requirements(self):
        self.requires("openblas/0.3.30", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        openblas_libraries = self._dep_libraries("openblas")
        openblas_includedirs = self._dep_include_dirs("openblas")

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.cache_variables["SUITESPARSE_ENABLE_PROJECTS"] = ";".join(self._projects)
        tc.cache_variables["SUITESPARSE_USE_CUDA"] = False
        tc.cache_variables["CHOLMOD_USE_CUDA"] = False
        tc.cache_variables["SUITESPARSE_USE_FORTRAN"] = False
        tc.cache_variables["SUITESPARSE_USE_PYTHON"] = False
        tc.cache_variables["SUITESPARSE_DEMOS"] = False
        tc.cache_variables["SUITESPARSE_REQUIRE_BLAS"] = True
        tc.cache_variables["BLA_VENDOR"] = "OpenBLAS"
        tc.cache_variables["BLAS_FOUND"] = True
        tc.cache_variables["LAPACK_FOUND"] = True
        tc.cache_variables["BLAS_LIBRARIES"] = ";".join(openblas_libraries)
        tc.cache_variables["LAPACK_LIBRARIES"] = ";".join(openblas_libraries)
        if openblas_includedirs:
            tc.cache_variables["BLAS_INCLUDE_DIRS"] = ";".join(openblas_includedirs)
            tc.cache_variables["LAPACK_INCLUDE_DIRS"] = ";".join(openblas_includedirs)
        if not self.options.with_openmp:
            tc.cache_variables["SUITESPARSE_USE_OPENMP"] = False
            tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pc", os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SuiteSparse")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::SuiteSparse")

        self._component("suitesparse_config", "suitesparseconfig", "SuiteSparse::SuiteSparseConfig",
                        aliases=["SuiteSparse::SuiteSparse_config"], pkg_config="SuiteSparse_config")
        self._component("amd", "amd", "SuiteSparse::AMD", requires=["suitesparse_config"], pkg_config="AMD")
        self._component("btf", "btf", "SuiteSparse::BTF", requires=["suitesparse_config"], pkg_config="BTF")
        self._component("camd", "camd", "SuiteSparse::CAMD", requires=["suitesparse_config"], pkg_config="CAMD")
        self._component("ccolamd", "ccolamd", "SuiteSparse::CCOLAMD", requires=["suitesparse_config"], pkg_config="CCOLAMD")
        self._component("colamd", "colamd", "SuiteSparse::COLAMD", requires=["suitesparse_config"], pkg_config="COLAMD")
        self._component("cxsparse", "cxsparse", "SuiteSparse::CXSparse", requires=["suitesparse_config"], pkg_config="CXSparse")
        self._component("ldl", "ldl", "SuiteSparse::LDL", requires=["amd"], pkg_config="LDL")
        self._component("cholmod", "cholmod", "SuiteSparse::CHOLMOD",
                        requires=["amd", "camd", "ccolamd", "colamd", "suitesparse_config", "openblas::openblas"],
                        pkg_config="CHOLMOD")
        self._component("klu", "klu", "SuiteSparse::KLU",
                        requires=["amd", "btf", "colamd", "suitesparse_config"], pkg_config="KLU")
        self._component("umfpack", "umfpack", "SuiteSparse::UMFPACK",
                        requires=["amd", "cholmod", "suitesparse_config", "openblas::openblas"], pkg_config="UMFPACK")
        self._component("spqr", "spqr", "SuiteSparse::SPQR",
                        requires=["cholmod", "suitesparse_config", "openblas::openblas"], pkg_config="SPQR")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["suitesparse_config"].system_libs = ["m"]

    def _component(self, name, lib, target, requires=None, aliases=None, pkg_config=None):
        component = self.cpp_info.components[name]
        component.set_property("cmake_target_name", target)
        if aliases:
            component.set_property("cmake_target_aliases", aliases)
        if pkg_config:
            component.set_property("pkg_config_name", pkg_config)
        component.libs = [lib]
        component.requires = requires or []

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
