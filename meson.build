project('emote',
    version: '3.1.0',
    meson_version: '>= 0.50.0',
    default_options: [ 'warning_level=2', ],
)

i18n = import('i18n')

# keybinderdeps = [
#     dependency('libkeybinder-3.0-0'),
#     # dependency('libgirepository1.0-dev'),
#     # dependency('gir1.2-keybinder-3.0')
# ]

# canberra_dep = dependency('libcanberra-gtk3')

subdir('emote')
subdir('static')

# meson.add_install_script('build-aux/meson/postinstall.py', 'emote')