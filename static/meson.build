datadir = join_paths(get_option('prefix'), get_option('datadir'))

configure_file(
  input: 'logo.svg',
  output: 'com.tomjwatson.Emote.svg',
  copy: true,
  install_dir: join_paths(datadir, 'icons', 'hicolor', 'scalable', 'apps')
)

configure_file(
  input: 'com.tomjwatson.Emote.desktop',
  output: 'com.tomjwatson.Emote.desktop',
  copy: true,
  install_dir: join_paths(datadir, 'applications')
)

install_subdir('.', install_dir: join_paths(datadir, meson.project_name(), 'static'))
