cmake_minimum_required(VERSION 3.15)
project(parmetis C)

include(GNUInstallDirs)

find_package(MPI REQUIRED COMPONENTS C)
find_package(metis REQUIRED CONFIG)
find_package(gklib REQUIRED CONFIG)

file(GLOB PARMETIS_SOURCES "libparmetis/*.c")

add_library(parmetis ${PARMETIS_SOURCES})

target_include_directories(parmetis
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/libparmetis
)

target_link_libraries(parmetis
    PUBLIC
        MPI::MPI_C
        metis::metis
    PRIVATE
        gklib::gklib
)

set_target_properties(parmetis PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
    POSITION_INDEPENDENT_CODE ${CMAKE_POSITION_INDEPENDENT_CODE}
)

install(TARGETS parmetis
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(FILES include/parmetis.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
