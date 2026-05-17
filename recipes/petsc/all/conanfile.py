from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs, cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, rm, rmdir
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc
from shlex import quote
import glob
import os


required_conan_version = ">=2.0"


class PETScConan(ConanFile):
    name = "petsc"
    version = "3.25.1"
    description = "Portable, extensible toolkit for scientific computation"
    license = "BSD-2-Clause"
    homepage = "https://petsc.org/"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("linear-algebra", "nonlinear-solvers", "mpi", "scientific-computing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "scalar_type": ["real", "complex"],
        "with_parmetis": [True, False],
        "with_metis": [True, False],
        "with_suitesparse": [True, False],
        "with_superlu_dist": [True, False],
        "with_hdf5": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "scalar_type": "real",
        "with_parmetis": False,
        "with_metis": False,
        "with_suitesparse": False,
        "with_superlu_dist": False,
        "with_hdf5": False,
        "hdf5/*:parallel": True,
        "hdf5/*:enable_cxx": False,
        "suitesparse/*:with_openmp": False,
        "superlu_dist/*:with_openmp": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("PETSc's configure build is not supported by this recipe with MSVC")
        if cross_building(self):
            raise ConanInvalidConfiguration("This PETSc recipe does not support cross-building yet")

    def requirements(self):
        self.requires("openblas/0.3.30", transitive_headers=True, transitive_libs=True)
        self.requires("openmpi/4.1.8", transitive_headers=True, transitive_libs=True)
        if self.options.with_parmetis:
            self.requires("parmetis/4.0.3", transitive_headers=True, transitive_libs=True)
        if self.options.with_metis or self.options.with_parmetis:
            self.requires("metis/5.2.1", transitive_headers=True, transitive_libs=True)
        if self.options.with_suitesparse:
            self.requires("suitesparse/7.12.2", transitive_headers=True, transitive_libs=True)
        if self.options.with_superlu_dist:
            self.requires("superlu_dist/9.2.1", transitive_headers=True, transitive_libs=True)
        if self.options.with_hdf5:
            self.requires("hdf5/1.14.6", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        self._create_openmpi_build_environment()

    def build(self):
        install_dir = os.path.join(self.build_folder, "install")
        petsc_arch = "arch-conan"
        openmpi_root = self.dependencies["openmpi"].package_folder
        openmpi_bin = os.path.join(openmpi_root, "bin")
        args = [
            f"PETSC_ARCH={petsc_arch}",
            f"--prefix={install_dir}",
            f"--with-shared-libraries={int(self.options.shared)}",
            f"--with-debugging={int(str(self.settings.build_type) == 'Debug')}",
            f"--with-scalar-type={self.options.scalar_type}",
            "--with-mpi=1",
            f"--with-cc={os.path.join(openmpi_bin, 'mpicc')}",
            f"--with-mpiexec={os.path.join(openmpi_bin, 'mpiexec')}",
            "--with-cxx=0",
            "--with-fc=0",
            "--with-clanguage=C",
            "--with-fortran-bindings=0",
            "--with-single-library=1",
            "--with-x=0",
            "--with-c2html=0",
            "--with-sowing=0",
            "--with-hwloc=0",
            "--with-hypre=0",
            "--with-mumps=0",
            "--with-petsc4py=0",
            "--with-ptscotch=0",
            "--with-scalapack=0",
            "--with-superlu=0",
            "--with-yaml=0",
            f"--with-blaslapack-lib=[{','.join(self._dep_libraries('openblas'))}]",
            f"--with-pic={int(self.options.get_safe('fPIC', False))}",
            f"--with-make-np={build_jobs(self)}",
        ]
        args.extend(self._optional_package_args(
            self.options.with_parmetis,
            "parmetis",
            "parmetis",
            extra_lib_deps=["metis", "gklib"],
        ))
        args.extend(self._optional_package_args(
            self.options.with_metis or self.options.with_parmetis,
            "metis",
            "metis",
            extra_lib_deps=["gklib"],
        ))
        args.extend(self._optional_package_args(
            self.options.with_superlu_dist,
            "superlu_dist",
            "superlu_dist",
            extra_lib_deps=["parmetis", "metis", "gklib", "openblas"],
        ))
        args.extend(self._optional_package_args(self.options.with_suitesparse, "suitesparse", "suitesparse"))
        args.extend(self._optional_package_args(
            self.options.with_hdf5,
            "hdf5",
            "hdf5",
            extra_lib_deps=["zlib"],
        ))
        if self.options.get_safe("fPIC", False):
            args.append("COPTFLAGS=-fPIC")
        configure_args = " ".join(quote(arg) for arg in args)
        make_vars = f"PETSC_DIR={quote(self.source_folder)} PETSC_ARCH={quote(petsc_arch)}"
        self.run(f"python3 ./configure {configure_args}", cwd=self.source_folder, env="conanbuild")
        self.run(f"make {make_vars} all -j{build_jobs(self)}", cwd=self.source_folder, env="conanbuild")
        self.run(f"make {make_vars} install", cwd=self.source_folder, env="conanbuild")

    def package(self):
        install_dir = os.path.join(self.build_folder, "install")
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", install_dir, self.package_folder)
        rm(self, "*.pyc", self.package_folder)
        rm(self, "*.pc", os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "petsc", "conf", "__pycache__"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "petsc", "examples"))
        rmdir(self, os.path.join(self.package_folder, "share", "petsc", "datafiles"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PETSc")
        self.cpp_info.set_property("cmake_target_name", "PETSc::PETSc")
        self.cpp_info.set_property("cmake_target_aliases", ["petsc::petsc"])
        self.cpp_info.set_property("pkg_config_name", "petsc")
        self.cpp_info.libs = ["petsc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.builddirs = []
        self.cpp_info.requires = [
            "openblas::openblas",
            "openmpi::openmpi",
        ]
        if self.options.with_parmetis:
            self.cpp_info.requires.append("parmetis::parmetis")
        if self.options.with_metis or self.options.with_parmetis:
            self.cpp_info.requires.append("metis::metis")
        if self.options.with_suitesparse:
            self.cpp_info.requires.append("suitesparse::suitesparse")
        if self.options.with_superlu_dist:
            self.cpp_info.requires.append("superlu_dist::superlu_dist")
        if self.options.with_hdf5:
            self.cpp_info.requires.append("hdf5::hdf5")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.runenv_info.define_path("PETSC_DIR", self.package_folder)
        self.runenv_info.define_path("PETSC_LIB_DIR", os.path.join(self.package_folder, "lib"))

    def _dep_libraries(self, name):
        dep = self.dependencies[name]
        cpp_info = dep.cpp_info.aggregated_components()
        paths = []
        for lib in cpp_info.libs:
            found = self._find_library(cpp_info.libdirs, dep.package_folder, lib)
            path = found if found else lib
            if path not in paths:
                paths.append(path)
        return paths

    def _dep_include_dirs(self, name):
        dep = self.dependencies[name]
        result = []
        for include_dir in dep.cpp_info.aggregated_components().includedirs:
            path = include_dir if os.path.isabs(include_dir) else os.path.join(dep.package_folder, include_dir)
            path = path.replace("\\", "/")
            if path not in result:
                result.append(path)
        return result

    def _petsc_dependency_args(self, include_option, lib_option, dep_name, extra_lib_deps=None):
        includes = self._dep_include_dirs(dep_name)
        libraries = self._dep_libraries(dep_name)
        for extra_dep in extra_lib_deps or []:
            if self._has_dependency(extra_dep):
                libraries.extend(self._dep_libraries(extra_dep))
        libraries = self._dedupe(libraries)

        args = []
        if includes:
            args.append(f"{include_option}=[{','.join(includes)}]")
        if libraries:
            args.append(f"{lib_option}=[{','.join(libraries)}]")
        return args

    def _has_dependency(self, name):
        try:
            self.dependencies[name]
            return True
        except KeyError:
            return False

    def _optional_package_args(self, enabled, petsc_name, dep_name, extra_lib_deps=None):
        args = [f"--with-{petsc_name}={int(bool(enabled))}"]
        if enabled:
            args.extend(self._petsc_dependency_args(
                f"--with-{petsc_name}-include",
                f"--with-{petsc_name}-lib",
                dep_name,
                extra_lib_deps=extra_lib_deps,
            ))
        return args

    @staticmethod
    def _dedupe(values):
        result = []
        for value in values:
            if value not in result:
                result.append(value)
        return result

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
