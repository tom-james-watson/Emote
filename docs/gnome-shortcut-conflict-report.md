# Draft: accepting a preferred global shortcut bypasses conflict resolution

Not submitted upstream. Based on a user's reproduction on GNOME; exact package
versions should be attached before filing against gnome-control-center.

## Reproduction

1. Create a custom shortcut that launches Emote, bound to Ctrl+Alt+E.
2. Have Emote call GlobalShortcuts.BindShortcuts with a new action ID and
   preferred_trigger = CTRL+ALT+e.
3. In Add Keyboard Shortcuts, accept the offered shortcut by clicking Add.
4. Observe that the existing custom shortcut remains assigned to the same keys.
5. Repeat with fresh portal state, but click the offered shortcut to enter its
   editor before accepting. The editor offers conflict replacement, and choosing
   Replace disables the custom binding.

Expected: accepting a preferred accelerator checks conflicts and obtains consent
to replace an existing binding, or leaves the new shortcut unassigned with a
clear explanation. Merely accepting the suggested accelerator should not skip
the conflict handling used by the editor.

The requester's successful portal response is not enough to determine whether
the resulting key combination will deliver Activated to that requester. Emote
does not require migration or verification: an existing command-based shortcut
may still open the app successfully.

## Sources

- [GNOME 50 dialog implementation](https://github.com/GNOME/gnome-control-center/blob/50.0/global-shortcuts-provider/cc-global-shortcut-dialog.c)
- [GlobalShortcuts API](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html)

## Related case to test separately

Saving an action without an accelerator persists a disabled entry. Repeating
BindShortcuts for the same ID preserves it rather than providing an editor.
Applications targeting v1 need to distinguish a disabled saved action from an
action which has never been registered. Changing action IDs is not a durable fix.
