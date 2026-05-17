cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(SuperLU_DIST REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE SuperLU_DIST::superlu_dist)
