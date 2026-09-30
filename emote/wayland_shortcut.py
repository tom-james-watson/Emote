"""Register Emote's launcher shortcut through the GlobalShortcuts portal."""

import os
import secrets

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

PORTAL_NAME = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
PORTAL_INTERFACE = "org.freedesktop.portal.GlobalShortcuts"
DBUS_INTERFACE = "org.freedesktop.DBus"
HOST_REGISTRY_INTERFACE = "org.freedesktop.host.portal.Registry"
REQUEST_INTERFACE = "org.freedesktop.portal.Request"
SESSION_INTERFACE = "org.freedesktop.portal.Session"

APP_ID = "com.tomjwatson.Emote"

SHORTCUT_ID = "open-emote"
LEGACY_SHORTCUT_ID = "open-picker"
SHORTCUT_DESCRIPTION = "Open Emote"
PREFERRED_TRIGGER = "CTRL+ALT+e"
CALL_TIMEOUT_MS = 15_000
RECOVERY_DELAY_MS = 1_000


class WaylandShortcut:
    def __init__(
        self, on_activated, on_bound=None, on_missing=None, on_unavailable=None
    ):
        self._on_activated = on_activated
        self._on_bound = on_bound
        self._on_missing = on_missing
        self._on_unavailable = on_unavailable
        self._bus = None
        self._session_handle = None
        self._activation_subscription = None
        self._changed_subscription = None
        self._closed_subscription = None
        self._owner_subscription = None
        self._request_subscriptions = set()
        self._generation = 0
        self._enabled = False
        self._host_registered = False
        self._bind_requested = False
        self._bind_attempted = False
        self._force_bind = False
        self._parent_window = ""
        self._registered = False
        self._shortcut_id = SHORTCUT_ID
        self._last_bound_trigger = None
        self._recover_source = None

    @property
    def is_registered(self):
        return self._registered

    def enable(self):
        if self._enabled:
            return

        self._enabled = True
        self._generation += 1
        generation = self._generation
        if self._bus is not None and not self._bus.is_closed():
            self._continue_bus_ready(generation)
            return
        try:
            address = Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None)
            flags = (
                Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
                | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
            )
            Gio.DBusConnection.new_for_address(
                address,
                flags,
                None,
                None,
                lambda source, result: self._on_bus_ready(source, result, generation),
            )
        except Exception as exc:
            self._fail(exc)

    def disable(self):
        self._enabled = False
        self._bind_requested = False
        self._generation += 1
        self._close_session()
        if self._recover_source is not None:
            GLib.source_remove(self._recover_source)
            self._recover_source = None
        if self._bus and self._owner_subscription is not None:
            self._bus.signal_unsubscribe(self._owner_subscription)
            self._owner_subscription = None

    def bind(self, parent_window=""):
        self._parent_window = parent_window
        self._bind_requested = True
        if not self._enabled:
            self.enable()
        elif self._session_handle:
            if self._bind_attempted:
                self.disable()
                self._force_bind = True
                self.enable()
            else:
                self._bind_requested = False
                self._bind_shortcut(self._generation)

    def close(self):
        self.disable()
        if self._bus is not None:
            try:
                self._bus.close_sync(None)
            except Exception:
                pass
            self._bus = None

    def _on_bus_ready(self, source, result, generation):
        if generation != self._generation or not self._enabled:
            return
        try:
            self._bus = Gio.DBusConnection.new_for_address_finish(result)
            self._continue_bus_ready(generation)
        except Exception as exc:
            self._fail(exc)

    def _continue_bus_ready(self, generation):
        if generation != self._generation or not self._enabled:
            return
        if self._owner_subscription is None:
            self._owner_subscription = self._bus.signal_subscribe(
                DBUS_INTERFACE,
                DBUS_INTERFACE,
                "NameOwnerChanged",
                "/org/freedesktop/DBus",
                PORTAL_NAME,
                Gio.DBusSignalFlags.MATCH_ARG0_NAMESPACE,
                self._on_portal_owner_changed,
            )
        # Use a private bus connection so GTK cannot make a portal call before
        # host registration associates the connection with Emote's app ID.
        if (
            os.environ.get("FLATPAK_ID")
            or os.environ.get("SNAP")
            or self._host_registered
        ):
            self._create_session(generation)
        else:
            self._register_host_app(generation)

    def _register_host_app(self, generation):
        """Give an unsandboxed process the identity required by newer portals."""
        self._bus.call(
            PORTAL_NAME,
            PORTAL_PATH,
            HOST_REGISTRY_INTERFACE,
            "Register",
            GLib.Variant("(sa{sv})", (APP_ID, {})),
            None,
            Gio.DBusCallFlags.NONE,
            CALL_TIMEOUT_MS,
            None,
            lambda connection, result: self._on_host_app_registered(
                connection, result, generation
            ),
        )

    def _on_host_app_registered(self, connection, result, generation):
        if generation != self._generation or not self._enabled:
            return
        try:
            connection.call_finish(result)
        except GLib.Error as exc:
            # The registry was added in xdg-desktop-portal 1.19.4. Older
            # versions infer host application IDs and do not expose it.
            unsupported = {
                "org.freedesktop.DBus.Error.UnknownInterface",
                "org.freedesktop.DBus.Error.UnknownMethod",
            }
            if Gio.DBusError.get_remote_error(exc) not in unsupported:
                self._fail(exc)
                return
        except Exception as exc:
            self._fail(exc)
            return
        self._host_registered = True
        self._create_session(generation)

    def _create_session(self, generation):
        request_token = self._new_token()
        session_token = self._new_token()
        request_path = self._request_path(request_token)
        session_path = self._session_path(session_token)
        options = {
            "handle_token": GLib.Variant("s", request_token),
            "session_handle_token": GLib.Variant("s", session_token),
        }
        self._call_request(
            "CreateSession",
            GLib.Variant("(a{sv})", (options,)),
            request_path,
            generation,
            lambda results: self._on_session_created(results, session_path, generation),
        )

    def _on_session_created(self, results, expected_session_path, generation):
        session_handle = results.get("session_handle")
        if session_handle != expected_session_path:
            self._fail(RuntimeError("the portal returned an unexpected session handle"))
            return

        self._session_handle = session_handle
        self._bind_attempted = False
        self._activation_subscription = self._bus.signal_subscribe(
            PORTAL_NAME,
            PORTAL_INTERFACE,
            "Activated",
            PORTAL_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_portal_activated,
        )
        self._changed_subscription = self._bus.signal_subscribe(
            PORTAL_NAME,
            PORTAL_INTERFACE,
            "ShortcutsChanged",
            PORTAL_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_shortcuts_changed,
        )
        self._closed_subscription = self._bus.signal_subscribe(
            PORTAL_NAME,
            SESSION_INTERFACE,
            "Closed",
            self._session_handle,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_session_closed,
        )
        if self._force_bind:
            self._force_bind = False
            self._bind_shortcut(generation)
        else:
            self._list_shortcuts(generation)

    def _list_shortcuts(self, generation):
        request_token = self._new_token()
        request_path = self._request_path(request_token)
        options = {"handle_token": GLib.Variant("s", request_token)}
        parameters = GLib.Variant("(oa{sv})", (self._session_handle, options))
        self._call_request(
            "ListShortcuts",
            parameters,
            request_path,
            generation,
            self._on_shortcuts_listed,
        )

    def _on_shortcuts_listed(self, results):
        shortcut = self._find_shortcut(results)
        if shortcut is not None:
            self._registered = True
            self._bind_requested = False
            self._notify_bound(shortcut)
        elif self._bind_requested:
            self._registered = False
            self._bind_requested = False
            self._bind_shortcut(self._generation)
        elif self._on_missing:
            self._registered = False
            self._last_bound_trigger = None
            self._on_missing(False)

    def _bind_shortcut(self, generation):
        self._bind_attempted = True
        request_token = self._new_token()
        request_path = self._request_path(request_token)
        shortcut_properties = {
            "description": GLib.Variant("s", SHORTCUT_DESCRIPTION),
            "preferred_trigger": GLib.Variant("s", PREFERRED_TRIGGER),
        }
        shortcuts = [(self._shortcut_id, shortcut_properties)]
        options = {"handle_token": GLib.Variant("s", request_token)}
        parameters = GLib.Variant(
            "(oa(sa{sv})sa{sv})",
            (self._session_handle, shortcuts, self._parent_window, options),
        )
        self._call_request(
            "BindShortcuts",
            parameters,
            request_path,
            generation,
            self._on_shortcut_bound,
        )

    def _on_shortcut_bound(self, results):
        shortcut = self._find_shortcut(results)
        if shortcut is not None and self._trigger_description(shortcut):
            self._registered = True
            self._notify_bound(shortcut)
            return
        if self._on_missing:
            self._registered = shortcut is not None
            self._on_missing(self._registered)

    def _find_shortcut(self, results):
        shortcuts = dict(results.get("shortcuts", []))
        # Preserve earlier development bindings, including disabled entries.
        # Never manufacture a new action ID to force another permission offer.
        candidates = (self._shortcut_id, SHORTCUT_ID, LEGACY_SHORTCUT_ID)
        for require_trigger in (True, False):
            for shortcut_id in candidates:
                properties = shortcuts.get(shortcut_id)
                if properties is not None and (
                    not require_trigger or self._trigger_description(properties)
                ):
                    self._shortcut_id = shortcut_id
                    return properties
        return None

    def _notify_bound(self, properties):
        trigger = self._trigger_description(properties)
        if trigger and self._on_bound:
            # GNOME emits ShortcutsChanged before completing BindShortcuts.
            # Treat both messages as one state transition so onboarding does
            # not advance twice.
            if trigger == self._last_bound_trigger:
                return
            self._last_bound_trigger = trigger
            self._on_bound(trigger)
        elif self._on_missing:
            self._last_bound_trigger = None
            self._on_missing(True)

    @staticmethod
    def _trigger_description(properties):
        trigger = properties.get("trigger_description")
        return trigger.strip() if isinstance(trigger, str) else None

    def _call_request(self, method, parameters, request_path, generation, on_success):
        context = {
            "generation": generation,
            "request_path": request_path,
            "on_success": on_success,
        }
        subscription = self._bus.signal_subscribe(
            PORTAL_NAME,
            REQUEST_INTERFACE,
            "Response",
            request_path,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_request_response,
            context,
        )
        context["subscription"] = subscription
        self._request_subscriptions.add(subscription)
        self._bus.call(
            PORTAL_NAME,
            PORTAL_PATH,
            PORTAL_INTERFACE,
            method,
            parameters,
            GLib.VariantType.new("(o)"),
            Gio.DBusCallFlags.NONE,
            CALL_TIMEOUT_MS,
            None,
            lambda connection, result: self._on_request_started(
                connection, result, request_path, subscription, generation
            ),
        )

    def _on_request_started(
        self, connection, result, request_path, subscription, generation
    ):
        if generation != self._generation or not self._enabled:
            self._unsubscribe_request(subscription)
            return
        try:
            returned_path = connection.call_finish(result).unpack()[0]
            if returned_path != request_path:
                self._unsubscribe_request(subscription)
                self._fail(
                    RuntimeError(
                        "the portal returned an unexpected request handle: "
                        f"expected {request_path}, got {returned_path}"
                    )
                )
        except Exception as exc:
            self._unsubscribe_request(subscription)
            self._fail(exc)

    def _on_request_response(
        self,
        _connection,
        _sender_name,
        _object_path,
        _interface_name,
        _signal_name,
        parameters,
        user_data,
    ):
        generation = user_data["generation"]
        on_success = user_data["on_success"]
        subscription = user_data["subscription"]
        self._unsubscribe_request(subscription)
        response, results = parameters.unpack()
        if generation != self._generation or not self._enabled:
            return

        if response != 0:
            self._fail(
                RuntimeError(
                    f"the desktop did not approve the shortcut (response {response})"
                )
            )
            return

        try:
            on_success(results)
        except Exception as exc:
            self._fail(exc)

    def _on_portal_activated(
        self,
        _connection,
        _sender_name,
        _object_path,
        _interface_name,
        _signal_name,
        parameters,
    ):
        session_handle, shortcut_id, _timestamp, options = parameters.unpack()
        if (
            self._enabled
            and session_handle == self._session_handle
            and shortcut_id == self._shortcut_id
        ):
            self._on_activated(options.get("activation_token"))

    def _on_shortcuts_changed(
        self,
        _connection,
        _sender_name,
        _object_path,
        _interface_name,
        _signal_name,
        parameters,
    ):
        session_handle, shortcuts = parameters.unpack()
        if not self._enabled or session_handle != self._session_handle:
            return
        shortcut = self._find_shortcut({"shortcuts": shortcuts})
        if shortcut is not None:
            self._registered = True
            self._notify_bound(shortcut)
        elif self._on_missing:
            self._registered = False
            self._last_bound_trigger = None
            self._on_missing(False)

    def _on_session_closed(self, *_args):
        if self._enabled:
            self._connection_lost(
                RuntimeError("the desktop closed the shortcut session")
            )

    def _on_portal_owner_changed(
        self,
        _connection,
        _sender_name,
        _object_path,
        _interface_name,
        _signal_name,
        parameters,
    ):
        _name, old_owner, new_owner = parameters.unpack()
        if self._enabled and old_owner and old_owner != new_owner:
            self._host_registered = False
            self._connection_lost(RuntimeError("the desktop portal restarted"))

    def _connection_lost(self, error):
        self._enabled = False
        self._generation += 1
        self._close_session(close_remote=False)
        if self._on_unavailable:
            self._on_unavailable(error)
        if self._recover_source is None:
            self._recover_source = GLib.timeout_add(
                RECOVERY_DELAY_MS, self._recover_after_loss
            )

    def _recover_after_loss(self):
        self._recover_source = None
        self.enable()
        return GLib.SOURCE_REMOVE

    def _fail(self, error):
        print("Could not register Wayland global shortcut:", error)
        self._enabled = False
        self._force_bind = False
        self._generation += 1
        self._close_session()
        if self._on_unavailable:
            self._on_unavailable(error)

    def _close_session(self, close_remote=True):
        for subscription in tuple(self._request_subscriptions):
            self._unsubscribe_request(subscription)

        if self._bus and self._activation_subscription is not None:
            self._bus.signal_unsubscribe(self._activation_subscription)
            self._activation_subscription = None
        if self._bus and self._changed_subscription is not None:
            self._bus.signal_unsubscribe(self._changed_subscription)
            self._changed_subscription = None
        if self._bus and self._closed_subscription is not None:
            self._bus.signal_unsubscribe(self._closed_subscription)
            self._closed_subscription = None

        session_handle = self._session_handle
        self._session_handle = None
        self._last_bound_trigger = None
        if close_remote and session_handle and self._bus:
            self._bus.call(
                PORTAL_NAME,
                session_handle,
                SESSION_INTERFACE,
                "Close",
                None,
                None,
                Gio.DBusCallFlags.NONE,
                CALL_TIMEOUT_MS,
                None,
                lambda connection, result: self._ignore_close_error(connection, result),
            )

    def _unsubscribe_request(self, subscription):
        if self._bus and subscription in self._request_subscriptions:
            self._bus.signal_unsubscribe(subscription)
            self._request_subscriptions.remove(subscription)

    @staticmethod
    def _ignore_close_error(connection, result):
        try:
            connection.call_finish(result)
        except Exception:
            pass

    def _request_path(self, token):
        sender = self._sender_name()
        return f"{PORTAL_PATH}/request/{sender}/{token}"

    def _session_path(self, token):
        sender = self._sender_name()
        return f"{PORTAL_PATH}/session/{sender}/{token}"

    def _sender_name(self):
        # Portal object paths encode the unique bus name without its leading
        # colon (":1.42" becomes "1_42").
        return self._bus.get_unique_name().lstrip(":").replace(".", "_")

    @staticmethod
    def _new_token():
        return f"emote_{secrets.token_hex(8)}"
