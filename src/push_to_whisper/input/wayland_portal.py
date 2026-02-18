import logging
import threading
import uuid
from typing import Any, Callable, List, Optional

from gi.repository import GLib
from pydbus import SessionBus

from push_to_whisper.input.base import BaseInputAdapter

logger = logging.getLogger(__name__)


class WaylandPortalInputAdapter(BaseInputAdapter):
    """
    Input adapter for Linux Wayland using xdg-desktop-portal GlobalShortcuts.
    Runs its own GLib MainLoop in a dedicated thread.
    """

    def __init__(self, app_id: str):
        self.app_id = app_id
        self.loop: Optional[GLib.MainLoop] = None
        self.dbus_thread: Optional[threading.Thread] = None

        self.session_handle: Optional[str] = None
        self.on_pressed: Optional[Callable[[str], None]] = None
        self.on_released: Optional[Callable[[str], None]] = None
        self._subscriptions: List[Any] = []
        self._requests: List[Any] = []

        # For debouncing duplicate signals from Portal
        self._last_event_id: str = ""
        self._last_event_name: str = ""
        self._last_event_time: float = 0.0

    def start(
        self,
        on_pressed: Callable[[str], None],
        on_released: Callable[[str], None],
        pipelines: list,
    ) -> None:
        self.on_pressed = on_pressed
        self.on_released = on_released

        # 1. Prepare the MainLoop
        self.loop = GLib.MainLoop()

        # 2. Define the thread function
        def run_loop():
            # SessionBus must be created within the thread that runs the loop
            self.bus = SessionBus()
            self.portal = self.bus.get(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
            )

            # A. Global Signal Subscription
            def on_signal(connection, sender, path, interface, signal, parameters):
                # Check for Response signal
                if signal == "Response":
                    try:
                        status, results = parameters
                        logger.info(
                            f"Portal: Received Response signal. Status: {status}"
                        )

                        if status == 0 and "session_handle" in results:
                            self.session_handle = results["session_handle"]
                            logger.info(
                                f"Portal: Session created successfully: {self.session_handle}"
                            )
                            self._bind_shortcuts(pipelines)
                    except Exception as e:
                        logger.error(f"Portal: Error parsing Response signal: {e}")

                # Check for Shortcut activation
                elif (
                    interface == "org.freedesktop.portal.GlobalShortcuts"
                    or signal in ["Activated", "Deactivated"]
                ):
                    self._handle_signal(
                        connection, sender, path, interface, signal, parameters
                    )

            sub = self.bus.con.signal_subscribe(
                None, None, None, None, None, 0, on_signal
            )
            self._subscriptions.append(sub)

            # B. Initialization sequence inside the loop context
            def deferred_init():
                try:
                    # Explicitly get the GlobalShortcuts interface to avoid method collisions!
                    shortcuts_iface = self.portal[
                        "org.freedesktop.portal.GlobalShortcuts"
                    ]

                    # 1. Bind Nickname
                    if hasattr(self.portal, "BindNickname"):
                        self.portal.BindNickname(self.app_id, "Push to Whisper")
                        logger.info(f"Portal: Bound nickname for {self.app_id}")

                    # 2. Create Session (via GlobalShortcuts interface)
                    handle_token = f"ptw_{uuid.uuid4().hex[:8]}"
                    options = {
                        "handle_token": GLib.Variant("s", handle_token),
                        "session_handle_token": GLib.Variant("s", handle_token),
                    }
                    req_path = shortcuts_iface.CreateSession(options)
                    self._requests.append(req_path)
                    logger.info(
                        f"Portal: CreateSession request sent. Request path: {req_path}"
                    )
                except Exception as e:
                    logger.error(f"Portal: Error during deferred init: {e}")
                return False

            GLib.idle_add(deferred_init)

            logger.info(
                "Wayland Portal: GLib MainLoop is now running in dedicated thread."
            )
            try:
                self.loop.run()
            except Exception as e:
                logger.error(f"Wayland Portal: MainLoop crashed: {e}")

        # 3. Start the thread
        self.dbus_thread = threading.Thread(target=run_loop, daemon=True)
        self.dbus_thread.start()

    def _bind_shortcuts(self, pipelines: list) -> None:
        try:
            # Explicitly use the GlobalShortcuts interface
            shortcuts_iface = self.portal["org.freedesktop.portal.GlobalShortcuts"]
            shortcuts_to_bind = []
            for p in pipelines:
                shortcuts_to_bind.append(
                    (
                        p.id,
                        {
                            "description": GLib.Variant("s", p.description or p.id),
                            "preferred_trigger": GLib.Variant("s", p.preferred_trigger),
                        },
                    )
                )

            bind_req_path = shortcuts_iface.BindShortcuts(
                self.session_handle,
                shortcuts_to_bind,
                "",  # parent_window
                {"handle_token": GLib.Variant("s", f"bind_{uuid.uuid4().hex[:8]}")},
            )
            self._requests.append(bind_req_path)
            logger.info(f"Portal: Requested binding for {len(pipelines)} shortcuts.")
        except Exception as e:
            logger.error(f"Portal: Failed to bind shortcuts: {e}")

    def _handle_signal(
        self, connection, sender, path, interface, signal_name, parameters
    ):
        try:
            if isinstance(parameters, GLib.Variant):
                params = parameters.unpack()
            else:
                params = parameters

            shortcut_id = params[1]

            # Simple debouncing: ignore duplicate signals within 100ms
            import time

            now = time.time()
            if (
                shortcut_id == self._last_event_id
                and signal_name == self._last_event_name
                and (now - self._last_event_time) < 0.1
            ):
                return
            self._last_event_id = shortcut_id
            self._last_event_name = signal_name
            self._last_event_time = now

            if signal_name == "Activated":
                if self.on_pressed:
                    self.on_pressed(shortcut_id)
            elif signal_name == "Deactivated":
                if self.on_released:
                    self.on_released(shortcut_id)
        except Exception as e:
            logger.debug(f"Portal: Error handling signal {signal_name}: {e}")

    def stop(self) -> None:
        if self.loop:
            self.loop.quit()
        if self.dbus_thread:
            self.dbus_thread.join(timeout=1.0)
        logger.info("Wayland Portal Input Adapter stopped.")
