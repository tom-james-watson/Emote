project('emote',
    version: '3.1.0',
    meson_version: '>= 0.50.0',
    default_options: [ 'warning_level=2', ],
)
# Warning levels: 0, 1, 2, 3, everything

i18n = import('i18n')

# keybinderdeps = [
#     dependency('keybinder-3.0'),
#     # dependency('gio-2.0'),
#     # dependency('gir1.2-keybinder-3.0')
# ]
# canberra_dep = dependency('libcanberra-gtk3')

subdir('emote')
subdir('static')
subdir('flatpak')
