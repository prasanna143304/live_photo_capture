import json, sys, shutil
import cv2
import numpy as np
import os
import time
from os import listdir
from os.path import isfile, join


thread = sys.argv[1]
currFolder = os.getcwd()
config_file = os.path.join(currFolder, "xbiz_config.json")
config = json.loads(os.environ.get("SIGN_DETECTION_CONFIG", open(config_file, "r", encoding="utf-8").read()))
input_dir = config['INPUT_JSON_PATH'] + "_" + str(thread)

def crop_image(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Unable to open the image file")
        height, width, _ = img.shape
        if width > 230 and height > 230:
            cropped_height = int(height * 0.5)
            cropped_img = img[0:cropped_height, 0:width]
            return cropped_img
        else:
            return img
    except Exception as e:
        return None

def convert_black_signature_to_blue(image):
    input_image = image.copy()
    gray_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
    _, thresholded = cv2.threshold(gray_image, 10, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blue_color = (255, 0, 0)
    signature_mask = np.zeros_like(input_image)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(signature_mask, (x, y), (x + w, y + h), blue_color, -1)
    result_image = cv2.addWeighted(input_image, 1, signature_mask, 1, 0)
    return result_image

def is_white_background(image_path, threshold=100):
    image = cv2.imread(image_path)
    grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    average_intensity = cv2.mean(grayscale_image)[0]
    if average_intensity > threshold:
        return True
    else:
        return False

def mainProcess(json_input):
    print("json_input", json_input)
    output_res = {}
    image_path = json_input["INPUT_IMAGE"]
    output_image_path = json_input["OUTPUT_IMAGE"]
    output_json_path = json_input["OUTPUT_JSON"]
    if "TXNID" in json_input:
        txn_id = json_input["TXNID"]
        output_image_path = join(output_image_path, txn_id + ".JPG")
        output_json_path = join(output_json_path, txn_id + ".json")  
    else:
        token = json_input["TOKEN"]
        output_image_path = join(output_image_path, token + ".JPG")
        output_json_path = join(output_json_path, token + ".json")  
    # txn_id = json_input["TXNID"]
    # output_image_path = json_input["OUTPUT_IMAGE"]
    # output_image_path = join(output_image_path, txn_id + ".JPG")
    # output_json_path = json_input["OUTPUT_JSON"]
    # output_json_path = join(output_json_path, txn_id + ".json")

    cropped_image = crop_image(image_path)
    print(f"cropped image", cropped_image)
    if cropped_image is not None:
        result_file = output_image_path
        image = cv2.imread(image_path)
        result = image.copy()
        blurred_image = cv2.GaussianBlur(image, (5, 5), 0)
        hsv_image = cv2.cvtColor(blurred_image, cv2.COLOR_BGR2HSV)
        lower = np.array([110, 50, 50])
        upper = np.array([145, 255, 255])
        mask2 = cv2.inRange(hsv_image, lower, upper)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opening = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel, iterations=1)
        close = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=2)
        cnts = cv2.findContours(close, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        try:
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            cnts = np.concatenate(cnts)
            x, y, w, h = cv2.boundingRect(cnts)
            roi_image = result[y - 70:y + h * 2, x - 70:x + w * 4]
            cv2.imwrite(result_file, roi_image)
            white_background = is_white_background(result_file)
            if white_background:
                output_res["SIGNATURE_FOUND"] = True
            else:
                output_res["SIGNATURE_FOUND"] = False
        except:
            try:
                new_image = convert_black_signature_to_blue(cropped_image)
                image_hsv = cv2.cvtColor(new_image, cv2.COLOR_BGR2HSV)
                lower = np.array([110, 50, 50])
                upper = np.array([145, 255, 255])
                mask2 = cv2.inRange(image_hsv, lower, upper)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                opening = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel, iterations=1)
                close = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=2)
                cnts = cv2.findContours(close, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cnts = cnts[0] if len(cnts) == 2 else cnts[1]
                cnts = np.concatenate(cnts)
                x, y, w, h = cv2.boundingRect(cnts)
                cv2.rectangle(result, (x, y), (x + w, y + h), (36, 255, 12), 2)
                roi_image = result[y:y + h, x:x + w]
                cv2.imwrite(result_file, roi_image)
                white_background = is_white_background(result_file)
                if white_background:
                    output_res["SIGNATURE_FOUND"] = True
                else:
                    output_res["SIGNATURE_FOUND"] = False
            except:
                output_res["SIGNATURE_FOUND"] = False
    if "SIGNATURE_FOUND" not in output_res:
        output_res["SIGNATURE_FOUND"] = False
    open(output_json_path, "w", encoding="utf-8").write(json.dumps(output_res, indent=4))
    shutil.copy(image_path, output_image_path)

def filter_files(files):
    new_files = []
    for file in files:
        if file.endswith(".json"):
            new_files.append(file)
    return new_files

def delete_file(json_file_path):
    try:
        os.remove(json_file_path)
    except:
        pass

def main_process_loop():
    while True:
        files = [f for f in listdir(input_dir) if isfile(join(input_dir, f))] if os.path.exists(input_dir) else []
        files = filter_files(files)
        if len(files) > 0:
            for file in files:
                start_time = time.time()
                mainProcess(json.loads(open(join(input_dir, file), "r", encoding="utf-8").read()))
                delete_file(join(input_dir, file))
                print("*--- %s seconds ---*" % (time.time() - start_time))
        else:
            time.sleep(0.5)
    
if __name__ == '__main__':
    main_process_loop()