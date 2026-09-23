import cv2
import os
import requests
import moviepy.editor as mp
import io
from datetime import datetime

class smile_detect(object):             
    def __init__(self, input):
        self.folder_path = "smiledetection/Files/"
        self.frames_output_dir = self.folder_path
        self.files_removed = False              
        self.total_frame_count = 0             
        self.frames_to_extract = 0             
        self.frame_interval = 0                 
        self.smile_detected = False
        self.video = input
        self.start_time = None  
        self.end_time = None  

    def __class__(self):
        pass

    def remove_files_in_folder(self):
        # Iterate over all files in the folder
        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            if os.path.isfile(file_path):  # Check if it's a file
                self.files_removed = True
                os.remove(file_path)  # Remove the file
                print(f"Deleted {file_path}")
                
    def create_frame(self):
        self.start_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        video_name = os.path.join(self.video) 
        if not os.path.exists(self.frames_output_dir):
            os.makedirs(self.frames_output_dir)
        video_capture = cv2.VideoCapture(video_name)
        if not video_capture.isOpened():
            print(f"Error: Could not open video file {video_name}")
            exit()

        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.total_frame_count = total_frames
        print(f"Total number of frames: {total_frames}")
        if total_frames > 5:
            frames_to_extract = total_frames//3
        else:
             frames_to_extract = 1
        self.frames_to_extract = frames_to_extract
        frame_interval = total_frames // frames_to_extract
        self.frame_interval = frame_interval
        print(f"Extracting every {frame_interval} frames")

        frame_number = 0
        current_frame = 0

        while current_frame < total_frames:
            # Read frame from video
            success, frame = video_capture.read()
            if not success:
                break

            # Save the frame if it's within the intervals we want
            if frame_number % frame_interval == 0:
                frame_filename = os.path.join(self.frames_output_dir, f"frame_{frame_number:04d}.png")
                cv2.imwrite(frame_filename, frame)
            
            frame_number += 1
            current_frame += 1
        video_capture.release()
        self.end_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        print(f"Frames extracted and saved to {self.frames_output_dir}")

    def detect_smile_in_frame(self, frame, face_cascade, smile_cascade):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)        
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))        
        for (x, y, w, h) in faces:
            roi_gray = gray_frame[y:y+h, x:x+w]
            smiles = smile_cascade.detectMultiScale(roi_gray, scaleFactor=1.8, minNeighbors=20, minSize=(25, 25))
            
            if len(smiles) > 0:
                return True  # Smile detected
        
        return False  # No smile detected

    
    def process_frames(self):
        face_cascade = cv2.CascadeClassifier("smiledetection/default_frontal_face.xml")
        smile_cascade = cv2.CascadeClassifier('smiledetection/default_smile_cascade.xml')
        for frame_file in self.collect_files():
            frame = cv2.imread(frame_file)
            if frame is None:
                print(f"Error loading image {frame_file}")
                continue
            if self.detect_smile_in_frame(frame, face_cascade, smile_cascade):
                print(f"Smile detected in {frame_file}")
                self.smile_detected = True
                break
            else:
                print(f"No smile detected in {frame_file}")

    # Specify the folder path
    def collect_files(self):
        frame_files = []
        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            if os.path.isfile(file_path):  
                with open(file_path, 'r') as file:
                    frame_files.append(f"{file_path}")
        return frame_files

    def to_dict(self, include_all=True, attributes=None):
        if include_all:
            return self.__dict__
        else:
            return {}
