import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runtime_library_paths(self):
        libdirs = []
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                full_libdir = libdir if os.path.isabs(libdir) else os.path.join(dependency.package_folder, libdir)
                if full_libdir not in libdirs:
                    libdirs.append(full_libdir)
        return libdirs

    def test(self):
        if can_run(self):
            command = os.path.join(self.cpp.build.bindir, "example")
            runtime_paths = self._runtime_library_paths()
            if runtime_paths and self.settings.os == "Linux":
                command = f"LD_LIBRARY_PATH={':'.join(runtime_paths)}:$LD_LIBRARY_PATH {command}"
            elif runtime_paths and self.settings.os == "Macos":
                command = f"DYLD_LIBRARY_PATH={':'.join(runtime_paths)}:$DYLD_LIBRARY_PATH {command}"
            self.run(command, env="conanrun")
