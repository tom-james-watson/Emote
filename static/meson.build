sharedir = join_paths(get_option('prefix'), get_option('datadir'))
pkgdatadir = join_paths(sharedir, meson.project_name())

configure_file(
  input: 'logo.svg',
  output: 'com.tomjwatson.Emote.svg',
  copy: true,
  install_dir: join_paths(sharedir, 'icons', 'hicolor', 'scalable', 'apps')
)

install_subdir('.', install_dir: join_paths(pkgdatadir, 'static'))