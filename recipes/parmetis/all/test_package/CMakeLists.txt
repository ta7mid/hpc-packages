cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(ParMETIS REQUIRED CONFIG)
find_package(MPI REQUIRED)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE ParMETIS::ParMETIS MPI::MPI_C)
