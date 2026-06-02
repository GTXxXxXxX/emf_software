from watchdog.events import FileSystemEventHandler
import time

class CustomHandler(FileSystemEventHandler):
    def __init__(self, path_queue):
        super().__init__()
        self.path_queue = path_queue
        self.last_processed = {}  # Stores {path: timestamp}
        self.cooldown_seconds = 1.0  # Ignore duplicates within 1 second

    def on_modified(self, event):
        if event.is_directory:
            return

        current_path = event.src_path
        now = time.time()

        # Check if we saw this file recently
        if current_path in self.last_processed:
            elapsed = now - self.last_processed[current_path]
            if elapsed < self.cooldown_seconds:
                return  # Skip duplicate event

        self.last_processed[current_path] = now

        print(f"Modified: {event.src_path}")
        self.path_queue.put(event.src_path)



