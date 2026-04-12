cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(SuperLU_DIST REQUIRED CONFIG)

add_executable(example src/example.c)
target_link_libraries(example PRIVATE SuperLU_DIST::superlu_dist)

set_target_properties(example PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS YES
)
