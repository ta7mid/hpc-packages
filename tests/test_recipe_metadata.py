from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


RECIPES = {
    "parmetis": {
        "version": "4.0.3",
        "cmake_file": "ParMETIS",
        "targets": ["ParMETIS::ParMETIS"],
        "pkg_config": ["parmetis"],
    },
    "suitesparse": {
        "version": "7.12.2",
        "cmake_file": "SuiteSparse",
        "targets": [
            "SuiteSparse::SuiteSparse_config",
            "SuiteSparse::AMD",
            "SuiteSparse::BTF",
            "SuiteSparse::CAMD",
            "SuiteSparse::CCOLAMD",
            "SuiteSparse::CHOLMOD",
            "SuiteSparse::COLAMD",
            "SuiteSparse::CXSparse",
            "SuiteSparse::KLU",
            "SuiteSparse::LDL",
            "SuiteSparse::SPQR",
            "SuiteSparse::UMFPACK",
        ],
        "pkg_config": ["SuiteSparse_config", "AMD", "CHOLMOD", "UMFPACK", "SPQR"],
    },
    "superlu_dist": {
        "version": "9.2.1",
        "cmake_file": "SuperLU_DIST",
        "targets": ["SuperLU_DIST::superlu_dist"],
        "pkg_config": ["superlu_dist"],
    },
    "petsc": {
        "version": "3.25.1",
        "cmake_file": "PETSc",
        "targets": ["PETSc::PETSc"],
        "pkg_config": ["petsc"],
    },
}


def recipe_file(name):
    return ROOT / "recipes" / name / "all" / "conanfile.py"


class RecipeMetadataTest(unittest.TestCase):
    def test_recipes_use_conan_center_index_layout(self):
        for name in RECIPES:
            with self.subTest(recipe=name):
                base = ROOT / "recipes" / name / "all"
                self.assertTrue((base / "conanfile.py").is_file())
                self.assertTrue((base / "conandata.yml").is_file())
                self.assertTrue((base / "test_package" / "conanfile.py").is_file())
                self.assertTrue((base / "test_package" / "CMakeLists.txt").is_file())
                self.assertTrue((base / "test_package" / "test_package.cpp").is_file())


    def test_recipes_pin_current_upstream_versions(self):
        for name, metadata in RECIPES.items():
            with self.subTest(recipe=name):
                text = recipe_file(name).read_text()
                self.assertIn('required_conan_version = ">=2.0"', text)
                self.assertIn(f'name = "{name}"', text)
                self.assertIn(f'version = "{metadata["version"]}"', text)


    def test_recipes_publish_upstream_compatible_cmake_names(self):
        for name, metadata in RECIPES.items():
            with self.subTest(recipe=name):
                text = recipe_file(name).read_text()
                self.assertIn(f'"cmake_file_name", "{metadata["cmake_file"]}"', text)
                for target in metadata["targets"]:
                    self.assertIn(target, text)
                for pkg_config_name in metadata["pkg_config"]:
                    self.assertTrue(
                        f'"pkg_config_name", "{pkg_config_name}"' in text
                        or f'pkg_config="{pkg_config_name}"' in text
                    )


    def test_recipes_do_not_vendor_available_conan_dependencies(self):
        dependency_expectations = {
            "parmetis": ["gklib/5.1.1", "metis/5.2.1", "openmpi/4.1.8"],
            "superlu_dist": ["parmetis/4.0.3", "openblas/0.3.30", "openmpi/4.1.8"],
            "petsc": [
                "openblas/0.3.30",
                "openmpi/4.1.8",
                "parmetis/4.0.3",
                "suitesparse/7.12.2",
                "superlu_dist/9.2.1",
                "metis/5.2.1",
                "hdf5/1.14.6",
            ],
        }
        for name, dependencies in dependency_expectations.items():
            with self.subTest(recipe=name):
                text = recipe_file(name).read_text()
                for dependency in dependencies:
                    self.assertIn(dependency, text)

    def test_recipes_pass_absolute_dependency_library_paths_to_upstream_builds(self):
        for name in ("suitesparse", "superlu_dist", "petsc"):
            with self.subTest(recipe=name):
                text = recipe_file(name).read_text()
                self.assertIn("dep.package_folder", text)
                self.assertIn("lib{lib}.so.*", text)

    def test_mpi_configure_recipes_use_openmpi_runtime_environment(self):
        for name in ("superlu_dist", "petsc"):
            with self.subTest(recipe=name):
                text = recipe_file(name).read_text()
                self.assertIn("OPAL_PREFIX", text)
                self.assertIn("DYLD_LIBRARY_PATH", text)

    def test_petsc_models_optional_external_packages_as_conan_options(self):
        text = recipe_file("petsc").read_text()
        for option in (
            "with_parmetis",
            "with_metis",
            "with_suitesparse",
            "with_superlu_dist",
            "with_hdf5",
        ):
            with self.subTest(option=option):
                self.assertIn(f'"{option}": [True, False]', text)
                self.assertIn(f'"{option}": False', text)

    def test_petsc_consumes_optional_external_packages_when_enabled(self):
        text = recipe_file("petsc").read_text()
        for option, petsc_name in (
            ("with_parmetis", "parmetis"),
            ("with_metis", "metis"),
            ("with_superlu_dist", "superlu_dist"),
            ("with_suitesparse", "suitesparse"),
            ("with_hdf5", "hdf5"),
        ):
            with self.subTest(option=option):
                self.assertIn(f"self.options.{option}", text)
                self.assertIn(f'"{petsc_name}"', text)
        self.assertIn('f"--with-{petsc_name}={int(bool(enabled))}"', text)
        self.assertIn('f"--with-{petsc_name}-include"', text)
        self.assertIn('f"--with-{petsc_name}-lib"', text)

    def test_petsc_debugging_follows_build_type(self):
        text = recipe_file("petsc").read_text()
        self.assertNotIn("with_debugging", text)
        self.assertIn("str(self.settings.build_type) == 'Debug'", text)


if __name__ == "__main__":
    unittest.main()
