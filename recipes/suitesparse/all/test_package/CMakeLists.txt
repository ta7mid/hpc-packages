cmake_minimum_required(VERSION 3.22)
project(test_package C)

# Exercises both per-subproject and namespaced-target discovery.
find_package(AMD     REQUIRED CONFIG)
find_package(CHOLMOD REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME}
    PRIVATE
        SuiteSparse::AMD
        SuiteSparse::CHOLMOD
)
