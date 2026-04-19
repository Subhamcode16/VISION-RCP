import pywinauto
from pywinauto import Desktop
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ui_diagnostic")

def list_antigravity_windows():
    print("\n--- Antigravity Windows Found ---")
    d = Desktop(backend="uia")
    windows = d.windows(title_re=".*Antigravity.*")
    
    if not windows:
        print("No windows matching '.*Antigravity.*' found.")
        return

    for i, w in enumerate(windows):
        title = w.window_text()
        print(f"[{i}] Title: {title}")
        
        # List Edit controls in this window
        try:
            edits = w.descendants(control_type="Edit")
            print(f"    - Found {len(edits)} Edit controls")
            for j, e in enumerate(edits):
                print(f"      ({j}) Name: '{e.window_text()}', ID: {e.element_info.automation_id}")
        except Exception as ex:
            print(f"    - Error listing controls: {ex}")
    print("---------------------------------\n")

if __name__ == "__main__":
    list_antigravity_windows()
