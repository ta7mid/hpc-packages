import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import copy, get, rmdir
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class PetscConan(ConanFile):
    name = "petsc"
    description = (
        "Portable, Extensible Toolkit for Scientific Computation - "
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

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openmpi/4.1.8", transitive_headers=True, transitive_libs=True)
        self.requires("openblas/0.3.27")
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

    def _dep_info(self, dep_name):
        """Return (include_dirs, lib_file_paths) for a Conan dependency.

        Handles both flat and component-based package_info layouts.
        """
        dep = self.dependencies[dep_name]
        pkg = dep.package_folder

        inc_dirs = [
            d if os.path.isabs(d) else os.path.join(pkg, d)
            for d in dep.cpp_info.includedirs
        ]

        libs = list(dep.cpp_info.libs)
        libdirs = list(dep.cpp_info.libdirs)
        for comp in dep.cpp_info.components.values():
            libs.extend(comp.libs)
            libdirs.extend(comp.libdirs)

        lib_files = []
        for libdir in libdirs:
            abs_dir = libdir if os.path.isabs(libdir) else os.path.join(pkg, libdir)
            for lib in libs:
                for prefix, ext in [("lib", ".a"), ("lib", ".so"), ("lib", ".dylib")]:
                    path = os.path.join(abs_dir, f"{prefix}{lib}{ext}")
                    if os.path.exists(path) and path not in lib_files:
                        lib_files.append(path)
                        break
        return inc_dirs, lib_files

    def _pkg_flags(self, dep_name, petsc_name=None):
        """Return PETSc configure flags for --with-<name>-include/lib."""
        name = petsc_name or dep_name
        inc_dirs, lib_files = self._dep_info(dep_name)
        flags = []
        if inc_dirs:
            flags.append(f"--with-{name}-include=[{','.join(inc_dirs)}]")
        if lib_files:
            flags.append(f"--with-{name}-lib=[{','.join(lib_files)}]")
        return flags

    # ── build ────────────────────────────────────────────────────────────

    def _find_shared_lib_dirs(self, lib_name):
        """Find directories containing a shared library in the Conan cache.

        This works around environments where a dependency (e.g. hwloc) is
        resolved as static in the Conan graph but the consuming package's
        binaries (e.g. openmpi's mpicc) were linked against the shared
        variant.
        """
        import glob
        cache_root = os.path.join(os.path.expanduser("~"), ".conan2", "p")
        dirs = []
        for path in glob.glob(os.path.join(cache_root, "b", f"{lib_name}*", "p", "lib")):
            if any(f.endswith(".so") for f in os.listdir(path)):
                dirs.append(path)
        return dirs

    def generate(self):
        # PETSc's configure needs MPI compiler wrappers (mpicc, mpicxx).
        # OpenMPI wrappers need OPAL_PREFIX to find config files, and
        # LD_LIBRARY_PATH so test programs can link against transitive
        # shared libraries from the Conan cache.
        env = Environment()
        mpi_dep = self.dependencies["openmpi"]
        env.define("OPAL_PREFIX", mpi_dep.package_folder)
        for dep in self.dependencies.host.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            for libdir in dep.cpp_info.libdirs:
                abs_dir = libdir if os.path.isabs(libdir) else os.path.join(pkg, libdir)
                env.prepend_path("LD_LIBRARY_PATH", abs_dir)
            for comp in dep.cpp_info.components.values():
                for libdir in comp.libdirs:
                    abs_dir = libdir if os.path.isabs(libdir) else os.path.join(pkg, libdir)
                    env.prepend_path("LD_LIBRARY_PATH", abs_dir)
        # OpenMPI binaries (mpicc, orted) may need shared hwloc even when
        # the Conan dependency graph resolves hwloc as static.
        for d in self._find_shared_lib_dirs("hwloc"):
            env.prepend_path("LD_LIBRARY_PATH", d)
        envvars = env.vars(self)
        envvars.save_script("conanbuild_petsc")

    def build(self):
        mpi_dep = self.dependencies["openmpi"]
        mpicc = os.path.join(mpi_dep.package_folder, "bin", "mpicc")
        mpicxx = os.path.join(mpi_dep.package_folder, "bin", "mpicxx")

        args = [
            f"--prefix={self.package_folder}",
            f"--with-shared-libraries={'1' if self.options.shared else '0'}",
            f"--with-debugging={'1' if self.settings.build_type == 'Debug' else '0'}",
            "--with-fc=0",
            "--with-fortran-bindings=0",
            f"--with-make-np={build_jobs(self)}",
            f"--with-openmp={'1' if self.options.with_openmp else '0'}",
            "--with-x=0",
            f"--with-cc={mpicc}",
            f"--with-cxx={mpicxx}",
            "PETSC_ARCH=conan",
        ]

        # Compiler flags
        cflags = []
        cxxflags = []
        if self.options.get_safe("fPIC"):
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

        # BLAS/LAPACK
        _, blas_libs = self._dep_info("openblas")
        if blas_libs:
            args.append(f"--with-blaslapack-lib=[{','.join(blas_libs)}]")

        # ParMETIS + METIS
        if self.options.with_parmetis:
            args.extend(self._pkg_flags("parmetis"))
            metis_inc, metis_libs = self._dep_info("metis")
            _, gklib_libs = self._dep_info("gklib")
            if metis_inc:
                args.append(f"--with-metis-include=[{','.join(metis_inc)}]")
            if metis_libs or gklib_libs:
                args.append(f"--with-metis-lib=[{','.join(metis_libs + gklib_libs)}]")
            # METIS headers need index/real type width defines
            metis_dep = self.dependencies["metis"]
            metis_defines = " ".join(f"-D{d}" for d in metis_dep.cpp_info.defines)
            if metis_defines:
                args.append(f"CPPFLAGS='{metis_defines}'")
        else:
            args.extend(["--with-parmetis=0", "--with-metis=0"])

        # SuperLU_DIST
        if self.options.with_superlu_dist:
            args.extend(self._pkg_flags("superlu-dist", "superlu_dist"))
        else:
            args.append("--with-superlu_dist=0")

        # SuiteSparse
        if self.options.with_suitesparse:
            args.extend(self._pkg_flags("suitesparse"))
        else:
            args.append("--with-suitesparse=0")

        # Configure
        self.run(
            f"python3 configure {' '.join(args)}",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # Build
        self.run(
            f"make PETSC_DIR={self.source_folder} PETSC_ARCH=conan"
            f" all -j{build_jobs(self)}",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        self.run(
            f"make PETSC_DIR={self.source_folder} PETSC_ARCH=conan install",
            cwd=self.source_folder,
            env="conanbuild",
        )
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
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
