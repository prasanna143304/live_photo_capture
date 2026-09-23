from scipy.spatial import distance as dist
from imutils.video import FileVideoStream
from imutils import face_utils
from imutils.video import count_frames
from imutils.video import FPS
import dlib
import cv2
from datetime import datetime
import sys
import os.path
from os import listdir
from os.path import isfile, join
import time
import json
import sys
import torch
# import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from smiledetection import smile_detection

thread = sys.argv[1]
currFolder = os.getcwd()
config_file = os.path.join(currFolder, "xbiz_config.json")
config = json.loads(os.environ.get("BLINK_DETECTION_CONFIG", open(config_file, "r", encoding="utf-8").read()))
ffmpeg = config['ffmpeg_path']
input_dir = config['INPUT_JSON_PATH'] + "_" + str(thread)
output_dir, output_face_dir, template_dir, output_video_path = "", "", "", ""

def eye_aspect_ratio(eye):
    a = dist.euclidean(eye[1], eye[5])
    b = dist.euclidean(eye[2], eye[4])
    c = dist.euclidean(eye[0], eye[3])
    ear = (a + b) / (2.0 * c)
    return ear

def convert_and_trim_bb(image, rect):
    startX = rect.left()
    startY = rect.top()
    endX = rect.right()
    endY = rect.bottom()
    startX = max(0, startX)
    startY = max(0, startY)
    endX = min(endX, image.shape[1])
    endY = min(endY, image.shape[0])
    w = endX - startX
    h = endY - startY
    return startX, startY, w, h

# execution_path = os.getcwd()
# detector = ObjectDetection()
# detector.setModelTypeAsRetinaNet()
# detector.setModelPath(os.path.join(f'{execution_path}/dependencies/' , "retinanet_resnet50_fpn_coco-eeacb38b.pth"))
# detector.loadModel()

# def full_face_detect(frame):
#     detections = detector.detectObjectsFromImage(input_image=frame, minimum_percentage_probability=90, display_percentage_probability=True)
#     print(detections)
#     if len(detections) == 1 and detections[0]['name'] == "person" and detections[0]['percentage_probability'] >= 96:
#         print(detections[0]['percentage_probability'])
#         return True
#     else:
#         return False

model = torch.hub.load('ultralytics/yolov5', 'yolov5x6', pretrained=True)
class_names = ['cell phone', 'laptop']


def object_detection(video_name, total_frames):
    print(datetime.now())
    global model, class_names

    # capturing the input video 
    cap = cv2.VideoCapture(video_name)
    
    start_frame = 0
    end_frame = total_frames
    frame_counter = 0

    # process each frame of the video
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_counter += 10

        if start_frame <= frame_counter < end_frame:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = model(frame_rgb)
            threshold = 0.2  # Set your desired confidence threshold here
            detected_objects = results.xyxy[0][results.xyxy[0][:, 4] >= threshold]
            
            # Check if cell phone, laptop, or TV is present in detected objects    
            detected_classes = [model.names[int(obj[5])] for obj in detected_objects]
            cell_phone_detected = any(class_name in detected_classes for class_name in class_names)

            # Check if person with confidence 0.9 is present in detected objects
            person_detected = any(obj[5] == 0 and obj[4] > 0.9 for obj in detected_objects)

            if cell_phone_detected:
                # print("Cell phone, laptop, TV detected!")
                print(f"FAKE FACE - Cell Phone or Laptop ")
                for obj in detected_objects:
                    if model.names[int(obj[5])] in class_names:
                        class_name = model.names[int(obj[5])]
                        confidence = float(obj[4]) * 100
                        print(f"- {class_name}: {confidence:.5f}%")
                cap.release()
                cv2.destroyAllWindows()
                return False
            elif person_detected and not cell_phone_detected:
                # print("live person detected.")
                print(f"LIVE FACE - {float(torch.tensor(detected_objects[:, 4][0])*100):.5f} %")
            else:
                # print("spoofed face")
                print(f"FAKE FACE - {float(torch.tensor(detected_objects[:, 4][0])*100):.5f} %")
                cap.release()
                cv2.destroyAllWindows()
                return False

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    # output_video.release()
    cv2.destroyAllWindows()
    print(datetime.now())
    return True        

# def process_frames(frame_rgb, cap):
#     # frame_counter += 10

#     # if start_frame <= frame_counter < end_frame:
#     results = model(frame_rgb)
#     threshold = 0.2  # Set your desired confidence threshold here
#     detected_objects = results.xyxy[0][results.xyxy[0][:, 4] >= threshold]
    
#     # Check if cell phone, laptop, or TV is present in detected objects    
#     detected_classes = [model.names[int(obj[5])] for obj in detected_objects]
#     cell_phone_detected = any(class_name in detected_classes for class_name in class_names)

#     # Check if person with confidence 0.9 is present in detected objects
#     person_detected = any(obj[5] == 0 and obj[4] > 0.9 for obj in detected_objects)

#     if cell_phone_detected:
#         # print("Cell phone, laptop, TV detected!")
#         print(f"FAKE FACE - Cell Phone or Laptop ")
#         for obj in detected_objects:
#             if model.names[int(obj[5])] in class_names:
#                 class_name = model.names[int(obj[5])]
#                 confidence = float(obj[4]) * 100
#                 print(f"- {class_name}: {confidence:.5f}%")
#         cap.release()
#         cv2.destroyAllWindows()
#         return False
#     elif person_detected and not cell_phone_detected:
#         # print("live person detected.")
#         print(f"LIVE FACE - {float(torch.tensor(detected_objects[:, 4][0])*100):.5f} %")
#     else:
#         # print("spoofed face")
#         print(f"FAKE FACE - {float(torch.tensor(detected_objects[:, 4][0])*100):.5f} %")
#         cap.release()
#         cv2.destroyAllWindows()
#         return False
        
#     cap.release()
#     # output_video.release()
#     cv2.destroyAllWindows()
#     return True

# def object_detection(video_name, total_frames):

#     global model, class_names

#     # capturing the input video 
#     cap = cv2.VideoCapture(video_name)
    
#     start_frame = 0
#     end_frame = total_frames
#     frame_counter = 0

#     with ThreadPoolExecutor(max_workers=5) as executor:

#         # process each frame of the video
#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             # frame_counter += 10

#             # if start_frame <= frame_counter < end_frame:
#             frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

#             future = executor.submit(process_frames, frame_rgb, cap)

#             if future.result():
#                 return True
#             else:
#                 return False

#                 # if cv2.waitKey(1) & 0xFF == ord('q'):
#                     # break   

def mainDetectionProcess(video_name, txn_no=None):
    print(f"main detectio time start {datetime.now()}")
    try:
        override_count = config['override']
        shape_predictor1 = config['shape_predictor_path']
        max_frame_count = config['max_frame_cnt']
        EYE_AR_CONSEC_FRAMES = config['frame_consec']
        EYE_AR_THRESH = config['eye_thresh']
        # convert to mp4
        input = video_name
        print("input ", input)
        if input.endswith(".webm"):
            filter = "-filter \"minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=15'\""
        else:
            filter = " -c:v libx264 -vf fps=15 -pix_fmt yuv420p "
        fileName = os.path.splitext(os.path.basename(video_name))[0]
        output = fileName + ".mp4"
        print("output ", output)
        os.system(ffmpeg + " -i \"" + input + "\" " + filter + " \"" + os.path.join(output_video_path, output) + "\" -y")
        video_name = os.path.join(output_video_path, output)
        print("video saved", video_name)
        # breakpoint()
        override = False if int(override_count) < 0 else True
        total_frames = count_frames(video_name, override=override)
        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor(shape_predictor1)
        vs = FileVideoStream(video_name).start()
        fps = FPS().start()
        output_list = []
        output_list.append("Live Video Analysis Start = " + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        output_list.append("Processing Time Start = " + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        output_list.append("DOCUMENT TYPE = Scanned Photo")
        output_list.append("Sub TYPE = Human Face Detection")
        output_list.append("Total Frame : {}".format(total_frames))
        output_list.append("Frame Jump by : 1")
        # defining and initializing required values
        frame_processed_count = 0
        frame_to_save_image = None
        rect_to_save_image = None
        multi_face_found = False
        max_face_found = 0
        TOTAL_BLINK = 0

                
        if video_name:
            try:
                obj = smile_detection.smile_detect(video_name)
                obj.create_frame()
                obj.process_frames()
                obj.remove_files_in_folder()
                smile_detection_dict = obj.to_dict()
                print(smile_detection_dict)
            except Exception as e:
                smile_detection_dict = {'folder_path': 'smiledetection/Files/', 'frames_output_dir': 'smiledetection/Files/', 'files_removed': False, 'total_frame_count': 0, 'frames_to_extract': 0, 'frame_interval': 0, 'smile_detected': False, 'video': video_name, 'start_time': None, 'end_time': None}
        if object_detection(video_name, total_frames):
            COUNTER = 0
            (lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
            (rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
            # i = 1
            # l = []
            while True:
                frame_processed_count = frame_processed_count + 1
                if frame_processed_count > max_frame_count:
                    break
                if not vs.more():
                    break
                frame = vs.read()
                if frame is None:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                rects = detector(gray, 0)
                if len(rects) > max_face_found:
                    max_face_found = len(rects)
                if len(rects) > 1:
                    for i in range(len(rects)):
                        outfacepath = output_face_dir + str(txn_no) + ".JPG"
                        boxes = convert_and_trim_bb(frame, rects[i])
                        x, y, w, h = boxes
                        cv2.imwrite(outfacepath, frame[y:y + h, x:x + w])
                        output_list.append("Face" + str(i + 1) + "=" + str(os.path.basename(outfacepath)))
                    outtemplatepath = template_dir + str(txn_no) + ".JPG"
                    cv2.imwrite(outtemplatepath, frame)
                    output_list.append("Template Face=" + str(os.path.basename(outtemplatepath)))
                    multi_face_found = True
                    break
                if len(rects) == 1:
                    face_found = True
                    rect = rects[0]
                    shape = predictor(gray, rect)
                    shape = face_utils.shape_to_np(shape)
                    leftEye = shape[lStart:lEnd]
                    rightEye = shape[rStart:rEnd]
                    leftEAR = eye_aspect_ratio(leftEye)
                    rightEAR = eye_aspect_ratio(rightEye)
                    ear = (leftEAR + rightEAR) / 2.0
                    if ear < float(EYE_AR_THRESH):
                        COUNTER += 1
                    else:
                        try:
                            if frame_to_save_image == None:
                                frame_to_save_image = frame
                                rect_to_save_image = rect
                        except:
                            pass
                        if COUNTER >= int(EYE_AR_CONSEC_FRAMES):
                            TOTAL_BLINK += 1
                            outfacepath = output_face_dir + str(txn_no) + '.JPG'
                            boxes = convert_and_trim_bb(frame_to_save_image, rect_to_save_image)
                            x, y, w, h = boxes
                            cv2.imwrite(outfacepath, frame_to_save_image[y:y + h, x:x + w])
                            output_list.append("Face1=" + str(os.path.basename(outfacepath)))
                            outtemplatepath = template_dir + str(txn_no) + ".JPG"
                            cv2.imwrite(outtemplatepath, frame_to_save_image)
                            output_list.append("Template Face=" + str(os.path.basename(outtemplatepath)))
                            break
                        COUNTER = 0
            fps.update()
        fps.stop()
        output_list.append("Face Found In Video : " + str(max_face_found))
        output_list.append("Total Face Found = " + str(max_face_found))
        output_list.append("Frame/Second : " + str(fps.fps()))
        output_list.append("Orignal Photo = " + txn_no)
        output_list.append("Group Photo = " + str(multi_face_found))
        output_list.append("Processing Time End=" + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        if TOTAL_BLINK > 0:
            output_list.append("Live Face:True->" + str(TOTAL_BLINK) + "/" + str(frame_processed_count))
        else:
            output_list.append("Still Face:True->" + str(TOTAL_BLINK) + "/" + str(frame_processed_count))
        output_list.append("Frame Scanned:" + str(frame_processed_count))
        #cv2.destroyAllWindows()
        vs.stop()
        list1 = '\n'.join(output_list)
        print(list1)
        json_response = {}
        for l in output_list:
            if "=" in l:
                json_response[l.split("=")[0].strip()] = l.split("=")[1].strip()
            elif ":" in l:
                json_response[l.split(":")[0].strip()] = l.split(":")[1].strip()
        json_response.update({"smile_detected":smile_detection_dict['smile_detected'] if smile_detection_dict['smile_detected'] else False})
        print(json_response)
        print('Process DONE!')
        file = output_dir + str(txn_no) + ".json"
        if os.path.isfile(file):
            os.remove(file)
        print(file)
        Out_f = open(file, "w", encoding="utf-8")
        Out_f.write(json.dumps(json_response, indent=4))
        Out_f.close()
        print(f"main detectio time end {datetime.now()}")
    except RuntimeError as e:
        print(e)
        print("Oops!", sys.exc_info()[0], "occurred.")

def filter_files(files):
    new_files = []
    for file in files:
        if file.endswith(".json"):
            new_files.append(file)
    return new_files

def mainProcess(json_path):
    global output_dir, output_face_dir, template_dir, output_video_path
    input_json = json.loads(open(json_path, "r", encoding="utf-8-sig").read())
    if all(i in input_json for i in ['OUTPUT_FACE_PATH','OUTPUT_JSON_PATH','OUTPUT_TEMPLATE_PATH','OUTPUT_VIDEO_PATH']):
        output_face_dir = input_json['OUTPUT_FACE_PATH']
        output_dir = input_json['OUTPUT_JSON_PATH']
        output_video_path = input_json['OUTPUT_VIDEO_PATH']
        template_dir = input_json['OUTPUT_TEMPLATE_PATH']
    os.makedirs(output_face_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(template_dir, exist_ok=True)
    os.makedirs(output_video_path, exist_ok=True)
    mainDetectionProcess(input_json["FILE"], os.path.basename(input_json["FILE"]).split(".")[0])

def delete_file(json_file_path):
    try:
        os.remove(json_file_path)
    except:
        pass

def create_folders():
    if input_dir and  not os.path.exists(input_dir):
        os.makedirs(input_dir)

def main_process_loop():
    while True:
        create_folders()
        files = [f for f in listdir(input_dir) if isfile(join(input_dir, f))] if os.path.exists(input_dir) else []
        files = filter_files(files)
        if len(files) > 0:
            for file in files:
                start_time = time.time()
                mainProcess(join(input_dir, file))
                delete_file(join(input_dir, file))
                print("--- %s seconds ---" % (time.time() - start_time))
        else:
            time.sleep(0.2)

if __name__ == '__main__':
    main_process_loop()