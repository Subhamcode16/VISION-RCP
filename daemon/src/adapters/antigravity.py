"""Antigravity Desktop Automation (RPA) adapter implementation."""

import asyncio
import os
import logging
import time
import ctypes
import re
from ctypes import wintypes
from typing import Dict, Any, Callable, Coroutine, Optional, List
from .base import AgentAdapter
from ..models import LogEntry

# --- C-Level Window Helpers (64-bit Safe) ---
def _get_active_window_titles() -> List[str]:
    """Uses ctypes to instantly list all top-level window titles."""
    titles = []
    
    # Define callback signature for x64/x86 compatibility
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    
    def foreach_window(hwnd, lParam):
        try:
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    if buff.value:
                        titles.append(buff.value)
        except Exception:
            pass # Skip problematic windows
        return True
    
    try:
        proc = WNDENUMPROC(foreach_window)
        ctypes.windll.user32.EnumWindows(proc, 0)
    except Exception as e:
        logging.getLogger("rcp.adapters.antigravity").error(f"EnumWindows failure: {e}")
        
    return titles

def _find_window_fast(pattern: str) -> bool:
    """Check if a window matching the regex exists without loading heavy SDKs."""
    try:
        titles = _get_active_window_titles()
        regex = re.compile(pattern, re.IGNORECASE)
        return any(regex.search(t) for t in titles)
    except Exception:
        return False

_SDK_CACHE = {"initialized": False, "available": False, "pywinauto": None, "Application": None, "Desktop": None}

def _get_sdk():
    """Lazy-load the automation SDK to avoid blocking server startup."""
    global _SDK_CACHE
    if _SDK_CACHE["initialized"]:
        return _SDK_CACHE["available"]

    logger = logging.getLogger("rcp.adapters.antigravity")
    try:
        start_time = time.time()
        logger.info("Initializing Desktop Automation SDK (this may take a moment on first launch)...")
        
        import pywinauto as pw
        from pywinauto import Application, Desktop
        
        _SDK_CACHE["pywinauto"] = pw
        _SDK_CACHE["Application"] = Application
        _SDK_CACHE["Desktop"] = Desktop
        _SDK_CACHE["available"] = True
        
        elapsed = time.time() - start_time
        logger.info(f"Automation SDK initialized in {elapsed:.2f}s")
    except ImportError:
        logger.warning("pywinauto not found. Adapter will run in mock mode.")
        _SDK_CACHE["available"] = False
    except Exception as e:
        logger.error(f"Error during Automation SDK initialization: {e}")
        _SDK_CACHE["available"] = False
    
    _SDK_CACHE["initialized"] = True
    return _SDK_CACHE["available"]

# Replace the top-level SDK_AVAILABLE check
def is_sdk_available():
    return _get_sdk()

logger = logging.getLogger("rcp.adapters.antigravity")

class AntigravityAdapter(AgentAdapter):
    """Adapter for the Antigravity Desktop GUI application using pywinauto."""

    def __init__(self, name: str, emit_callback: Callable[[LogEntry], Coroutine]):
        super().__init__(name, emit_callback)
        self.app: Optional[Any] = None
        self.window: Any = None
        self.monitor_task: Optional[asyncio.Task] = None
        self.watchdog_task: Optional[asyncio.Task] = None
        self.last_message_count = 0
        self.window_title_re = ".*Antigravity.*"
        self.polling_interval = 0.5
        self.retry_count = 0
        self.max_retries = 5
        self._config: Dict[str, Any] = {}

    async def start(self, config: Dict[str, Any]) -> None:
        """Connect to the running Antigravity application (Non-blocking)."""
        self.is_running = True
        self._config = config
        self.window_title_re = config.get("window_title_re", ".*Antigravity.*")
        self.polling_interval = config.get("polling_interval_ms", 500) / 1000.0
        self.retry_count = 0
        
        # Start the connection process and watchdog in the background
        # This returns immediately so the daemon doesn't time out the request
        self.watchdog_task = asyncio.create_task(self._watchdog_loop())

    async def _do_connect(self) -> bool:
        """Connect to the Antigravity window only if it has already been discovered."""
        try:
            # 1. Light check (CTYPES) before we even load the heavy SDK
            if not _find_window_fast(self.window_title_re):
                return False

            # 2. Window confirmed! Now we load the heavy engine (Lazy Load)
            if not is_sdk_available():
                return False

            # 3. Connect via pywinauto
            app_class = _SDK_CACHE["Application"]
            
            def connect_sync():
                return app_class(backend="uia").connect(title_re=self.window_title_re, timeout=3)
            
            self.app = await asyncio.to_thread(connect_sync)
            self.window = self.app.window(title_re=self.window_title_re)
            
            window_text = await asyncio.to_thread(self.window.window_text)
            await self.emit_message(f"Success: Connected to '{window_text}'. Link active.")
            
            self._init_monitoring()
            return True
            
        except Exception as e:
            logger.debug(f"Deep connect failed: {e}")
            return False

    def _init_monitoring(self):
        """Reset state and start the stream task."""
        self.last_message_count = self._get_message_count()
        if not self.monitor_task or self.monitor_task.done():
            self.monitor_task = asyncio.create_task(self.stream_output())

    async def _watchdog_loop(self) -> None:
        """Lightweight watchdog that only escalates to heavy scans when necessary."""
        await self.emit_message("Searching for Antigravity window...")
        
        while self.is_running:
            try:
                # 1. Check health (Use window handle if we have it, else search)
                is_alive = False
                if self.window:
                    try:
                        # Light check first
                        is_alive = await asyncio.to_thread(self.window.exists)
                    except:
                        is_alive = False

                # 2. Reconnection Logic
                if not is_alive:
                    # Light search (Very fast)
                    found_light = await asyncio.to_thread(_find_window_fast, self.window_title_re)
                    
                    if found_light:
                        if self.retry_count < self.max_retries:
                            self.retry_count += 1
                            await self.emit_message(f"[WATCHDOG] Found app! Connecting ({self.retry_count}/{self.max_retries})...")
                            success = await self._do_connect()
                            if success:
                                self.retry_count = 0
                            else:
                                await asyncio.sleep(2)
                                continue
                    else:
                        # Optimization: Skip heavy engine entirely if light search fails
                        # This keeps the dashboard smooth even if the app isn't open
                        titles = await asyncio.to_thread(_get_active_window_titles)
                        top_apps = [t for t in titles if len(t.strip()) > 0][:12]
                        await self.emit_message(f"[DISCOVERY] Still waiting for Antigravity. Currently open: {', '.join(top_apps)}")
                        await asyncio.sleep(5)
                        continue

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog glitch: {e}")
                await asyncio.sleep(5)

    def _get_message_count(self) -> int:
        """Count the number of list items/bubbles in the chat area."""
        if not self.window:
            return 0
        try:
            # We assume messages are stored in a List or similar container
            # This is a heuristic that will be refined by the ui_scout output
            return len(self.window.descendants(control_type="ListItem"))
        except:
            return 0

    def _get_latest_message_text(self) -> str:
        """Extract the text from the most recent chat bubble."""
        if not self.window:
            return ""
        try:
            items = self.window.descendants(control_type="ListItem")
            if not items:
                return ""
            # Get the last item and its text content
            last_item = items[-1]
            return last_item.window_text()
        except:
            return ""

    async def send_message(self, message: str) -> None:
        """Inject the user message into the Antigravity (VS Code Sidebar) chat input."""
        if not self.is_running or not self.window:
            await self.emit_message(f"[STUB ECHO]: {message}")
            return

        try:
            # 1. Target strategy: Try standard 'Message input' first, then common VS Code patterns
            input_box = None
            strategies = [
                {"title": "Message input", "control_type": "Edit"},
                {"title": "Ask anything...", "control_type": "Edit"},
                {"title_re": ".*Chat.*input.*", "control_type": "Edit"},
                {"auto_id": "interactive.input", "control_type": "Edit"}
            ]

            for strategy in strategies:
                try:
                    target = self.window.child_window(**strategy)
                    if target.exists(timeout=1):
                        input_box = target
                        break
                except:
                    continue

            if not input_box:
                # Fallback: Just try to type if the window is focused
                await self.emit_message("Warning: Exact chat input not found. Attempting global keys...")
                self.window.set_focus()
                await asyncio.sleep(0.2)
                self.window.type_keys(message + "{ENTER}", with_spaces=True)
                return

            # 2. Focus and Type
            input_box.set_focus()
            await asyncio.sleep(0.5) # Allow focus animation
            input_box.type_keys(message + "{ENTER}", with_spaces=True, set_foreground=True)
            
            await self.emit_message(f"Sent to Sidebar: {message}")
            
        except Exception as e:
            logger.error(f"Failed to send message via UI: {e}")
            await self.emit_message(f"Send Error: {e}")

    async def stream_output(self) -> None:
        """Background loop to detect and capture new messages from the GUI."""
        while self.is_running:
            try:
                current_count = self._get_message_count()
                
                if current_count > self.last_message_count:
                    # New message detected
                    new_text = self._get_latest_message_text()
                    if new_text:
                        await self.emit_message(new_text)
                    self.last_message_count = current_count
                
                await asyncio.sleep(self.polling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Monitoring glitch: {e}")
                await asyncio.sleep(self.polling_interval)

    async def interrupt(self) -> None:
        """Simulate an interrupt by sending Escape or a stop command if buttons exist."""
        if self.window:
            try:
                self.window.type_keys("{ESC}")
                await self.emit_message("Sent ESC interrupt signal.")
            except:
                pass

    async def stop(self) -> None:
        """Terminate the automation session."""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
        self.window = None
        self.app = None
        await self.emit_message("Desktop automation session stopped.")

    async def send_approval(self, decision: bool) -> None:
        """Search for approval buttons in the UI and click them."""
        if not self.window:
            return
            
        try:
            target_text = "Approve" if decision else "Reject"
            btn = self.window.child_window(title=target_text, control_type="Button")
            btn.click()
            await self.emit_message(f"Clicked UI button: {target_text}")
        except:
            await self.emit_message(f"Could not find '{target_text}' button in UI.")
