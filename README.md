# hpc-packages

Personal Conan v2 recipes for HPC libraries that are not in
[Conan Center Index](https://github.com/conan-io/conan-center-index).

## Recipes

| Package      | Versions | Notes                                                          |
| ------------ | -------- | -------------------------------------------------------------- |
| parmetis     | 4.0.3    | Pinned to a commit on `main`; non-OSI license                  |
| suitesparse  | 7.12.2   | Lean default core; SPQR / ParU / GraphBLAS / … opt-in          |
| superlu_dist | 9.2.1    | Distributed sparse direct solver; depends on local parmetis    |

## Usage

Build a recipe locally:

```shell
conan create recipes/parmetis/all --version=4.0.3
```

Consume from CMake:

```cmake
find_package(ParMETIS REQUIRED)
target_link_libraries(my_app PRIVATE ParMETIS::ParMETIS)
```

## License

The recipe code in this repository is licensed under the MIT License
(see [LICENSE](LICENSE)). Each packaged upstream project retains its own
license; ParMETIS is distributed under an academic, non-OSI license that
restricts commercial use — see
<https://github.com/KarypisLab/ParMETIS/blob/main/LICENSE>.
