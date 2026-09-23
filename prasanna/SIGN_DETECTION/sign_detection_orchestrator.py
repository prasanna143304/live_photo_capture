import os
import time
from os import listdir
from os.path import isfile, join
import threading
import json
import shutil

INPUT_JSON_PATH = ""
THREAD = ""
curr_dir = os.getcwd()

def init_json():
    global INPUT_JSON_PATH, THREAD
    stream = open("xbiz_config.json", 'r')
    currFolder = os.getcwd()
    config_file = os.path.join(currFolder, "xbiz_config.json")
    dictionary = json.loads(os.environ.get("SIGN_DETECTION_CONFIG", open(config_file, "r", encoding="utf-8").read()))
    INPUT_JSON_PATH = dictionary["INPUT_JSON_PATH"]
    THREAD = dictionary["THREAD"]

def create_folders():
    os.makedirs(os.path.join(curr_dir, INPUT_JSON_PATH), exist_ok=True)
    for i in range(THREAD):
        os.makedirs(os.path.join(curr_dir, INPUT_JSON_PATH + "_" + str(i + 1)), exist_ok=True)

def process(thread):
    try:
        thread_py_path = os.path.join(curr_dir, "thread.py")
        # thread_exe_path = os.path.join(curr_dir, "thread.exe")
        os.system("python \"" + thread_py_path + "\" " + thread)
        # os.system("\"" + thread_exe_path + "\" " + thread)
    except Exception as e:
        print(e)

def start_thread():
    threads = []
    for i in range(int(THREAD)):
        threads.append(threading.Thread(target=process, args=(str(i + 1),)))
    for thread in threads:
        thread.start()

def get_lowest_load_thread():
    loads = []
    for i in range(int(THREAD)):
        loads.append(len([f for f in listdir(join(curr_dir, INPUT_JSON_PATH + "_" + str(i + 1))) if isfile(join(join(curr_dir, INPUT_JSON_PATH + "_" + str(i + 1)), f))]))
    return loads.index(min(loads))

def filter_files(files):
    new_files = []
    for file in files:
        if file.lower().endswith(".json"):
            new_files.append(file)
    return new_files

def start_process():
    while True:
        files = filter_files([f for f in listdir(join(curr_dir, INPUT_JSON_PATH)) if isfile(join(join(curr_dir, INPUT_JSON_PATH), f))])
        if len(files) > 0:
            for file in files:
                try:
                    lowest_load_thread = get_lowest_load_thread()
                    shutil.copy(join(join(curr_dir, INPUT_JSON_PATH), file), join(join(curr_dir, INPUT_JSON_PATH + "_" + str(lowest_load_thread + 1)), file))
                    os.remove(join(join(curr_dir, INPUT_JSON_PATH), file))
                except Exception as e:
                    pass
        else:
            time.sleep(0.5)

init_json()
create_folders()
start_thread()
start_process()