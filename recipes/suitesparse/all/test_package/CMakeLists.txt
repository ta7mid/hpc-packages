cmake_minimum_required(VERSION 3.22)
project(test_package C)

# Conan generates a single SuiteSparseConfig.cmake; the per-component
# targets (SuiteSparse::AMD, SuiteSparse::CHOLMOD, etc.) live inside it.
find_package(SuiteSparse REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME}
    PRIVATE
        SuiteSparse::AMD
        SuiteSparse::CHOLMOD
)
