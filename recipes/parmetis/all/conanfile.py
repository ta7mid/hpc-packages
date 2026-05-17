import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)

required_conan_version = ">=2.0.9"


class ParMetisConan(ConanFile):
    name = "parmetis"
    description = (
        "ParMETIS is an MPI-based parallel library that implements a variety "
        "of algorithms for partitioning unstructured graphs, meshes, and "
        "computing fill-reducing orderings of sparse matrices."
    )
    license = "LicenseRef-ParMETIS"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/KarypisLab/ParMETIS"
    topics = ("graph", "partitioning", "mesh", "mpi", "parallel", "hpc", "sparse-matrix")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

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
        # parmetis.h does #include <metis.h>, and the patched libparmetis links
        # metis::metis PUBLIC, so headers and libs must propagate to consumers.
        self.requires("metis/[>=5.2.1 <6]", transitive_headers=True, transitive_libs=True)
        # Every public ParMETIS function takes MPI_Comm; the patched libparmetis
        # links MPI::MPI_C PUBLIC, so MPI headers and libs propagate.
        self.requires("openmpi/[>=4.1.0 <5]", transitive_headers=True, transitive_libs=True)
        # libparmetis/parmetislib.h does `#include <GKlib.h>` privately. gklib
        # is a transitive dep of metis but metis doesn't expose its headers
        # (no transitive_headers=True on its own require), so we declare gklib
        # directly here to surface its include path to our build. The patched
        # libparmetis links gklib::gklib PRIVATE, so consumers don't see it.
        self.requires("gklib/[>=5.1 <6]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.15 <4]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} does not support Windows. ParMETIS targets POSIX systems."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SHARED"] = bool(self.options.shared)
        tc.cache_variables["PARMETIS_BUILD_TOOLS"] = bool(self.options.tools)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if not self.options.tools:
            rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Honor upstream's "ParMETIS" branding in the generated CMake config.
        self.cpp_info.set_property("cmake_file_name", "ParMETIS")
        self.cpp_info.set_property("cmake_target_name", "ParMETIS::ParMETIS")
        self.cpp_info.set_property("pkg_config_name", "parmetis")

        self.cpp_info.libs = ["parmetis"]

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
