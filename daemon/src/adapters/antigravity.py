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
        self.seen_texts: set[str] = set()
        self.emitted_hashes: List[str] = [] # Stage 15: Store last 20 message hashes
        self.last_user_query = "" # Stage 16: For echo scrubbing
        self.is_bootstrapped = False
        
        # Noise filter patterns
        self.noise_patterns = [
            re.compile(r"Thought for \d+ s", re.I),
            re.compile(r"Ask anything", re.I),
            re.compile(r"Mention @", re.I),
            re.compile(r"for workflows", re.I),
            re.compile(r"Using \d+ files", re.I),
            re.compile(r"Search the web", re.I),
            re.compile(r"^\.+$"), # Ellipses
            re.compile(r"^Running", re.I),
            re.compile(r"Summarizing Latest", re.I),
            re.compile(r"am now focusing", re.I),
            re.compile(r"completed that stage", re.I),
            re.compile(r"primary task is", re.I),
            re.compile(r"\[ARTIFACT:.*\]", re.I),
            re.compile(r"Path: file:///.*", re.I),
            re.compile(r"\[[x /]\] (Implement|Locate|Update|Verify|Final).*", re.I),
            re.compile(r"Analyzed .*#.*", re.I),
            re.compile(r"Generating .*", re.I),
            re.compile(r"Successfully (updated|modified|fixed).*", re.I),
            re.compile(r"^(Assessing|Evaluating|Analyzing|Planning|Thinking|Considering)", re.I),
            re.compile(r"context of the recent", re.I),
            re.compile(r"suggests a fresh", re.I),
            re.compile(r"strategizing (how to )?fulfill", re.I),
            re.compile(r"I'm currently focused on", re.I),
            re.compile(r"leverage my tools", re.I),
            re.compile(r"figure out how to make", re.I),
            re.compile(r"Found \d+ folders?", re.I),
            re.compile(r"located .+ (in )?C:\\", re.I),
            re.compile(r"request (is )?simple", re.I),
            re.compile(r"complex code is needed", re.I),
            re.compile(r"listing contents, nothing more", re.I),
            re.compile(r"Generating Deduplication", re.I),
            re.compile(r"Mobile Resilience", re.I),
            re.compile(r"Short-Circuit Link", re.I),
            re.compile(r"^(Generating|Analyzing|Starting|Connecting|Stopping|Retrying|Searching|Found|Success|Completed).{1,5}$", re.I),
            re.compile(r"^(Acknowledging|Processing|Observing|I'm processing|Reconciling|Observed|However, I've).*", re.I),
            re.compile(r"^(metadata|keyboardinterrupt|manually terminated|apparent interruption).*", re.I),
            # Stage 22: Enhanced Meta-Commentary Purge
            re.compile(r"Acknowledge and Contextualize", re.I),
            re.compile(r"see the user's greeting", re.I),
            re.compile(r"priority is to acknowledge", re.I),
            re.compile(r"follow global rule", re.I),
            re.compile(r"asking \d+-\d+ mandatory questions", re.I)
        ]

        # Bootstrap patterns (Redirect to terminal, not chat)
        self.bootstrap_patterns = [
            "Searching for Antigravity window...",
            "[WATCHDOG]",
            "[DISCOVERY]",
            "Success: Connected to",
            "Scraper bootstrapped with"
        ]

        # Vibe Buffering State
        self.emit_buffer: List[str] = []
        self.last_fragment_time = 0.0
        self.last_emitted_text: Optional[str] = None
        self.flush_delay = 2.0 # Increased further to ensure full sentence capture
        self.last_send_time = 0.0 # Throttling for typing-echo
        self.is_thinking = False
        self.thinking_messages = []
        
        # --- Sentinel Agent State ---
        self.sentinel_enabled = True
        self.risky_patterns = [
            re.compile(r"\brm\b", re.I),
            re.compile(r"\bdel\b", re.I),
            re.compile(r"\berase\b", re.I),
            re.compile(r"\bformat\b", re.I),
            re.compile(r"\bmkfs\b", re.I),
            re.compile(r"\bfdisk\b", re.I),
            re.compile(r"rd\s+/s", re.I),
            re.compile(r"powershell\s+.*Remove-Item", re.I),
            re.compile(r"system32", re.I)
        ]
        self.last_sentinel_action_time = 0.0

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
            await self.emit_diagnostic(f"Success: Connected to '{window_text}'. Link active.")
            
            # Auto-focus to ensure link is active
            try:
                self.window.set_focus()
                self.window.set_foreground()
            except:
                pass

            # Initial snapshot for "Capture from now forward"
            await self._snapshot_current_text()
            
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
        await self.emit_diagnostic("Searching for Antigravity window...")
        
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
                            await self.emit_diagnostic(f"[WATCHDOG] Found app! Connecting ({self.retry_count}/{self.max_retries})...")
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
                        await self.emit_diagnostic(f"[DISCOVERY] Still waiting for Antigravity. Currently open: {', '.join(top_apps)}")
                        await asyncio.sleep(5)
                        continue

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog glitch: {e}")
                await asyncio.sleep(5)

    async def _snapshot_current_text(self) -> None:
        """Capture all current text elements to mark them as 'seen'."""
        if not self.window:
            return
        
        try:
            texts = await asyncio.to_thread(self.window.descendants, control_type="Text")
            for t in texts:
                content = t.window_text().strip()
                if content:
                    self.seen_texts.add(content)
            self.is_bootstrapped = True
            logger.info(f"Scraper bootstrapped with {len(self.seen_texts)} existing text segments.")
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")

    def _should_filter(self, text: str) -> bool:
        """Check if a text segment is UI noise or already seen."""
        if not text or len(text) < 2:
            return True
            
        # Only filter exact matches if they are tool-like noise or extremely short
        if text in self.seen_texts and len(text) < 50:
            return True
            
        # Hard filter for bootstrap logs (redirected to terminal)
        for pattern in self.bootstrap_patterns:
            if pattern in text:
                logger.info(f"REDIRECT_TO_TERM: {text}")
                return True

        for pattern in self.noise_patterns:
            if pattern.search(text):
                return True
                
        return False

    def _join_fragments_semantically(self, buffer: list) -> str:
        """Joins text fragments while preserving list structures and paragraphs (Stage 10/11)."""
        if not buffer:
            return ""
            
        processed_lines = []
        pending_bullet = None
        
        for frag in buffer:
            try:
                # Stage 22: Smart Line Splitting
                # If a fragment contains multiple lines, we still treat them as related
                # but we strip leading/trailing whitespace carefully.
                lines = str(frag).split("\n")
                for line in lines:
                    cleaned = line.strip()
                    if not cleaned:
                        continue
                    
                    # Bullet Glue Logic: If this fragment IS just a bullet, hold it
                    markers = ("*", "-", "•", "—", "▸", "▹", "▪", "▫", "·", "»", "✅", "❌", "!", "?")
                    if cleaned in markers and len(cleaned) == 1:
                        pending_bullet = cleaned
                        continue
                    
                    if pending_bullet:
                        cleaned = f"{pending_bullet} {cleaned}"
                        pending_bullet = None
                        
                    processed_lines.append(cleaned)
            except:
                continue
        
        if not processed_lines:
            return ""

        blocks = []
        current_block = []
        last_item_type = None # "list", "header", or "text"

        for line in processed_lines:
            # 1. Determine Item Type
            is_numbered = len(line) > 2 and line[0].isdigit() and (line[1] == "." or line[1] == ")")
            markers_pattern = ("*", "-", "•", "—", "▸", "▹", "▪", "▫", "·", "»", "✅", "❌", "!", "?")
            is_list = any(line.startswith(m) for m in markers_pattern) or is_numbered
            
            # Header Strictness
            is_header = not is_list and line.endswith(":") and len(line) < 60 and len(line.split()) > 1
            current_type = "list" if is_list else ("header" if is_header else "text")

            # 2. Handle Block Transitions and Joining
            if last_item_type is not None and current_type != last_item_type:
                # Flush the previous block
                if last_item_type == "text":
                    blocks.append(" ".join(current_block)) # JOIN TEXT WITH SPACES
                else:
                    # ENSURE BULLETS HAVE SPACE FOR MARKDOWN
                    processed_block = []
                    for b in current_block:
                        if b and b[0] in markers_pattern and (len(b) == 1 or b[1] != ' '):
                            processed_block.append(f"{b[0]} {b[1:].strip()}")
                        else:
                            processed_block.append(b)
                    blocks.append("\n".join(processed_block)) # KEEP LISTS/HEADERS VERTICAL
                current_block = []

            # 3. Add to Current Block
            current_block.append(line)
            last_item_type = current_type

        # Flush final block
        if current_block:
            if last_item_type == "text":
                blocks.append(" ".join(current_block))
            else:
                processed_block = []
                markers_pattern = ("*", "-", "•", "—", "▸", "▹", "▪", "▫", "·", "»", "✅", "❌", "!", "?")
                for b in current_block:
                    if b and b[0] in markers_pattern and (len(b) == 1 or b[1] != ' '):
                        processed_block.append(f"{b[0]} {b[1:].strip()}")
                    else:
                        processed_block.append(b)
                blocks.append("\n".join(processed_block))

        # 4. Join blocks with appropriate spacing
        # Double newlines between different types of content
        final_text = "\n\n".join(blocks).strip()
        
        # Stage 17/22: Anchor Scrubbing & Response Focusing
        ANCHOR_PHRASES = [
            "I have successfully accessed the", 
            "I have successfully",
            "Sure, here is the", 
            "Here is the list", 
            "The contents of the", 
            "Based on my analysis", 
            "I've found the following",
            "This session focused on"
        ]
        
        lower_text = final_text.lower()
        earliest_anchor_pos = -1
        
        for anchor in ANCHOR_PHRASES:
            pos = lower_text.find(anchor.lower())
            if pos != -1:
                if earliest_anchor_pos == -1 or pos < earliest_anchor_pos:
                    earliest_anchor_pos = pos
        
        if earliest_anchor_pos != -1 and earliest_anchor_pos < len(final_text) / 2:
            final_text = final_text[earliest_anchor_pos:].strip()

        # Final Formatting: If text is still suspiciously fragmented, verify joining
        # (This handles the case where every word was a separate 'text' block)
        if last_item_type == "text" and "\n" in final_text and final_text.count("\n") > final_text.count(". "):
             # Likely a false-positive for verticality in a continuous paragraph
             final_text = final_text.replace("\n", " ").replace("  ", " ")

        return final_text

    def _get_message_count(self) -> int:
        """DEPRECATED: Using text diffing instead."""
        return len(self.seen_texts)

    def _get_latest_message_text(self) -> str:
        """Universal Vacuum: Captures all text elements by alignment, with semantic deduplication."""
        if not self.window:
            return ""
        try:
            # 1. Capture EVERYTHING that has text
            items = self.window.descendants()
            text_bearing = []
            for item in items:
                try:
                    txt = item.window_text().strip()
                    # Filter out tiny artifacts, UI buttons, and "Thought for" noise
                    if txt and len(txt) > 1:
                        if any(noise in txt for noise in ["Copy", "Retry", "Undo", "Thought for", "Analysing", "Evaluating", "Thinking", "Processing"]):
                            continue
                        text_bearing.append(item)
                except: continue

            if not text_bearing:
                return ""
            
            # 2. Identify and Cluster AI Fragments (Absolute Alignment)
            # AI messages are ALWAYS on the left (usually < 450px)
            # User messages are ALWAYS on the right (usually > 500px)
            message_cluster = []
            
            for item in text_bearing:
                rect = item.rectangle()
                # 100px to 450px is the "AI Zone" (handles most resolutions)
                if 50 < rect.left < 450:
                    message_cluster.append(item)
            
            if not message_cluster:
                # Fallback: Capture everything if the UI is very compact
                message_cluster = [it for it in text_bearing if it.rectangle().left < 400]
            
            # 3. Sort by screen position (Top-to-Bottom)
            message_cluster.sort(key=lambda x: x.rectangle().top)
            
            # 4. Semantic Deduplication (Remove fragments contained within larger fragments)
            raw_fragments = [p.window_text().strip() for p in message_cluster]
            final_fragments = []
            
            for i, frag in enumerate(raw_fragments):
                # Only add if this fragment isn't already a part of a larger, surrounding fragment
                is_subset = False
                for j, other in enumerate(raw_fragments):
                    if i != j and frag in other and len(other) > len(frag):
                        is_subset = True
                        break
                
                if not is_subset and frag not in final_fragments:
                    final_fragments.append(frag)
            
            return "\n".join(final_fragments)
        except Exception as e:
            logger.debug(f"Stage 21 Universal Vacuum failed: {e}")
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
                await self.emit_diagnostic("Warning: Exact chat input not found. Attempting global keys...")
                self.window.set_focus()
                await asyncio.sleep(0.2)
                self.window.type_keys(message + "{ENTER}", with_spaces=True)
                return
            
            # 2. Focus and Type
            input_box.set_focus()
            await asyncio.sleep(0.5) # Allow focus animation
            input_box.type_keys(message + "{ENTER}", with_spaces=True, set_foreground=True)
            
            # Proactively filter the input to avoid an echo bubble in the dashboard
            self.seen_texts.add(message)
            self.last_user_query = message # Stage 16: Save for scrubbing
            import hashlib
            msg_hash = hashlib.sha256(message.strip().encode()).hexdigest()
            self.emitted_hashes.append(msg_hash)
            if len(self.emitted_hashes) > 20: self.emitted_hashes.pop(0)
            
            self.last_emitted_text = message
            self.last_send_time = time.time() # Start the ignore-echo period

            # Reset thinking state for the new turn
            self.is_thinking = False
            
        except Exception as e:
            logger.error(f"Failed to send message via UI: {e}")
            await self.emit_message(f"Send Error: {e}")

    async def stream_output(self) -> None:
        """Background loop with intelligent paragraph merging and vibe status."""
        import random
        
        while self.is_running:
            try:
                if not self.window or not self.is_bootstrapped:
                    await asyncio.sleep(1)
                    continue

                # Stage 4: Ignore period after sending to prevent typing-echo
                if time.time() - self.last_send_time < 0.8:
                    await asyncio.sleep(self.polling_interval)
                    continue

                # Stage 21 Universal Vacuum: Captures text by alignment (More robust than ListItem)
                # This ensures we get both thinking segments AND the final response even if they are in different containers.
                vacuumed_text = await asyncio.to_thread(self._get_latest_message_text)
                
                # Periodic Diagnostic Pulse (Every 10 polls)
                if self.monitor_cycle % 10 == 0 and vacuumed_text:
                    await self.emit_diagnostic(f"[SCRAPER] Memory Check: {len(vacuumed_text)} chars in buffer. Peek: '{vacuumed_text[:50]}...'")
                
                new_fragments = []
                
                if vacuumed_text:
                    # Filter the entire vacuumed block
                    # Only treat as 'new' if it's not exactly what we last emitted
                    if vacuumed_text != self.last_emitted_text:
                         # Filter lines individually
                         lines = vacuumed_text.split("\n")
                         for line in lines:
                             if not self._should_filter(line.strip()):
                                 new_fragments.append(line.strip())

                # Stage 5 Fallback: If no ListItems (bubbles) found, perform a 'Safe Zone' scan
                # This ensures we don't miss text if the agent uses non-standard containers.
                if not new_fragments:
                    try:
                        window_rect = self.window.rectangle()
                        window_height = window_rect.height()
                        safety_threshold = window_rect.top + (window_height * 0.75) # Upper 75% focus

                        all_texts = await asyncio.to_thread(self.window.descendants, control_type="Text")
                        for t in all_texts:
                            rect = t.rectangle()
                            content = t.window_text().strip()
                            
                            # Skip if in the 'Input Safety Zone' (bottom 25% of window)
                            # Alignment logic: AI text is usually left-aligned but with a margin.
                            # We accept everything above 100px to handle small resolutions.
                            if rect.left > 100:
                                if rect.top > safety_threshold:
                                    continue
                            
                            if content and len(content) > 1 and not self._should_filter(content):
                                new_fragments.append(content)
                                self.seen_texts.add(content)
                    except:
                        pass

                # Supplemental Thinking Check (still useful for status)
                # We do a targeted check for '...' text that might be global
                all_texts = await asyncio.to_thread(self.window.descendants, control_type="Text")
                found_thinking_indicator = any(t.window_text().strip() == "..." for t in all_texts[:50])

                # 3. Handle Fragment Buffering
                if new_fragments:
                    self.emit_buffer.extend(new_fragments)
                    self.last_fragment_time = time.time()
                    self.is_thinking = False # Content arrived!

                # 4. Flush Buffer when silence detected
                if self.emit_buffer and (time.time() - self.last_fragment_time > self.flush_delay):
                    # Snapshot and Clear to prevent race conditions
                    snapshot = list(self.emit_buffer)
                    self.emit_buffer = []
                    
                    try:
                        full_text = self._join_fragments_semantically(snapshot)
                        
                        if full_text:
                            # Diagnostic: Mirror to stdout so user can see it if dashboard glitches
                            logger.info(f"BRIDGE_FINAL_RESPONSE: {full_text[:100]}...")
                            await self.emit_diagnostic(f"[BRIDGE] Flushed response ({len(snapshot)} frags).")
                            
                            # Hash-based deduplication guard (Stage 15)
                            import hashlib
                            clean_text = full_text.strip()
                            text_hash = hashlib.sha256(clean_text.encode()).hexdigest()
                            
                            is_duplicate = text_hash in self.emitted_hashes
                            
                            # Subset Guard: If this new text contains the previous emitted text 
                            # as a prefix, it's just a more complete capture of the same message.
                            is_subset = False
                            if self.last_emitted_text and len(clean_text) > len(self.last_emitted_text):
                                if clean_text.startswith(self.last_emitted_text):
                                    is_subset = True
                                    logger.debug(f"Subset detected: ignoring partial overlap.")
                                    # If the 'subset' has grown at all, we check if it's significant growth
                                    if len(clean_text) > len(self.last_emitted_text) + 1:
                                        is_subset = False

                            if full_text and not is_duplicate and not is_subset and full_text != self.last_emitted_text:
                                # Final non-destructive scrub for internal monologue
                                meta_markers = ["Processing", "Thinking", "I'm processing"] 
                                lines = full_text.split("\n")
                                final_lines = []
                                for line in lines:
                                    trimmed = line.strip()
                                    if not trimmed: continue

                                    # 1. Always keep greetings or plan headers
                                    if trimmed.lower().startswith(("hello", "hi ", "hey ", "how can i help")):
                                        final_lines.append(line)
                                        continue

                                    # 2. Check for meta markers
                                    found_meta = False
                                    for m in meta_markers:
                                        if trimmed.lower().startswith(m.lower()):
                                            # If line starts with a thought but contains more content, strip just the thought
                                            for separator in [". ", ": ", "! "]:
                                                if separator in trimmed:
                                                    final_lines.append(trimmed.split(separator, 1)[1].strip())
                                                    found_meta = True
                                                    break
                                            if found_meta: break
                                            # If it's just the header line, skip it entirely
                                            found_meta = True
                                            break
                                    
                                    # 3. If no meta found, it's actual content
                                    if not found_meta:
                                        final_lines.append(line)
                                
                                content = "\n".join(final_lines).strip()
                                
                                if content:
                                    await self.emit_message(content)
                                    self.last_emitted_text = full_text
                                    self.emitted_hashes.append(text_hash)
                                    if len(self.emitted_hashes) > 20: self.emitted_hashes.pop(0)
                    except Exception as e:
                        await self.emit_diagnostic(f"[BRIDGE] Join error: {e}")
                        logger.error(f"Semantic join failed: {e}")
                
                # Stage 23: Sentinel Agent Scan (Auto-Approval)
                if self.sentinel_enabled and time.time() - self.last_sentinel_action_time > 3.0:
                    await self._run_sentinel_check()
                
                await asyncio.sleep(self.polling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Monitoring glitch: {e}")
                await asyncio.sleep(self.polling_interval)

    async def _run_sentinel_check(self) -> None:
        """Searches for 'Run command?' prompts and applies guardrails."""
        if not self.window:
            return

        try:
            # 1. Look for the 'Run command?' trigger
            trigger = self.window.child_window(title="Run command?", control_type="Text")
            if not await asyncio.to_thread(trigger.exists, timeout=0.1):
                return

            # 2. Extract the command text (usually in a sibling or nearby group)
            # We look for the first 'Text' or 'Edit' element that looks like a command block
            descendants = await asyncio.to_thread(self.window.descendants)
            trigger_idx = -1
            for i, d in enumerate(descendants):
                if d.window_text() == "Run command?":
                    trigger_idx = i
                    break
            
            if trigger_idx == -1:
                return

            pending_command = ""
            # Search forward from the trigger to find the command block
            for i in range(trigger_idx + 1, min(trigger_idx + 10, len(descendants))):
                text = descendants[i].window_text().strip()
                if text and len(text) > 5 and not any(btn in text for btn in ["Allow", "Deny", "Run command?"]):
                    pending_command = text
                    break

            if not pending_command:
                return

            # 3. Apply Guardrails
            is_risky = any(p.search(pending_command) for p in self.risky_patterns)
            
            if is_risky:
                await self.emit_diagnostic(f"🛡️ [SENTINEL] GUARDRAIL TRIGGERED: Risky command detected - '{pending_command[:50]}...'")
                await self.emit_message(f"⚠️ **Sentinel Guardrail:** A potentially destructive command was blocked for your review: `{pending_command}`")
                self.last_sentinel_action_time = time.time() # Cooldown to prevent spam
                return

            # 4. Auto-Approve (Safe)
            # Only log auto-approvals to terminal/diagnostic, not the main chat
            await self.emit_diagnostic(f"✅ [SENTINEL] Auto-approving safe command: '{pending_command[:50]}...'")
            allow_btn = self.window.child_window(title="Allow", control_type="Button")
            
            if await asyncio.to_thread(allow_btn.exists, timeout=0.5):
                await asyncio.to_thread(allow_btn.click)
                self.last_sentinel_action_time = time.time()
            else:
                # Try finding by text if button title is different
                btns = await asyncio.to_thread(self.window.descendants, control_type="Button")
                for b in btns:
                    if "Allow" in b.window_text():
                        await asyncio.to_thread(b.click)
                        self.last_sentinel_action_time = time.time()
                        break
        except Exception as e:
            logger.debug(f"Sentinel check failed: {e}")

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
