## Copyright (C) 2011 Aldebaran Robotics

clean(WSA)
# Note the space is important, we need to set it to something!
set(WSA_INCLUDE_DIRS " " CACHE STRING "" FORCE)
# winsock2.h requires with ws2_32.lib
set(WSA_LIBRARIES "ws2_32" CACHE STRING "" FORCE)
export_lib(WSA)

