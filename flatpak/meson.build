sharedir = join_paths(get_option('prefix'), get_option('datadir'))
pkgdatadir = join_paths(sharedir, meson.project_name())
appdir = join_paths(sharedir, 'applications')

conf = configuration_data()
conf.set('pkgdatadir', pkgdatadir)
configure_file(
  input: 'com.tomjwatson.Emote.desktop',
  output: 'com.tomjwatson.Emote.desktop',
  configuration: conf,
  install: true,
  install_dir: appdir
)
