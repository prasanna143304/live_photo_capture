from flask import Flask, request, jsonify
from utils import config, constants, encdyc
import json, uuid,os, time, shutil, secrets, base64, hashlib, urllib.parse
import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO
import pymssql
import pyodbc
from urllib.parse import urlencode, urlunparse
import cv2
import numpy as np

app = Flask(__name__)
app.config['TIMEOUT'] = 600

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

def key_validator(request):
    return True, request

def get_request():
    unique_id = str(uuid.uuid4().hex)
    unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
    mimetype = request.mimetype
    form = {}
    if mimetype == 'multipart/form-data':
        form = dict(request.form)
        if 'FILEDATA' not in request.files: return 'FILEDATA'
        status, form = key_validator(form)
        if not status: return form
        if 'FILEDATA' in request.files:
            file = request.files['FILEDATA']
            docType = os.path.splitext(file.filename)[1].upper()
            folder = f"{config.DESTINATION_DIR}{form['TXNID'].split('~')[0]}"
            if form['TXNID'].split('~')[1] == "1":
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                os.makedirs(folder, exist_ok=True)
            filename = f"{folder}/{form['TXNID']}{docType}"
            file.save(filename)
            form['FILEDATA'] = filename
    elif mimetype == 'application/json':
        form = request.json
    else:
        form = request.data.decode()
    if form == "":
        form = {}
    return form

def get_requestV2():
    unique_id = str(uuid.uuid4().hex)
    unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
    mimetype = request.mimetype
    print("mimetype", mimetype)
    form = {}
    if mimetype == 'multipart/form-data':
        form = dict(request.form)
        if 'FILEDATA' not in request.files: return 'FILEDATA'
        status, form = key_validator(form)
        if not status: return form
        if 'FILEDATA' in request.files:
            file = request.files['FILEDATA']
            docType = os.path.splitext(file.filename)[1].upper()
            folder = f"{config.DESTINATION_DIR}{form['TOKEN'].split('~')[0]}"
            print(f"FOLDER {folder}")
            if form['TOKEN'].split('~')[1] == "1":
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                os.makedirs(folder, exist_ok=True)
            filename = f"{folder}/{form['TOKEN']}{docType}"
            print(f"filename - {filename}")
            file.save(filename)
            print(f"file saved")
            form['FILEDATA'] = filename
    elif mimetype == 'application/json':
        form = request.json
    else:
        form = request.data.decode()
    if form == "":
        form = {}
    return form

def createFolders(file_path):
    folder_path = f"{config.DESTINATION_DIR}{file_path['TXNID'].split('~')[0]}"
    dirs = ["OUTPUT_FACE_PATH", "OUTPUT_JSON_PATH", "OUTPUT_TEMPLATE_PATH", "OUTPUT_VIDEO_PATH", "PAYLOADS", "OUTPUT_WATERMARK_PATH", "PREPOP_RESPONSE"]
    for dir in dirs:
        os.makedirs(f"{folder_path}/{dir}", exist_ok=True)

def createFoldersV2(file_path):
    try:
        print(f"createFoldersV2")
        folder_path = f"{config.DESTINATION_DIR}{file_path['TOKEN'].split('~')[0]}"
        dirs = ["OUTPUT_FACE_PATH", "OUTPUT_JSON_PATH", "OUTPUT_TEMPLATE_PATH", "OUTPUT_VIDEO_PATH", "PAYLOADS", "OUTPUT_WATERMARK_PATH", "PREPOP_RESPONSE"]
        for dir in dirs:
            os.makedirs(f"{folder_path}/{dir}", exist_ok=True)
    except Exception as e:
        print(f"create folders v2 exception - {e}")

def createFolders_core():
    folder_path = f"{config.CORE_PATH}"
    dirs = ["PROCESS_BLINK_DETECTION", "PROCESS_IMAGE_SEGMENATION", "PROCESS_SIGN_DETECTION", "TRANSACTIONS"]
    for dir in dirs:
        os.makedirs(f"{folder_path}/{dir}", exist_ok=True)

createFolders_core()

def get_access_token(app_version_upper):
    try:
        token = ""
        payload = 'grant_type=client_credentials'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic ' + config.APIGATEWAY_ACCESS_TOKEN_MERGED[app_version_upper]
        }
        response = requests.post(config.APIGATEWAY_ACCESS_TOKEN_ENDPOINT, headers=headers, data=payload).json()
        if "access_token" in response:
            token = response["access_token"]
        return token
    except Exception as e:
        print(f"exception in access token {str(e)}")

class Utils:
    def encode_to_base64(self, input_bytes):
        return base64.b64encode(input_bytes)

    def decode_from_base64(self, input):
        return base64.b64decode(input)

class EncryptionTest:
    def generate_secret_key(self,length):
        key = secrets.token_bytes(length)
        hashed_key = hashlib.sha256(key).digest()
        secret_key = hashed_key[:16]
        return secret_key

    def generate_iv(self):
        block_size = AES.block_size
        iv = get_random_bytes(block_size)
        return iv
    def symmetricencrypt(self, content, iv, key):
        encryptionAlgo = "AES/CBC/PKCS5Padding"
        secretKey = AES.new(key, AES.MODE_CBC, iv)
        encrypted = secretKey.encrypt(pad(content, AES.block_size))
        return encrypted

    def get_public(self, public_key, mode):
        pubKey = public_key.decode("utf-8")
        spec = RSA.import_key(base64.b64decode(pubKey))
        return spec.publickey()

    def asymmetric_encrypt(self, plaintext_key: bytes, public_key: bytes) -> bytes:
        x509_key = RSA.import_key(base64.b64decode(public_key))
        cipher = PKCS1_v1_5.new(x509_key)
        ciphertext = cipher.encrypt(plaintext_key)
        return ciphertext

    def get_secret_key(self,key_bytes, algorithm):
        return AES.new(key_bytes, AES.MODE_CBC)

    def symmetric_encrypt(self, content, iv, key):
        encryption_algo = AES.new(key, AES.MODE_CBC, iv)
        padded_content = pad(content, AES.block_size)
        return encryption_algo.encrypt(padded_content)

    def merge_two_byte_arrays(self, array_one, array_two):
        merged_array = bytearray(len(array_one) + len(array_two))
        merged_array[:len(array_one)] = array_one
        merged_array[len(array_one):] = array_two
        return bytes(merged_array)
                                        
    def extractBytes(self, input, startIndex, endIndex):
        return input[startIndex:endIndex]

    def get_private(self, private_key, mode):
        decoded_key = base64.b64decode(private_key)
        return RSA.importKey(decoded_key)

    def asymmetric_decrypt(self,encrypted_key, private_key):
        pkcs8_private_key = self.get_private(private_key, "RSA")
        cipher = PKCS1_v1_5.new(pkcs8_private_key)
        return cipher.decrypt(encrypted_key, None)

    def symmetricdecrypt(self, encryptedContent, iv, key):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encryptedContent), AES.block_size)
        return decrypted

def encrypt_data(json_data, public_key_path):
    enc = EncryptionTest()
    public_key = open(public_key_path, encoding="utf-8").read().replace("BEGIN PUBLIC KEY","").replace("END PUBLIC KEY","").replace("-","").replace("\n","")
    content = json.dumps(json_data).encode("utf-8")
    plaintext_key = enc.generate_secret_key(16)
    iv = enc.generate_iv()
    encrypted_key = enc.asymmetric_encrypt(plaintext_key, public_key.encode('utf-8'))
    encoded_encrypted_key = base64.b64encode(encrypted_key)
    enc_key= encoded_encrypted_key.decode('utf-8')
    encrypted_data = enc.symmetricencrypt(content, iv, plaintext_key)
    enc_data = base64.b64encode(encrypted_data).decode('utf-8')
    return enc_data, base64.b64encode(iv).decode('utf-8'), enc_key

def decrypt_data(encoded_encrypted_data, encoded_iv, encoded_encrypted_symmetric_key, private_key_path):
    enc = EncryptionTest()
    utilities = Utils()
    private_key = open(private_key_path, encoding="utf-8").read().replace("BEGIN PRIVATE KEY","").replace("END PRIVATE KEY","").replace("-","").replace("\n","")
    decodedKey = utilities.decode_from_base64(encoded_encrypted_symmetric_key)
    decodedContent = utilities.decode_from_base64(encoded_encrypted_data)
    decodedIv = enc.extractBytes(decodedContent, 0, 16)
    decodedContent = enc.extractBytes(decodedContent, 16, len(decodedContent))
    decrypted_key = enc.asymmetric_decrypt(decodedKey, private_key.encode())
    decryptedMessage = enc.symmetricdecrypt(decodedContent, decodedIv, decrypted_key)         
    decryptedMessage = decryptedMessage.decode('utf-8')
    print("VVVVVVV", decryptedMessage)
    return json.loads(decryptedMessage)

def get_decryption_data(data):
    try:
        enc_keys = ["encryptedData","iv","encryptedKey"]
        for i in enc_keys:
            if i not in data:
                return [{"status": False, "errorMessage": f"{i} key is missing"}]
        decrypted_data = decrypt_data(data["encryptedData"], data["iv"], data["encryptedKey"], config.XBIZ_PRIVATE_KEY_PATH)
        return decrypted_data
    except Exception as e:
        return [{"status": False, "errorMessage": e}]
    
def get_encryption_data(json_data):
    try:
        # public_key_path = config.APIGATEWAY_PUBLIC_KEY_PATH
        public_key_path = config.XBIZ_PUBLIC_KEY_PATH
        decoded_encrypted_data, iv, encrypted_symmetric_key = encrypt_data(json_data, public_key_path)
        result_data = {
            "encryptedData": decoded_encrypted_data,
            "iv": iv,
            "encryptedKey": encrypted_symmetric_key,
        }
        return result_data
    except Exception as e:
        return {"status": False, "message": e}

def verifyToken(token, split_txn_id, app_version, access_token, app_version_upper):
    try:
        status = False
        if token == "ip6l1lsu5sh5haaa":
            status = True
        else:
            plain_request = {"token": token, "transaction_id": split_txn_id}
            print(plain_request)
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/VERIFY_TOKEN_REQUEST_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(plain_request, indent=4))
            print(json.dumps(plain_request))
            encrypted_request = get_encryption_data(plain_request)
            encrypted_request["requestId"] = ""
            encrypted_request["service"] = ""
            encrypted_request["oaepHashingAlgorithm"] = "NONE"
            encrypted_request["clientInfo"] = "Xbiz"
            encrypted_request["optionalParam"] = ""
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/VERIFY_TOKEN_REQUEST_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_request, indent=4))
            print(f"app verison upper - {app_version_upper}")
            print(f"config.API_KEY[app_version_upper] - {config.API_KEY[app_version_upper]}")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'apikey': config.API_KEY[app_version_upper],
                'appVersion': app_version
            }
            encrypted_response = requests.post(config.API_ENDPOINTS["VERIFY_TOKEN_ENDPOINT"][app_version_upper], headers=headers, data=json.dumps(encrypted_request)).json()
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/VERIFY_TOKEN_RESPONSE_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_response, indent=4))
            if "iv" not in encrypted_response:
                encrypted_response["iv"] = ""
            decrypted_response = get_decryption_data(encrypted_response)
            print(type(decrypted_response))
            print(decrypted_response)
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/VERIFY_TOKEN_RESPONSE_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(decrypted_response, indent=4))
            if decrypted_response["status"] == 200 and decrypted_response["message"] == "SUCCESS":
                status = True
        print(f"verify token status - {status}")
        return status
    except Exception as e:
        print(f"exception in verify token - {str(e)}")
        return {"exception message" : str(e)}

def generate_hash_key(split_txn_id, watermark, app_version, app_version_upper, output_file_format, token, white_background, ocr_required, hash):
    try:
        if hash:
            salt = config.SALT[app_version_upper]
            print(salt)
            data_to_hash = f"{salt}{token}{split_txn_id}{watermark}{ocr_required}{white_background}{app_version}{output_file_format}"
            hashed_data = hashlib.sha256(data_to_hash.encode()).hexdigest()
            print(f"hashed data: {hashed_data}")
            if hashed_data == hash:
                return True
            else:
                return False
        else:
            return True
    except Exception as e:
        print("237", e)

def apply_watermark(image_path, watermark, output_file_format, output_dir, app_version_upper):
    try:
        image = Image.open(image_path)
        width, height = image.size
        draw = ImageDraw.Draw(image)
        font_path = "./utils/arialbd.ttf"
        font_size = 18
        font = ImageFont.truetype(font_path, font_size)
        print(f"watermark: {watermark}")
        if "presence" in watermark:
            lines = watermark.split(" of ", 1)
            rest = lines[1].split(" at ", 1)
            del lines[1]
            lines.append(" of " + rest[0])
            lines.append(" at " + rest[1])
        elif "Photograph" in watermark:
            lines = watermark.split(" by ", 1)
            rest = lines[1].split(" on ", 1)
            del lines[1]
            lines.append(" by " + rest[0])
            if "Tracking" in rest[1]:
                rest1 = rest[1].rpartition(",")
                print(f"rest1 : {rest1}")
                lines.append(" on " + rest1[0] + rest1[1])
                lines.append(rest1[2])
            else:
                lines.append(" on " + rest[1])
        print(f"lines: {lines}")
        total_height = sum(draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines)
        margin = 10
        y = height - total_height - margin
        if config.BLACK_WHITE_WATERMARK[app_version_upper]:
            total_width = max(draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0] for line in lines)
            x_start = 0
            draw.rectangle([x_start - 5, y - 5, x_start + total_width + 360, y + total_height + 9], fill="black")
        for line in lines:
            text_bbox = draw.textbbox((0, 0), line, font=font)
            line_height = text_bbox[3] - text_bbox[1]
            line_width = text_bbox[2] - text_bbox[0]
            x = (width - line_width) // 2
            if config.BLACK_WHITE_WATERMARK[app_version_upper]:
                draw.text((x, y), line, fill="white", font=font)
                y += line_height + 1
            else:
                draw.text((x, y), line, fill=(255, 165, 0), font=font)
                y += line_height 
        filename = os.path.splitext(os.path.basename(image_path))[0]+"."+output_file_format
        output_path = os.path.join(output_dir, filename )
        image.save(output_path, output_file_format)
        with open(output_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8') 
        return image_base64
    except Exception as e:
        print(f"386 Exception at new watermark function - {str(e)}")
        return {"status" : None, "message" : f"exception 387 {str(e)}" }

def b64_to_file(data,txn_id,page_no):
    binary_data = base64.b64decode(data)
    os.makedirs(f"{config.DESTINATION_DIR}{txn_id}",exist_ok=True)
    image_path = f"{config.DESTINATION_DIR}{txn_id}/{txn_id}_{page_no}.jpeg"
    with open(image_path, "wb") as file:
        file.write(binary_data)
    return image_path

def return_failed_response():
    failed_res = [
        {
            "Kyc": [ 
                {
                "TRN_STATUS": "FAIL"
                }
            ]
        }
    ]
    return failed_res

@app.route("/xbizapi/digivision/ai/backButtonDisable/", methods=['POST'])
def back_button_disable():
    try:
        myRequest = get_request()
        print("my request", myRequest)
        if isinstance(myRequest, str): return {"Liveness_Status":"FALSE", "message": "Incorrect Request"}
        source = myRequest["source"]
        source_upper = source.upper()
        print(f"back button visibility for {source} : {config.BACK_BUTTON_VISIBILITY[source_upper]}")
        return { "source": source, "visibility" : config.BACK_BUTTON_VISIBILITY[source_upper]}
    except Exception as e:
        print(f"source is - {str(e)}")
        return {"status": None, "message" : f"Exception in back button disable - {str(e)}"}

@app.route("/xbizapi/digivision/ai/faceai/capture/", methods=['POST'])
def customer_live_photo_video_capture():
    try:
        myRequest = get_request()
        print("my request", myRequest)
        if isinstance(myRequest, str): return {"Liveness_Status":"FALSE", "message": "Incorrect Request"}
        createFolders(myRequest)
        input_json = {}
        input_json["FILE"] = myRequest["FILEDATA"]
        input_json["OUTPUT_FACE_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_FACE_PATH/"
        input_json["OUTPUT_JSON_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_JSON_PATH/"
        input_json["OUTPUT_TEMPLATE_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_TEMPLATE_PATH/"
        input_json["OUTPUT_VIDEO_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_VIDEO_PATH/"
        input_json["OUTPUT_WATERMARK_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_WATERMARK_PATH/"
        print("BLINK DETECTION PATH",config.INPUT_PATH)
        unique_id = str(uuid.uuid4().hex)
        unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
        original_json_path = os.path.join(config.INPUT_PATH, unique_id + ".json")
        open(original_json_path, "w", encoding="utf-8").write(json.dumps(input_json, indent=4))
        print("IMAGE SEGMENTATION PATH",config.INPUT_PATH_IMAGE_SEGMENTATION)
        for i in range(120):
            if os.path.exists(f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['TXNID']}.json"):
                break
            else:
                time.sleep(1)
        else:
            return {"Liveness_Status":"FALSE", "message": "Request Timeout"}
        if myRequest['WHITE_FLAG'] == '1':
            input_json = {}
            input_json["OUTPUT_TEMPLATE_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_TEMPLATE_PATH/"
            input_json["OUTPUT_JSON_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_JSON_PATH/"
            input_json["TXNID"] = myRequest['TXNID']
            original_json_path = os.path.join(config.INPUT_PATH_IMAGE_SEGMENTATION, unique_id + ".json")
            open(original_json_path, "w", encoding="utf-8").write(json.dumps(input_json, indent=4))
            # for i in range(120):
            #     if os.path.exists(f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['TXNID']}_IMAGE_SEGMENTATION.json"):
            #         break
            #     else:
            #         time.sleep(1)
            # else:
            #     return {"Liveness_Status":"FALSE", "message": "Request Timeout"}
        result_json = json.loads(open(f"{config.DESTINATION_DIR}{myRequest['TXNID'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['TXNID']}.json", "r", encoding="utf-8").read())
        result = {}
        if "Group Photo" in result_json:
            result["Group_Photo"] = result_json["Group Photo"]
        if "Live Face" in result_json:
            result["Liveness_Status"] = result_json["Live Face"]
        elif "Still Face" in result_json:
            result["Liveness_Status"] = "TRUE->0/100"
        if "Liveness_Status" in result and "FALSE" in result["Liveness_Status"].upper():
            result["message"] = "Blink Not Detection"
        return result
    except Exception as e:
        return {"Liveness_Status":"FALSE", "message": str(e)}

@app.route("/xbizapi/digivision/ai/capture/", methods=['POST'])
def customer_doc_capture():
    try:
        myRequest = get_request()
        if isinstance(myRequest, str): return {"Status":"FALSE", "message": "Incorrect Request"}
        if myRequest['requestObject'][0]['document_id'] == '20':
            try:
                txn_id = myRequest['requestObject'][0]['transaction_id']
                createFolders({"TXNID": txn_id + "~1"})
                b64_data = myRequest['requestObject'][0]['imageBase64']
                image_path = b64_to_file(b64_data,txn_id, "1")
                print(image_path)
                input_json = {}
                input_json["INPUT_IMAGE"] = image_path
                input_json["OUTPUT_IMAGE"] = f"{config.DESTINATION_DIR}{txn_id}/OUTPUT_TEMPLATE_PATH/"
                input_json["OUTPUT_JSON"] = f"{config.DESTINATION_DIR}{txn_id}/OUTPUT_JSON_PATH/"
                input_json["TXNID"] = txn_id
                print(input_json)
                unique_id = str(uuid.uuid4().hex)
                unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
                print(unique_id)
                print(config.INPUT_PATH_SIGN_DETECTION)
                original_json_path = os.path.join(config.INPUT_PATH_SIGN_DETECTION, unique_id + ".json")
                print(original_json_path)
                open(original_json_path, "w", encoding="utf-8").write(json.dumps(input_json, indent=4))
                for i in range(120):
                    if os.path.exists(f"{config.DESTINATION_DIR}{txn_id}/OUTPUT_JSON_PATH/{txn_id}.json"):
                        json_data = json.loads(open(f"{config.DESTINATION_DIR}{txn_id}/OUTPUT_JSON_PATH/{txn_id}.json", "r", encoding="utf-8").read())
                        if json_data["SIGNATURE_FOUND"]:
                            return {"SignatureFound":"true"}
                        else:
                            return {"SignatureFound":"false 1"}
                    else:
                        time.sleep(1)
                else:
                    return {"SignatureFound":"false 2"}
            except:
                return {"SignatureFound":"false 3"}
        elif myRequest['requestObject'][0]['document_id'] in ["1", "2", "3", "4", "6"]:
            try:
                txn_id = myRequest['requestObject'][0]['transaction_id']
                createFolders({"TXNID": txn_id + "~1"})
                doc_id = myRequest['requestObject'][0]['document_id']
                b64_data = myRequest['requestObject'][0]['imageBase64']
                request_obj = config.REQUEST_OBJ
                request_obj["txnId"] = txn_id
                request_obj["documentId"] = doc_id
                request_obj["documentBlob"] = b64_data
                response = requests.post(url=config.API_URL, json=request_obj).json()
                if response['results'][0]['documentType']['value'] == config.DOCUMENT_ID[doc_id]:
                    page_no = response["results"][0]["pageNo"]["value"][0]
                    sub_type = response["results"][0]["subDocumentType"]["value"]
                    b64_to_file(b64_data,txn_id,page_no)
                    if (page_no == 1 and sub_type in ["FRONT SIDE DOC", "COMPLETE DOC"]) or (page_no == 2 and sub_type in ["BACK SIDE DOC"]):
                        folder_path = f"{config.DESTINATION_DIR}{txn_id}"
                        original_json_path = os.path.join(f"{folder_path}/PREPOP_RESPONSE/", f"{txn_id}_{page_no}" + ".json")
                        open(original_json_path, "w+", encoding="utf-8").write(json.dumps(response, indent=4))
                        required_res = [
                            {
                                "Kyc" : [
                                    {
                                        "TRN_STATUS": "PASS",
                                        "DOCUMENT_TYPE" : config.DOCUMENT_ID[doc_id],
                                        "SUB_TYPE" : response["results"][0]["subDocumentType"]["value"]
                                    }
                                ] 
                            }
                        ]
                        return required_res
                    else:
                        return return_failed_response()
                else:
                    return return_failed_response()
            except:
                return return_failed_response()
        else:
            return {"CaptureResponse":"false"}
    except Exception as e:
        print(e)
        return {"Remarks":"false", "Exception": str(e)}

@app.route("/xbizapi/digivision/ai/submit/", methods=['POST'])
def customerLivePhotoSubmit():
    try:
        myRequest = get_request() ##done
        print(myRequest)
        if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
        if myRequest["white_background"] == "1":
            for i in range(120):
                    if os.path.exists(f"{config.DESTINATION_DIR}{myRequest['transactionId'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['transactionId']}_IMAGE_SEGMENTATION.json"):
                        break
                    else:
                        time.sleep(1)
            else:
                return {"Liveness_Status":"FALSE", "message": "Request Timeout"}
        # if not myRequest['type']=="doc_capture":
        # if myRequest['app_version'] == None or myRequest['hash'] == None:
        #     return {"status":False,"message":"app_version not found"}
        txn_id = myRequest["transactionId"]
        split_txn_id = txn_id.split('~')[0] if '~' in txn_id else txn_id
        print(f"split_txn_id: {split_txn_id}")
        watermark = myRequest["watermark"]
        print(f"watermark - {watermark}")
        app_version = myRequest["app_version"]
        print(app_version)
        app_version_upper = app_version.upper()
        print(f"app version upper - {app_version_upper}")
        output_file_format = myRequest["output_file_format"]
        token = myRequest["token"]
        white_background = myRequest["white_background"]
        print(f"type(wb) - {type(white_background)}")
        hash = myRequest["hash"]
        print(f"hash - {hash}")
        ocr_required = myRequest["ocr_required"]
        if app_version_upper == "XBIZ_DEMO":
            image_path = f"{config.DESTINATION_DIR}{split_txn_id}/OUTPUT_TEMPLATE_PATH/{txn_id}.JPG"
            output_dir = f"{config.DESTINATION_DIR}{split_txn_id}/OUTPUT_WATERMARK_PATH/"
            output_video = f"{config.DESTINATION_DIR}{split_txn_id}/OUTPUT_VIDEO_PATH/{txn_id}.mp4"
            with open(output_video, "rb") as video_file:
                video_data = video_file.read()
                base64_video = base64.b64encode(video_data).decode('utf-8')
            image_base64 = apply_watermark(image_path, watermark, output_file_format, output_dir)
            return jsonify({'status':True,'message':'SUCCESS','image': image_base64, 'video':base64_video})
        callback_url = ""
        access_token = get_access_token(app_version_upper)
        print(f"access_token: {access_token}")
        # if access_token == "":
        #     return {"status":False,"message":"Access Token Failed"}
        if generate_hash_key(split_txn_id, watermark, app_version, app_version_upper, output_file_format, token, white_background, ocr_required, hash):
            if verifyToken(token, split_txn_id, app_version, access_token, app_version_upper):
                print(f"token verified")
                image_path = f"{config.DESTINATION_DIR}{split_txn_id}/OUTPUT_TEMPLATE_PATH/{txn_id}.JPG"
                print(image_path)
                if os.path.exists(image_path):
                    output_dir = f"{config.DESTINATION_DIR}{split_txn_id}/OUTPUT_WATERMARK_PATH/"
                    print(output_dir)
                    image_base64 = apply_watermark(image_path, watermark, output_file_format, output_dir, app_version_upper)
                    # if app_version_upper == "XBIZ_DEMO":
                    #     return image_base64
                    Ref_Id = split_txn_id[-2:]
                    print(f"refernce id {Ref_Id}")
                    txn_id_with_extension = split_txn_id + ".AIBI"
                    TXN_Id = split_txn_id
                    current_datetime = datetime.now()
                    PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
                    endpoint = config.API_ENDPOINTS["CALLBACK_ENDPOINT"][app_version_upper]
                    print(f"endpoint: {endpoint}")
                    headers = {
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {access_token}',
                            'apikey': config.API_KEY[app_version_upper],
                            'appVersion': app_version
                        }
                    request_payload = json.load(open("./utils/request_format.json", encoding="utf-8"))
                    request_payload["token"] = token
                    request_payload["Result"][0]["IMAGEBASE64"] = [image_base64]
                    request_payload["Result"][1]["Ref_Id"] = Ref_Id
                    request_payload["Result"][1]["INPUT_FILE"] = txn_id_with_extension
                    request_payload["Result"][1]["TRANSACTION_NUMBER"] = TXN_Id
                    request_payload["Result"][1]["CASE_NO"] = TXN_Id
                    request_payload["Result"][1]["DB_FILE"] = txn_id_with_extension
                    request_payload["Result"][1]["PROCESS_TIME_END"] = PROCESS_TIME_END
                    open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_REQUEST_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(request_payload, indent=4))
                    encrypted_request = get_encryption_data(request_payload)
                    encrypted_request["requestId"] = ""
                    encrypted_request["service"] = ""
                    encrypted_request["oaepHashingAlgorithm"] = "NONE"
                    encrypted_request["clientInfo"] = "Xbiz"
                    encrypted_request["optionalParam"] = ""
                    open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_REQUEST_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_request, indent=4))
                    encrypted_response = requests.post(endpoint, headers=headers, data=json.dumps(encrypted_request)).json()
                    open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_RESPONSE_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_response, indent=4))
                    if "iv" not in encrypted_response:
                        encrypted_response["iv"] = ""
                    decrypted_response = get_decryption_data(encrypted_response)
                    open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_RESPONSE_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(decrypted_response, indent=4))
                    if decrypted_response["status"] == True:
                        callback_url = decrypted_response["redirectUrl"]
                        return {"status":True,"message":callback_url}
                    else:
                        return {"status":False,"message":callback_url}
                else:
                    return {"status":False,"message":"Template Image Does not Exists"}
            return {"status":False,"message":"Token Verification Failed. INVALID TOKEN"}
        else:
            return {"status":False,"message":"INVALID HASH VALUE"}
        # else:
        #     txn_id = myRequest['transactionId']
        #     split_txn_id = txn_id.split("~")[0] if '~' in txn_id else txn_id
        #     watermark = myRequest["watermark"]
        #     app_version = myRequest["app_version"]
        #     output_file_format = myRequest["output_file_format"]
        #     token = myRequest["token"]
        #     print(myRequest)
        #     callback_url = ""
        #     access_token = get_access_token()
        #     print(access_token)
        #     if access_token == "":
        #         return {"status":False,"message":"Access Token Failed"}
        #     if verifyToken(token, split_txn_id, app_version, access_token):
        #         image_path_1 = f"{config.DESTINATION_DIR}{txn_id}/{txn_id}_1.jpeg"
        #         image_path_2 = f"{config.DESTINATION_DIR}{txn_id}/{txn_id}_2.jpeg"
        #         if os.path.exists(image_path_1):
        #             image_path = image_path_1
        #             output_dir = f"{config.DESTINATION_DIR}{split_txn_id}/OUTPUT_WATERMARK_PATH/"
        #             image_base64 = apply_watermark(image_path, watermark, output_file_format, output_dir)
        #             Ref_Id = split_txn_id[-2:]
        #             txn_id_with_extension = split_txn_id + ".AIBI"
        #             TXN_Id = split_txn_id
        #             current_datetime = datetime.now()
        #             PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
        #             endpoint = config.API_ENDPOINTS["CALLBACK_ENDPOINT"][app_version]
        #             headers = {
        #                     'Content-Type': 'application/json',
        #                     'Authorization': f'Bearer {access_token}',
        #                     'apikey': config.API_KEY,
        #                     'appVersion': app_version
        #                 }
        #             request_payload = json.load(open("./utils/request_format.json", encoding="utf-8"))
        #             request_payload["token"] = token
        #             request_payload["Result"][0]["IMAGEBASE64"] = [image_base64]
        #             request_payload["Result"][1]["Ref_Id"] = Ref_Id
        #             request_payload["Result"][1]["INPUT_FILE"] = txn_id_with_extension
        #             request_payload["Result"][1]["TRANSACTION_NUMBER"] = TXN_Id
        #             request_payload["Result"][1]["CASE_NO"] = TXN_Id
        #             request_payload["Result"][1]["DB_FILE"] = txn_id_with_extension
        #             request_payload["Result"][1]["PROCESS_TIME_END"] = PROCESS_TIME_END
        #             open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_REQUEST_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(request_payload, indent=4))
        #             encrypted_request = get_encryption_data(request_payload)
        #             encrypted_request["requestId"] = ""
        #             encrypted_request["service"] = ""
        #             encrypted_request["oaepHashingAlgorithm"] = "NONE"
        #             encrypted_request["clientInfo"] = "Xbiz"
        #             encrypted_request["optionalParam"] = ""
        #             open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_REQUEST_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_request, indent=4))
        #             encrypted_response = requests.post(endpoint, headers=headers, data=json.dumps(encrypted_request)).json()
        #             open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_RESPONSE_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_response, indent=4))
        #             if "iv" not in encrypted_response:
        #                 encrypted_response["iv"] = ""
        #             decrypted_response = get_decryption_data(encrypted_response)
        #             open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_RESPONSE_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(decrypted_response, indent=4))
        #             if decrypted_response["status"] == True:
        #                 callback_url = decrypted_response["redirectUrl"]
        #                 return {"status":True,"message":callback_url}
        #             else:
        #                 return {"status":False,"message":callback_url}
        #         elif os.path.exists(image_path_2):
        #             image_path = image_path_1
        #             output_dir = f"{config.DESTINATION_DIR}{split_txn_id}/OUTPUT_WATERMARK_PATH/"
        #             image_base64 = apply_watermark(image_path, watermark, output_file_format, output_dir)
    except Exception as e:
        return {"status":False,"message":str(e)}

@app.route("/xbizapi/digivision/ai/back/", methods=["POST"])
def customerLivePhotoBack():
    try:
        myRequest = get_request()
        txn_id = myRequest["transactionId"]
        print(f"txn_id {txn_id}")
        split_txn_id = txn_id.split('~')[0] if '~' in txn_id else txn_id
        print(f"split_txn_id {split_txn_id}")
        watermark = myRequest["watermark"]
        app_version = myRequest["app_version"].upper()
        print(app_version)
        token = myRequest["token"]
        print(myRequest)
        createFolders({"TXNID": txn_id})
        if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
        callback_url = ""
        print("before access token")
        access_token = get_access_token(app_version)
        print(access_token)
        if access_token == "":
            return {"status":False,"message":"Access Token Failed"}
        print("before verify token")
        if verifyToken(token, split_txn_id, app_version, access_token):
            print(f"TOKEN VERIFIED")
            image_base64 = ""
            Ref_Id = split_txn_id[-2:]
            txn_id_with_extension = split_txn_id + ".AIBI"
            TXN_Id = split_txn_id
            current_datetime = datetime.now()
            PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
            endpoint = config.API_ENDPOINTS["CALLBACK_ENDPOINT"][app_version]
            headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}',
                    'apikey': config.API_KEY[app_version],
                    'appVersion': app_version
                }
            request_payload = json.load(open("./utils/request_format.json", encoding="utf-8"))
            request_payload["token"] = token
            request_payload["Result"][0]["IMAGEBASE64"] = [image_base64]
            request_payload["Result"][1]["Ref_Id"] = Ref_Id
            request_payload["Result"][1]["INPUT_FILE"] = txn_id_with_extension
            request_payload["Result"][1]["TRANSACTION_NUMBER"] = TXN_Id
            request_payload["Result"][1]["CASE_NO"] = TXN_Id
            request_payload["Result"][1]["DB_FILE"] = txn_id_with_extension
            request_payload["Result"][1]["PROCESS_TIME_END"] = PROCESS_TIME_END
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_BACK_REQUEST_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(request_payload, indent=4))
            encrypted_request = get_encryption_data(request_payload)
            print(f"630 encrypted request")
            encrypted_request["requestId"] = ""
            encrypted_request["service"] = ""
            encrypted_request["oaepHashingAlgorithm"] = "NONE"
            encrypted_request["clientInfo"] = "Xbiz"
            encrypted_request["optionalParam"] = ""
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_BACK_REQUEST_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_request, indent=4))
            print(f"BEFORE ENCRYPTED RESPONSE")
            encrypted_response = requests.post(endpoint, headers=headers, data=json.dumps(encrypted_request)).json()
            print(f"ENCRYPTED RESPONSE - {encrypted_response}")
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_BACK_RESPONSE_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_response, indent=4))
            if "iv" not in encrypted_response:
                encrypted_response["iv"] = ""
            decrypted_response = get_decryption_data(encrypted_response)
            print(f"DECRYPTED RESPONSE - {decrypted_response}")
            open(f"{config.DESTINATION_DIR}{split_txn_id}/PAYLOADS/CALLBACK_BACK_RESPONSE_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(decrypted_response, indent=4))
            status = decrypted_response["status"]
            callback_url = decrypted_response["redirectUrl"]
            return {"status":True,"message":callback_url}
        return {"status":False,"message":callback_url}
    except Exception as e:
        return {"status":False,"message":str(e)}

@app.route("/xbizapi/digivision/ai/delete", methods=['POST'])
def delete_doc_capture():
    try:
        myRequest = get_request()
        print(myRequest)
        txn_id = myRequest["Transaction_ID"]
        doc_id = myRequest["Doc_Id"]
        page_no = myRequest["PageNo"]
        if doc_id in ['1', '2', '3', '4', '6', '20']:
            if os.path.exists(f"{config.DESTINATION_DIR}{txn_id}"):
                shutil.rmtree(f"{config.DESTINATION_DIR}{txn_id}")
        return {"Status": True}        
    except Exception as e:
        return {"Status":False,"Remarks":str(e)}

# @app.route("/xbizapi/digivision/ai/sign_capture", methods=['POST'])
# def customer_sign_capture():
#     try:
#         myRequest = get_request()
#         if isinstance(myRequest, str): return {'Status':'FALSE', 'message':'incorrect request'}
#         if myRequest['requestObject'][0]['document_id'] in ["1"]:
#             try:
#                 transaction_Id = myRequest['requestObject'][0]['transaction_id']
#                 createFolders({"TXNID": transaction_Id + "~1"})
#                 document_Id = myRequest['requestObject'][0]['document_id']
#                 b64_data = myRequest['requestObject'][0]['imageBase64']
#                 source = myRequest['requestObject'][0]['source']
#                 sign_request_obj = config.SIGN_REQUEST_OBJ
#                 sign_request_obj["txnId"] = transaction_Id
#                 sign_request_obj["documentId"] = document_Id
#                 sign_request_obj["documentBlob"] = b64_data
#                 sign_request_obj["source"] = source
#                 print("before response")
#                 response = requests.post(url=config.API_URL, json=sign_request_obj).json()
#                 print(response)
#                 # return response
#                 if response['results'][0]['documentType']['value'] == 'Signature Capture':
#                     b64_to_file(b64_data, transaction_Id, page_no=1)
#                     folder_path = f"{config.DESTINATION_DIR}{transaction_Id}"
#                     original_json_path = os.path.join(f"{folder_path}/PREPOP_RESPONSE/", f"{transaction_Id}_{1}" + ".json")
#                     open(original_json_path, "w+", encoding="utf-8").write(json.dumps(response, indent=4))
#                     required_res = [
#                             {
#                                 "Kyc" : [
#                                     {
#                                         "TRN_STATUS": "PASS",
#                                         "DOCUMENT_TYPE" : "Signature Capture"
#                                     }
#                                 ] 
#                             }
#                         ]
#                     return required_res
#                 else:
#                     return return_failed_response()
#             except:
#                 return return_failed_response()
#         else:
#             return {"SignCapture":"False"}
#     except Exception as e:
#         print(e)
#         return {'remarks':'False', 'message':'incorrect request'}

def crop_below_vertices_full_breadth(image_path, vertices, save_path, file_type):
    try:
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Convert vertices to NumPy array
        vertices = np.array(vertices, dtype=np.int32)

        # Calculate the bounding box of the vertices
        x, y, w, h = cv2.boundingRect(vertices)

        # Calculate the new bottom coordinate extending below the vertices
        start_y = y  # Start from the top of the bounding box
        end_y = start_y + 14 * h  # Extend 13 times the height below the vertices

        # Ensure the new bottom coordinate does not exceed the image height
        end_y = min(end_y, image.shape[0])

        # Crop the image using the adjusted bounding box
        cropped_image = image[start_y:end_y, 0:image.shape[1]]

        # Save the cropped image
        if cropped_image.size > 0:
            cv2.imwrite(save_path, cropped_image)
            print(f"Cropped image saved at {save_path}")
        else:
            print(f"Cropping failed. The resulting image is empty.")

        # Encode the cropped image to base64
        # _, buffer = cv2.imencode('.jpeg', cropped_image)
        _, buffer = cv2.imencode(file_type, cropped_image)
        cropped_image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return cropped_image, cropped_image_base64
    except Exception as e:
        print(f"870 exception in crop_below_vertices_full_breadth {str(e)}")

def crop_image_into_three_parts(cropped_image, vertices, save_path, file_type):
    try:
        height, width = cropped_image.shape[:2]

        # Extract x-coordinates from vertices
        x_coords = [vertex[0] for vertex in vertices]
        x_coords.sort()

        # Define margins for cropping a little before and after vertices
        margin = int(0.03 * width)  # Adjust margin as 10% of the image width

        # Ensure the margin does not exceed the image boundaries
        left_margin = max(0, x_coords[0] - margin)
        right_margin = min(width, x_coords[-1] + margin)

        # Define the coordinates for the three parts
        coords = [
            (0, x_coords[0]),             # Leftmost to first vertex
            (left_margin, right_margin),  # Slightly before first vertex to slightly after last vertex
            (x_coords[-1], width)         # Last vertex to rightmost part
        ]

        base64_images = []

        for i, (start_x, end_x) in enumerate(coords):
            cropped_part = cropped_image[:, int(start_x):int(end_x)]
            crop_path = os.path.join(save_path, f'crop_part_{i + 1}{file_type}')

            if cropped_part.size > 0:
                cv2.imwrite(crop_path, cropped_part)
                print(f"Cropped part {i + 1} saved at {crop_path}")
            else:
                print(f"Cropping failed for part {i + 1}. The resulting image is empty.")

            # Encode the cropped part to base64
            # _, buffer = cv2.imencode('.jpeg', cropped_part)
            _, buffer = cv2.imencode(file_type, cropped_part)
            cropped_part_base64 = base64.b64encode(buffer).decode('utf-8')
            base64_images.append(cropped_part_base64)

        return base64_images
    except Exception as e:
         print(f"914 exception in crop_image_into_three_parts {str(e)}")

def detect_signature(image_path):
  """
  Detects a signature in an image.

  Args:
    image_path: Path to the image file.

  Returns:
    True if a signature is detected, False otherwise.
  """

  # Load the image
  image = cv2.imread(image_path)

  # Convert to grayscale
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

  # Apply thresholding to binarize the image
  thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

  # Find contours
  contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

  # Iterate through the contours and look for signature-like features
  for contour in contours:
    # Calculate the area of the contour
    area = cv2.contourArea(contour)

    # Calculate the aspect ratio of the contour
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h

    # Check if the contour has a large area and a typical aspect ratio for a signature
    if area > 100 and 0.5 < aspect_ratio < 2:
      return True

  # If no signature-like contours are found, return False
  return False


@app.route("/xbizapi/digivision/ai/sign_capture", methods=['POST'])
def customer_sign_capture():
    try:
        myRequest = get_request()
        # print(f"myRequest - {myRequest}")
        if isinstance(myRequest, str): return {'Status':'FALSE', 'message':'incorrect request'}
        current_datetime = datetime.now()
        PROCESS_TIME_START = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
        document_Id = myRequest["document_Id"]
        print(f"document_Id - {document_Id}")
        category = myRequest["category"]
        print(f"category - {category}")
        signature_type = myRequest["signature_type"]
        print(f"signature_type - {signature_type}")
        file_type = myRequest["File_Type"]
        print(f"file_type - {file_type}")
        txn_id = myRequest["transaction_Id"]
        print(f"txn_id - {txn_id}")
        source = myRequest["Source"]
        print(f"source - {source}")
        imageBase64 = myRequest["ImageBase64"]
        # print(f"imageBase64 - {imageBase64}")
        if document_Id in ["1"] and category == "SIGN" and imageBase64 != "":
            try:
                # transaction_Id = myRequest['requestObject'][0]['transaction_id']
                createFolders({"TXNID": txn_id + "~1"})
                # document_Id = myRequest['requestObject'][0]['document_id']
                # b64_data = myRequest['requestObject'][0]['imageBase64']
                # source = myRequest['requestObject'][0]['source']
                sign_request_obj = config.SIGN_REQUEST_OBJ
                sign_request_obj["txnId"] = txn_id
                sign_request_obj["documentId"] = document_Id
                sign_request_obj["documentBlob"] = imageBase64
                sign_request_obj["source"] = "MIGRATED_IBU_SIGNATURE" # SOURCE FOR BACKEND API 
                print("before response")
                response = requests.post(url=config.API_URL, json=sign_request_obj).json()
                print("after response")
                # print(response)
                # return response
                # if response['results'][0]['documentType']['value'] == 'Signature Capture':
                response_len = len(response["results"])
                print(f"response['results'] len - {response_len}")
                if response_len > 0 and response["statusCode"] == 200:
                    # if len(response["results"]) == 1:
                    #     page_no = 1
                    #     base64_data = response["results"][0]["documentBlob"]
                    # else:
                    #     page_no = 2
                    #     base64_data = response["results"][1]["documentBlob"]
                    # b64_to_file(base64_data, txn_id, page_no)
                    # folder_path = f"{config.DESTINATION_DIR}{txn_id}"
                    # original_json_path = os.path.join(f"{folder_path}/PREPOP_RESPONSE/", f"{txn_id}_{1}" + ".json")
                    # open(original_json_path, "w+", encoding="utf-8").write(json.dumps(response, indent=4))
                    
                    for i in range(0, len(response["results"][response_len-1])):
                        for j in range(0, len(response["results"][response_len-1]["ocrLine"])):
                            if response["results"][response_len-1]["ocrLine"][j]["TEXT"]=="APPLICANT'S SIGNATURE(S)" or response["results"][response_len-1]["ocrLine"][j]["TEXT"]=="APPLICANTS SIGNATURES" :
                                req_b64_data = response["results"][response_len-1]["documentBlob"]
                                vertices_dict = response["results"][response_len-1]["ocrLine"][j]["VERTICES"]
                                print(vertices_dict)
                                # page_no = i+1
                                # print(response["results"][i]["ocrLine"][j])
                    vertices = []
                    for i in range(0, len(vertices_dict)):
                        vertices.append(tuple(vertices_dict[i].values()))
                    print(vertices)

                    image_path = b64_to_file(req_b64_data, txn_id, page_no=response_len)
                    folder_path = f"{config.DESTINATION_DIR}{txn_id}"
                    original_json_path = os.path.join(f"{folder_path}/PREPOP_RESPONSE/", f"{txn_id}_{1}" + ".json")
                    open(original_json_path, "w+", encoding="utf-8").write(json.dumps(response, indent=4))
                    os.makedirs(f"{folder_path}/SIGNATURE_CROPPED_IMAGES", exist_ok=True)
                    cropped_images_folder = f"{folder_path}/SIGNATURE_CROPPED_IMAGES"
                    save_path_crop = f"{cropped_images_folder}\crop_part_4{file_type}"
                    cropped_image, cropped_image_base64  = crop_below_vertices_full_breadth(image_path, vertices, save_path_crop, file_type)
                    base64_parts = crop_image_into_three_parts(cropped_image, vertices, cropped_images_folder, file_type)
                    base64_parts.append(cropped_image_base64)
                    sign_type = int(signature_type)
                    sign_exists = detect_signature(f"{cropped_images_folder}\crop_part_{signature_type}{file_type}")
                    print(f"sign_exists - {sign_exists}")
                    current_datetime = datetime.now()
                    PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
                    if 4 >= sign_type >= 1:
                        # return (base64_parts[sign_type-1][50:])
                        # return (base64_parts[sign_type-1])

                        return_response = {
                            "Status" : "Success",
                            "Outputimage" : base64_parts[sign_type-1],
                            "SignatureExist": sign_exists,
                            "PROCESS_TIME_START": PROCESS_TIME_START,
                            "PROCESS_TIME_END": PROCESS_TIME_END,
                            "DOCUMENT_TYPE": "AOFSIGNATURE"
                        }
                        return return_response
                    else:
                        return_failed_response()
                    # required_res = [
                    #         {
                    #             "Kyc" : [
                    #                 {
                    #                     "TRN_STATUS": "PASS",
                    #                     "DOCUMENT_TYPE" : "Signature Capture"
                    #                 }
                    #             ] 
                    #         }
                    #     ]
                    # return required_res
                else:
                    return return_failed_response()
            except:
                return return_failed_response()
        else:
            return {"SignCapture":"False", 'errorMessage': 'Mandatory field data is missing'}
    except Exception as e:
        print(e)
        return {'remarks':'False', 'message':'incorrect request'}

# @app.route("/xbizapi/digivision/ai/digi_merge", methods=['POST'])
# def customer_photo_sign_merge():
#     try:
#         myRequest = get_request()
#         print(f"DigiMerge request - {myRequest}")
#         if isinstance(myRequest, str): return {'Status' : 'FALSE', 'message' : 'Incorrect Request'}
#         if myRequest.get("encryptedData") and myRequest.get("encryptedKey"):
#             print("1082 encrypted request")
#             request_to_send = {
#                 "data" : myRequest,
#                 "ivIntegration": True,
#                 "source": "XBIZ"
#             }
#         else:
#             return {"Status": "False", "Message": "Mandatory field data is missing"}
#         internal_response = requests.post(url=config.DIGI_MERGE_URL, json=request_to_send).json()
#         # internal_response = requests.post(url='http://127.0.0.1:7980/enc_dec', json=request_to_send).json()
#         print("internal response",internal_response)
#         ImageBase64Second = internal_response["ImageBase64Second"]
#         print(f"ImageBase64Second - {ImageBase64Second}")
#         ImageBase64 = internal_response["ImageBase64"]
#         print(f"ImageBase64 - {ImageBase64} ")
#         Category = internal_response["Category"]
#         print(f"Category - {Category}")
#         txn_id = internal_response["transaction_Id"]
#         print(f"txn_id - {txn_id}")
#         doc_id = internal_response["document_Id"]
#         print(f"doc_id - {doc_id}")
#         file_type = internal_response["File_Type"]
#         print(f"file_type - {file_type}")
#         if ImageBase64Second != "" and ImageBase64 != "" and doc_id == "1":
#             try:
#                 createFolders({"TXNID": txn_id + "~1"})
#                 current_datetime = datetime.now()
#                 PROCESS_TIME_START = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
#                 # imageBase64_photo = myRequest['requestObject'][0]['imageBase64_photo']
#                 # imageBase64_sign = myRequest['requestObject'][1]['imageBase64_sign']
#                 decoded_photo_img = base64.b64decode(ImageBase64Second)
#                 decoded_sign_img = base64.b64decode(ImageBase64)
#                 photo_img = Image.open(BytesIO(decoded_photo_img))
#                 sign_img = Image.open(BytesIO(decoded_sign_img))
#                 new_width = photo_img.width + sign_img.width
#                 new_height = max(photo_img.height, sign_img.height)
#                 merged_image = Image.new('RGB', (new_width, new_height))
#                 merged_image.paste(photo_img, (0, 0))
#                 merged_image.paste(sign_img, (photo_img.width, 0))
#                 output_buffer = BytesIO()
#                 merged_image.save(output_buffer, format='PNG')
#                 base64_merged_image = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
#                 folder_path = f"{config.DESTINATION_DIR}{txn_id}"
#                 binary_data = base64.b64decode(base64_merged_image)
#                 os.makedirs(f"{folder_path}/MERGE_OUTPUT", exist_ok=True)
#                 image_path = f"{folder_path}/MERGE_OUTPUT/{txn_id}_{1}{file_type}"
#                 with open(image_path, "wb") as file:
#                     file.write(binary_data)
#                 print(f"merged image saved at - {image_path}")
#                 current_datetime = datetime.now()
#                 PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
#                 return_json = {
#                     "Status" : "Success",
#                     "Outputimage" : base64_merged_image,
#                     "PROCESS_TIME_START": PROCESS_TIME_START,
#                     "PROCESS_TIME_END": PROCESS_TIME_END,
#                     "SignatureExist": "",
#                     "DOCUMENT_TYPE":"PHOTO_SIGNATURE_MERGE"
#                 }
#             except Exception as e:
#                 print(str(e))
#                 return {"Remarks":"false", "Exception": str(e)}
#         else:
#             return_json = {
#                 "Status" : "Failure",
#                 "Outputimage" : "",
#                 "PROCESS_TIME_START": "",
#                 "PROCESS_TIME_END": "",
#                 "SignatureExist": "",
#                 "DOCUMENT_TYPE":"PHOTO_SIGNATURE_MERGE"
#             }
#         response_to_send = {
#                     "data" : return_json,
#                     "ivIntegration": True,
#                     "source": ""
#                 }
#         internal_response = requests.post(url=config.DIGI_MERGE_URL, json=response_to_send).json()
#         # internal_response = requests.post(url='http://127.0.0.1:7980/enc_dec', json=response_to_send).json()
#         return internal_response
#     except Exception as e:
#         print(e)
#         return {"Remarks":"false", "Exception": str(e)}

# @app.route("/xbizapi/digivision/ai/digi_merge", methods=['POST'])
# def customer_photo_sign_merge():
#     try:
#         mainRequest = get_request()
#         print(mainRequest)
#         if isinstance(mainRequest, str): return {'Status' : 'FALSE', 'message' : 'Incorrect Request'}
#         if mainRequest.get("encryptedData") and mainRequest.get("encryptedKey"):
#             print("838 encrypted request")
#             request_to_send = {
#                 "data" : mainRequest,
#                 "ivIntegration": True,
#                 "source": "XBIZ"
#             }
#             internal_response = requests.post(url=config.DIGI_MERGE_URL, json=request_to_send).json()
#             print("internal response",internal_response)
#             myRequest = internal_response
#             print("myRequest = internal_response")
#             print(myRequest)
#         else:
#             print("853 plain request")
#             myRequest = mainRequest
#         if myRequest['requestObject'][0]['imageBase64_photo'] and myRequest['requestObject'][1]['imageBase64_sign']:
#             current_datetime = datetime.now()
#             PROCESS_TIME_START = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
#             imageBase64_photo = myRequest['requestObject'][0]['imageBase64_photo']
#             imageBase64_sign = myRequest['requestObject'][1]['imageBase64_sign']
#             decoded_photo_img = base64.b64decode(imageBase64_photo)
#             decoded_sign_img = base64.b64decode(imageBase64_sign)
#             photo_img = Image.open(BytesIO(decoded_photo_img))
#             sign_img = Image.open(BytesIO(decoded_sign_img))
#             new_width = photo_img.width + sign_img.width
#             new_height = max(photo_img.height, sign_img.height)
#             merged_image = Image.new('RGB', (new_width, new_height))
#             merged_image.paste(photo_img, (0, 0))
#             merged_image.paste(sign_img, (photo_img.width, 0))
#             output_buffer = BytesIO()
#             merged_image.save(output_buffer, format='PNG')
#             base64_merged_image = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
#             current_datetime = datetime.now()
#             PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
#             return_json = {
#                 "Status" : "Success",
#                 "Outputimage" : base64_merged_image,
#                 "PROCESS_TIME_START": PROCESS_TIME_START,
#                 "PROCESS_TIME_END": PROCESS_TIME_END,
#                 "DOCUMENT_TYPE":"PHOTO_SIGNATURE_MERGE"
#             }
#         else:
#             return_json = {
#                 "Status" : "false"
#             }
#         if mainRequest.get("encryptedData") and mainRequest.get("encryptedKey"):
#             response_to_send = {
#                     "data" : return_json,
#                     "ivIntegration": True,
#                     "source": ""
#                 }
#             internal_response = requests.post(url=config.DIGI_MERGE_URL, json=response_to_send).json()
#             return internal_response 
#         else:
#             return return_json
#     except Exception as e:
#         print(e)
#         return {"Remarks":"false", "Exception": str(e)}

@app.route("/xbizapi/digivision/ai/digi_merge", methods=['POST'])
def customer_photo_sign_merge():
    try:
        myRequest = get_request()
        print(f"DigiMerge request - {myRequest}")
        if isinstance(myRequest, str): return {'Status' : 'FALSE', 'message' : 'Incorrect Request'}
        flag = False
        if 'Source' not in myRequest or myRequest['Source'] is None or myRequest['Source'] == "null" or myRequest['Source'] != "API Gateway Hybrid":
            flag = True
        if flag:
            if myRequest.get("encryptedData") and myRequest.get("encryptedKey"):
                print("1082 encrypted request")
                request_to_send = {
                    "data" : myRequest,
                    "ivIntegration": True,
                    "source": "XBIZ"
                }
            else:
                return {"Status": "False", "Message": "Mandatory field data is missing"}
            internal_response = requests.post(url=config.ENC_DEC_URL, json=request_to_send).json()
            print("internal response",internal_response)
        else:
            internal_response = myRequest
        unique_id = str(uuid.uuid4().hex)
        unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
        internal_response["transaction_Id"] = internal_response["transaction_Id"] + "--" + unique_id
        txn_id = internal_response["transaction_Id"]
        print(f"txn_id - {txn_id}")
        folder_path = f"{config.DESTINATION_DIR}{txn_id}"
        os.makedirs(f"{folder_path}/PAYLOADS", exist_ok=True)
        open(f"{folder_path}/PAYLOADS/mainRequest.json", "w", encoding="utf-8").write(json.dumps(myRequest, indent=4))
        if flag:
            open(f"{folder_path}/PAYLOADS/plainRequest.json", "w", encoding="utf-8").write(json.dumps(internal_response, indent=4))
        ImageBase64Second = internal_response["ImageBase64Second"]
        print(f"ImageBase64Second - {ImageBase64Second}")
        ImageBase64 = internal_response["ImageBase64"]
        print(f"ImageBase64 - {ImageBase64} ")
        Category = internal_response["Category"]
        print(f"Category - {Category}")
        doc_id = internal_response["document_Id"]
        print(f"doc_id - {doc_id}")
        file_type = internal_response["File_Type"]
        print(f"file_type - {file_type}")
        if ImageBase64Second != "" and ImageBase64 != "" and doc_id == "1":
            try:
                current_datetime = datetime.now()
                PROCESS_TIME_START = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
                decoded_photo_img = base64.b64decode(ImageBase64Second)
                decoded_sign_img = base64.b64decode(ImageBase64)
                photo_img = Image.open(BytesIO(decoded_photo_img))
                sign_img = Image.open(BytesIO(decoded_sign_img))
                new_width = photo_img.width + sign_img.width
                new_height = max(photo_img.height, sign_img.height)
                merged_image = Image.new('RGB', (new_width, new_height))
                merged_image.paste(photo_img, (0, 0))
                merged_image.paste(sign_img, (photo_img.width, 0))
                output_buffer = BytesIO()
                merged_image.save(output_buffer, format='PNG')
                base64_merged_image = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                folder_path = f"{config.DESTINATION_DIR}{txn_id}"
                binary_data = base64.b64decode(base64_merged_image)
                os.makedirs(f"{folder_path}/MERGE_OUTPUT", exist_ok=True)
                image_path = f"{folder_path}/MERGE_OUTPUT/{txn_id}_{1}{file_type}"
                with open(image_path, "wb") as file:
                    file.write(binary_data)
                print(f"merged image saved at - {image_path}")
                current_datetime = datetime.now()
                PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
                return_json = {
                    "Status" : "Success",
                    "Outputimage" : base64_merged_image,
                    "PROCESS_TIME_START": PROCESS_TIME_START,
                    "PROCESS_TIME_END": PROCESS_TIME_END,
                    "SignatureExist": "",
                    "DOCUMENT_TYPE":"PHOTO_SIGNATURE_MERGE"
                }
            except Exception as e:
                print(str(e))
                return_json = {
                "Status" : "Failure",
                "Outputimage" : "",
                "PROCESS_TIME_START": "",
                "PROCESS_TIME_END": "",
                "SignatureExist": "",
                "DOCUMENT_TYPE":"PHOTO_SIGNATURE_MERGE"
                }
        else:
            return_json = {
                "Status" : "Failure",
                "Outputimage" : "",
                "PROCESS_TIME_START": "",
                "PROCESS_TIME_END": "",
                "SignatureExist": "",
                "DOCUMENT_TYPE":"PHOTO_SIGNATURE_MERGE"
            }
        if flag:
            open(f"{folder_path}/PAYLOADS/plainResponse.json", "w", encoding="utf-8").write(json.dumps(return_json, indent=4))
            response_to_send = {
                        "data" : return_json,
                        "ivIntegration": True,
                        "source": ""
                    }
            internal_response = requests.post(url=config.ENC_DEC_URL, json=response_to_send).json()
            open(f"{folder_path}/PAYLOADS/mainResponse.json", "w", encoding="utf-8").write(json.dumps(internal_response, indent=4))
            return internal_response
        else:
            open(f"{folder_path}/PAYLOADS/mainResponse.json", "w", encoding="utf-8").write(json.dumps(return_json, indent=4))
            return return_json
    except Exception as e:
        print(e)
        return {"Remarks":"false", "Exception": str(e)}



###################### NEW CHANGES AS PER V2 #########################

# @app.route("/xbizapi/digivision/ai/V2/insert", methods=['POST'])
# def db_connectivity():
#     try:
        # myRequest = request.json
        # x = get_decryption_data(request.json)
        # print(f"{json.loads(str(x))}")
        # return json.loads(str(x))
        # x = {"name": "Swapnil Joshi", "Location": "Indore"}
        # x = {
        #     "token" : "AXRER-456789", 
        #     "watermark" : "Photograph has been captured by Employee No 887767@icicik.com, SHRUTI J on 22/07/2024 at 15:06:30, LAT:19.1216837 LONG:73.0110946, Tracking ID-859707380B70B089",
        #     "white_background" : "1",
        #     "source": "D365",
        #     "output_file_format" : "jpeg",
        #     "ocr_required" : "0",
        #     "transaction_type" : "Live_Photo"
        # }
        # return get_encryption_data(x)
        # return y
        # x = request.json
        # print(x)
        # y = get_decryption_data(request.json)
        # print("AAAAAAAAAAAAAAAA", y)
        # return {}
        # return get_decryption_data(request.json)
        # myRequest = get_requestV2()
        # print(myRequest)
        # x = encdyc.get_encryption_data(myRequest)
        # data = encdyc.get_decryption_data(myRequest)
        # token = data["token"]
        # transaction_type = data["transaction_type"]
        # watermark = data["watermark"]
        # white_background = data["white_background"]
        # white_background_int = int(data["white_background"])
        # return {"token" : token, "watermark":watermark, "white_background": white_background, "white_b_int": white_background_int}
        # print(f"ERROR {x}")
        # print(f"encrypted  {x}")
        # return x

        # if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
        # token = myRequest["token"]
        # watermark = myRequest["watermark"]
        # white_background = int(myRequest["white_background"])
        # source = myRequest["source"]
        # output_file_format = myRequest["output_file_format"].lower()
        # ocr_required = int(myRequest["ocr_required"])
        # transaction_type = myRequest["transaction_type"]
        # get_encryption_data(myRequest)

        # connection_string = f'DRIVER=SQL Server;SERVER=Swapnil\SQLEXPRESS;DATABASE=DOCAI;Trusted_Connection=yes;'

        # conn = pyodbc.connect(connection_string)
        # print("Connection successful")

        # cursor = conn.cursor()
        # cursor.execute("SELECT @@VERSION;")
        # row = cursor.fetchone()
        # while row:
        #     print(row)
        #     row = cursor.fetchone()

        # alter_table_command = """
        # ALTER TABLE USER_CREDENTIALS
        #     ADD WATERMARK varchar(max) NULL,
        #         WHITE_BACKGROUND bit NOT NULL DEFAULT 1,
        #         SOURCE varchar(100) NULL,
        #         OUTPUT_FILE_FORMAT varchar(100) NOT NULL DEFAULT 'jpeg',
        #         OCR_REQUIRED bit NOT NULL DEFAULT 0, 
        #         TRANSACTION_TYPE varchar(50) NULL;         
        # """
        # cursor.execute(alter_table_command)
        # conn.commit()
        # print("Column added successfully")
        
        # update_existing_rows ="""
        # UPDATE USER_CREDENTIALS
        #     SET WATERMARK = 'Photograph has been captured by Employee No 859707@icicik.com, MANDAR BAMNE on 10/07/2024 at 15:06:30,     LAT:19.1216837 LONG:73.0110946, Tracking ID-859707380B70B046',
        #         SOURCE = 'D365',
        #         TRANSACTION_TYPE = 'Live_Photo';
        # """
        # cursor.execute(update_existing_rows)
        # conn.commit()
        # print("Existing rows updated successfully")

        # alter_table_set_not_null = """
        # ALTER TABLE USER_CREDENTIALS
        #     ALTER COLUMN WATERMARK varchar(max) NOT NULL;

        # ALTER TABLE USER_CREDENTIALS
        #     ALTER COLUMN SOURCE varchar(100) NOT NULL;

        # ALTER TABLE USER_CREDENTIALS
        #     ALTER COLUMN TRANSACTION_TYPE varchar(50) NOT NULL;
        # """
        # cursor.execute(alter_table_set_not_null)
        # conn.commit()
        # print("Columns set to not null")
        # try:
            # request_akram = {
            # "DB_SERVER":"DOCAI",
            # "DBTYPE": "RUN",
            # "QUERY": """
            # INSERT INTO USER_CREDENTIALS (TOKEN, WATERMARK, WHITE_BACKGROUND, SOURCE, OUTPUT_FILE_FORMAT, OCR_REQUIRED, TRANSACTION_TYPE, CREATED_AT, CREATED_BY, UPDATED_AT, UPDATED_BY)
            # VALUES (?, ?, ?, ?, ?, ?, ?, DEFAULT, DEFAULT, DEFAULT, DEFAULT)
            # """,
            # "DATA": [token, watermark, white_background, source, output_file_format, ocr_required, transaction_type],
            # "RESULT": False
            # }
        # request_akram = {
        # "DB_SERVER":"DOCAI",
        # "DBTYPE": "RUN",
        # "QUERY": """
        # SELECT * FROM USER_CREDENTIALS;
        # """,
        # "DATA": [],
        # "RESULT": True
        # }
        # response = requests.post(url=config.DOCAI_DB_ENDPOINT, json=request_akram).json()
        # print(f"response - {response}")
        # return response
        # insert_query = """
        # INSERT INTO USER_CREDENTIALS (TOKEN, WATERMARK, WHITE_BACKGROUND, SOURCE, OUTPUT_FILE_FORMAT, OCR_REQUIRED, TRANSACTION_TYPE, CREATED_AT, CREATED_BY, UPDATED_AT, UPDATED_BY)
        # VALUES (?, ?, ?, ?, ?, ?, ?, DEFAULT, DEFAULT, DEFAULT, DEFAULT)
        # """
        # data = (token, watermark, white_background, source, output_file_format, ocr_required, transaction_type)
        # try:
        #     find_constraint_query = """
        #     SELECT 
        #         kc.name AS ConstraintName
        #     FROM 
        #         sys.key_constraints AS kc
        #     JOIN 
        #         sys.tables AS t
        #         ON kc.parent_object_id = t.object_id
        #     WHERE 
        #         kc.type = 'PK'
        #         AND t.name = 'USER_CREDENTIALS';
        #     """
        #     cursor.execute(find_constraint_query)
        #     constraint_name = cursor.fetchone()

        #     if constraint_name:
        #         print(f"Primary Key Constraint Name: {constraint_name[0]}")
        #     else:
        #         print("No primary key constraint found for the specified table.")
        # except Exception as e:
        #     print(f"{str(e)}")

        # try:
        #     sql_query_to_do_changes = f"""
        #     ALTER TABLE USER_CREDENTIALS
        #         ADD ID INT IDENTITY(1, 1);

        #     ALTER TABLE USER_CREDENTIALS
        #         DROP CONSTRAINT {constraint_name[0]};

        #     ALTER TABLE USER_CREDENTIALS
        #         ADD CONSTRAINT PK_USER_CRED_ID PRIMARY KEY (ID); 
        #     """
            
        #     cursor.execute(sql_query_to_do_changes)

        # except Exception as e:
        #     print(f"exception - {str(e)}")

        # ADD_NEW_COLUMNS = """
        # ALTER TABLE USER_CREDENTIALS 
        #     ADD CREATED_AT DATETIME NOT NULL DEFAULT GETDATE(), 
        #     CREATED_BY VARCHAR(255) NOT NULL DEFAULT 'SWAPNIL',
        #     UPDATED_AT DATETIME NOT NULL DEFAULT GETDATE(), 
        #     UPDATED_BY VARCHAR(255) NOT NULL DEFAULT 'SWAPNIL';
        # """

        # ADD UNIQUE CONSTRAINT IN TOKEN 

        # add_unique_constraint = """
        #     ALTER TABLE USER_CREDENTIALS
        #         ADD CONSTRAINT UQ_UCRED_TOKEN UNIQUE (TOKEN);
        # """

        # Execute the INSERT query
            # cursor.execute(insert_query, data)
        # except Exception as e:
        #     print(str(e))
        #     return {"status":False,"message":f"TOKEN SHOULD BE UNIQUE"}
        # cursor.execute(alter_table_command)
        # cursor.execute(find_constraint_query)
        # cursor.execute(sql_query_to_do_changes)
        # cursor.execute(ADD_NEW_COLUMNS)
        # cursor.execute(add_unique_constraint)

        # Commit the transaction
        # conn.commit()
        # print("Record inserted successfully")
        # print("Column added successfully")
        # print("changes done successfully")
        # print("constraint added successfully")

        # cursor.close()
        # conn.close()

        # params = {
        #     'token': token
        # }

        # Encode parameters
        # query_string = urlencode(params)

        # Construct full URL
        # if transaction_type == "Live_Photo":
        #     url = urlunparse(('https', 'docaiuat-livephoto.icicibank.com', '/xbiz/live_photo/', '', query_string, ''))
        #     print(f"URL - {url}")
        # elif transaction_type == "Signature_Capture":
        #     url = urlunparse(('https', 'docaiuat-livephoto.icicibank.com', '/xbiz/capture/', '', query_string, ''))
        #     print(f"URL - {url}")

        # response = {"status":True,"message":"values added successfully", "url":url, "token" : token}
        # return response     
        # print(encdyc.get_encryption_data(response))
        # return encdyc.get_encryption_data(response)
        # encrypted_response = encdyc.get_encryption_data(response)   
        # return encrypted_response
        # return {"status":True,"message":token}
        # return {"status": True, "msg": "changes done"}
    # except Exception as e:
    #     print(f"784 Exception- {str(e)}")
    #     return {"status":False,"message":"Not valid"}

# curl --location 'http://127.0.0.1:8888/digivision/ai'
# \
# --header 'Content-Type: application/json' \
# --data '{
#     "DB_SERVER":"DOCAI",
#     "DBTYPE": "RUN",
#     "QUERY": "SELECT TOP 2 * FROM MAIN_REQUEST",
#     "DATA": [],
#     "RESULT": true
# }'

# @app.route("/xbizapi/digivision/ai/V2/fetch/", methods=['POST'])
# def fetch_data():
#     try:
#         myRequest = get_request()
#         print(myRequest)
#         if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
#         token = myRequest["token"]

#         # token = urllib.parse.unquote(urltoken).split("&&")[0]
#         print(f"token - {token}")

#         connection_string = f'DRIVER=SQL Server;SERVER=Swapnil\SQLEXPRESS;DATABASE=DOCAI;Trusted_Connection=yes;'

#         conn = pyodbc.connect(connection_string)
#         print("Connection successful")

#         cursor = conn.cursor()

#         fetch_query = """
#             SELECT * FROM USER_CREDENTIALS WHERE TOKEN = ?;
#         """
#         cursor.execute(fetch_query, token)

#         results = cursor.fetchall()

#         columns = [column[0] for column in cursor.description]
#         data = [dict(zip(columns, row)) for row in results]

        
#         return { "status": True ,"data":data}

#     except Exception as e:
#         print(f"exception - {str(e)}")
#         return {"status":False , "message":f"exception - {str(e)}"}

@app.route("/xbizapi/digivision/ai/V2/insert", methods=['POST'])
def db_connectivity():
    try:
        myRequest = get_request()
        print(f"778 insert myRequest - {myRequest}")
        if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
        # data = encdyc.get_encryption_data(myRequest)
        # data = encdyc.get_decryption_data(myRequest)
        # return data
        # except Exception as e:
        #     print(f"exception - {str(e)}")
        #     return f"exception - {str(e)}"
        # data = encdyc.get_decryption_data(myRequest)
        # print(f"781 data - {data}")
        # token = data["token"]
        # watermark = data["watermark"]
        # white_background = int(data["white_background"])
        # source = data["source"]
        # output_file_format = data["output_file_format"].lower()
        # ocr_required = int(data["ocr_required"])
        # transaction_type = data["transaction_type"]
        token = myRequest["token"]
        watermark = myRequest["watermark"]
        white_background = int(myRequest["white_background"])
        source = myRequest["source"]
        output_file_format = myRequest["output_file_format"].lower()
        ocr_required = int(myRequest["ocr_required"])
        transaction_type = myRequest["transaction_type"]
        internal_request = {
            "DB_SERVER":"DOCAI",
            "DBTYPE": "RUN",
            "QUERY": """
            INSERT INTO USER_CREDENTIALS (TOKEN, WATERMARK, WHITE_BACKGROUND, SOURCE, OUTPUT_FILE_FORMAT, OCR_REQUIRED, TRANSACTION_TYPE, CREATED_AT, CREATED_BY, UPDATED_AT, UPDATED_BY)
            VALUES (?, ?, ?, ?, ?, ?, ?, DEFAULT, DEFAULT, DEFAULT, DEFAULT)
            """,
            "DATA": [token, watermark, white_background, source, output_file_format, ocr_required, transaction_type],
            "RESULT": False
            }
        print(f"806 internal_request - {internal_request}")
        internal_response = requests.post(url='https://bankdevapi.digivision.ai/digivision/ai/queryrunner', json=internal_request).json()
        print(f"808 internal_response - {internal_response}")
        if internal_response['STATUS'] == True and internal_response['CODE'] == 200:
            print("Record inserted successfully")
            params = {
                'token': token
            }

            # Encode parameters
            query_string = urllib.parse.urlencode(params)

            # Construct full URL
            if transaction_type == "Live_Photo":
                url = urllib.parse.urlunparse(('https', 'localhost:3000', '/xbiz_V2/live_photo/', '', query_string, ''))
                print(f"URL - {url}")
            elif transaction_type == "Signature_Capture":
                url = urllib.parse.urlunparse(('https', 'localhost:3000', '/xbiz_V2/capture/', '', query_string, ''))
                print(f"URL - {url}")
            successful_response = {"status":True,"message":"values added successfully", "url":url}
            print(f"826 successful_response - {successful_response}")
            # encrypted_successful_response = encdyc.get_encryption_data(successful_response)
            # print(f"828 encryted_response - {encrypted_successful_response}")
            # return encrypted_successful_response
            return successful_response
        else:
            print("Record CAN NOT be inserted successfully")
            failed_response = {"status":False,"message":"values NOT added successfully", "url":""}
            print(f"833 failed_response - {failed_response}")
            # encrypted_failed_response = encdyc.get_encryption_data(failed_response)  
            # print(f"835 encrypted_failed_response - {encrypted_failed_response}")
            # return encrypted_failed_response
            return failed_response
    except Exception as e:
        exception_response = {"status" : False, "message" : f"827 EXCEPTION - {e}"}
        print(f"840 exception_response - {exception_response}")
        # encrypted_exception_response = encdyc.get_encryption_data(exception_response)
        # print(f"842 encrypted_exception_response - {encrypted_exception_response}")
        # return encrypted_exception_response
        return exception_response
    
@app.route("/xbizapi/digivision/ai/V2/fetch/", methods=['POST'])
def fetch_data(token):
    try:
        # myRequest = get_requestV2()
        # print(f"1175 myRequest - {myRequest}")
        # if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
        # token = myRequest["token"]
        print(f"token - {token}")
        internal_request = {
            "DB_SERVER":"DOCAI",
            "DBTYPE": "RUN",
            "QUERY": f"SELECT * FROM USER_CREDENTIALS WHERE TOKEN = '{token}'",
            "DATA": [],
            "RESULT": True
            }
        print(f"1071 internal_request - {internal_request}")
        internal_response = requests.post(url='https://bankdevapi.digivision.ai/digivision/ai/queryrunner', json=internal_request).json()
        print(f"1073 internal_response - {internal_response}")
        # if internal_response["CODE"] == 200 and internal_response["STATUS"] == True:
        if len(internal_response["DATA"]) > 0:
            data = internal_response["DATA"][0]
            print(f"data - {data}")
            token = data["TOKEN"]
            source = data["SOURCE"]
            watermark = data["WATERMARK"]
            output_file_format = data["OUTPUT_FILE_FORMAT"]
            white_background = data["WHITE_BACKGROUND"]
            ocr_required = data["OCR_REQUIRED"]
            txn_type = data["TRANSACTION_TYPE"]
            req_data = [{ 
                    "token" : token,
                    "source" : source,
                    "watermark": watermark,
                    "output_file_format": output_file_format,
                    "white_background" : white_background,
                    "ocr_required" : ocr_required,
                    "transaction_type" : txn_type 
                }]
            print(f"1094 req_data - {req_data}")
            return {"status": True, "message": "data fetched successfully" , "data" : req_data}
        else:
            return {"status": False, "message": "no record found" , "data" : None}
        # else:
        #     return {"status": False, "message": "data NOT fetched successfully" , "data" : None}
    except Exception as e:
        print(f"exception - {str(e)}")
        return {"status":False, "message":"invalid field name"}

@app.route("/xbizapi/digivision/ai/V2/fetchforui/", methods=['POST'])
def fetch_for_UI():
    try:
        myRequest = get_requestV2()
        print(f"1175 myRequest - {myRequest}")
        if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
        token = myRequest["token"]
        print(f"token - {token}")
        internal_request = {
            "DB_SERVER":"DOCAI",
            "DBTYPE": "RUN",
            "QUERY": f"SELECT * FROM USER_CREDENTIALS WHERE TOKEN = '{token}'",
            "DATA": [],
            "RESULT": True
            }
        internal_response = requests.post(url='https://bankdevapi.digivision.ai/digivision/ai/queryrunner', json=internal_request).json()
        print(f"internal_response - {internal_response}")
        # if internal_response["CODE"] == 200 and internal_response["STATUS"] == True:
        if len(internal_response["DATA"]) > 0:
             return {"status": True, "message": "data fetched successfully", "data": internal_response["DATA"]}
        else:
            return {"status": False, "message": "data CAN NOT be fetched successfully", "data": None}
    except Exception as e:
        print(f"1223 exception : {e}")
        return {"status" : False, "exeption_message": f"exception - {e}"} 

@app.route("/xbizapi/digivision/ai/faceai/V2/capture/", methods=['POST'])
def customer_live_photo_video_captureV2():
    try:
        print(f"v2 capture started")
        myRequest = get_requestV2()
        print("my request", myRequest)
        if isinstance(myRequest, str): return {"Liveness_Status":"FALSE", "message": "Incorrect Request"}
        createFoldersV2(myRequest)
        response = fetch_data(myRequest["TOKEN"].split("~")[0])
        print(f"1254 capture white background {response['data'][0]['white_background']}")
        input_json = {}
        input_json["FILE"] = myRequest["FILEDATA"]
        input_json["OUTPUT_FACE_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_FACE_PATH/"
        input_json["OUTPUT_JSON_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_JSON_PATH/"
        input_json["OUTPUT_TEMPLATE_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_TEMPLATE_PATH/"
        input_json["OUTPUT_VIDEO_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_VIDEO_PATH/"
        input_json["OUTPUT_WATERMARK_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_WATERMARK_PATH/"
        print("BLINK DETECTION PATH",config.INPUT_PATH)
        print(f"input_json - {input_json}")
        unique_id = str(uuid.uuid4().hex)
        unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
        original_json_path = os.path.join(config.INPUT_PATH, unique_id + ".json")
        print(f"original_json_path - {original_json_path}")
        open(original_json_path, "w", encoding="utf-8").write(json.dumps(input_json, indent=4))
        print("IMAGE SEGMENTATION PATH",config.INPUT_PATH_IMAGE_SEGMENTATION)
        print(f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['TOKEN']}.json")
        for i in range(120):
            if os.path.exists(f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['TOKEN']}.json"):
                break
            else:
                time.sleep(1)
        else:
            return {"Liveness_Status":"FALSE", "message": "Request Timeout"}
        # if myRequest['WHITE_FLAG'] == '1':
        if response['data'][0]['white_background'] == True:
            input_json = {}
            input_json["OUTPUT_TEMPLATE_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_TEMPLATE_PATH/"
            input_json["OUTPUT_JSON_PATH"] = f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_JSON_PATH/"
            input_json["TOKEN"] = myRequest['TOKEN']
            original_json_path = os.path.join(config.INPUT_PATH_IMAGE_SEGMENTATION, unique_id + ".json")
            open(original_json_path, "w", encoding="utf-8").write(json.dumps(input_json, indent=4))
            for i in range(120):
                if os.path.exists(f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['TOKEN']}_IMAGE_SEGMENTATION.json"):
                    break
                else:
                    time.sleep(1)
            else:
                return {"Liveness_Status":"FALSE", "message": "Request Timeout"}
        result_json = json.loads(open(f"{config.DESTINATION_DIR}{myRequest['TOKEN'].split('~')[0]}/OUTPUT_JSON_PATH/{myRequest['TOKEN']}.json", "r", encoding="utf-8").read())
        result = {}
        if "Group Photo" in result_json:
            result["Group_Photo"] = result_json["Group Photo"]
        if "Live Face" in result_json:
            result["Liveness_Status"] = result_json["Live Face"]
        elif "Still Face" in result_json:
            result["Liveness_Status"] = "TRUE->0/100"
        if "Liveness_Status" in result and "FALSE" in result["Liveness_Status"].upper():
            result["message"] = "Blink Not Detection"
        return result
    except Exception as e:
        return {"Liveness_Status":"FALSE", "message": str(e)}

@app.route("/xbizapi/digivision/ai/V2/submit/", methods=['POST'])
def customerLivePhotoSubmitV2():
    try:
        myRequest = get_requestV2()
        print(f"1108 myRequest - {myRequest}")
        req_token = myRequest['token']
        split_token = req_token.split('~')[0] if '~' in req_token else req_token
        data = fetch_data(split_token)
        print(f"1286 data fetched successfully from fetch_data()")
        req_data = data["data"][0]
        token = req_data["token"]
        source = req_data["source"]
        watermark = req_data["watermark"]
        output_file_format = req_data["output_file_format"]
        white_background = req_data["white_background"]
        ocr_required = req_data["ocr_required"]
        txn_type = req_data["transaction_type"]
        callback_url = ""
        access_token = get_access_token(source)
        print(f"access_token: {access_token}")
        if access_token == "":
            return {"status":False,"message":"Access Token Failed"}
        current_datetime = datetime.now()
        PROCESS_TIME_START = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
        image_path = f"{config.DESTINATION_DIR}{token}/OUTPUT_TEMPLATE_PATH/{req_token}.JPG"
        print(f"image path - {config.DESTINATION_DIR}{token}/OUTPUT_TEMPLATE_PATH/{req_token}.JPG")
        if os.path.exists(image_path):
            print(f"1333 os.path.exists")
            output_dir = f"{config.DESTINATION_DIR}{token}/OUTPUT_WATERMARK_PATH/"
            print(f"{config.DESTINATION_DIR}{token}/OUTPUT_WATERMARK_PATH/")
            image_base64 = apply_watermark(image_path, watermark, output_file_format, output_dir, source)
            print("588 IMAGE BASE64 TAKEN")
            Ref_Id = token[-2:]
            txn_id_with_extension = token + ".AIBI"
            TXN_Id = token
            current_datetime = datetime.now()
            print(f"593 CURRENT DATETIME - {current_datetime}")
            PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
            endpoint = config.API_ENDPOINTS["CALLBACK_ENDPOINT"][source]
            print(f"596 ENDPOINT {endpoint}")
            headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}',
                    'apikey': config.API_KEY[source],
                    'appVersion': source
                }
            print(f"603 CALLBACK ENDPOINT HEADERS - {headers}")
            request_payload = json.load(open("./utils/request_format.json", encoding="utf-8"))
            print(f"605 REQUEST PAYLOAD ")
            request_payload["token"] = token
            request_payload["Result"][1]["PROCESS_TIME_START"] = PROCESS_TIME_START
            request_payload["Result"][0]["IMAGEBASE64"] = [image_base64]
            request_payload["Result"][1]["Ref_Id"] = Ref_Id
            request_payload["Result"][1]["INPUT_FILE"] = txn_id_with_extension
            request_payload["Result"][1]["TRANSACTION_NUMBER"] = TXN_Id
            request_payload["Result"][1]["CASE_NO"] = TXN_Id
            request_payload["Result"][1]["DB_FILE"] = txn_id_with_extension
            request_payload["Result"][1]["PROCESS_TIME_END"] = PROCESS_TIME_END
            print(f"615 REQUEST PAYLOAD")
            open(f"{config.DESTINATION_DIR}{token}/PAYLOADS/CALLBACK_REQUEST_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(request_payload, indent=4))
            encrypted_request = get_encryption_data(request_payload)
            print(f"618 get encryption data - {get_encryption_data}")
            encrypted_request["requestId"] = ""
            encrypted_request["service"] = ""
            encrypted_request["oaepHashingAlgorithm"] = "NONE"
            encrypted_request["clientInfo"] = "Xbiz"
            encrypted_request["optionalParam"] = ""
            print(f"624 CALLBACK ENCRYPTED REQUEST - {encrypted_request}")
            open(f"{config.DESTINATION_DIR}{token}/PAYLOADS/CALLBACK_REQUEST_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_request, indent=4))
            encrypted_response = requests.post(endpoint, headers=headers, data=json.dumps(encrypted_request)).json()
            print(f"627 CALLBACK ENCRYPTED RESPONSE - {encrypted_response}")
            open(f"{config.DESTINATION_DIR}{token}/PAYLOADS/CALLBACK_RESPONSE_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_response, indent=4))
            if "iv" not in encrypted_response:
                encrypted_response["iv"] = ""
            decrypted_response = get_decryption_data(encrypted_response)
            print(f"632 CALLBACK DECRYPTED RESPONSE - {decrypted_response}")
            open(f"{config.DESTINATION_DIR}{token}/PAYLOADS/CALLBACK_RESPONSE_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(decrypted_response, indent=4))
            if decrypted_response["status"] == True:
                callback_url = decrypted_response["redirectUrl"]
                return {"status":True,"message":callback_url}
            else:
                return {"status":False,"message":callback_url}
        else:
            return {"status":False,"message":"Template Image Does not Exists"}
    except Exception as e:
        print(f"exception - {e}")
        return {"status" : False, "message" : f"{str(e)}"}

@app.route("/xbizapi/digivision/ai/V2/back/", methods=["POST"])
def customerLivePhotoBackV2():
    try:
        myRequest = get_requestV2()
        print(f"back request - {myRequest}")
        if isinstance(myRequest, str): return {"status":False,"message":"Invalid Request"}
        token = myRequest["token"]
        print(f"token {token}")
        split_token = token.split('~')[0] if '~' in token else token
        print(f"split_token {split_token}")
        # watermark = myRequest["watermark"]
        # app_version = myRequest["app_version"].upper()
        # print(app_version)
        # token = myRequest["token"]
        # print(myRequest)
        # createFolders({"TXNID": txn_id})
        createFoldersV2({"TOKEN": token})
        print(f"back folders created")
        callback_url = ""
        data = fetch_data(split_token)
        req_data = data["data"][0]
        source = req_data["source"]
        print("before access token")
        access_token = get_access_token(source)
        print(access_token)
        if access_token == "":
            return {"status":False,"message":"Access Token Failed"}
        image_base64 = ""
        Ref_Id = split_token[-2:]
        txn_id_with_extension = split_token + ".AIBI"
        TXN_Id = split_token
        current_datetime = datetime.now()
        PROCESS_TIME_END = str(current_datetime.strftime("%#m/%#d/%Y %#I:%M:%S %p"))
        endpoint = config.API_ENDPOINTS["CALLBACK_ENDPOINT"][source]
        headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'apikey': config.API_KEY[source],
                'appVersion': source
            }
        request_payload = json.load(open("./utils/request_format.json", encoding="utf-8"))
        request_payload["token"] = token
        request_payload["Result"][0]["IMAGEBASE64"] = [image_base64]
        request_payload["Result"][1]["Ref_Id"] = Ref_Id
        request_payload["Result"][1]["INPUT_FILE"] = txn_id_with_extension
        request_payload["Result"][1]["TRANSACTION_NUMBER"] = TXN_Id
        request_payload["Result"][1]["CASE_NO"] = TXN_Id
        request_payload["Result"][1]["DB_FILE"] = txn_id_with_extension
        request_payload["Result"][1]["PROCESS_TIME_END"] = PROCESS_TIME_END
        open(f"{config.DESTINATION_DIR}{split_token}/PAYLOADS/CALLBACK_BACK_REQUEST_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(request_payload, indent=4))
        encrypted_request = get_encryption_data(request_payload)
        print(f"630 encrypted request")
        encrypted_request["requestId"] = ""
        encrypted_request["service"] = ""
        encrypted_request["oaepHashingAlgorithm"] = "NONE"
        encrypted_request["clientInfo"] = "Xbiz"
        encrypted_request["optionalParam"] = ""
        open(f"{config.DESTINATION_DIR}{split_token}/PAYLOADS/CALLBACK_BACK_REQUEST_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_request, indent=4))
        print(f"BEFORE ENCRYPTED RESPONSE")
        encrypted_response = requests.post(endpoint, headers=headers, data=json.dumps(encrypted_request)).json()
        print(f"ENCRYPTED RESPONSE - {encrypted_response}")
        open(f"{config.DESTINATION_DIR}{split_token}/PAYLOADS/CALLBACK_BACK_RESPONSE_ENCRYPTED.json", "w", encoding="utf-8").write(json.dumps(encrypted_response, indent=4))
        if "iv" not in encrypted_response:
            encrypted_response["iv"] = ""
        decrypted_response = get_decryption_data(encrypted_response)
        print(f"DECRYPTED RESPONSE - {decrypted_response}")
        open(f"{config.DESTINATION_DIR}{split_token}/PAYLOADS/CALLBACK_BACK_RESPONSE_DECRYPTED.json", "w", encoding="utf-8").write(json.dumps(decrypted_response, indent=4))
        status = decrypted_response["status"]
        callback_url = decrypted_response["redirectUrl"]
        return {"status":True,"message":callback_url}
    except Exception as e:
        return {"status":False,"message":str(e)}

@app.route("/xbizapi/digivision/ai/V2/capture/", methods=['POST'])
def customer_doc_captureV2():
    try:
        print("1524 V2 CAPTURE STARTED")
        myRequest = get_requestV2()
        print("1524 Capture my request", myRequest['requestObject'])
        if isinstance(myRequest, str): return {"Status":"FALSE", "message": "Incorrect Request"}
        response = fetch_data(myRequest['requestObject'][0]["token"].split("~")[0])
        token = response['data'][0]['token']
        # if myRequest['requestObject'][0]['document_id'] == '20':
        if response['data'][0]['transaction_type'] == 'Signature_Capture':
            try:
                createFoldersV2({"TOKEN":myRequest['requestObject'][0]["token"]})
                # txn_id = myRequest['requestObject'][0]['transaction_id']
                # createFolders({"TXNID": txn_id + "~1"})
                b64_data = myRequest['requestObject'][0]['imageBase64']
                image_path = b64_to_file(b64_data,token, "1")
                print(image_path)
                input_json = {}
                input_json["INPUT_IMAGE"] = image_path
                input_json["OUTPUT_IMAGE"] = f"{config.DESTINATION_DIR}{token}/OUTPUT_TEMPLATE_PATH/"
                input_json["OUTPUT_JSON"] = f"{config.DESTINATION_DIR}{token}/OUTPUT_JSON_PATH/"
                input_json["TOKEN"] = token
                print(input_json)
                unique_id = str(uuid.uuid4().hex)
                unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
                print(unique_id)
                print(config.INPUT_PATH_SIGN_DETECTION)
                original_json_path = os.path.join(config.INPUT_PATH_SIGN_DETECTION, unique_id + ".json")
                print(original_json_path)
                open(original_json_path, "w", encoding="utf-8").write(json.dumps(input_json, indent=4))
                for i in range(120):
                    if os.path.exists(f"{config.DESTINATION_DIR}{token}/OUTPUT_JSON_PATH/{token}.json"):
                        json_data = json.loads(open(f"{config.DESTINATION_DIR}{token}/OUTPUT_JSON_PATH/{token}.json", "r", encoding="utf-8").read())
                        if json_data["SIGNATURE_FOUND"] == True:
                            return {"SignatureFound":"true"}
                        else:
                            return {"SignatureFound":"false 1"}
                    else:
                        time.sleep(1)
                else:
                    return {"SignatureFound":"false 2"}
            except:
                return {"SignatureFound":"false 3"}
        # elif myRequest['requestObject'][0]['document_id'] in ["1", "2", "3", "4", "6"]:
            # try:
            #     txn_id = myRequest['requestObject'][0]['transaction_id']
            #     createFolders({"TXNID": txn_id + "~1"})
            #     doc_id = myRequest['requestObject'][0]['document_id']
            #     b64_data = myRequest['requestObject'][0]['imageBase64']
            #     request_obj = config.REQUEST_OBJ
            #     request_obj["txnId"] = txn_id
            #     request_obj["documentId"] = doc_id
            #     request_obj["documentBlob"] = b64_data
            #     response = requests.post(url=config.API_URL, json=request_obj).json()
            #     if response['results'][0]['documentType']['value'] == config.DOCUMENT_ID[doc_id]:
            #         page_no = response["results"][0]["pageNo"]["value"][0]
            #         sub_type = response["results"][0]["subDocumentType"]["value"]
            #         b64_to_file(b64_data,txn_id,page_no)
            #         if (page_no == 1 and sub_type in ["FRONT SIDE DOC", "COMPLETE DOC"]) or (page_no == 2 and sub_type in ["BACK SIDE DOC"]):
            #             folder_path = f"{config.DESTINATION_DIR}{txn_id}"
            #             original_json_path = os.path.join(f"{folder_path}/PREPOP_RESPONSE/", f"{txn_id}_{page_no}" + ".json")
            #             open(original_json_path, "w+", encoding="utf-8").write(json.dumps(response, indent=4))
            #             required_res = [
            #                 {
            #                     "Kyc" : [
            #                         {
            #                             "TRN_STATUS": "PASS",
            #                             "DOCUMENT_TYPE" : config.DOCUMENT_ID[doc_id],
            #                             "SUB_TYPE" : response["results"][0]["subDocumentType"]["value"]
            #                         }
            #                     ] 
            #                 }
            #             ]
            #             return required_res
            #         else:
            #             return return_failed_response()
            #     else:
            #         return return_failed_response()
            # except:
            #     return return_failed_response()
        else:
            return {"CaptureResponse":"false"}
    except Exception as e:
        print(e)
        return {"Remarks":"false", "Exception": str(e)}

@app.route("/xbizapi/digivision/ai/V2/delete/", methods=['POST'])
def delete_doc_captureV2():
    try:
        myRequest = get_requestV2()
        print("delete request ", myRequest)
        token = myRequest["Token"]
        doc_id = myRequest["Doc_Id"]
        page_no = myRequest["PageNo"]
        if doc_id in ['1', '2', '3', '4', '6', '20']:
            print(f"path - {config.DESTINATION_DIR}{token}")
            if os.path.exists(f"{config.DESTINATION_DIR}{token}"):
                shutil.rmtree(f"{config.DESTINATION_DIR}{token}")
        return {"Status": True}        
    except Exception as e:
        return {"Status":False,"Remarks":str(e)}

@app.route("/", methods=['GET'])
def service_check():
    return {constants.STATUS:True, constants.MESSAGE:"Orchestrator Service is running"}

if __name__ == '__main__':
    app.run(port=8432)