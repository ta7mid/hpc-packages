import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir

required_conan_version = ">=2.0.9"


# Inter-module dependency graph parsed from src/<module>/CMakeLists.txt
# LIBRARIES_TO_LINK clauses in ns-3.47.
#
# Modules NOT exposed (require external non-ConanCenter libraries):
#   brite, click, openflow, visualizer
#
# Module names keep upstream's hyphenated form ("internet-apps",
# "point-to-point", ...); Conan option keys substitute underscores
# (with_internet_apps, with_point_to_point, ...).
_MODULES = {
    # Core (deps-free or near-deps-free)
    "core":                    [],
    "stats":                   ["core"],
    "network":                 ["stats"],
    "antenna":                 ["core"],
    "mobility":                ["antenna", "network"],
    "propagation":             ["mobility"],
    "config-store":            ["core"],

    # Layer-2 / link / device modules
    "bridge":                  ["network"],
    "csma":                    ["network"],
    "energy":                  ["network"],
    "fd-net-device":           ["network"],
    "mpi":                     ["network"],
    "point-to-point":          ["network"],  # also "mpi" when NS3_MPI=ON
    "topology-read":           ["network"],
    "traffic-control":         ["network"],
    "virtual-net-device":      ["network"],

    # IP / internet layer
    "internet":                ["bridge", "traffic-control"],
    "applications":            ["internet"],
    "flow-monitor":            ["internet"],
    "internet-apps":           ["internet"],
    "nix-vector-routing":      ["internet"],
    "olsr":                    ["internet"],
    "sixlowpan":               ["internet"],
    "tap-bridge":              ["internet", "network"],
    "csma-layout":             ["csma", "internet", "point-to-point"],
    "point-to-point-layout":   ["internet", "mobility", "point-to-point"],

    # Wireless / spectrum
    "buildings":               ["propagation"],
    "spectrum":                ["antenna", "buildings", "propagation"],
    "lr-wpan":                 ["spectrum"],
    "wifi":                    ["energy", "spectrum"],
    "uan":                     ["energy", "mobility"],
    "zigbee":                  ["lr-wpan"],

    # Routing / ad-hoc
    "mesh":                    ["applications", "wifi"],
    "aodv":                    ["applications", "internet-apps", "wifi"],
    "dsdv":                    ["internet-apps", "mesh"],
    "dsr":                     ["mesh"],

    # Cellular
    "lte": [
        "applications", "buildings", "config-store", "csma", "fd-net-device",
        "point-to-point", "spectrum", "virtual-net-device",
    ],

    # Interface to external NetAnim viewer (no library dep)
    "netanim":                 ["lr-wpan", "lte", "uan", "wifi"],
}

# Default-enabled modules per the user's spec.
_DEFAULT_ENABLED = {
    "applications", "bridge", "core", "csma", "internet", "internet-apps",
    "network", "point-to-point", "topology-read",
}


def _opt_key(module):
    """Conan option key for a module. Underscores instead of hyphens."""
    return "with_" + module.replace("-", "_")


class Ns3Conan(ConanFile):
    name = "ns-3"
    description = (
        "ns-3 is a discrete-event network simulator for Internet systems, "
        "targeted primarily for research and educational use. It is a free "
        "software project licensed under the GNU GPLv2 license."
    )
    license = "GPL-2.0-only"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.nsnam.org"
    topics = (
        "network-simulator", "discrete-event", "tcp-ip", "wifi", "lte",
        "networking", "research", "education",
    )

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    # Option set: required toggles, six external deps, plus a with_<module>
    # boolean per ns-3 module.
    options = {
        "shared":         [True, False],
        "fPIC":           [True, False],
        "with_sqlite3":   [True, False],
        "with_gsl":       [True, False],
        "with_eigen":     [True, False],
        "with_libxml2":   [True, False],
        "with_mpi":       [True, False],
        "with_boost":     [True, False],
        **{_opt_key(m): [True, False] for m in _MODULES},
    }
    default_options = {
        "shared":         False,
        "fPIC":           True,
        "with_sqlite3":   False,
        "with_gsl":       False,
        "with_eigen":     False,
        "with_libxml2":   False,
        "with_mpi":       False,
        "with_boost":     False,
        **{_opt_key(m): (m in _DEFAULT_ENABLED) for m in _MODULES},

        # When with_mpi=True we need MPI::MPI_CXX; Conan's openmpi gates
        # that target behind enable_cxx (matches the superlu_dist and
        # gridpack pattern).
        "openmpi/*:enable_cxx": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # C++23 surface -- keep compiler.cppstd / libcxx settings.

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_sqlite3:
            self.requires("sqlite3/[>=3.45 <4]")
        if self.options.with_gsl:
            self.requires("gsl/[>=2.7 <3]")
        if self.options.with_eigen:
            self.requires("eigen/[>=3.4 <4]")
        if self.options.with_libxml2:
            self.requires("libxml2/[>=2.12 <3]")
        if self.options.with_boost:
            self.requires("boost/[>=1.83 <2]")
        if self.options.with_mpi:
            self.requires(
                "openmpi/[>=4.1.0 <5]",
                transitive_headers=True,
                transitive_libs=True,
            )

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.20 <4]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} does not support Windows. ns-3 targets POSIX systems."
            )
        # At least one module must be enabled (otherwise NS3_ENABLED_MODULES
        # is empty and the build is meaningless).
        if not self._enabled_modules():
            raise ConanInvalidConfiguration(
                f"{self.ref}: at least one with_<module>=True is required "
                "(default-enabled set covers applications, bridge, core, csma, "
                "internet, internet-apps, network, point-to-point, topology-read)."
            )
        # C++23 -- block stdlib versions that can't compile ns-3.47.
        cppstd = self.settings.get_safe("compiler.cppstd")
        if cppstd:
            n = int(str(cppstd).replace("gnu", ""))
            if n < 23:
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires C++23 or newer (got cppstd={cppstd})."
                )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # -- helpers --

    def _enabled_modules(self):
        return [m for m in _MODULES if self.options.get_safe(_opt_key(m))]

    def _enabled_closure(self):
        """Topological closure of enabled modules over the dep graph."""
        out = set()
        stack = list(self._enabled_modules())
        # mpi module is implicit when NS3_MPI=ON
        if self.options.with_mpi:
            stack.append("mpi")
        while stack:
            m = stack.pop()
            if m in out:
                continue
            out.add(m)
            stack.extend(_MODULES[m])
        return out

    def generate(self):
        tc = CMakeToolchain(self)
        cv = tc.cache_variables

        # Build behavior
        cv["BUILD_SHARED_LIBS"]             = bool(self.options.shared)
        cv["NS3_ENABLE_TESTS"]              = False
        cv["NS3_ENABLE_EXAMPLES"]           = False
        cv["NS3_ENABLE_PYTHON_BINDINGS"]    = False
        cv["NS3_NATIVE_OPTIMIZATIONS"]      = False
        cv["NS3_WARNINGS_AS_ERRORS"]        = False
        cv["NS3_PRECOMPILE_HEADERS"]        = False
        cv["NS3_FETCH_OPTIONAL_COMPONENTS"] = False
        cv["NS3_VERBOSE"]                   = False

        # Module selection -- pass the user's enabled set; ns-3 resolves deps.
        cv["NS3_ENABLED_MODULES"] = ";".join(sorted(self._enabled_modules()))

        # External feature flags -- each must be explicit OFF when we don't
        # provide the dep (upstream's defaults are ON for sqlite/gsl/eigen).
        cv["NS3_SQLITE"]      = bool(self.options.with_sqlite3)
        cv["NS3_GSL"]         = bool(self.options.with_gsl)
        cv["NS3_EIGEN"]       = bool(self.options.with_eigen)
        cv["NS3_MPI"]         = bool(self.options.with_mpi)
        cv["NS3_GTK3"]        = False
        cv["NS3_DOCS"]        = False
        cv["NS3_NETANIM"]     = False
        cv["NS3_DPDK"]        = False
        cv["NS3_EMULATION"]   = False
        cv["NS3_TAP_DEVICES"] = False

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
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
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses", "LICENSES"),
        )
        cmake = CMake(self)
        cmake.install()

        # Strip upstream's CMake config; Conan regenerates one with the
        # correct components and relocatable paths.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # Strip the documentation and scratch directories upstream may install.
        for sub in ("doc", "share"):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                rmdir(self, d)
        # bin/ contains test runners and Python wrappers -- non-relocatable.
        if os.path.isdir(os.path.join(self.package_folder, "bin")):
            rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Setting cmake_target_name on the root cpp_info while declaring
        # components causes Conan's CMakeDeps to emit an aggregate ns3::ns3
        # target linking every component.
        self.cpp_info.set_property("cmake_file_name", "ns3")
        self.cpp_info.set_property("cmake_target_name", "ns3::ns3")
        self.cpp_info.set_property("pkg_config_name", "ns3")

        # ns-3 appends a build-profile suffix to library filenames in Debug
        # builds. Conan's settings.build_type=Debug triggers it; otherwise
        # the suffix is empty.
        suffix = "-debug" if self.settings.build_type == "Debug" else ""
        version_tag = self.version  # e.g. "3.47"

        enabled = self._enabled_closure()
        for m in sorted(enabled):
            c = self.cpp_info.components[m.replace("-", "_")]
            c.set_property("cmake_target_name", f"ns3::{m}")
            c.libs = [f"ns{version_tag}-{m}{suffix}"]
            c.includedirs = ["include"]  # public headers at include/ns3/
            # Intra-package deps
            c.requires = [d.replace("-", "_") for d in _MODULES[m]]
            if self.settings.os in ("Linux", "FreeBSD"):
                c.system_libs = ["m", "pthread", "dl", "rt"]

        # Cross-package deps land on core (the universal sub-component),
        # except sqlite3 which the stats module owns and openmpi which the
        # mpi module owns.
        c_core = self.cpp_info.components["core"]
        if self.options.with_boost:
            c_core.requires.append("boost::boost")
        if self.options.with_libxml2:
            c_core.requires.append("libxml2::libxml2")
        if self.options.with_gsl:
            c_core.requires.append("gsl::gsl")
        if self.options.with_eigen:
            c_core.requires.append("eigen::eigen")
        if self.options.with_sqlite3 and "stats" in enabled:
            self.cpp_info.components["stats"].requires.append("sqlite3::sqlite3")
        if self.options.with_mpi and "mpi" in enabled:
            self.cpp_info.components["mpi"].requires.append("openmpi::openmpi")
