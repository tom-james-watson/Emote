pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'emote')
python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'emote.in',
  output: 'emote',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

install_data(
  '__init__.py',
  '__main__.py',
  'config.py',
  'css.py',
  'debouncer.py',
  'emojis.py',
  'keyboard_shortcuts.py',
  'picker.py',
  'picker_dialogs.py',
  'settings.py',
  'user_data.py',
  'wayland_paste.py',
  'wayland_shortcut.py',
  'x11_hotkey.py',
  install_dir: moduledir,
)
