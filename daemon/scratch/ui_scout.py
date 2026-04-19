import pywinauto
from pywinauto import Desktop
import logging
import sys

# Set up logging to avoid cluttering output
logging.basicConfig(level=logging.ERROR)

def scout_antigravity():
    print("\n[VIBE SCOUT] Searching for Antigravity window...")
    try:
        d = Desktop(backend="uia")
        windows = d.windows(title_re=".*Antigravity.*")
        
        if not windows:
            print("[!] No window matching '.*Antigravity.*' found.")
            return

        target = windows[0]
        print(f"[*] Found: {target.window_text()}")
        print("-" * 50)
        
        # 1. Try to find all Text elements
        print("[1] Extracting all TEXT elements:")
        texts = target.descendants(control_type="Text")
        for i, t in enumerate(texts[-15:]): # Last 15 for brevity
            val = t.window_text().strip()
            if val:
                print(f"    [{i}] Text: \"{val}\" (AutoID: {t.element_info.automation_id})")

        # 2. Try to find ListItems (Bubbles)
        print("\n[2] Extracting all LISTITEM elements:")
        items = target.descendants(control_type="ListItem")
        for i, item in enumerate(items[-10:]):
            children = item.descendants(control_type="Text")
            child_text = " | ".join([c.window_text().strip() for c in children if c.window_text()])
            print(f"    [{i}] ListItem Child Text: \"{child_text}\"")

        # 3. Try to find the full tree summary (if requested or small)
        print("\n[3] Tree Summary (Automation IDs):")
        for child in target.descendants()[:20]: # First 20 to avoid giant dump
             print(f"    Type: {child.control_type}, ID: {child.element_info.automation_id}, Title: {child.window_text()[:40]}")

    except Exception as e:
        print(f"[!] Scout Error: {e}")

if __name__ == "__main__":
    scout_antigravity()
