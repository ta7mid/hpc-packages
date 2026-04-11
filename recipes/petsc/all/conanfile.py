import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import copy, get, rmdir
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0.9"


class PetscConan(ConanFile):
    name = "petsc"
    description = (
        "Portable, Extensible Toolkit for Scientific Computation — "
        "scalable solvers for PDEs and sparse linear/nonlinear systems"
    )
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://petsc.org"
    topics = ("pde", "sparse-solver", "linear-algebra", "mpi", "scientific-computing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
        "with_parmetis": [True, False],
        "with_superlu_dist": [True, False],
        "with_suitesparse": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": True,
        "with_parmetis": True,
        "with_superlu_dist": True,
        "with_suitesparse": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("openblas/0.3.25")
        if self.options.with_parmetis:
            self.requires("parmetis/4.0.3")
            self.requires("metis/5.2.1")
        if self.options.with_superlu_dist:
            self.requires("superlu-dist/9.2.1")
        if self.options.with_suitesparse:
            self.requires("suitesparse/7.12.2")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Windows")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── helpers ──────────────────────────────────────────────────────────

    def _collect_dep_info(self, dep_name):
        """Return (include_dirs, lib_paths) for a Conan dependency."""
        dep = None
        for name, d in self.dependencies.host.items():
            if str(name).startswith(dep_name):
                dep = d
                break
        if dep is None:
            return [], []
        include_dirs = []
        for d in dep.cpp_info.includedirs:
            if not os.path.isabs(d):
                d = os.path.join(dep.package_folder, d)
            include_dirs.append(d)
        # Also check components
        if hasattr(dep.cpp_info, "components"):
            for comp in dep.cpp_info.components.values():
                for d in comp.includedirs:
                    if not os.path.isabs(d):
                        d = os.path.join(dep.package_folder, d)
                    if d not in include_dirs:
                        include_dirs.append(d)

        lib_paths = []
        libdirs = list(dep.cpp_info.libdirs)
        libs = list(dep.cpp_info.libs)
        if hasattr(dep.cpp_info, "components"):
            for comp in dep.cpp_info.components.values():
                libdirs.extend(comp.libdirs)
                libs.extend(comp.libs)
        for libdir in libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(dep.package_folder, libdir)
            for lib in libs:
                for ext in (".a", ".so", ".dylib", ".lib"):
                    path = os.path.join(libdir, f"lib{lib}{ext}")
                    if os.path.exists(path) and path not in lib_paths:
                        lib_paths.append(path)
        return include_dirs, lib_paths

    def _pkg_flag(self, dep_name, petsc_name=None):
        """Return configure flags for --with-<petsc_name>-include/lib."""
        name = petsc_name or dep_name
        inc_dirs, lib_paths = self._collect_dep_info(dep_name)
        flags = []
        if inc_dirs:
            flags.append(f"--with-{name}-include=[{','.join(inc_dirs)}]")
        if lib_paths:
            flags.append(f"--with-{name}-lib=[{','.join(lib_paths)}]")
        return flags

    # ── build ────────────────────────────────────────────────────────────

    def generate(self):
        # PETSc's configure expects MPI compiler wrappers (mpicc, mpicxx).
        # OpenMPI's wrapper needs OPAL_PREFIX and LD_LIBRARY_PATH to locate
        # its config files and transitive shared libs from the Conan cache.
        env = Environment()
        mpi_dep = self.dependencies["openmpi"]
        env.define("OPAL_PREFIX", mpi_dep.package_folder)
        # Collect LD_LIBRARY_PATH for all transitive shared libs
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                env.prepend_path("LD_LIBRARY_PATH", libdir)
            if hasattr(dep.cpp_info, "components"):
                for comp in dep.cpp_info.components.values():
                    for libdir in comp.libdirs:
                        if not os.path.isabs(libdir):
                            libdir = os.path.join(dep.package_folder, libdir)
                        env.prepend_path("LD_LIBRARY_PATH", libdir)
        envvars = env.vars(self)
        envvars.save_script("conanbuild_petsc")

    def build(self):
        args = [
            f"--prefix={self.package_folder}",
            f"--with-shared-libraries={'1' if self.options.shared else '0'}",
            f"--with-debugging={'1' if self.settings.build_type == 'Debug' else '0'}",
            "--with-fc=0",
            "--with-fortran-bindings=0",
            f"--with-make-np={build_jobs(self)}",
            f"--with-openmp={'1' if self.options.with_openmp else '0'}",
            "--with-x=0",
        ]

        # Use MPI compiler wrappers — PETSc auto-detects MPI through them
        mpi_dep = self.dependencies["openmpi"]
        mpicc = os.path.join(mpi_dep.package_folder, "bin", "mpicc")
        mpicxx = os.path.join(mpi_dep.package_folder, "bin", "mpicxx")
        args.extend([f"--with-cc={mpicc}", f"--with-cxx={mpicxx}"])

        # Optimization and PIC flags
        cflags = []
        cxxflags = []
        if self.options.get_safe("fPIC", False):
            cflags.append("-fPIC")
            cxxflags.append("-fPIC")
        if self.settings.build_type == "Release":
            cflags.append("-O3")
            cxxflags.append("-O3")
        elif self.settings.build_type == "Debug":
            cflags.extend(["-g", "-O0"])
            cxxflags.extend(["-g", "-O0"])
        if cflags:
            args.append(f"COPTFLAGS='{' '.join(cflags)}'")
        if cxxflags:
            args.append(f"CXXOPTFLAGS='{' '.join(cxxflags)}'")

        # Set PETSC_ARCH for build output directory
        args.append("PETSC_ARCH=conan")

        # METIS headers require compile-time defines (not embedded in headers)
        if self.options.with_parmetis:
            metis_dep = self.dependencies["metis"]
            metis_defines = " ".join(
                f"-D{d}" for d in metis_dep.cpp_info.defines
            )
            args.append(f"CPPFLAGS='{metis_defines}'")

        # BLAS/LAPACK
        _, blas_libs = self._collect_dep_info("openblas")
        if blas_libs:
            lib_str = ",".join(blas_libs)
            args.append(f"--with-blaslapack-lib=[{lib_str}]")

        # Optional packages
        if self.options.with_parmetis:
            args.extend(self._pkg_flag("parmetis"))
            # METIS depends on GKlib — include GKlib libs with METIS
            metis_inc, metis_libs = self._collect_dep_info("metis")
            _, gklib_libs = self._collect_dep_info("gklib")
            args.append(
                f"--with-metis-include=[{','.join(metis_inc)}]"
            )
            args.append(
                f"--with-metis-lib=[{','.join(metis_libs + gklib_libs)}]"
            )
        else:
            args.append("--with-parmetis=0")
            args.append("--with-metis=0")

        if self.options.with_superlu_dist:
            args.extend(self._pkg_flag("superlu-dist", "superlu_dist"))
        else:
            args.append("--with-superlu_dist=0")

        if self.options.with_suitesparse:
            args.extend(self._pkg_flag("suitesparse"))
        else:
            args.append("--with-suitesparse=0")

        # Run configure
        self.run(
            f"python3 configure {' '.join(args)}",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # Build
        self.run(
            f"make PETSC_DIR={self.source_folder} PETSC_ARCH=conan all -j{build_jobs(self)}",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        self.run(
            f"make PETSC_DIR={self.source_folder} PETSC_ARCH=conan install",
            cwd=self.source_folder,
            env="conanbuild",
        )
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Remove PETSc's share/cmake modules — consumers use Conan targets
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "petsc"))

    def package_info(self):
        self.cpp_info.libs = ["petsc"]
        self.cpp_info.set_property("cmake_file_name", "PETSc")
        self.cpp_info.set_property("cmake_target_name", "PETSc::PETSc")
        self.cpp_info.set_property("pkg_config_name", "petsc")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "rt", "dl", "pthread", "stdc++"])

        self.cpp_info.requires = ["openmpi::openmpi", "openblas::openblas"]
        if self.options.with_parmetis:
            self.cpp_info.requires.extend(["parmetis::parmetis", "metis::metis"])
        if self.options.with_superlu_dist:
            self.cpp_info.requires.append("superlu-dist::superlu-dist")
        if self.options.with_suitesparse:
            self.cpp_info.requires.append("suitesparse::suitesparse")
