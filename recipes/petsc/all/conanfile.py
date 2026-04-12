import re
from glob import glob
from os import path
from shlex import quote

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import build_jobs, cross_building
from conan.tools.env import Environment
from conan.tools.files import chdir, copy, get, load, replace_in_file, rmdir, save

required_conan_version = ">=2.1"


class PetscConan(ConanFile):
    name = "petsc"
    description = "Portable, Extensible Toolkit for Scientific Computation"
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://petsc.org/"
    topics = ("hpc", "mpi", "linear-algebra", "solver", "scientific-computing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "hwloc/*:shared": True,
    }

    _petsc_arch = "arch-conan"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = path.join(self.folders.build, "generators")

    def requirements(self):
        self.requires("openblas/0.3.30")
        self.requires("openmpi/4.1.8")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("PETSc does not support Windows in this recipe")
        if cross_building(self):
            raise ConanInvalidConfiguration("Cross-building PETSc is not supported")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _dependency_library_paths(self, dependency_name):
        dependency = self.dependencies[dependency_name]
        entries = []

        if dependency.cpp_info.libs:
            entries.append((dependency.cpp_info.libdirs, dependency.cpp_info.libs))

        for component in dependency.cpp_info.components.values():
            if component.libs:
                libdirs = component.libdirs or dependency.cpp_info.libdirs
                entries.append((libdirs, component.libs))

        library_paths = []
        for libdirs, libs in entries:
            for libdir in libdirs:
                absolute_libdir = libdir if path.isabs(libdir) else path.join(dependency.package_folder, libdir)
                for lib in libs:
                    match = None
                    for pattern in (
                        f"lib{lib}.a",
                        f"lib{lib}.so",
                        f"lib{lib}.so.*",
                        f"lib{lib}.dylib",
                        f"{lib}.lib",
                    ):
                        candidates = sorted(glob(path.join(absolute_libdir, pattern)))
                        if candidates:
                            match = candidates[0]
                            break
                    if match and match not in library_paths:
                        library_paths.append(match)

        if not library_paths:
            raise ConanInvalidConfiguration(f"Unable to determine library paths for dependency '{dependency_name}'")

        return library_paths

    def _dependency_link_flags(self, dependency_name):
        dependency = self.dependencies[dependency_name]
        flags = []

        for library_path in self._dependency_library_paths(dependency_name):
            if library_path not in flags:
                flags.append(library_path)

        def append_system_flags(system_libs):
            for system_lib in system_libs:
                flag = f"-l{system_lib}"
                if flag not in flags:
                    flags.append(flag)

        append_system_flags(dependency.cpp_info.system_libs)
        for component in dependency.cpp_info.components.values():
            append_system_flags(component.system_libs)

        return flags

    def _build_environment(self):
        env = Environment()
        openmpi_root = self.dependencies["openmpi"].package_folder

        env.prepend_path("PATH", path.join(openmpi_root, "bin"))
        env.define("OPAL_PREFIX", openmpi_root)

        runtime_var = "DYLD_LIBRARY_PATH" if self.settings.os == "Macos" else "LD_LIBRARY_PATH"
        runtime_paths = []
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                absolute_libdir = libdir if path.isabs(libdir) else path.join(dependency.package_folder, libdir)
                if absolute_libdir not in runtime_paths:
                    runtime_paths.append(absolute_libdir)
            for component in dependency.cpp_info.components.values():
                for libdir in component.libdirs or dependency.cpp_info.libdirs:
                    absolute_libdir = libdir if path.isabs(libdir) else path.join(dependency.package_folder, libdir)
                    if absolute_libdir not in runtime_paths:
                        runtime_paths.append(absolute_libdir)
        for runtime_path in runtime_paths:
            env.prepend_path(runtime_var, runtime_path)

        return env.vars(self)

    def _patch_runtime_path_lookup(self):
        str_c = path.join(self.source_folder, "src", "sys", "utils", "str.c")
        replace_in_file(
            self,
            str_c,
            """PetscErrorCode PetscGetPetscDir(const char *dir[])
{
  PetscFunctionBegin;
  PetscAssertPointer(dir, 1);
  *dir = PETSC_DIR;
  PetscFunctionReturn(PETSC_SUCCESS);
}
""",
            """PetscErrorCode PetscGetPetscDir(const char *dir[])
{
  const char *petsc_dir = getenv("PETSC_DIR");

  PetscFunctionBegin;
  PetscAssertPointer(dir, 1);
  *dir = petsc_dir && petsc_dir[0] ? petsc_dir : PETSC_DIR;
  PetscFunctionReturn(PETSC_SUCCESS);
}
""",
            strict=True,
        )
        replace_in_file(
            self,
            str_c,
            """  char         *work, *par, *epar = NULL, env[1024], *tfree, *a = (char *)aa;
  const char   *s[] = {"${PETSC_ARCH}", "${PETSC_DIR}", "${PETSC_LIB_DIR}", "${DISPLAY}", "${HOMEDIRECTORY}", "${WORKINGDIRECTORY}", "${USERNAME}", "${HOSTNAME}", "${PETSC_MAKE}", NULL};
  char         *r[] = {NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL};
  PetscBool     flag;
""",
            """  char         *work, *par, *epar = NULL, env[1024], *tfree, *a = (char *)aa;
  const char   *petsc_dir = getenv("PETSC_DIR");
  const char   *petsc_lib_dir = getenv("PETSC_LIB_DIR");
  const char   *s[] = {"${PETSC_ARCH}", "${PETSC_DIR}", "${PETSC_LIB_DIR}", "${DISPLAY}", "${HOMEDIRECTORY}", "${WORKINGDIRECTORY}", "${USERNAME}", "${HOSTNAME}", "${PETSC_MAKE}", NULL};
  char         *r[] = {NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL};
  PetscBool     flag;
""",
            strict=True,
        )
        replace_in_file(
            self,
            str_c,
            """  /* replace that are in environment */
  PetscCall(PetscOptionsGetenv(comm, "PETSC_LIB_DIR", env, sizeof(env), &flag));
  if (flag) {
    PetscCall(PetscFree(r[2]));
    PetscCall(PetscStrallocpy(env, &r[2]));
  }
""",
            """  /* replace that are in environment */
  if (petsc_dir && petsc_dir[0]) {
    PetscCall(PetscFree(r[1]));
    PetscCall(PetscStrallocpy(petsc_dir, &r[1]));
  }
  if (petsc_lib_dir && petsc_lib_dir[0]) {
    PetscCall(PetscFree(r[2]));
    PetscCall(PetscStrallocpy(petsc_lib_dir, &r[2]));
  }
""",
            strict=True,
        )

    def _sanitize_generated_headers(self):
        include_folder = path.join(self.source_folder, self._petsc_arch, "include")
        petscconf_h = path.join(include_folder, "petscconf.h")
        petscconf = load(self, petscconf_h)
        petscconf = petscconf.replace(self.package_folder, "${PETSC_DIR}")
        petscconf = re.sub(r'^(#define PETSC_MPICC_SHOW) ".*"$', r'\1 ""', petscconf, flags=re.MULTILINE)
        petscconf = re.sub(r'^(#define PETSC_PYTHON_EXE) ".*"$', r'\1 "python3"', petscconf, flags=re.MULTILINE)
        save(self, petscconf_h, petscconf)

        save(
            self,
            path.join(include_folder, "petscconfiginfo.h"),
            'static const char *petscconfigureoptions = "Conan-packaged PETSc build";\n',
        )
        save(
            self,
            path.join(include_folder, "petscmachineinfo.h"),
            """static const char *petscmachineinfo = "\\n"
"-----------------------------------------\\n"
"Conan-packaged PETSc build\\n"
"-----------------------------------------\\n";
static const char *petsccompilerinfo = "\\n"
"Using C compiler information provided by the package manager\\n"
"-----------------------------------------\\n";
static const char *petsccompilerflagsinfo = "\\n"
"Using compiler flags provided by the package manager\\n"
"-----------------------------------------\\n";
static const char *petsclinkerinfo = "\\n"
"Using linker flags provided by the package manager\\n"
"-----------------------------------------\\n";
""",
        )

    def _configure_args(self):
        openmpi_root = self.dependencies["openmpi"].package_folder
        openblas_flags = " ".join(self._dependency_link_flags("openblas"))
        shared = 1 if self.options.shared else 0
        fpic = 1 if self.options.shared else 0
        debugging = 1 if self.settings.build_type == "Debug" else 0

        args = [
            f"PETSC_ARCH={self._petsc_arch}",
            f"--prefix={self.package_folder}",
            f"--with-cc={path.join(openmpi_root, 'bin', 'mpicc')}",
            f"--with-mpiexec={path.join(openmpi_root, 'bin', 'mpiexec')}",
            "--with-mpi=1",
            "--with-cxx=0",
            "--with-fc=0",
            "--with-clanguage=C",
            "--with-fortran-bindings=0",
            "--with-sowing=0",
            f"--with-debugging={debugging}",
            f"--with-shared-libraries={shared}",
            f"--with-pic={fpic}",
            "--with-single-library=1",
            "--with-scalar-type=real",
            "--with-precision=double",
            "--with-64-bit-indices=0",
            "--with-x=0",
            "--with-openmp=0",
            "--with-ssl=0",
            "--with-hdf5=0",
            "--with-fftw=0",
            "--with-hwloc=0",
            "--with-hypre=0",
            "--with-metis=0",
            "--with-mumps=0",
            "--with-parmetis=0",
            "--with-petsc4py=0",
            "--with-ptscotch=0",
            "--with-scalapack=0",
            "--with-superlu=0",
            "--with-superlu_dist=0",
            "--with-suitesparse=0",
            "--with-yaml=0",
            f"--with-blaslapack-lib={openblas_flags}",
        ]
        if not self.options.shared and self.options.get_safe("fPIC", False):
            args.append("CFLAGS+=-fPIC")
        return args

    def build(self):
        configure_command = "python3 ./configure " + " ".join(quote(argument) for argument in self._configure_args())
        make_command = f"make PETSC_DIR={quote(self.source_folder)} PETSC_ARCH={quote(self._petsc_arch)} MAKE_NP={build_jobs(self)} all"

        with chdir(self, self.source_folder):
            self._patch_runtime_path_lookup()
            with self._build_environment().apply():
                self.run(configure_command)
                self._sanitize_generated_headers()
                self.run(make_command)

    def package(self):
        install_command = f"make PETSC_DIR={quote(self.source_folder)} PETSC_ARCH={quote(self._petsc_arch)} install"

        with chdir(self, self.source_folder):
            with self._build_environment().apply():
                self.run(install_command)

        copy(self, "LICENSE", self.source_folder, path.join(self.package_folder, "licenses"))
        rmdir(self, path.join(self.package_folder, "lib", "petsc", "conf"))
        rmdir(self, path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, path.join(self.package_folder, "share", "petsc", "examples"))
        rmdir(self, path.join(self.package_folder, "share", "petsc", "datafiles"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PETSc")
        self.cpp_info.set_property("cmake_target_name", "PETSc::PETSc")
        self.cpp_info.set_property("pkg_config_name", "PETSc")
        self.cpp_info.builddirs = []
        self.cpp_info.libs = ["petsc"]
        self.cpp_info.requires = ["openblas::openblas_component", "openmpi::openmpi"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["dl", "m"])

        openmpi_root = self.dependencies["openmpi"].package_folder
        self.cpp_info.includedirs.extend([
            path.join(openmpi_root, "include"),
            path.join(openmpi_root, "include", "openmpi"),
        ])
        self.runenv_info.define_path("PETSC_DIR", self.package_folder)
        self.runenv_info.define_path("PETSC_LIB_DIR", path.join(self.package_folder, "lib"))
