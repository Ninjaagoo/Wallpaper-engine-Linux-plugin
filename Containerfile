# Isolate native dependencies from the host distribution, including immutable hosts.
FROM registry.fedoraproject.org/fedora:44
RUN dnf install -y cmake gcc-c++ make git zlib-devel lz4-devel ffmpeg-free-devel \
    libX11-devel libXrandr-devel libXxf86vm-devel libXinerama-devel libXcursor-devel \
    libXi-devel mesa-libGL-devel mesa-libEGL-devel glew-devel glfw-devel glm-devel \
    SDL2-devel freeglut-devel pulseaudio-libs-devel mpv-devel mpv wayland-devel \
    wayland-protocols-devel dbus-devel gmp-devel freetype-devel mesa-dri-drivers \
    && dnf clean all
COPY linux-wallpaperengine /src/linux-wallpaperengine
RUN cmake -S /src/linux-wallpaperengine -B /tmp/engine-build \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    && cmake --build /tmp/engine-build --target linux-wallpaperengine --parallel 2 \
    && mkdir -p /opt/runtime \
    && cp -a /tmp/engine-build/output/. /opt/runtime/ \
    && cp -a /tmp/engine-build/lib/libkissfft*.so* /opt/runtime/ \
    && rm -rf /tmp/engine-build /src/linux-wallpaperengine
# Runtime files are exported by install.py. They remain in the image for reinstallation.
CMD ["/bin/bash"]
