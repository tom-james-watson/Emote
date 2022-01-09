FROM ubuntu:20.04

RUN apt-get update

# # pyenv
#
# ENV DEBIAN_FRONTEND=noninteractive
#
# RUN apt-get install -y \
#     make \
#     build-essential \
#     libssl-dev \
#     zlib1g-dev \
#     libbz2-dev \
#     libreadline-dev \
#     libsqlite3-dev \
#     wget \
#     curl \
#     llvm \
#     libncurses5-dev \
#     libncursesw5-dev \
#     xz-utils \
#     tk-dev \
#     libffi-dev \
#     liblzma-dev \
#     python-openssl \
#     git \
#   && rm -rf /var/lib/apt/lists/*
#
# ENV PYENV_ROOT /root/.pyenv
# ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
#
# RUN set -ex && curl https://pyenv.run | bash
# RUN pyenv update
# RUN PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.8.9
#
# RUN eval "$(pyenv init -)"

# pipenv

# python deps

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get install -y \
  libcairo-gobject2 \
  libcairo2 \
  libfontconfig1 \
  libfreetype6 \
  libgirepository-1.0-1 \
  libpixman-1-0 \
  libpng16-16 \
  libx11-6 \
  libxau6 \
  libxcb-render0 \
  libxcb-shm0 \
  libxcb1 \
  libxdmcp6 \
  libxext6 \
  libxrender1 \
  libkeybinder-3.0-0 \
  gir1.2-keybinder-3.0 \
  python3-distutils-extra \
  sound-theme-freedesktop \
  pulseaudio-utils \
  python3-gi \
  gir1.2-unity-5.0 \
  gir1.2-notify-0.7 \
  gir1.2-gtk-3.0 \
  gir1.2-pango-1.0 \
  appmenu-gtk2-module \
  appmenu-gtk3-module \
  libcanberra-gtk-module \
  libcanberra-gtk3-module \
  libglib2.0-dev \
  libpango1.0-dev \
  libgirepository1.0-dev \
  libgdk-pixbuf2.0-dev \
  python3-gi \
  libgtk-3-0 \
  libgtk-3-dev \
  libgirepository1.0-dev \
  python3-venv \
  libkeybinder-dev \
  python-gobject

RUN apt-get install -y pipenv

ENTRYPOINT ["/bin/bash"]

COPY . project
