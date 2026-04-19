import time
import sys

def main():
    print("Noisy Logger Started. Frequency: 10Hz (100ms)")
    print("Press Ctrl+C to stop.")
    
    count = 0
    try:
        while True:
            # Output a timestamped counter
            print(f"[{time.strftime('%H:%M:%S')}] Pulse #{count:04d} - The bridge is alive.")
            sys.stdout.flush() # Ensure it's not buffered
            count += 1
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nLogger stopped.")

if __name__ == "__main__":
    main()
