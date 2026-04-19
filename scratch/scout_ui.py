import sys
from pywinauto import Desktop
import logging

def scout_antigravity():
    print("Searching for Antigravity window...")
    try:
        app = Desktop(backend="uia").window(title_re=".*Antigravity.*")
        if not app.exists():
            print("Antigravity window not found!")
            return

        print(f"Found: {app.window_text()}")
        
        # Get all descendants
        print("Scouting UI hierarchy (last 50 elements)...")
        desc = app.descendants()
        
        for i, item in enumerate(desc[-50:]):
            try:
                rect = item.rectangle()
                text = item.window_text().strip()
                c_type = item.control_type()
                print(f"[{i}] Type: {c_type:10} | Rect: {rect} | Text: {text[:50]}")
            except:
                continue
                
    except Exception as e:
        print(f"Scout failed: {e}")

if __name__ == "__main__":
    scout_antigravity()
