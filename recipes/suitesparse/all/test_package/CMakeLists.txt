cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(SuiteSparse REQUIRED COMPONENTS
    suitesparse_config
    amd
    btf
    camd
    ccolamd
    colamd
    cholmod
    cxsparse
    ldl
    klu
    umfpack
)

add_executable(example src/example.c)
target_link_libraries(example PRIVATE
    SuiteSparse::SuiteSparseConfig
    SuiteSparse::AMD
    SuiteSparse::BTF
    SuiteSparse::CAMD
    SuiteSparse::CCOLAMD
    SuiteSparse::COLAMD
    SuiteSparse::CHOLMOD
    SuiteSparse::CXSparse
    SuiteSparse::LDL
    SuiteSparse::KLU
    SuiteSparse::UMFPACK
)

set_target_properties(example PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS YES
)
