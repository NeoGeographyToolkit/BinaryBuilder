#----------------------------------------------------------------
# Generated CMake target import file for configuration "RelWithDebInfo".
#----------------------------------------------------------------

# Commands may need to know the format version.
SET(CMAKE_IMPORT_FILE_VERSION 1)

# Compute the installation prefix relative to this file.
GET_FILENAME_COMPONENT(_IMPORT_PREFIX "${CMAKE_CURRENT_LIST_FILE}" PATH)
GET_FILENAME_COMPONENT(_IMPORT_PREFIX "${MY_BOOST_DIR}" PATH)

# Import target "boost_date_time-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time.a"
  )

# Import target "boost_date_time-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time-mt.a"
  )

# Import target "boost_date_time-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-shared PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_date_time.${MY_BOOST_VERSION}"
  )

# Import target "boost_date_time-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_date_time-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_date_time-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time-d.a"
  )

# Import target "boost_date_time-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time-mt-d.a"
  )

# Import target "boost_date_time-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-shared-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_date_time-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_date_time-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_date_time-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_date_time-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_date_time-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_date_time-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_thread-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_thread-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_thread-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_thread-mt.a"
  )

# Import target "boost_thread-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_thread-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_thread-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_thread-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_thread-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_thread-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_thread-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_thread-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_thread-mt-d.a"
  )

# Import target "boost_thread-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_thread-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_thread-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_thread-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_thread-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_regex-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_regex-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_regex-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libicuuc.so;/usr/lib/libicui18n.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_regex.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_regex.${MY_BOOST_VERSION}"
  )

# Import target "boost_regex-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_regex-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_regex-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libicuuc.so;/usr/lib/libicui18n.so;pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_regex-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_regex-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_regex-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_regex-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_regex-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libicuuc.so;/usr/lib/libicui18n.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_regex-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_regex-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_regex-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_regex-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_regex-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libicuuc.so;/usr/lib/libicui18n.so;pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_regex-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_regex-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_serialization-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization.a"
  )

# Import target "boost_serialization-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization-mt.a"
  )

# Import target "boost_serialization-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-shared PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_serialization.${MY_BOOST_VERSION}"
  )

# Import target "boost_serialization-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_serialization-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_serialization-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization-d.a"
  )

# Import target "boost_serialization-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization-mt-d.a"
  )

# Import target "boost_serialization-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-shared-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_serialization-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_serialization-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_serialization-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_serialization-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_serialization-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_serialization-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_wserialization-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_serialization-static"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization.a"
  )

# Import target "boost_wserialization-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_serialization-mt-static"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization-mt.a"
  )

# Import target "boost_wserialization-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_serialization-shared"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_wserialization.${MY_BOOST_VERSION}"
  )

# Import target "boost_wserialization-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_serialization-mt-shared"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_wserialization-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_wserialization-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_serialization-static-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization-d.a"
  )

# Import target "boost_wserialization-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_serialization-mt-static-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization-mt-d.a"
  )

# Import target "boost_wserialization-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_serialization-shared-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_wserialization-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_wserialization-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wserialization-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wserialization-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_serialization-mt-shared-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wserialization-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_wserialization-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_graph-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_graph-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_graph-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_regex-shared"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_graph.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_graph.${MY_BOOST_VERSION}"
  )

# Import target "boost_graph-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_graph-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_graph-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_regex-mt-shared"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_graph-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_graph-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_graph-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_graph-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_graph-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_regex-shared-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_graph-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_graph-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_graph-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_graph-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_graph-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_regex-mt-shared-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_graph-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_graph-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_python-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python.a"
  )

# Import target "boost_python-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python-mt.a"
  )

# Import target "boost_python-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_python.${MY_BOOST_VERSION}"
  )

# Import target "boost_python-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_python-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_python-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python-d.a"
  )

# Import target "boost_python-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python-mt-d.a"
  )

# Import target "boost_python-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_python-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_python-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_python-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_python-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;/usr/lib/python2.6/config/libpython2.6.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_python-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_python-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_system-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system.a"
  )

# Import target "boost_system-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system-mt.a"
  )

# Import target "boost_system-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-shared PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_system.${MY_BOOST_VERSION}"
  )

# Import target "boost_system-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_system-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_system-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system-d.a"
  )

# Import target "boost_system-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system-mt-d.a"
  )

# Import target "boost_system-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-shared-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_system-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_system-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_system-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_system-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_system-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_system-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_prg_exec_monitor-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor.a"
  )

# Import target "boost_prg_exec_monitor-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor-mt.a"
  )

# Import target "boost_prg_exec_monitor-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-shared PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_prg_exec_monitor.${MY_BOOST_VERSION}"
  )

# Import target "boost_prg_exec_monitor-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_prg_exec_monitor-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_prg_exec_monitor-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor-d.a"
  )

# Import target "boost_prg_exec_monitor-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor-mt-d.a"
  )

# Import target "boost_prg_exec_monitor-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-shared-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_prg_exec_monitor-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_prg_exec_monitor-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_prg_exec_monitor-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_prg_exec_monitor-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_prg_exec_monitor-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_prg_exec_monitor-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_test_exec_monitor-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_test_exec_monitor-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_test_exec_monitor-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_test_exec_monitor.a"
  )

# Import target "boost_test_exec_monitor-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_test_exec_monitor-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_test_exec_monitor-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_test_exec_monitor-mt.a"
  )

# Import target "boost_test_exec_monitor-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_test_exec_monitor-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_test_exec_monitor-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_test_exec_monitor-d.a"
  )

# Import target "boost_test_exec_monitor-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_test_exec_monitor-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_test_exec_monitor-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_test_exec_monitor-mt-d.a"
  )

# Import target "boost_unit_test_framework-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework.a"
  )

# Import target "boost_unit_test_framework-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework-mt.a"
  )

# Import target "boost_unit_test_framework-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-shared PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_unit_test_framework.${MY_BOOST_VERSION}"
  )

# Import target "boost_unit_test_framework-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_unit_test_framework-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_unit_test_framework-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework-d.a"
  )

# Import target "boost_unit_test_framework-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework-mt-d.a"
  )

# Import target "boost_unit_test_framework-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-shared-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_unit_test_framework-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_unit_test_framework-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_unit_test_framework-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_unit_test_framework-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_unit_test_framework-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_unit_test_framework-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_filesystem-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_system-static"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem.a"
  )

# Import target "boost_filesystem-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_system-mt-static"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem-mt.a"
  )

# Import target "boost_filesystem-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_system-shared"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_filesystem.${MY_BOOST_VERSION}"
  )

# Import target "boost_filesystem-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_system-mt-shared"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_filesystem-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_filesystem-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_system-static-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem-d.a"
  )

# Import target "boost_filesystem-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_system-mt-static-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem-mt-d.a"
  )

# Import target "boost_filesystem-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "boost_system-shared-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_filesystem-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_filesystem-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_filesystem-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_filesystem-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_system-mt-shared-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_filesystem-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_filesystem-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_iostreams-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams.a"
  )

# Import target "boost_iostreams-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so;pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams-mt.a"
  )

# Import target "boost_iostreams-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_iostreams.${MY_BOOST_VERSION}"
  )

# Import target "boost_iostreams-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so;pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_iostreams-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_iostreams-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams-d.a"
  )

# Import target "boost_iostreams-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so;pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams-mt-d.a"
  )

# Import target "boost_iostreams-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_iostreams-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_iostreams-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_iostreams-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_iostreams-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "/usr/lib/libz.so;/usr/lib/libbz2.so;pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_iostreams-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_iostreams-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_program_options-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options.a"
  )

# Import target "boost_program_options-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options-mt.a"
  )

# Import target "boost_program_options-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-shared PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_program_options.${MY_BOOST_VERSION}"
  )

# Import target "boost_program_options-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_program_options-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_program_options-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options-d.a"
  )

# Import target "boost_program_options-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options-mt-d.a"
  )

# Import target "boost_program_options-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-shared-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_program_options-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_program_options-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_program_options-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_program_options-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_program_options-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_program_options-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_signals-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-static PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals.a"
  )

# Import target "boost_signals-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals-mt.a"
  )

# Import target "boost_signals-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-shared PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_signals.${MY_BOOST_VERSION}"
  )

# Import target "boost_signals-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_signals-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_signals-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-static-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals-d.a"
  )

# Import target "boost_signals-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals-mt-d.a"
  )

# Import target "boost_signals-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-shared-debug PROPERTIES
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_signals-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_signals-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_signals-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_signals-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_signals-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_signals-mt-d.${MY_BOOST_VERSION}"
  )

# Import target "boost_wave-mt-static" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wave-mt-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wave-mt-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_filesystem-mt-static;boost_thread-mt-static;boost_date_time-mt-static"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wave-mt.a"
  )

# Import target "boost_wave-mt-shared" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wave-mt-shared APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wave-mt-shared PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_filesystem-mt-shared;boost_thread-mt-shared;boost_date_time-mt-shared"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wave-mt-${MY_BOOST_VERSION}.so"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_wave-mt-${MY_BOOST_VERSION}.so"
  )

# Import target "boost_wave-mt-static-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wave-mt-static-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wave-mt-static-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_filesystem-mt-static-debug;boost_thread-mt-static-debug;boost_date_time-mt-static-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wave-mt-d.a"
  )

# Import target "boost_wave-mt-shared-debug" for configuration "RelWithDebInfo"
SET_PROPERTY(TARGET boost_wave-mt-shared-debug APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
SET_TARGET_PROPERTIES(boost_wave-mt-shared-debug PROPERTIES
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELWITHDEBINFO "pthread;rt;boost_filesystem-mt-shared-debug;boost_thread-mt-shared-debug;boost_date_time-mt-shared-debug"
  IMPORTED_LOCATION_RELWITHDEBINFO "${MY_BOOST_DIR}/lib/libboost_wave-mt-d.${MY_BOOST_VERSION}"
  IMPORTED_SONAME_RELWITHDEBINFO "libboost_wave-mt-d.${MY_BOOST_VERSION}"
  )

# Cleanup temporary variables.
SET(_IMPORT_PREFIX)

# Commands beyond this point should not need to know the version.
SET(CMAKE_IMPORT_FILE_VERSION)
