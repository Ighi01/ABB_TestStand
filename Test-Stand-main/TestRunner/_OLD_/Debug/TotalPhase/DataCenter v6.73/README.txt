                       Total Phase Data Center
                       -----------------------

Installation Instructions
-------------------------
Additional libraries may be required to be installed depending on
the operating system.


Ubuntu Linux (32bit)
--------------------
sudo apt-get install libc6:i386 zlib1g:i386 \
    libstdc++6:i386 libgtk2.0-0:i386 libpango1.0-0:i386 \
    libxxf86vm1:i386 libsm6:i386 libgstreamer-plugins-base0.10-0:i386


Ubuntu Linux v15.10 or above (64bit)
------------------------------------
sudo apt-get install libgstreamer-plugins-base0.10-0


Debian Linux (32bit or 64bit)
-----------------------------
Remove all libraries under lib except libruntime.so and install
libqtwebkit4 and libphonon4
