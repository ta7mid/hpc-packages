from os import path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.1"


class ParmetisConan(ConanFile):
    name = "parmetis"
    description = "Parallel graph partitioning and fill-reducing matrix ordering library"
    license = "LicenseRef-ParMETIS"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://karypis.github.io/glaros/software/metis/overview.html"
    topics = ("graph", "partitioning", "sparse-matrix", "mpi", "parallel")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_64bit_types": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_64bit_types": False,
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

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
        self.requires("openmpi/4.1.8")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("ParMETIS does not support Windows in this recipe")
        if cross_building(self):
            raise ConanInvalidConfiguration("Cross-building ParMETIS is not supported")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        bits = 64 if self.options.with_64bit_types else 32
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.preprocessor_definitions["IDXTYPEWIDTH"] = str(bits)
        tc.preprocessor_definitions["REALTYPEWIDTH"] = str(bits)
        if self.settings.build_type == "Debug":
            tc.preprocessor_definitions["DEBUG"] = ""
        else:
            tc.preprocessor_definitions["NDEBUG2"] = ""
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ParMETIS")
        self.cpp_info.set_property("cmake_target_name", "ParMETIS::ParMETIS")
        self.cpp_info.set_property("pkg_config_name", "parmetis")
        bits = 64 if self.options.with_64bit_types else 32

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
            self.cpp_info.defines.append("LINUX")
        elif self.settings.os == "Macos":
            self.cpp_info.defines.append("MACOS")
        elif self.settings.os == "SunOS":
            self.cpp_info.defines.append("SUNOS")

        self.cpp_info.defines.append(f"IDXTYPEWIDTH={bits}")
        self.cpp_info.defines.append(f"REALTYPEWIDTH={bits}")
        self.cpp_info.libs = ["parmetis", "metis", "GKlib"]
        self.cpp_info.requires = ["openmpi::openmpi"]
        mpi_package_folder = self.dependencies["openmpi"].package_folder
        self.cpp_info.includedirs.extend([
            path.join(mpi_package_folder, "include"),
            path.join(mpi_package_folder, "include", "openmpi"),
        ])
