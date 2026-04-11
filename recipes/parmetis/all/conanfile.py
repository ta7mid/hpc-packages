import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.0.9"


class ParmetisConan(ConanFile):
    name = "parmetis"
    description = (
        "MPI-based library for partitioning graphs, partitioning finite "
        "element meshes, and producing fill-reducing orderings for sparse matrices"
    )
    license = "LicenseRef-ParMETIS"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/KarypisLab/ParMETIS"
    topics = ("graph-partitioning", "parallel-computing", "mpi", "sparse-matrices")
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
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # gklib is needed directly: parmetis internals include <GKlib.h>
        self.requires("gklib/5.1.1")
        self.requires("metis/5.2.1", transitive_headers=True, transitive_libs=True)
        # parmetis.h includes <mpi.h>, so consumers need MPI headers
        self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Windows")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["parmetis"]
        self.cpp_info.set_property("cmake_file_name", "parmetis")
        self.cpp_info.set_property("cmake_target_name", "parmetis::parmetis")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
