import re

# The logic from antigravity.py
noise_patterns = [
    re.compile(r"request (is )?simple", re.I),
    re.compile(r"complex code is needed", re.I),
    re.compile(r"listing contents, nothing more", re.I),
    re.compile(r"Generating Deduplication", re.I),
    re.compile(r"Mobile Resilience", re.I),
    re.compile(r"Short-Circuit Link", re.I),
    re.compile(r"^(Generating|Analyzing|Starting|Connecting|Stopping|Retrying|Searching|Found|Success|Completed).{1,5}$", re.I),
    re.compile(r"^(Acknowledging|Processing|Observing|I'm processing|Reconciling|Observed|However, I've).*", re.I),
    re.compile(r"^(metadata|keyboardinterrupt|manually terminated|apparent interruption).*", re.I),
]

def should_filter(content):
    if not content: return True
    for pattern in noise_patterns:
        if pattern.search(content):
            return True
    return False

# Test cases from the user's screenshots
test_cases = [
    "Acknowledging User's Progress",
    "I'm processing the user's positive feedback, noting their appreciation for recent accomplishments.",
    "However, I've observed a KeyboardInterrupt in the metadata",
    "apparent interruption.",
    "Hello co-partner! How can I help?", # SHOULD NOT FILTER
    "1. Bullet one", # SHOULD NOT FILTER
]

for tc in test_cases:
    filtered = should_filter(tc)
    print(f"[{'FILTERED' if filtered else 'PASSED'}] {tc}")
