# Start the Vision-RCP Relay Server
$env:RELAY_ACCESS_TOKEN = "VISION_DEV_TOKEN_CHANGE_ME"
& "C:\Users\User\OneDrive\Desktop\projects\Vision-RCP\daemon\.venv\Scripts\python.exe" server.py > relay.log 2>&1
