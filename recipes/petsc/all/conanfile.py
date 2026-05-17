import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, rm, rmdir
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0.9"


class PetscConan(ConanFile):
    name = "petsc"
    description = (
        "PETSc, the Portable, Extensible Toolkit for Scientific Computation, "
        "is a suite of data structures and routines for the scalable parallel "
        "solution of scientific applications modeled by partial differential "
        "equations on MPI-based distributed-memory systems."
    )
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://petsc.org"
    topics = (
        "pde", "solvers", "linear-algebra", "krylov", "preconditioners",
        "mpi", "parallel", "hpc", "scientific-computing",
    )

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared":            [True, False],
        "fPIC":              [True, False],
        "precision":         ["single", "double", "__float128"],
        "scalar_type":       ["real", "complex"],
        "index64":           [True, False],
        "with_openmp":       [True, False],
        # Local hpc-packages deps
        "with_metis":        [True, False],
        "with_parmetis":     [True, False],
        "with_superlu_dist": [True, False],
        "with_suitesparse":  [True, False],
        # ConanCenter deps
        "with_hdf5":         [True, False],
        "with_fftw":         [True, False],
        "with_yaml":         [True, False],
        "with_zlib":         [True, False],
        "with_sundials":     [True, False],
        "with_netcdf":       [True, False],
        "with_cgns":         [True, False],
        "with_boost":        [True, False],
    }
    default_options = {
        "shared":            False,
        "fPIC":              True,
        "precision":         "double",
        "scalar_type":       "real",
        "index64":           False,
        "with_openmp":       True,
        "with_metis":        False,
        "with_parmetis":     False,
        "with_superlu_dist": False,
        "with_suitesparse":  False,
        "with_hdf5":         False,
        "with_fftw":         False,
        "with_yaml":         False,
        "with_zlib":         False,
        "with_sundials":     False,
        "with_netcdf":       False,
        "with_cgns":         False,
        "with_boost":        False,

        # PETSc's SuiteSparse package config requires SuiteSparseQR_C_solve
        # (libspqr.a), which is opt-in in our suitesparse recipe. Force it
        # on for any consumer that also pulls suitesparse. Harmless when
        # with_suitesparse=False (suitesparse isn't in the graph).
        "suitesparse/*:with_spqr": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        # Apple Clang ships without libomp; PETSc's configure rejects it as
        # "CC Compiler has no support for OpenMP". Default OFF on macOS so
        # the lean build succeeds out of the box. Users with `brew install
        # libomp` (or a custom CC) can override via -o '&:with_openmp=True'.
        if self.settings.os == "Macos":
            self.options.with_openmp = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # PETSc has C, C++, and (optionally) Fortran TUs. We keep
        # compiler.cppstd / libcxx settings since the C++ surface affects ABI
        # of consumers compiling against installed headers.

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Always required.
        self.requires(
            "openmpi/[>=4.1.0 <5]",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "openblas/[>=0.3.27 <1]",
            transitive_headers=False,
            transitive_libs=True,
        )

        # METIS is needed standalone (with_metis) and also pulled transitively
        # through parmetis. Conan's solver handles dedup.
        if self.options.with_parmetis:
            self.requires(
                "parmetis/4.0.3",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_metis:
            # If parmetis is also on, this is a redundant direct require but
            # makes the dependency graph explicit and lets Conan version-resolve.
            self.requires(
                "metis/[>=5.2.1 <6]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_superlu_dist:
            self.requires(
                "superlu_dist/9.2.1",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_suitesparse:
            self.requires(
                "suitesparse/7.12.2",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_hdf5:
            self.requires(
                "hdf5/[>=1.14 <2]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_fftw:
            self.requires(
                "fftw/[>=3.3.10 <4]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_yaml:
            self.requires(
                "libyaml/[>=0.2.5 <1]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_zlib:
            self.requires(
                "zlib/[>=1.3 <2]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_sundials:
            self.requires(
                "sundials/[>=6 <8]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_netcdf:
            self.requires(
                "netcdf/[>=4.8 <5]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_cgns:
            self.requires(
                "cgns/[>=4.3 <5]",
                transitive_headers=False,
                transitive_libs=True,
            )
        if self.options.with_boost:
            self.requires(
                "boost/[>=1.83 <2]",
                transitive_headers=False,
                transitive_libs=True,
            )

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} does not support Windows. PETSc targets POSIX systems."
            )
        if self.options.with_parmetis and not self.options.with_metis:
            raise ConanInvalidConfiguration(
                f"{self.ref} with_parmetis=True requires with_metis=True."
            )
        if self.options.index64:
            # Either metis or parmetis (which pulls metis) may be in the graph;
            # in both cases the (single) metis must be built 64-bit-indexed.
            metis_in_graph = self.options.with_metis or self.options.with_parmetis
            if metis_in_graph:
                try:
                    metis_64 = bool(self.dependencies["metis"].options.with_64bit_types)
                except (KeyError, AttributeError):
                    metis_64 = False
                if not metis_64:
                    raise ConanInvalidConfiguration(
                        f"{self.ref} index64=True with METIS/ParMETIS enabled requires "
                        "metis to be built with with_64bit_types=True. Pass "
                        "`-o metis/*:with_64bit_types=True`."
                    )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # AutotoolsToolchain populates compiler env (CC, CXX, CFLAGS, LDFLAGS,
        # cross-compile flags). PETSc's configure does not consume these in the
        # autoconf sense, but having them in env is harmless and makes the
        # toolchain visible to any sub-builds.
        tc = AutotoolsToolchain(self)
        tc.generate()

        # Surface dep bin/ directories on PATH so mpicc et al. are findable.
        VirtualBuildEnv(self).generate()

    def _configure_args(self):
        pkg = self.package_folder.replace("\\", "/")
        args = [
            f"--prefix={pkg}",
            f"--with-shared-libraries={1 if self.options.shared else 0}",
            f"--with-debugging={1 if self.settings.build_type == 'Debug' else 0}",
            f"--with-precision={self.options.precision}",
            f"--with-scalar-type={self.options.scalar_type}",
            f"--with-64-bit-indices={1 if self.options.index64 else 0}",
            f"--with-openmp={1 if self.options.with_openmp else 0}",
            "--with-fortran-bindings=0",
            # Disable Fortran entirely: Conan's openmpi defaults to
            # fortran="no" so mpif90 isn't actually a wrapper, and PETSc's
            # configure rejects it. --with-fc=0 stops PETSc from probing
            # for a Fortran compiler altogether.
            "--with-fc=0",
            "--with-x=0",
        ]

        # Conan's openmpi mpicc wrapper-data file omits the Apple Frameworks
        # that libhwloc.a needs on macOS (CoreFoundation, IOKit). When PETSc
        # links its test programs statically against libmpi.a, the hwloc
        # symbols left dangling cause configure to declare MPI unusable.
        # Inject the frameworks via PETSc's LIBS variable on macOS.
        if self.settings.os == "Macos":
            args.append('LIBS="-framework CoreFoundation -framework IOKit"')

        # When metis/parmetis are enabled, propagate the IDXTYPEWIDTH and
        # REALTYPEWIDTH compile definitions that the metis recipe sets via
        # cpp_info.defines. Without them, <metis.h> errors out at PETSc's
        # configure-time header check with "Incorrect user-supplied value
        # fo IDXTYPEWIDTH". (CMake-based consumers get these for free
        # through metis::metis; PETSc consumes metis via bare paths, so we
        # forward them through PETSc's CPPFLAGS variable.)
        if self.options.with_metis or self.options.with_parmetis:
            metis_defs = self.dependencies["metis"].cpp_info.aggregated_components().defines
            if metis_defs:
                args.append("CPPFLAGS=\"" + " ".join(f"-D{d}" for d in metis_defs) + "\"")

        args += [
            "--with-mpi=1",
            f"--with-mpi-dir={self.dependencies['openmpi'].package_folder}",
            f"--with-blaslapack-dir={self.dependencies['openblas'].package_folder}",
        ]

        def _tpl(opt, flag_with, flag_dir, dep_name):
            on = bool(self.options.get_safe(opt))
            if on:
                root = self.dependencies[dep_name].package_folder
                args.append(f"--{flag_with}=1")
                args.append(f"--{flag_dir}={root}")
            else:
                args.append(f"--{flag_with}=0")

        def _explicit_tpl(opt, flag_with, dep_names):
            """Use --with-X-include + --with-X-lib (explicit paths) to bypass
            PETSc's auto-discovery for TPLs whose Conan packages have
            non-trivial transitive deps that PETSc doesn't know about
            (e.g. metis -> gklib, parmetis -> metis -> gklib)."""
            if not self.options.get_safe(opt):
                args.append(f"--{flag_with}=0")
                return
            includes = []
            libfiles = []
            for d in dep_names:
                cpp = self.dependencies[d].cpp_info.aggregated_components()
                libdir = cpp.libdirs[0]
                for inc in cpp.includedirs:
                    if inc not in includes:
                        includes.append(inc)
                for libname in cpp.libs:
                    if self.dependencies[d].options.get_safe("shared"):
                        ext = ".dylib" if self.settings.os == "Macos" else ".so"
                    else:
                        ext = ".a"
                    libfiles.append(os.path.join(libdir, f"lib{libname}{ext}"))
            args.append(f"--{flag_with}=1")
            args.append(f"--{flag_with}-include=[{','.join(includes)}]")
            args.append(f"--{flag_with}-lib=[{','.join(libfiles)}]")

        # metis -> gklib, parmetis -> metis -> gklib: PETSc's --with-X-dir=
        # auto-discovery doesn't know to also link libGKlib.a, leaving
        # gk_mcoreMalloc/gk_randint32/etc. undefined. Use the explicit form
        # with all transitive .a files spelled out.
        _explicit_tpl("with_metis",    "with-metis",    ["metis", "gklib"])
        _explicit_tpl("with_parmetis", "with-parmetis", ["parmetis", "metis", "gklib"])

        # SuiteSparse: PETSc's auto-discovery hardcodes a fixed link list
        # that requires libspqr.a (which is opt-in in our recipe) and a
        # bare -lmetis (which our SuiteSparse doesn't externally link --
        # CHOLMOD uses the internal bundled SuiteSparse_metis). Use the
        # explicit form, listing only the lib files we actually ship.
        _explicit_tpl("with_suitesparse", "with-suitesparse", ["suitesparse"])

        _tpl("with_superlu_dist", "with-superlu_dist", "with-superlu_dist-dir", "superlu_dist")
        _tpl("with_hdf5",         "with-hdf5",         "with-hdf5-dir",         "hdf5")
        _tpl("with_fftw",         "with-fftw",         "with-fftw-dir",         "fftw")
        _tpl("with_yaml",         "with-yaml",         "with-yaml-dir",         "libyaml")
        _tpl("with_zlib",         "with-zlib",         "with-zlib-dir",         "zlib")
        # PETSc's package name for SUNDIALS is `sundials2` (legacy from the
        # SUNDIALS 2.x integration era); the option name follows.
        _tpl("with_sundials",     "with-sundials2",    "with-sundials2-dir",    "sundials")
        _tpl("with_netcdf",       "with-netcdf",       "with-netcdf-dir",       "netcdf")
        _tpl("with_cgns",         "with-cgns",         "with-cgns-dir",         "cgns")
        _tpl("with_boost",        "with-boost",        "with-boost-dir",        "boost")

        return args

    @property
    def _petsc_arch(self):
        return "conan"

    def build(self):
        args = " ".join(self._configure_args())

        # Source both conanbuild (CC/CFLAGS/...) and conanrun (OPAL_PREFIX,
        # PATH for openmpi's mpicc wrapper, etc.) so the configure-time
        # subprocesses can find and invoke mpicc correctly. Without
        # OPAL_PREFIX, openmpi's mpicc looks at the wrong wrapper-data
        # file path and fails with "Cannot open configuration file".
        envs = ["conanbuild", "conanrun"]

        # 1. configure -- writes $PETSC_DIR/$PETSC_ARCH/{lib,include,...}.
        # PETSc's configure auto-detects PETSC_DIR from cwd, so cwd=
        # source_folder is sufficient. PETSC_ARCH defaults to a host-
        # derived name unless we pass it explicitly via --PETSC_ARCH=.
        self.run(
            f"./configure --PETSC_ARCH={self._petsc_arch} {args}",
            cwd=self.source_folder,
            env=envs,
        )

        # 2. build -- pass PETSC_DIR/PETSC_ARCH as make variables.
        self.run(
            f"make PETSC_DIR={self.source_folder} "
            f"PETSC_ARCH={self._petsc_arch} all",
            cwd=self.source_folder,
            env=envs,
        )

    def package(self):
        self.run(
            f"make PETSC_DIR={self.source_folder} "
            f"PETSC_ARCH={self._petsc_arch} install",
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )

        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        # Keep upstream's lib/pkgconfig/PETSc.pc -- GridPACK and other PETSc
        # consumers (notably anything that uses pkg_check_modules(PETSc))
        # rely on it being present at $PETSC_DIR/lib/pkgconfig/. The .pc's
        # hardcoded paths point to this exact package_folder, which Conan's
        # content-addressed cache makes stable across the producer and
        # consumer ends of the same build graph.
        # rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        for sub in ("examples", "datafiles", "saws", "configs", "tutorials"):
            rmdir(self, os.path.join(self.package_folder, "share", "petsc", sub))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # bin/ contains user-facing scripts (petscmpiexec wrappers etc.) whose
        # contents reference the build path. They're more harmful than useful
        # in a relocatable Conan package; drop the whole dir.
        if os.path.isdir(os.path.join(self.package_folder, "bin")):
            rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PETSc")
        self.cpp_info.set_property("cmake_target_name", "PETSc::PETSc")
        self.cpp_info.set_property("pkg_config_name", "PETSc")

        self.cpp_info.libs = ["petsc"]
        self.cpp_info.includedirs = ["include"]

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]

        if self.options.index64:
            self.cpp_info.defines.append("PETSC_USE_64BIT_INDICES")
