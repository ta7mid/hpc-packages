cmake_minimum_required(VERSION 3.15)
project(ParMETIS LANGUAGES C)

include(CheckFunctionExists)
include(CheckIncludeFile)
include(GNUInstallDirs)

find_package(MPI REQUIRED COMPONENTS C)

check_include_file(execinfo.h HAVE_EXECINFO_H)
check_function_exists(getline HAVE_GETLINE)

set(parmetis_compile_definitions)
if(CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "FreeBSD")
    list(APPEND parmetis_compile_definitions LINUX)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    list(APPEND parmetis_compile_definitions MACOS)
elseif(CMAKE_SYSTEM_NAME STREQUAL "SunOS")
    list(APPEND parmetis_compile_definitions SUNOS)
endif()

if(HAVE_EXECINFO_H)
    list(APPEND parmetis_compile_definitions HAVE_EXECINFO_H)
endif()

if(HAVE_GETLINE)
    list(APPEND parmetis_compile_definitions HAVE_GETLINE)
endif()

file(GLOB gklib_sources CONFIGURE_DEPENDS metis/GKlib/*.c)
add_library(GKlib ${gklib_sources})
set_target_properties(GKlib PROPERTIES
    OUTPUT_NAME GKlib
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS YES
)
target_include_directories(GKlib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/metis/GKlib>
)
target_compile_definitions(GKlib PRIVATE ${parmetis_compile_definitions})
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Windows")
    target_link_libraries(GKlib PUBLIC m)
endif()

file(GLOB metis_sources CONFIGURE_DEPENDS metis/libmetis/*.c)
add_library(metis ${metis_sources})
set_target_properties(metis PROPERTIES
    OUTPUT_NAME metis
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS YES
)
target_include_directories(metis
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/metis/libmetis
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/metis/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_compile_definitions(metis PRIVATE ${parmetis_compile_definitions})
target_link_libraries(metis PUBLIC GKlib)

file(GLOB parmetis_sources CONFIGURE_DEPENDS libparmetis/*.c)
add_library(parmetis ${parmetis_sources})
add_library(ParMETIS::ParMETIS ALIAS parmetis)
set_target_properties(parmetis PROPERTIES
    OUTPUT_NAME parmetis
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS YES
)

target_include_directories(parmetis
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/libparmetis
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_compile_definitions(parmetis PRIVATE ${parmetis_compile_definitions})
target_link_libraries(parmetis
    PUBLIC
        MPI::MPI_C
        metis
)

install(TARGETS GKlib metis parmetis
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(FILES include/parmetis.h metis/include/metis.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(DIRECTORY metis/GKlib/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR} FILES_MATCHING PATTERN "*.h")
