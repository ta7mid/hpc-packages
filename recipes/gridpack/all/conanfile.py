import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir

required_conan_version = ">=2.0.9"


# Component dep graph, mirrored verbatim from the user-supplied FindGridPACK
# module. Conan component key -> (library file basename or None for INTERFACE,
# list of cross-package and intra-package requires).
#
# Intra-package requires are bare component keys ("math", "parallel", ...).
# Cross-package requires use "pkg::component" form ("boost::mpi",
# "openmpi::openmpi", "global-arrays::gapp").
_COMPONENTS = {
    # INTERFACE-only -- headers + transitive Boost link, no library file.
    "utilities": {
        "lib": None,
        "requires": ["boost::headers", "boost::serialization"],
    },

    # Core libraries
    "parallel": {
        "lib": "gridpack_parallel",
        "requires": [
            "boost::mpi", "boost::random", "boost::serialization",
            "global-arrays::gapp", "environment",
        ],
    },
    "environment": {
        "lib": "gridpack_environment",
        "requires": ["boost::mpi"],
    },
    "configuration": {
        "lib": "gridpack_configuration",
        "requires": ["boost::headers", "parallel", "openmpi::openmpi"],
    },
    "math": {
        "lib": "gridpack_math",
        "requires": ["boost::headers", "configuration", "parallel"],
    },
    "components": {
        "lib": "gridpack_components",
        "requires": [
            "boost::headers", "boost::serialization", "math", "utilities",
        ],
    },
    "analysis": {
        "lib": "gridpack_analysis",
        "requires": ["global-arrays::gapp", "parallel"],
    },
    "partition": {
        "lib": "gridpack_partition",
        "requires": ["boost::headers", "parallel"],
    },
    "timer": {
        "lib": "gridpack_timer",
        "requires": [
            "boost::headers", "boost::serialization", "parallel",
            "openmpi::openmpi",
        ],
    },

    # Application matrix components
    "ymatrix_components": {
        "lib": "gridpack_ymatrix_components",
        "requires": ["boost::headers", "components"],
    },
    "pfmatrix_components": {
        "lib": "gridpack_pfmatrix_components",
        "requires": ["boost::headers", "components", "ymatrix_components"],
    },
    "dsmatrix_components": {
        "lib": "gridpack_dsmatrix_components",
        "requires": ["boost::headers", "components", "ymatrix_components"],
    },
    "kdsmatrix_components": {
        "lib": "gridpack_kdsmatrix_components",
        "requires": ["boost::headers", "components", "ymatrix_components"],
    },
    "sematrix_components": {
        "lib": "gridpack_sematrix_components",
        "requires": ["boost::headers", "components", "ymatrix_components"],
    },

    # Application modules
    "powerflow_module": {
        "lib": "gridpack_powerflow_module",
        "requires": [
            "boost::headers", "configuration", "pfmatrix_components",
        ],
    },
    "dynamic_simulation_full_y_module": {
        "lib": "gridpack_dynamic_simulation_full_y_module",
        "requires": [
            "boost::headers", "components", "configuration", "math",
            "parallel", "powerflow_module", "ymatrix_components",
        ],
    },
    "hadrec_module": {
        "lib": "gridpack_hadrec_module",
        "requires": [
            "boost::headers", "configuration",
            "dynamic_simulation_full_y_module", "powerflow_module",
        ],
    },
    "kalmands_module": {
        "lib": "gridpack_kalmands_module",
        "requires": ["boost::headers", "configuration"],
    },
    "state_estimation_module": {
        "lib": "gridpack_state_estimation_module",
        "requires": ["boost::headers"],
    },
}


class GridPACKConan(ConanFile):
    name = "gridpack"
    description = (
        "GridPACK is a high-performance computing framework for developing "
        "applications that analyze electric power grids. It provides modules "
        "for power-flow, dynamic simulation, contingency analysis, and state "
        "estimation built on top of MPI, Global Arrays, PETSc, and Boost."
    )
    license = "LicenseRef-GridPACK"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/GridOPTICS/GridPACK"
    topics = (
        "power-grid", "power-flow", "dynamic-simulation", "state-estimation",
        "mpi", "parallel", "hpc", "petsc", "global-arrays",
    )

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC":   [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC":   True,

        # PETSc must be real, double precision, parallel -- AND must have
        # parmetis, suitesparse, and superlu_dist enabled (GridPACK uses
        # all three through PETSc).
        "petsc/*:scalar_type":        "real",
        "petsc/*:precision":          "double",
        "petsc/*:index64":            False,
        "petsc/*:with_parmetis":      True,
        "petsc/*:with_metis":         True,
        "petsc/*:with_suitesparse":   True,
        "petsc/*:with_superlu_dist":  True,

        # Global Arrays must build the C++ bindings GridPACK uses, with
        # 4-byte ints, no BLAS, no Fortran.
        "global-arrays/*:with_cxx":      True,
        "global-arrays/*:with_fortran":  False,
        "global-arrays/*:with_blas":     False,
        "global-arrays/*:with_i8":       False,

        # Boost must include the MPI component.
        "boost/*:with_mpi":              True,

        # GridPACK's CMake links MPI::MPI_CXX. Conan's openmpi only emits that
        # target when enable_cxx=True.
        "openmpi/*:enable_cxx": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # GridPACK's environment/parallel headers transitively expose Boost.MPI
        # types and MPI_Comm; Boost is heavily used in public headers
        # (Boost.Serialization, Boost.Smart_Ptr). Headers + libs both
        # propagate to consumers.
        self.requires(
            "openmpi/[>=4.1.0 <5]",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "boost/[>=1.83 <2]",
            transitive_headers=True,
            transitive_libs=True,
        )
        # PETSc and GA are linked at runtime but not exposed through
        # GridPACK's public headers. transitive_libs only.
        self.requires(
            "global-arrays/5.9.2",
            transitive_headers=False,
            transitive_libs=True,
        )
        self.requires(
            "petsc/3.25.1",
            transitive_headers=False,
            transitive_libs=True,
        )
        # gridpack_partition links libparmetis directly. ParMETIS also comes
        # transitively through PETSc, but declaring it explicitly keeps the
        # graph honest and lets us point upstream's FindParMETIS.cmake at
        # the right path in generate().
        self.requires(
            "parmetis/4.0.3",
            transitive_headers=False,
            transitive_libs=True,
        )

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <4]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} does not support Windows. GridPACK targets POSIX systems."
            )

        # Belt-and-braces: catch the case where a user overrides our forced
        # dep options on the CLI and would break GridPACK's configure step
        # deep into the build.
        petsc = self.dependencies["petsc"].options
        if str(petsc.scalar_type) != "real":
            raise ConanInvalidConfiguration(
                f"{self.ref} requires petsc to be built with scalar_type=real."
            )
        if str(petsc.precision) != "double":
            raise ConanInvalidConfiguration(
                f"{self.ref} requires petsc to be built with precision=double."
            )
        for required_opt in ("with_parmetis", "with_suitesparse", "with_superlu_dist"):
            if not bool(petsc.get_safe(required_opt)):
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires petsc to be built with "
                    f"{required_opt}=True (used internally by GridPACK)."
                )

        ga = self.dependencies["global-arrays"].options
        if not bool(ga.with_cxx):
            raise ConanInvalidConfiguration(
                f"{self.ref} requires global-arrays to be built with with_cxx=True."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        cv = tc.cache_variables

        # Build behavior.
        cv["BUILD_SHARED_LIBS"]            = bool(self.options.shared)
        cv["ENABLE_ENVIRONMENT_FROM_COMM"] = True
        cv["USE_PROGRESS_RANKS"]           = False
        cv["BUILD_GA"]                     = False  # we supply GA via Conan
        # Disable upstream's unit-test build -- it adds binaries whose
        # link lines don't carry MPI symbols and would otherwise fail
        # to link in this Conan-driven build.
        cv["GRIDPACK_ENABLE_TESTS"]        = False

        # FindGA.cmake (shipped in src/cmake-modules/) runs a tiny test
        # program via check_cxx_source_runs / check_cxx_source_compiles to
        # verify GA works. The check is hostile to Conan: it reads legacy
        # MPI_LIBRARY / MPI_LIBRARIES variables that Conan's MPIConfig.cmake
        # overwrites with a name-only list lacking -L flags, so the link
        # step fails on MPI_Init / MPI_Abort / .... We have the real
        # MPI::MPI_C target (and ns3-style cmake_target_name wiring on
        # our global-arrays recipe), so the test adds no information --
        # pre-cache the two outcome variables as TRUE to short-circuit
        # check_cxx_source_*.
        cv["CHECK_COMPILATION_ONLY"] = True
        cv["GA_TEST_RUNS"]           = True
        cv["GA_TEST_COMM_RUNS"]      = True

        # When GridPACK calls find_package(ParMETIS REQUIRED), CMake finds
        # Conan's auto-generated ParMETISConfig.cmake (in the generators
        # folder, ahead of the upstream FindParMETIS.cmake module). That
        # config sets ParMETIS_FOUND=TRUE and the ParMETIS::ParMETIS
        # target, but does NOT set the legacy uppercase PARMETIS_FOUND /
        # PARMETIS_LIBRARY / PARMETIS_INCLUDE_DIR / METIS_LIBRARY variables
        # that GridPACK's partition/CMakeLists.txt:67 checks ("A partition
        # implementation must be specified" otherwise). Provide all four
        # legacy variables explicitly so the partition build sees a
        # ParMETIS installation.
        metis_libdir = self.dependencies["metis"].cpp_info.aggregated_components().libdirs[0]
        if self.dependencies["metis"].options.get_safe("shared"):
            metis_ext = ".dylib" if self.settings.os == "Macos" else ".so"
        else:
            metis_ext = ".a"
        cv["METIS_LIBRARY"] = os.path.join(metis_libdir, f"libmetis{metis_ext}").replace("\\", "/")

        pm_libdir = self.dependencies["parmetis"].cpp_info.aggregated_components().libdirs[0]
        pm_incdir = self.dependencies["parmetis"].cpp_info.aggregated_components().includedirs[0]
        if self.dependencies["parmetis"].options.get_safe("shared"):
            pm_ext = ".dylib" if self.settings.os == "Macos" else ".so"
        else:
            pm_ext = ".a"
        cv["PARMETIS_LIBRARY"]     = os.path.join(pm_libdir, f"libparmetis{pm_ext}").replace("\\", "/")
        cv["PARMETIS_INCLUDE_DIR"] = pm_incdir.replace("\\", "/")
        cv["PARMETIS_TEST_RUNS"]   = True
        cv["PARMETIS_FOUND"]       = True

        # Tell upstream's CMake modules where to find Conan-supplied deps.
        petsc_root    = self.dependencies["petsc"].package_folder.replace("\\", "/")
        ga_root       = self.dependencies["global-arrays"].package_folder.replace("\\", "/")
        parmetis_root = self.dependencies["parmetis"].package_folder.replace("\\", "/")
        cv["PETSC_DIR"]    = petsc_root
        cv["PETSC_ARCH"]   = ""
        cv["GA_DIR"]       = ga_root
        cv["PARMETIS_DIR"] = parmetis_root

        # MPI launcher discovery -- point at Conan's openmpi.
        ompi_root = self.dependencies["openmpi"].package_folder.replace("\\", "/")
        cv["MPIEXEC_EXECUTABLE"] = f"{ompi_root}/bin/mpirun"

        # FindGA.cmake's compile-test reads the legacy MPI_INCLUDE_PATH /
        # MPI_LIBRARY / MPI_LIBRARIES variables that Conan's MPIConfig.cmake
        # does not populate (modern CMake uses MPI_C_INCLUDE_DIRS,
        # MPI::MPI_C, etc.). Without them, the test compiles `#include
        # <mpi.h>` cannot find the header and the link cannot resolve
        # MPI_Init / MPI_Abort / .... Populate the legacy variables
        # explicitly so the test succeeds.
        ompi_incdir = self.dependencies["openmpi"].cpp_info.aggregated_components().includedirs[0]
        ompi_libdir = self.dependencies["openmpi"].cpp_info.aggregated_components().libdirs[0]
        if self.dependencies["openmpi"].options.get_safe("shared"):
            lib_ext = ".dylib" if self.settings.os == "Macos" else ".so"
        else:
            lib_ext = ".a"
        mpi_c_lib  = os.path.join(ompi_libdir, f"libmpi{lib_ext}").replace("\\", "/")
        mpi_cxx_lib = os.path.join(ompi_libdir, f"libmpi_cxx{lib_ext}").replace("\\", "/")
        cv["MPI_INCLUDE_PATH"]     = ompi_incdir.replace("\\", "/")
        cv["MPI_CXX_INCLUDE_PATH"] = ompi_incdir.replace("\\", "/")
        cv["MPI_C_INCLUDE_PATH"]   = ompi_incdir.replace("\\", "/")
        cv["MPI_LIBRARY"]          = mpi_c_lib
        cv["MPI_LIBRARIES"]        = f"{mpi_cxx_lib};{mpi_c_lib}"
        # MPI_CXX_LIBRARIES must include both the C++ binding lib AND the
        # core C library -- libmpi_cxx.a alone leaves _ompi_mpi_int /
        # _ompi_mpi_op_sum / ... undefined when GridPACK links its tests
        # (parallel/mpi_test references those via boost::mpi).
        cv["MPI_CXX_LIBRARIES"]    = f"{mpi_cxx_lib};{mpi_c_lib}"
        cv["MPI_C_LIBRARIES"]      = mpi_c_lib

        # On macOS, openmpi transitively requires hwloc which needs
        # Apple Frameworks (CoreFoundation, IOKit). Conan's framework
        # propagation through cpp_info to executables is broken in some
        # GridPACK link lines (they end up with bare "IOKit" not
        # "-framework IOKit"). Inject them globally via the linker flags
        # so every executable that pulls hwloc symbols can link.
        if self.settings.os == "Macos":
            cv["CMAKE_EXE_LINKER_FLAGS"] = "-framework CoreFoundation -framework IOKit"

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()
        # GridPACK's CMakeLists.txt:303 builds
        #   PKG_CONFIG_PATH=${PETSC_DIR}/lib/pkgconfig:${PETSC_DIR}/${PETSC_ARCH}/lib/pkgconfig:...
        # from the PETSC_DIR cache variable above, then calls
        # pkg_check_modules(PETSC REQUIRED IMPORTED_TARGET PETSc). The
        # petsc recipe keeps upstream's lib/pkgconfig/PETSc.pc in the
        # package so this discovery path finds PETSc naturally; we do
        # not need PkgConfigDeps here.

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # GridPACK's CMakeLists is at <source>/src/CMakeLists.txt -- the
        # tarball has no top-level CMake project.
        cmake.configure(build_script_folder="src")
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.md",
            src=os.path.join(self.source_folder, "docs", "markdown"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        # Strip upstream's hand-rolled GridPACK.cmake (it references build-time
        # absolute paths). Conan regenerates a relocatable consumer config
        # via CMakeDeps.
        rm(self, "GridPACK.cmake", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Setting cmake_target_name on the root cpp_info while also declaring
        # components causes Conan's CMakeDeps to emit an aggregate
        # GridPACK::GridPACK target that links every component.
        self.cpp_info.set_property("cmake_file_name", "GridPACK")
        self.cpp_info.set_property("cmake_target_name", "GridPACK::GridPACK")
        self.cpp_info.set_property("pkg_config_name", "gridpack")

        for name, spec in _COMPONENTS.items():
            c = self.cpp_info.components[name]
            c.set_property("cmake_target_name", f"GridPACK::{name}")
            if spec["lib"] is not None:
                c.libs = [spec["lib"]]
            c.requires = list(spec["requires"])
            if self.settings.os in ("Linux", "FreeBSD"):
                c.system_libs = ["m", "pthread", "dl", "rt"]

        # USE_PROGRESS_RANKS / ENABLE_ENVIRONMENT_FROM_COMM are compile-time
        # switches that GridPACK public headers branch on. Propagate them so
        # consumers see the same view as the packaged build.
        for c in self.cpp_info.components.values():
            c.defines.append("USE_PROGRESS_RANKS=0")
            c.defines.append("ENABLE_ENVIRONMENT_FROM_COMM=1")
