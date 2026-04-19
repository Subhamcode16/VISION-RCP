import sys
import os
import asyncio
import time
from pywinauto import Desktop

# Ensure UTF-8 output for icons
sys.stdout.reconfigure(encoding='utf-8')

async def probe():
    print("Searching for Antigravity window...")
    desktop = Desktop(backend="uia")
    windows = desktop.windows(title_re=".*Antigravity.*")
    if not windows:
        print("Window not found.")
        return
    
    win = windows[0]
    print(f"Found: {win.window_text()}")
    
    print("\n--- INSIGHT: Edits (Inputs) ---")
    edits = win.descendants(control_type="Edit")
    for e in edits:
        try:
            print(f"Edit Box Found! Title: '{e.window_text()}' | ID: {e.element_info.automation_id}")
        except:
            pass

    print("\n--- INSIGHT: Chat List Analysis ---")
    items = win.descendants(control_type="ListItem")
    print(f"Found {len(items)} ListItems.")
    for i, item in enumerate(items[-5:]): # Last 5
        try:
            print(f"[{i}] ListItem Text: {item.window_text()[:100]}")
            # Check for specific children
            texts = item.descendants(control_type="Text")
            for t in texts:
                print(f"    - Child Text: {t.window_text()}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(probe())
