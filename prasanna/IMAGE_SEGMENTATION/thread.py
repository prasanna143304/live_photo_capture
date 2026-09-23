from pixellib.tune_bg import alter_bg
import time
from os import listdir
from os.path import isfile, join
import os, sys
import json
import tensorflow as tf
from datetime import datetime 


thread = sys.argv[1]
currFolder = os.getcwd()
config_file = os.path.join(currFolder, "xbiz_config.json")
config =  json.loads(os.environ.get("IMAGE_SEGMENTATION_CONFIG", open(config_file, "r", encoding="utf-8").read()))
model_path = config['PASCALVOC_MODEL_PATH']
bg_path = config['BG_PATH']
input_dir = config['INPUT_JSON_PATH'] + "_" + str(thread)
template_dir = ""
sess = tf.compat.v1.Session()
change_bg = alter_bg(model_type="pb")
change_bg.load_pascalvoc_model(model_path)

def create_folders():
    if template_dir and not os.path.exists(template_dir):
        os.makedirs(template_dir)

def filter_files(files):
    # print(f" filterfiles start {datetime.now()}")
    new_files = []
    for file in files:
        if file.endswith(".json"):
            new_files.append(file)
    # print(f" filterfiles end {datetime.now()}")
    return new_files

def delete_file(json_file_path):
    print(f" deletefiles start {datetime.now()}")
    try:
        os.remove(json_file_path)
    except:
        pass
    print(f" deletefiles end {datetime.now()}")

def mainDetectionProcess(image_folder):
        print(f" maindetectionprocess start {datetime.now()}")
        files = [f for f in listdir(image_folder) if isfile(join(image_folder, f))]
        print("**************")
        print(files)
        print("*****************")
        print(f'len {len(files)}')
        for file in files:
            start_time = time.time()
            file_path = os.path.join(image_folder,file)
            change_bg.change_bg_img(file_path, bg_path, output_image_name=file_path, detect="person")
            print("--- %s seconds ---" % (time.time() - start_time))
        print(f"maindetectionprocess end {datetime.now()}")


# def mainProcess(json_path):
#     print(f" mainprocess start {datetime.now()}")
#     global template_dir
#     input_json = json.loads(open(json_path, "r", encoding="utf-8-sig").read())
#     if all(i in input_json for i in ['OUTPUT_TEMPLATE_PATH']):
#         template_dir = input_json['OUTPUT_TEMPLATE_PATH']
#         os.makedirs(template_dir, exist_ok=True)
#         mainDetectionProcess(input_json["OUTPUT_TEMPLATE_PATH"])
#         open(f"{input_json['OUTPUT_JSON_PATH']}{input_json['TXNID']}_IMAGE_SEGMENTATION.json", "w", encoding="utf-8").write(json.dumps({"STATUS": "SUCCESS"}, indent=4))
#     print(f"mainprocess end {datetime.now()}")


def mainProcess(json_path):
    print(f" mainprocess start {datetime.now()}")
    global template_dir
    input_json = json.loads(open(json_path, "r", encoding="utf-8-sig").read())
    if all(i in input_json for i in ['OUTPUT_TEMPLATE_PATH']):
        template_dir = input_json['OUTPUT_TEMPLATE_PATH']
        os.makedirs(template_dir, exist_ok=True)
        mainDetectionProcess(input_json["OUTPUT_TEMPLATE_PATH"])
        if 'TXNID' in input_json:
            open(f"{input_json['OUTPUT_JSON_PATH']}{input_json['TXNID']}_IMAGE_SEGMENTATION.json", "w", encoding="utf-8").write(json.dumps({"STATUS": "SUCCESS"}, indent=4))
        else:
            open(f"{input_json['OUTPUT_JSON_PATH']}{input_json['TOKEN']}_IMAGE_SEGMENTATION.json", "w", encoding="utf-8").write(json.dumps({"STATUS": "SUCCESS"}, indent=4))
    print(f"mainprocess end {datetime.now()}")

def main_process_loop():
    # print(f" len of dir {len(listdir(input_dir))}")
    while True:
        create_folders()
        files = [f for f in listdir(input_dir) if isfile(join(input_dir, f))] if os.path.exists(input_dir) else []
        files = filter_files(files)
        # print(f"files len {len(files)}")
        if len(files) > 0:
            for file in files:
                start_time = time.time()
                mainProcess(join(input_dir, file))
                time.sleep(0.1)
                delete_file(join(input_dir, file))
                print("*--- %s seconds ---*" % (time.time() - start_time))
        else:
            time.sleep(0.5)


if __name__ == '__main__':
    main_process_loop()