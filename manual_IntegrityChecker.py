import hashlib
import os
import json

def generate_file_hash(file_path, algorithm='sha256'):
    hash_object = hashlib.new(algorithm)

    with open(file_path, 'rb') as file:
        while chunk := file.read(4096):
            hash_object.update(chunk)

    return hash_object.hexdigest()

def scanFolder(folder_path, algorithm='sha256'):
    hash_files = {}

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.abspath(os.path.join(root, file)).lower()

            try:
                file_hash = generate_file_hash(full_path, algorithm)
                hash_files[full_path] = file_hash
                print(f"Hashed: {full_path}")

            except Exception as e:
                print(f"Error hashing {full_path}: {e}")

    return hash_files

def baseline(data):
    try:
        with open("baseline.json", "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)
    except Exception as e:
        print("Error saving baseline:", e)


def load_baseline(filename="baseline.json"):
    try:
        with open(filename, "r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        print("File not found")
    return{}

def comparing_baseline(baseline_data, current_data):

    baseline_files = set(baseline_data.keys())
    current_files = set(current_data.keys())

    #Detect new file
    new_file = current_files-baseline_files
    for file in new_file:
        print(f"New File Detected: {file}")

    #delete file
    deleted_file = baseline_files-current_files
    for file in deleted_file:
        print(f"Deleted file Detected: {file}")

    #modify files
    common_files = baseline_files & current_files
    for file in common_files:
        if baseline_data[file] != current_data[file]:
            print(f"File Modified: {file}")


#main
folder_path = input("Enter Folder Path: ")
algo = input("Choose algo: md5/sha1/sha256: ")



print("\nScanning current State....")
current_hash_data = scanFolder(folder_path, algo)

print("\nLoading Baseline....")
baseline_data = load_baseline()

if not baseline_data:
    print("\nNo baseline found. Creating new baseline...")
    baseline(current_hash_data)
else:
    print("\nComparing...\n")
    comparing_baseline(baseline_data, current_hash_data)

baseline(current_hash_data)







