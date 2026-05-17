import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir

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


class GridPackConan(ConanFile):
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
    }

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

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
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
