from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir
from conan.tools.scm import Version
import os


required_conan_version = ">=2.0"


class ParMETISConan(ConanFile):
    name = "parmetis"
    version = "4.0.3"
    description = "MPI-based parallel graph partitioning and sparse matrix ordering library"
    license = "LicenseRef-University-of-Minnesota-ParMETIS"
    homepage = "https://github.com/KarypisLab/ParMETIS"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("graph-partitioning", "mesh-partitioning", "mpi", "sparse-matrix")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("ParMETIS' MPI build is not supported by this recipe on Windows")
        if str(self.settings.compiler) == "gcc" and Version(self.settings.compiler.version) < "7":
            raise ConanInvalidConfiguration("ParMETIS requires a compiler with C99 support")

    def requirements(self):
        self.requires("gklib/5.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("metis/5.2.1", transitive_headers=True, transitive_libs=True)
        self.requires("openmpi/4.1.8", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["SHARED"] = bool(self.options.shared)
        tc.variables["GKLIB_PATH"] = self.dependencies["gklib"].package_folder.replace("\\", "/")
        tc.variables["METIS_PATH"] = self.dependencies["metis"].package_folder.replace("\\", "/")
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.cmake", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ParMETIS")
        self.cpp_info.set_property("cmake_target_name", "ParMETIS::ParMETIS")
        self.cpp_info.set_property("cmake_target_aliases", ["parmetis::parmetis", "ParMETIS::parmetis"])
        self.cpp_info.set_property("pkg_config_name", "parmetis")
        self.cpp_info.libs = ["parmetis"]
        self.cpp_info.requires = ["gklib::gklib", "metis::metis", "openmpi::openmpi"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
