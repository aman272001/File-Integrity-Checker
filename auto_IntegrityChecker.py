import hashlib
import os
import json
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASELINE_FILE = "baseline.json"
LOG_FILE = "logs.txt"


def norm(path):
    return os.path.normcase(os.path.abspath(path))


IGNORED = {norm(BASELINE_FILE), norm(LOG_FILE)}


def say(msg):
    print(msg, flush=True)


def generate_file_hash(file_path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def safe_hash(path, retries=5, delay=0.2):
    """Hash a file, retrying briefly if it's still locked by the creating app."""
    for _ in range(retries):
        try:
            return generate_file_hash(path)
        except FileNotFoundError:
            return None          # already renamed or deleted
        except PermissionError:
            time.sleep(delay)    # still being written/locked
    return None


def scan_folder(folder_path):
    hashes = {}
    for root, _, files in os.walk(folder_path):
        for name in files:
            full = norm(os.path.join(root, name))
            if full in IGNORED:
                continue
            h = safe_hash(full)
            if h:
                hashes[full] = h
    return hashes


def save_baseline(data):
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def write_log(event_type, path):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} | {event_type} | {path}\n")


class MonitorHandler(FileSystemEventHandler):

    def on_created(self, event):
        if event.is_directory:
            return
        path = norm(event.src_path)
        if path in IGNORED:
            return
        h = safe_hash(path)
        if h is None:
            return  # renamed/deleted right away; on_moved will cover it
        baseline_dataa[path] = h
        say(f"[+] File Created: {path}")
        write_log("CREATED", path)

    def on_modified(self, event):
        if event.is_directory:
            return
        path = norm(event.src_path)
        if path in IGNORED:
            return
        h = safe_hash(path)
        if h is None:
            return
        if path not in baseline_dataa:
            baseline_dataa[path] = h
            say(f"[+] New File Detected: {path}")
            write_log("CREATED", path)
        elif baseline_dataa[path] != h:
            baseline_dataa[path] = h
            say(f"[!] File Modified: {path}")
            write_log("MODIFIED", path)

    def on_moved(self, event):
        src, dest = norm(event.src_path), norm(event.dest_path)

        if event.is_directory:
            for old in [p for p in baseline_dataa if p.startswith(src + os.sep)]:
                baseline_dataa[dest + old[len(src):]] = baseline_dataa.pop(old)
            say(f"[~] Folder Renamed: {src} -> {dest}")
            write_log("RENAMED", f"{src} -> {dest}")
            return

        if src in baseline_dataa:
            baseline_dataa[dest] = baseline_dataa.pop(src)
        else:
            h = safe_hash(dest)
            if h is None:
                return
            baseline_dataa[dest] = h

        say(f"[~] File Renamed: {src} -> {dest}")
        write_log("RENAMED", f"{src} -> {dest}")

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = norm(event.src_path)
        if path in baseline_dataa:
            del baseline_dataa[path]
            say(f"[-] File Deleted: {path}")
            write_log("DELETED", path)


# main
folder_to_watch = input("Enter Folder Path: ").strip().strip('"')

baseline_dataa = scan_folder(folder_to_watch)
save_baseline(baseline_dataa)

observer = Observer()
observer.schedule(MonitorHandler(), folder_to_watch, recursive=True)
observer.start()
say("Monitoring started... (Ctrl+C to stop)")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()
save_baseline(baseline_dataa)  # persist the final state