# ydotool

https://github.com/ReimuNotMoe/ydotool is a xdotool-equivalent for Wayland. It allows us to simulate a ctrl-v paste to write the emoji out on selection.

`ydotool` is a the application itself
`ydotoold` is a daemon that `ydotool` needs to communicate with to perform the actions

These binaries were built in an Ubuntu 18.04 VM. This was necessary so that they are built with the same `libc6`/`libstdc++6` versions as are available in the `core-18` base snap package.
