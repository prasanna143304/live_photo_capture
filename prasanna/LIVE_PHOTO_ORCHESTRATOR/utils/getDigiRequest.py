from flask import request
import json, secrets, hashlib, uuid, base64, threading, string
from google.cloud import storage
from utils_orchestrator import config, constants
import re, shutil, os,requests
from io import BytesIO
from PIL import Image, ImageSequence, ImageFile
import numpy as np
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from base64 import b64decode
from Crypto.PublicKey import RSA
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

doc_master_json = json.load(open(config.folder_source + "utils_orchestrator/doc_master.json"))
request_validator = json.load(open(config.folder_source + "utils_orchestrator/request_pattern.json"))
prepop_detect_keylist = json.load(open(config.folder_source + "detectionMatrix/prepopDetection.json"))
req_validation_json = json.load(open(config.folder_source + "utils_orchestrator/request_validation.json"))
verification_master = json.load(open(config.folder_source + "utils_orchestrator/xbiz_verification.json"))
EXTRA_PREPOP_KEYS = request_validator["EXTRA_PREPOP_KEYS"]
OCR_GENERIC_MASTER = verification_master["GENERIC_OCR_CONFIG"][config.CLIENT_NAME]
addon = {"confidenceScore": "0","matchingScore": "0","coordinate": {}}
image_extensions = ['.JPG', '.JPEG', '.PNG', '.GIF', '.BMP', '.SVG', '.WEBP', '.TIFF', '.TIF', '.ICO', '.PDF', '.JFIF', '.PSD', '.EPS', '.AI', '.INDD', '.RAW', '.CR2', '.NEF', '.SRW', '.DNG', '.ARW', '.ORF', '.RW2', '.PEF', '.XCF']
audio_extensions = ['.WAV', '.MP3', '.MP4', '.WEBM', '.MKV', '.AVI', '.MOV', '.AAC', 'M4A']


def docai_db(data, dbtype, current_stage, db_dict):
    try:
        if not isinstance(data, dict):
            data = {"DATA": data}
        db_data = data.copy()
        db_data.update({"DBTYPE":dbtype, "STAGE":current_stage, "DB_SERVER": config.DB_SERVER}) 
        db_data.update(db_dict)
        requests.post(config.DOCAI_DB_ENDPOINT, json=db_data).json()
    except Exception as e:
        print(f"DATABASE ERROR : {e}")

def docai_database(data, dbtype, current_stage, db_dict):
    if str(config.DB_SERVER).upper() == "NONE": return ''
    if dbtype == "AI_RESPONSE" and config.DB_SERVER == "ORACLE": return ''
    thread = threading.Thread(target=docai_db, args=(data, dbtype, current_stage, db_dict))
    thread.start()


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
    
    
def get_pdf_extension_type(decoded_data):
  try:
    with BytesIO(decoded_data) as pdf_file:
      try:
        pdf_version = pdf_file.read(10).decode("ascii").split("%PDF-")[1].split()[0]
      except Exception as e:
        pdf_version = None
    print('doctype .pdf and pdf_version: ', pdf_version)
    return ".pdf"
  except Exception as e:
    print(f"Error decoding PDF: {e}")
    return ""

def get_extension_type(base64_data, pdfStatus=False):
    try:
        decoded_data = base64.b64decode(base64_data)
        if decoded_data.startswith(b'\xFF\xD8'):return ".jpeg"
        elif decoded_data.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):return ".png"
        elif decoded_data.startswith(b'\x49\x49\x2A\x00') or decoded_data.startswith(b'\x4D\x4D\x00\x2A'):return ".tiff"
        elif decoded_data.startswith(b"%PDF-") and pdfStatus: return get_pdf_extension_type(decoded_data)
        else:return ""
    except:return ""
        

def check_base64(s):
    try:
        decoded = base64.b64decode(s.encode('utf-8'))
        return True
    except Exception:return False

def save_base64_to_file(base64_string, output_file):
    with open(output_file, 'wb') as file:
        decoded_bytes = base64.b64decode(base64_string)
        file.write(decoded_bytes)
    return output_file

def tif_to_first_image_base64(tiff_filename, jpeg_filename):
    with Image.open(tiff_filename) as tif:
        for i, page in enumerate(ImageSequence.Iterator(tif)):
            tif_image = np.array(page)
            Image.fromarray(tif_image).convert('RGB').save(jpeg_filename, 'JPEG')
            return True


def save_file(form, req_type):
    print(f"REQUEST FORM TYPE : {req_type}")
    no_need = form["DOCUMENT"]
    if not os.path.exists(config.path + form["TXN_ID"]): os.makedirs(config.path + form["TXN_ID"])
    icore_file_name = f"{config.path}{form['TXN_ID']}/ICORE_UPLOAD_FILE"
    if config.ORG_FILENAME:
        docName = form["documentName"] if "documentName" in form and len(form["documentName"]) > 3 else form["TXN_ID"]
        docName = os.path.splitext(os.path.basename(docName))[0]
    else:
        docName = form["TXN_ID"]
    file_name = config.path + form["TXN_ID"] + "/" + docName + form["DOC_TYPE"]
    if req_type == "multipart/form-data":
        if 'documentBlob' in request.files:
            file = request.files['documentBlob']
            if file.filename != '':
                form["DOC_TYPE"] = os.path.splitext(file.filename)[1].upper()
                form["docType"] = form["DOC_TYPE"]
                if config.ORG_FILENAME:
                    file_name = config.path + form["TXN_ID"] + "/" + os.path.splitext(os.path.basename(file.filename))[0] + form["DOC_TYPE"]
                else:
                    file_name = config.path + form["TXN_ID"] + "/" + form["TXN_ID"] + form["DOC_TYPE"]
                file.save(file_name)
                path_name = file_name.replace(config.path, config.source)
                form.update({"DOCUMENT": path_name, "documentBlob" : path_name})
                if len(form["documentName"]) == 0:
                    form["documentName"] = os.path.basename(path_name)
        elif 'DOCUMENT' in request.files:
            file = request.files['DOCUMENT']
            if file.filename != '':
                file.save(file_name)
                form["DOCUMENT"] = file_name.replace(config.path, config.source)
        if "icoreImage" in request.files:
            file = request.files['icoreImage']
            if file.filename != '':
                icore_file_name = f"{config.path}{form['TXN_ID']}/ICORE_UPLOAD_FILE"
                os.makedirs(icore_file_name, exist_ok=True)
                icore_doc_type = os.path.splitext(file.filename)[1].lower()
                icore_file_name = f"{icore_file_name}/icore{icore_doc_type}"
                if icore_doc_type in [".jpeg", ".png", ".tif", ".tiff", ".jpg"]:
                    file.save(icore_file_name)
                    form["icoreImage"] = icore_file_name
                else:
                    form["icoreImage"] = ""
        if "matchingBlob" in request.files:
            file = request.files['matchingBlob']
            if file.filename != '':
                matching_blob_file_name = f"{config.path}{form['TXN_ID']}/MATCH_BLOB"
                os.makedirs(matching_blob_file_name, exist_ok=True)
                icore_doc_type = os.path.splitext(file.filename)[1].lower()
                matching_blob_file_name = f"{matching_blob_file_name}/image.jpeg"
                if icore_doc_type in [".jpeg", ".png", ".tif", ".tiff", ".jpg"]:
                    file.save(matching_blob_file_name)
                    form["matchingBlob"] = matching_blob_file_name
                else:
                    form["matchingBlob"] = ""
                                
    elif req_type == "application/json":
        try:
            if form["source"] not in ["AUDIOAI_TTS"]:
                status = check_base64(form["DOCUMENT"])
                if not status: return "8000"
                file = base64.b64decode(form["DOCUMENT"])
                with open(file_name, 'wb') as file_writer:
                    file_writer.write(file)
                    form["DOCUMENT"] = file_name.replace(config.path, config.source)
            if "icoreImage" in form:
                icore_file_name = f"{config.path}{form['TXN_ID']}/ICORE_UPLOAD_FILE"
                os.makedirs(icore_file_name, exist_ok=True)
                file_extension = get_extension_type(form["icoreImage"])
                icore_file_name = icore_file_name + "/icore" + file_extension
                if file_extension in [".jpeg", ".png", ".tif", ".tiff", ".jpg"]:
                    save_base64_to_file(form["icoreImage"], icore_file_name)
                    form["icoreImage"] = icore_file_name
                else:
                    form["icoreImage"] = ""
            if "customerPhotoBlob" in form:
                icore_file_name = f"{config.path}{form['TXN_ID']}/CUSTOMER_PHOTO"
                os.makedirs(icore_file_name, exist_ok=True)
                file_extension = get_extension_type(form["customerPhotoBlob"])
                icore_file_name = icore_file_name + "/CUSTOMER_PHOTO.jpeg"
                if file_extension in [".jpeg", ".png", ".tif", ".tiff", ".jpg"]:
                    save_base64_to_file(form["customerPhotoBlob"], icore_file_name)
                    form["customerPhotoBlob"] = icore_file_name
                else:
                    form["customerPhotoBlob"] = ""
            if "matchingBlob" in form:
                matching_blob_file_name = f"{config.path}{form['TXN_ID']}/MATCH_BLOB"
                os.makedirs(matching_blob_file_name, exist_ok=True)
                file_extension = get_extension_type(form["matchingBlob"])
                matching_blob_file_name = matching_blob_file_name + "/image" + ".jpeg"
                if file_extension in [".jpeg", ".png", ".tif", ".tiff", ".jpg"]:
                    save_base64_to_file(form["matchingBlob"], matching_blob_file_name)
                    form["matchingBlob"] = matching_blob_file_name
                else:
                    form["matchingBlob"] = ""
        except:
            return "8000"
    return form
    
def download_file_from_gcs(uri, service_key_path):
    client = storage.Client.from_service_account_json(service_key_path)
    uri_parts = uri.replace("gs://", "").split("/")
    bucket_name = uri_parts[0]
    object_name = "/".join(uri_parts[1:])
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(object_name)
    file_content = blob.download_as_bytes()
    base64_data = base64.b64encode(file_content).decode("utf-8")
    return base64_data


def filter_request(request, type="Default"):
    try:
        if config.CLIENT_NAME == "BAJAJ":request["source"] = ''.join(re.findall(r'[A-Z_]+', str(request["source"]).upper()))
        request["source"] = request["source"].strip().upper()
        request["task"] = request["task"].strip().upper()
        request.update({
            "TASK": request["task"],
            "TXN_ID": request["txnId"],
            "DOCUMENT": request["documentBlob"],
            "DOC_TYPE": request["docType"].upper(),
            "CHANNEL": request["channel"],
            "TYPE": request["type"],
            "DOC_ID": request["documentId"],
            "DOC_NAME": request["documentName"],
            "SOURCE": request["source"],
            "CLUSTER": request["cluster"],
            "NODE": request["node"],
            "CASENO":request["caseNo"]
        })
        if type == "LOS":
            request.update({
                "DOCUMENT": request["documentBlob"]
            })
    except Exception as e:
        print(f"REQUEST KEY CHECK EXCEPTION : {e}") 
    return request


def detection_filter_request(request):
    try:
        request.update({
            "TXN_ID": request["txnId"],
            "DOCUMENT": request["documentBlob"],
            "DOC_NAME": request["documentName"],
            "DOC_TYPE": request["docType"].upper(),
            "SOURCE": request["source"],
            "CASENO":request["caseNo"]
        })
    except Exception as e:
        print(f"REQUEST KEY CHECK EXCEPTION : {e}") 
    return request


def extraction_filter_request(request):
    try:
        request.update({
            "TXN_ID": request["txnId"],
            "DOCUMENT": request["documentBlob"],
            "DOC_NAME": request["documentName"],
            "DOCUMENT_TYPE": request["documentType"],
            "DOC_TYPE": request["docType"].upper(),
            "SOURCE": request["source"],
            "CASENO":request["caseNo"]
        })
    except Exception as e:
        print(f"REQUEST KEY CHECK EXCEPTION : {e}") 
    return request

def valid_request(request, mandatory_keys, allValues = False):
    found_all = True
    for mandatory_key in mandatory_keys:
        if mandatory_key not in request.keys():
            found_all = False
            return found_all, {
                "status": False,
                "statusCode": 8005,
                "message": f"MISSING_REQUIRED_FIELD : {mandatory_key}",
                "errorMessage": "Mandatory field is missing",
                "results": [],
                "stage": "orchestrator"
            }
    value_checked = ["documentBlob", "docType", "txnId", "type", "caseNo"]
    if allValues:
        for mandatory_key in mandatory_keys:
            if mandatory_key not in value_checked: value_checked.append(mandatory_key)
    if request.get("source", "") in "AUDIOAI_TTS":
        value_checked.remove("docType")
    for mandatory_key in mandatory_keys:
        if mandatory_key in request.keys() and mandatory_key in value_checked and request[mandatory_key] == "" or str(request[mandatory_key]).startswith("--"):
            found_all = False
            if "MIMETYPE" in request and request["MIMETYPE"] == "application/json" and "SOURCE" in request and request["SOURCE"] != "LOS" :
                msg = " || Only 'JPEG/PNG/JPG/PDF/TIFF/TIF' file format doesn't require docType"
            else:msg = ""
            return found_all, {
                "status": False,
                "statusCode": 8004,
                "message": f"MISSING_REQUIRED_FIELD_DATA : {mandatory_key}{msg}",
                "errorMessage": "Mandatory field data is missing",
                "results": [],
                "stage": "orchestrator"
            }
    return found_all, request

def contains_special_characters(input_string):
    special_chars = string.punctuation
    for char in input_string:
        if char in special_chars:
            return True
    return False

def detection_valid_request(request, detection_mandatory_keys):
    found_all = True
    message = ''
    for mandatory_key in detection_mandatory_keys:
        if mandatory_key not in request.keys():
            found_all = False
            message = f'{mandatory_key} key is missing'
            return found_all, message
        if mandatory_key in request.keys() and mandatory_key in ["documentBlob", "docType", "txnId", "type"] and request[mandatory_key] == "" or request[mandatory_key].startswith("--"):
            found_all = False
            message = f'{mandatory_key} cannot be blank'
            return found_all, message
    return found_all, request

def extraction_valid_request(request, extraction_mandatory_keys):
    found_all = True
    message = ''
    for mandatory_key in extraction_mandatory_keys:
        if mandatory_key not in request.keys():
            found_all = False
            message = f'{mandatory_key} key is missing'
            return found_all, message
        if mandatory_key in request.keys() and mandatory_key in ["documentBlob", "documentType", "docType", "txnId", "type"] and request[mandatory_key] == "" or request[mandatory_key].startswith("--"):
            found_all = False
            message = f'{mandatory_key} cannot be blank'
            return found_all, message
    return found_all, request

def valid_json():
    try:
        if request.mimetype == 'application/json': 
            form = request.json
        elif request.mimetype == 'multipart/form-data':
            form = dict(request.form)
        elif request.mimetype == 'application/x-www-form-urlencoded':
            form = json.loads(next(iter(request.form.keys())))
        return True
    except Exception as e:
        print('Request Error : ', e)
        return False

def check_open_braces():
    form = request.get_data(as_text=True)
    if str(form)[0] == "{":
        return True
    return False

def check_close_braces():
    form = request.get_data(as_text=True)
    if str(form)[-1] == "}":
        return True
    return False

def length_validation(request):
    length_master = {"task": 20, "txnId": 100, "docType": 5, "channel": 10, "type": 100, "documentId": 100, "source": 20, "cluster": 10, "node": 10, "documentName": 100, "caseNo": 100, "documentBlob": 1000}
    for key, value in length_master.items():
        if len(request[key]) > value:
                return False, {
            "status": False,
            "statusCode": 8006,
            "message": f"INVALID_FIELD_LENGTH : {key}, MAX_LIMIT : {value}",
            "errorMessage": f"Length of field exceeds defined length : {len(request[key])}",
            "results": [],
            "stage": "orchestrator"
        }
    return True, request

def errorUpdate(field_name):
    errorMessage = {
                "status": False,
                "statusCode": 8003,
                "message": f"INVALID_FIELD : {field_name}",
                "errorMessage": f"FORMAT is not in the format mentioned, Valid Format : '{field_name}':"+'{value}',
                "results": [],
                "stage": "orchestrator"}
    return errorMessage

def field_validation(request):
    field_list = ["actuals", "arguments"]
    if "source" in request and request["source"] == "KYC_DATA": field_list.append("documentType")
    for field_name in field_list:
        if field_name in request and isinstance(request[field_name], str): 
            try:
                data = json.loads(request[field_name])
                request[field_name] = data
            except Exception as e:
                return False, errorUpdate(field_name)
        if (field_name in request) and not isinstance(request[field_name], (dict, list)):
            return False, errorUpdate(field_name)
        if field_name == "actuals" and field_name in request and request[field_name]:
            for key, value in request[field_name].items():
                if value.upper() in ["NONE", "NA", "NULL", "NAN"]:
                    request[field_name][key] = ""
    return True, request

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
    enc_data = base64.b64encode(enc.merge_two_byte_arrays(iv, encrypted_data)).decode('utf-8')
    return enc_data, "", enc_key

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
    return json.loads(decryptedMessage)

def get_decryption_data():
    try:
        data = request.json
        enc_keys = ["encryptedData","iv","encryptedKey"]
        for i in enc_keys:
            if i not in data:
                return [{"status": False, "errorMessage": f"{i} key is missing"}]
        decrypted_data = decrypt_data(data["encryptedData"], data["iv"], data["encryptedKey"], config.private_key)
        if decrypt_data is None: return [{"status": False, "errorMessage": "Decryption failed"}]
        return decrypted_data
    except Exception as e:
        return [{"status": False, "errorMessage": e}]
    
def get_encryption_data(json_data, encStatus, txn_id = "", encSource = ""):
    try:
        if not encStatus: return json_data
        enc_req_path = f"{config.path}{txn_id}/ENCRYPTION/request.json"
        if not os.path.exists(enc_req_path) and txn_id: return json_data
        if encSource:
            public_key_path_dict = {
                "API Gateway Hybrid": config.public_key_hybrid
            }
            if encSource.strip() in public_key_path_dict: print(f"{txn_id} ENCRYPTION METHOD: HYBRID")
            else: print(f"{txn_id} ENCRYPTION METHOD: NON-HYBRID, REMARKS: [INVALID ENCRYPTION SOURCE KEY ❌ '{encSource.strip()}']")
            public_key_path = public_key_path_dict.get(encSource.strip(), config.public_key)
        else:
            print(f"{txn_id} ENCRYPTION METHOD: NON-HYBRID")
            public_key_path = config.public_key
        decoded_encrypted_data, iv, encrypted_symmetric_key = encrypt_data(json_data, public_key_path)
        result_data = {
            "encryptedData": decoded_encrypted_data,
            "iv": iv,
            "encryptedKey": encrypted_symmetric_key,
        }
        if txn_id:
            enc_path = f"{config.path}{txn_id}/ENCRYPTION"
            os.makedirs(enc_path, exist_ok=True)
            with open(f"{enc_path}/response.json", "w", encoding="utf-8") as ff: json.dump(result_data, ff, indent=4)
        return result_data
    except Exception as e:
        return [{"status": False, "message": e}]
    
def ibank_key_validation(form):
    specialList = ["documentId", "caseNo", "txnId"]
    if "documentName" in form:
        dotCount = form["documentName"].count(".")
        if dotCount > 1: return "8016", str(dotCount)
        spcialFound = contains_special_characters(form["documentName"].replace(".",""))
        if spcialFound: return "8017", "documentName"
    for splkeys in specialList:
        if splkeys in form:
            spcialFound = contains_special_characters(form[splkeys])
            if spcialFound: return "8017", splkeys
    return ""

def check_IGOLD(form):
    status = False
    source = form.get("source","").strip().upper()
    arguments = str(form.get("arguments",""))
    if source == "IGOLD" and "folderName" in arguments:
        status = True
        form["documentBlob"], form["DOCUMENT"], form["docType"] = "IGOLD", "IGOLD", ".JPEG"
    return status, form
 
def get_request(type):
    unique_id = str(uuid.uuid4().hex)
    unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
    mimetype = request.mimetype
    form = {}
    try:
        if mimetype == 'application/x-www-form-urlencoded':
            if not valid_json():
                if not check_open_braces():return "8007"
                if not check_close_braces():return "8008"
                return "8002"
            form = json.loads(next(iter(request.form.keys())))
            if not form:return "8001"
            form["MIMETYPE"] = mimetype
            form = filter_request(form)
            if config.CLIENT_NAME == "ICICI" and not type: 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
        elif mimetype == 'multipart/form-data':
            if not valid_json():
                if not check_open_braces():return "8007"
                if not check_close_braces():return "8008"
                return "8002"
            form = dict(request.form)
            if not form:return "8001"
            form["MIMETYPE"] = mimetype
            form["documentBlob"] = ""
            igoldStatus, form = check_IGOLD(form)
            form = filter_request(form)
            if config.CLIENT_NAME == "ICICI" and not type: 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
            form = save_file(form, "multipart/form-data") if not igoldStatus else form
            if isinstance(form, str):return form
            if type in ["AUDIOAI", "VCIP_AUDITOR_V3", "SERVER_AUDITOR"]:
                if form["DOC_TYPE"].upper() not in audio_extensions:return "8015", form["DOC_TYPE"]
            else:
                if form["DOC_TYPE"].upper() not in image_extensions:return "8015", form["DOC_TYPE"]
        elif mimetype == 'application/json':
            if not valid_json():
                if not check_open_braces():return "8007"
                if not check_close_braces():return "8008"
                return "8002"
            form = request.json
            if not form:return "8001"
            enc_form = request.json
            encStatus = False
            if config.CLIENT_NAME in ["ICICI", "XBIZ"] and "encryption" in form and form["encryption"]:
                encStatus = True
                form = get_decryption_data()
                if isinstance(form, list):
                    print(f"Decryption error: {form[0]}") 
                    return "8014"
            if type:
                keys_to_add = ["task", "channel", "documentId", "channel", "cluster", "node", "caseNo"]
                for key_to_add in keys_to_add:
                    if key_to_add not in form:
                        form[key_to_add] = "1"
            form["MIMETYPE"] = mimetype
            igoldStatus, form = check_IGOLD(form)
            form["documentBlob"] = form["documentBlob"].strip()
            if form["documentBlob"].startswith("gs://"):
                uri = form["documentBlob"]
                service_key_path = "SERVICE_KEY.json"
                form["documentBlob"] = download_file_from_gcs(uri, service_key_path)
                form["docType"] = os.path.splitext(uri)[1].upper()
            if not type:
                old_doctype = form["docType"].upper()
                if old_doctype and old_doctype.upper() not in image_extensions:return "8015", old_doctype
                new_docType = get_extension_type(form["documentBlob"], pdfStatus = True).upper()
                if new_docType: form.update({"docType": new_docType})
                if form["docType"].upper() not in image_extensions:return "8015", form["docType"]
            form = filter_request(form, type)
            if config.CLIENT_NAME == "ICICI" and not type: 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            if form["TXN_ID"] != "":
                form["OG_TXN_ID"] = form["TXN_ID"]
                x_txn_id = form["TXN_ID"] + "--" + unique_id
                form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
            form = save_file(form, "application/json") if not igoldStatus else form
            if isinstance(form, str):return form
            if encStatus:
                enc_path = f"{config.path}{x_txn_id}/ENCRYPTION"
                os.makedirs(enc_path, exist_ok=True)
                with open(f"{enc_path}/request.json", "w", encoding="utf-8") as ff: json.dump(enc_form, ff, indent=4)
        else:
            form = request.data.decode()
        if form == "":
            form = {}
    except Exception as e:
        print(f"EXCEPTION IN GET REQUEST : {e}")
    return form
    

def get_rawfile(path):
    item_path = ''
    for item in os.listdir(path):
        file_path = os.path.join(path, item)
        if os.path.isfile(file_path):
            item_path = file_path.replace("\\", "/")
            break
    return item_path

def check_docai_validation(type=""):
    request_data = get_request(type)
    if not isinstance(request_data, dict):
        if isinstance(request_data, tuple):
            data =  req_validation_json[request_data[0]]
            errorData = data.copy()
            errorData["errorMessage"] = errorData["errorMessage"] + request_data[1].replace(".","")
            return False, errorData
        return False, req_validation_json[request_data]
    mandatory_keys = request_validator["MANDATORY_KEYS"]
    status, message = valid_request(request_data, mandatory_keys)
    if not status: return False, message 
    request_data["documentBlob"] = request_data["DOCUMENT"]  
    print(f"\nOrchestrator Request: {str(request_data)}")     
    if not type:
        if config.CLIENT_NAME == "ICICI":
            status2, request_data = length_validation(request_data)
            if not status2: return False, request_data
        status3, request_data = field_validation(request_data)
        if not status3: return False, request_data
        packet_folder = config.path + request_data[constants.TXN_ID] + "/" + "PACKET"
        os.makedirs(packet_folder, exist_ok=True)
        igoldFolderName = request_data.get("arguments",{}).get("folderName", "")
        if igoldFolderName: request_data.update({"folderName":igoldFolderName})
        json_request = {key: request_data[key] for key in mandatory_keys}
        try:
            if "icoreImage" in request_data and request_data["icoreImage"]: 
                file_ext = os.path.splitext(request_data["icoreImage"])[1].lower()
                jpeg_file = request_data["icoreImage"].replace("/icore.","/icore_image.").replace(file_ext,".jpeg")
                if file_ext == ".jpeg":
                    shutil.copy(request_data["icoreImage"], jpeg_file)
                elif file_ext in [".png", ".jpg"]:
                    image = Image.open(request_data["icoreImage"])
                    if image.mode != "RGB":image = image.convert("RGB")
                    image.save(jpeg_file, "JPEG") 
                elif file_ext in [".tif", ".tiff"]:
                    tif_to_first_image_base64(request_data["icoreImage"], jpeg_file)
                    thread = threading.Thread(target=tif_to_first_image_base64, args=(request_data["icoreImage"], jpeg_file))
                    thread.start()
                request_data["icoreImage"] = jpeg_file
                json_request["icoreImage"] = base64.b64encode(open(jpeg_file, 'rb').read()).decode('utf-8') if os.path.exists(jpeg_file) else "" 
            rawfile = get_rawfile(config.path + request_data["TXN_ID"])
            if rawfile: json_request['documentBlob'] = base64.b64encode(open(rawfile, 'rb').read()).decode('utf-8')
        except:pass
        json_request.update({"actuals":request_data.get('actuals', {}),"arguments":request_data.get('arguments', {})})
        with open(f"{packet_folder}/request.json", "w") as f: json.dump(json_request, f, indent=4)       
        request_data["documentBlob"] = request_data["DOCUMENT"]
    return True, request_data


def detection_get_request():
    unique_id = str(uuid.uuid4().hex)
    unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
    mimetype = request.mimetype
    form = {}
    try :
        if mimetype == 'application/x-www-form-urlencoded':
            form = json.loads(next(iter(request.form.keys())))
            form["MIMETYPE"] = mimetype
            form = detection_filter_request(form)
            if config.CLIENT_NAME == "ICICI": 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
        elif mimetype == 'multipart/form-data':
            if not valid_json():
                if not check_open_braces():return "8007"
                if not check_close_braces():return "8008"
                return "8002"
            form = dict(request.form)
            if not form:return "8001"
            form["MIMETYPE"] = mimetype
            form["documentBlob"] = ""
            form = detection_filter_request(form)
            if config.CLIENT_NAME == "ICICI": 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
            form = save_file(form, "multipart/form-data")
            if isinstance(form, str):return form
            if form["DOC_TYPE"].upper() not in image_extensions:return "8015", form["DOC_TYPE"]
        elif mimetype == 'application/json':
            if not valid_json():
                if not check_open_braces():return "8007"
                if not check_close_braces():return "8008"
                return "8002"
            form = request.json
            if not form:return "8001"
            enc_form = request.json
            encStatus = False
            if config.CLIENT_NAME in ["ICICI", "XBIZ"] and "encryption" in form and form["encryption"]:
                encStatus = True
                form = get_decryption_data()
                if isinstance(form, list):
                    print(f"Decryption error: {form[0]}") 
                    return "8014"
            form["MIMETYPE"] = mimetype
            form["documentBlob"] = form["documentBlob"].strip()
            if form["documentBlob"].startswith("gs://"):
                uri = form["documentBlob"]
                service_key_path = "SERVICE_KEY.json"
                form["documentBlob"] = download_file_from_gcs(uri, service_key_path)
                form["docType"] = os.path.splitext(uri)[1].upper()
            status = check_base64(form["documentBlob"])
            if not status: return "8000"
            old_doctype = form["docType"].upper()
            if old_doctype and old_doctype.upper() not in image_extensions:return "8015", old_doctype
            new_docType = get_extension_type(form["documentBlob"], pdfStatus = True).upper()
            if new_docType: form.update({"docType": new_docType})
            if form["docType"].upper() not in image_extensions:return "8015", form["docType"]
            form = detection_filter_request(form)
            if config.CLIENT_NAME == "ICICI": 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            if form["TXN_ID"] != "":
                form["OG_TXN_ID"] = form["TXN_ID"]
                x_txn_id = form["TXN_ID"] + "--" + unique_id
                form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
            form = save_file(form, "application/json")
            if isinstance(form, str):return form
            if encStatus:
                enc_path = f"{config.path}{x_txn_id}/ENCRYPTION"
                os.makedirs(enc_path, exist_ok=True)
                with open(f"{enc_path}/request.json", "w", encoding="utf-8") as ff: json.dump(enc_form, ff, indent=4)
        else:
            form = request.data.decode()
        if form == "":
            form = {}
    except Exception as e:
        print(f"EXCEPTION IN GET REQUEST : {e}")
    return form

def detection_validation():
    request_data = detection_get_request()
    if not isinstance(request_data, dict):
        if isinstance(request_data, tuple):
            data =  req_validation_json[request_data[0]]
            errorData = data.copy()
            errorData["errorMessage"] = errorData["errorMessage"] + request_data[1].replace(".","")
            return False, errorData
        return False, req_validation_json[request_data]
    detection_mandatory_keys = request_validator["DETECTION_MANDATORY_KEYS"]
    status, message = detection_valid_request(request_data, detection_mandatory_keys)
    if status:
        rawfile = get_rawfile(config.path + message["TXN_ID"])
        message['documentBlob'] = base64.b64encode(open(rawfile, 'rb').read()).decode('utf-8')
        packet_folder = config.path + message[constants.TXN_ID] + "/" + "PACKET"
        os.makedirs(packet_folder, exist_ok=True)
        json_request = {key: message[key] for key in detection_mandatory_keys}
        json_request.update({"actuals":message.get('actuals', {}),"arguments":message.get('arguments', {})})
        with open(f"{packet_folder}/request.json", "w") as f: json.dump(json_request, f, indent=4)       
        message["documentBlob"] = message["DOCUMENT"]
    return status, message

def extraction_get_request():
    unique_id = str(uuid.uuid4().hex)
    unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
    mimetype = request.mimetype
    form = {}
    try :
        if mimetype == 'application/x-www-form-urlencoded':
            form = json.loads(next(iter(request.form.keys())))
            form["MIMETYPE"] = mimetype
            form = extraction_filter_request(form)
            if config.CLIENT_NAME == "ICICI": 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
        elif mimetype == 'multipart/form-data':
            form = dict(request.form)
            form["MIMETYPE"] = mimetype
            form["documentBlob"] = ""
            form = extraction_filter_request(form)
            if config.CLIENT_NAME == "ICICI": 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
            form = save_file(form, "multipart/form-data")
            if isinstance(form, str):return form
            if form["DOC_TYPE"].upper() not in image_extensions:return "8015", form["DOC_TYPE"]
        elif mimetype == 'application/json':
            form = request.json
            enc_form = request.json
            encStatus = False
            if config.CLIENT_NAME in ["ICICI", "XBIZ"] and "encryption" in form and form["encryption"]:
                encStatus = True
                form = get_decryption_data()
                if isinstance(form, list):
                    print(f"Decryption error: {form[0]}") 
                    return "8014"
            form["MIMETYPE"] = mimetype
            form["documentBlob"] = form["documentBlob"].strip()
            if form["documentBlob"].startswith("gs://"):
                uri = form["documentBlob"]
                service_key_path = "SERVICE_KEY.json"
                form["documentBlob"] = download_file_from_gcs(uri, service_key_path)
                form["docType"] = os.path.splitext(uri)[1].upper()
            status = check_base64(form["documentBlob"])
            if not status: return "8000"
            old_doctype = form["docType"].upper()
            if old_doctype and old_doctype.upper() not in image_extensions:return "8015", old_doctype
            new_docType = get_extension_type(form["documentBlob"], pdfStatus = True).upper()
            if new_docType: form.update({"docType": new_docType})
            if form["docType"].upper() not in image_extensions:return "8015", form["docType"]
            form = extraction_filter_request(form)
            if config.CLIENT_NAME == "ICICI": 
                status = ibank_key_validation(form)
                if isinstance(status, tuple): return status
            if form["TXN_ID"] != "":
                form["OG_TXN_ID"] = form["TXN_ID"]
                x_txn_id = form["TXN_ID"] + "--" + unique_id
                form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
                form = save_file(form, "application/json")
            if encStatus:
                enc_path = f"{config.path}{x_txn_id}/ENCRYPTION"
                os.makedirs(enc_path, exist_ok=True)
                with open(f"{enc_path}/request.json", "w", encoding="utf-8") as ff: json.dump(enc_form, ff, indent=4)
        else:
            form = request.data.decode()
        if form == "":
            form = {}
    except Exception as e:
        print(f"EXCEPTION IN GET REQUEST : {e}")
    return form


def extraction_validation():
    request_data = extraction_get_request()
    if not isinstance(request_data, dict):
        if isinstance(request_data, tuple):
            data =  req_validation_json[request_data[0]]
            errorData = data.copy()
            errorData["errorMessage"] = errorData["errorMessage"] + request_data[1].replace(".","")
            return False, errorData
        return False, req_validation_json[request_data]
    extraction_mandatory_keys = request_validator["EXTRACTION_MANDATORY_KEYS"]
    status, request_data = valid_request(request_data, extraction_mandatory_keys)
    if not status: return status, request_data
    status, request_data = field_validation(request_data)
    if not status: return False, request_data
    if status:
        rawfile = get_rawfile(config.path + request_data["TXN_ID"])
        request_data['documentBlob'] = base64.b64encode(open(rawfile, 'rb').read()).decode('utf-8')
        packet_folder = config.path + request_data[constants.TXN_ID] + "/" + "PACKET"
        os.makedirs(packet_folder, exist_ok=True)
        json_request = {key: request_data[key] for key in extraction_mandatory_keys}
        json_request.update({"actuals":request_data.get('actuals', {}),"arguments":request_data.get('arguments', {})})
        with open(f"{packet_folder}/request.json", "w") as f: json.dump(json_request, f, indent=4)       
        request_data["documentBlob"] = request_data["DOCUMENT"]
    return status, request_data

def verification_get_request():
    unique_id = str(uuid.uuid4().hex)
    unique_id = str(unique_id.lower()[:int(len(unique_id)/5)])
    mimetype = request.mimetype
    form = {}
    try :
        if mimetype == 'application/x-www-form-urlencoded':
            form = json.loads(next(iter(request.form.keys())))
            form["MIMETYPE"] = mimetype
            form["TXN_ID"] = form["txnId"] 
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
        elif mimetype == 'multipart/form-data':
            form = dict(request.form)
            form["MIMETYPE"] = mimetype
            form["TXN_ID"] = form["txnId"] 
            form["OG_TXN_ID"] = form["TXN_ID"]
            x_txn_id = form["TXN_ID"] + "--" + unique_id
            form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
        elif mimetype == 'application/json':
            form = request.json
            enc_form = request.json
            encStatus = False
            if config.CLIENT_NAME in ["ICICI", "XBIZ"] and "encryption" in form and form["encryption"]:
                encStatus = True
                form = get_decryption_data()
                if isinstance(form, list):
                    print(f"Decryption error: {form[0]}") 
                    return "8014"
            form["MIMETYPE"] = mimetype
            form["TXN_ID"] = form["txnId"] 
            if form["TXN_ID"] != "":
                form["OG_TXN_ID"] = form["TXN_ID"]
                x_txn_id = form["TXN_ID"] + "--" + unique_id
                form.update({"TXN_ID":x_txn_id, "txnId" : x_txn_id})
            if encStatus:
                enc_path = f"{config.path}{x_txn_id}/ENCRYPTION"
                os.makedirs(enc_path, exist_ok=True)
                with open(f"{enc_path}/request.json", "w", encoding="utf-8") as ff: json.dump(enc_form, ff, indent=4)
        else:
            form = request.data.decode()
        if form == "":
            form = {}
    except Exception as e:
        print(f"EXCEPTION IN VERIFY REQUEST API: {e}")
    return form

def datas_and_actual_validation(request):
    for key, value in request.items():
        if isinstance(value, str):
            request[key] = value.strip()
    falseResponse = {
        "status": False,
        "statusCode": 8018,
        "results": [],
        "stage": "orchestrator"
    }
    if request["client"] not in verification_master["VERIFICATION_MASTER"]:
        falseResponse.update({"message":"Invalid client", "errorMessage": "Make sure to send proper Client"})
        return False, falseResponse
    if request["clientId"] != verification_master["VERIFICATION_MASTER"][request["client"]]["V_ID"]:
        falseResponse.update({"message":"Invalid clientId", "errorMessage": "Make sure to send proper clientId"})
        return False, falseResponse
    if request["clientSecret"] != verification_master["VERIFICATION_MASTER"][request["client"]]["V_SECRET"]:
        falseResponse.update({"message":"Invalid clientSecret", "errorMessage": "Make sure to send proper clientSecret"})
        return False, falseResponse
    if request["channel"] not in verification_master["VERIFICATION_MASTER"][request["client"]]["CHANNEL"]:
        falseResponse.update({"message":"Invalid channel", "errorMessage": "Make sure to use proper channel"})
        return False, falseResponse
    departmentMaster = verification_master["VERIFICATION_MASTER"][request["client"]]["CHANNEL"][request["channel"]]["DEPARTMENT"]
    if request["clientDepartment"] not in departmentMaster:
        falseResponse.update({"message":"Invalid clientDepartment", "errorMessage": "Make sure to send proper ClientDepartment"})
        return False, falseResponse
    if request["task"] not in verification_master["VERIFICATION_ENTITIES"]:
        falseResponse.update({"message":"Invalid task", "errorMessage": "Make sure to send proper Task"})
        return False, falseResponse
    if request["task"] not in departmentMaster[request["clientDepartment"]]:
        falseResponse.update({"statusCode": 8019, "message":"Permission denied", "errorMessage": "Given clientDepartment doesn't have permission for this task"})
        return False, falseResponse
    actualMaster = verification_master["VERIFICATION_ENTITIES"][request["task"]]["ACTUAL_MASTER"]
    if not all(i in request["arguments"] for i in actualMaster.keys()):
        falseResponse.update({"statusCode": 8020, "message":"Invalid arguments Key", "errorMessage": "Make sure to send proper key in arguments"})
        return False, falseResponse
    for i in actualMaster.keys():
        if not request["arguments"][i]:
            falseResponse.update({"statusCode": 8020, "message":"Missing arguments Value", "errorMessage": "Make sure to send proper value in arguments Key"})
            return False, falseResponse
    request.update({
        "documentType": verification_master["VERIFICATION_ENTITIES"][request["task"]]["DOCUMENT_TYPE"],
        "payload": {value: request["arguments"][key]  for key, value in actualMaster.items()}
    })
    return True, request

def verification_validation():
    request_data = verification_get_request()
    if not isinstance(request_data, dict):
        if isinstance(request_data, tuple):
            data =  req_validation_json[request_data[0]]
            errorData = data.copy()
            errorData["errorMessage"] = errorData["errorMessage"] + request_data[1].replace(".","")
            return False, errorData
        return False, req_validation_json[request_data]
    verification_mandatory_keys = verification_master["VERIFICATION_MANDATORY_KEYS"]
    status, request_data = valid_request(request_data, verification_mandatory_keys, allValues = True)
    if not status: return status, request_data
    status, request_data = field_validation(request_data)
    if not status: return False, request_data
    status, request_data = datas_and_actual_validation(request_data)
    if not status: return False, request_data
    packet_folder = config.path + request_data[constants.TXN_ID] + "/" + "PACKET"
    os.makedirs(packet_folder, exist_ok=True)
    json_request = {key: request_data[key] for key in verification_mandatory_keys}
    with open(f"{packet_folder}/request.json", "w") as f: json.dump(json_request, f, indent=4)       
    return status, request_data

def ocr_path_to_text(path):
    if os.path.exists(path):
        raw_text = open(path, encoding="utf-8").read()
        raw_text = raw_text if len(raw_text) > 0 else "NA"
    else:
        raw_text = ""
    return raw_text


def prepopRequest(request, doc_types, Category):
    source_path = config.source
    destination_path = config.path
    ocr_datas = request["DATA"]
    req = {"Requestobject": [], "DOC_TYPES": ",".join(doc_types)}
    for i in range(len(ocr_datas)):
        ocr_data = ocr_datas[i]
        ocr_data = ocr_data.replace(source_path, destination_path).replace('\\', '/')
        dict = {"File_Type": ".raw", "transaction_Id": ocr_data.split("/")[-3], "document_Id": "2", "UserName": config.PP_DM_USR, "Password": config.PP_DM_PWD, "Category": Category}
        raw_text = open(ocr_data, encoding="utf-8").read()
        raw_text = raw_text if len(raw_text) > 0 else "NA"
        ocr_data_sorted = ocr_data.replace("/OCR/", "/OCR_SORTED/")
        ocr_data_sorted_v2 = ocr_data.replace("/OCR/", "/OCR_SORTED_V2/")
        raw_text_sorted = ocr_path_to_text(ocr_data_sorted)
        raw_text_sorted_v2 = ocr_path_to_text(ocr_data_sorted_v2)
        dict["ImageBase64"] = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
        dict["ImageBase64Sorted"] = base64.b64encode(raw_text_sorted.encode("utf-8")).decode("utf-8")
        dict["ImageBase64Sorted2"] = base64.b64encode(raw_text_sorted_v2.encode("utf-8")).decode("utf-8")
        req["Requestobject"].append(dict)
    print(f"\n\nPREPOP REQUEST : {str(req)[:200]}")
    return req

def prepop_merge_into_one(python_response, dotnet_response, source):
    response = {"Kyc": []}
    kyc_documents = [
        "PAN CARD", "AADHAAR CARD", "DRIVING LICENCE", "VOTER CARD", "PASSPORT"
    ]
    doc_type_master = doc_master_json["DOCUMENT_TYPE"]
    extraKeys = {
        "PASSPORT": ["YEAR_OF_BIRTH", "GENDER", "NATIONALITY_CODE", "PASSPORT_EXPIRY_STATUS"],
        "AADHAAR CARD": ["YEAR_OF_BIRTH", "GENDER"],
        "PAN CARD": ["YEAR_OF_BIRTH"],
        "DRIVING LICENCE": ["YEAR_OF_BIRTH", "GENDER"],
        "VOTER CARD": ["YEAR_OF_BIRTH", "GENDER"]
    }
    for index, data in enumerate(python_response):
        prepopDoctype = data["DOCUMENT_TYPE"]
        dotnetDoctype = dotnet_response[index]["DOCUMENT_TYPE"]
        subtypePython = data.get("SUB_TYPE", "")
        print(f"PYTHON PAGE {index+1} DOCTYPE: {prepopDoctype}")
        print(f"DOTNET PAGE {index+1} DOCTYPE: {dotnetDoctype}")
        # subtypeDotnet = data.get("SUBDOCUMENT_TYPE", "")
        if prepopDoctype in kyc_documents:
            if prepopDoctype == dotnetDoctype:
                mydata = dotnet_response[index]
                extraDataList = extraKeys.get(prepopDoctype, [])
                extraDict = {mykey: data.get(mykey, "") for mykey in extraDataList if data.get(mykey, "") and not dotnet_response[index].get(mykey, "")}
                mydata.update(extraDict)
                mydata.update({"SUBDOCUMENT_TYPE": subtypePython, "SUB_TYPE": subtypePython})
            else:
                mydata = {}
                document_type_no = next((key for key, value in doc_type_master.items() if value.lower() == prepopDoctype.lower()), "other")
                print(f"Document type page {index+1}: {prepopDoctype}")
                if document_type_no in prepop_detect_keylist:
                    mylist = prepop_detect_keylist[document_type_no][1]
                    for key in mylist:
                        if document_type_no == "16" and source != "IGOLD" and key in ["PLAIN_BANGLE","NON-STANDARD_ORNAMENTS","BANGLE_AND_SIMILAR","BROAD_BANGLE"]:continue
                        if source not in ["FTA","ISV_OUT_V2"] and key == "AMOUNTWORDVSNUM" and document_type_no in ["6", "45"]:continue
                        mydata[key] = ""
                    else:
                        mydata.update({"DOCUMENT_TYPE": prepopDoctype,"SUBDOCUMENT_TYPE": subtypePython, "SUB_TYPE": subtypePython})
                else:
                    mydata = {"DOCUMENT_TYPE": "NA", "SUBDOCUMENT_TYPE": "NA", "SUB_TYPE": "NA"}
            response["Kyc"].append(mydata)
        else:
            response["Kyc"].append(data)
    return response


def date_formatter(date):
    DD, MM, YYYY = date.split("/")
    if len(DD.strip()) < 2 and DD.strip().isdigit():DD = "0" + DD.strip()
    if len(MM.strip()) < 2 and MM.strip().isdigit():MM = "0" + MM.strip()
    if len(YYYY.strip()) == 2 and YYYY.strip().isdigit():
        if int(YYYY) > 50: YYYY = "19" + YYYY.strip()
        else: YYYY = "20" + YYYY.strip()
    date = DD + "/" + MM + "/" + YYYY
    return date       


def adding_coordinates(key, value, co_value):
    if config.CLIENT_NAME == 'XBIZ' and config.path in ["E:/Projects/DIGISUITE/FILES/","E:/FILES/","D:/FILES/"]:
        if key in value: 
            if "coordinate" in value: value["coordinate"] = co_value
        else:
            if "coordinate" in value: value["coordinate"] = []
    return value

def amountFilterICICI(amount):
    rupees = amount.split(".")[0]
    if len(rupees) > 9: amount = ""
    return amount
        
def prepopResponse(response, source, txn_id, txt_list, qrKey = False):
    addon = {"confidenceScore": "0","matchingScore": "0","coordinate": {}}
    if qrKey: addon.update({qrKey: ""})
    else: 
        if "qrData" in addon: addon.pop("qrData")
    print(f"\n{source} PREPOP RESPONSE :\n{str(response)[:200]}")
    DATE_POSSIBLE_KEYNAMES = ["doi","dob","doi","doe","date"]
    doc_type_master = doc_master_json["DOCUMENT_TYPE"]
    main_response = {constants.STATUS: True, constants.CODE: 200, constants.MESSAGE: "Success", constants.EXCEPTION_MESSAGE: "", constants.DATA: [], constants.TXN_ID:txn_id}
    prepop_response_list, extract_data_list = [], []
    prepop_folder = config.path + txn_id + "/" + "PREPOP"
    if not os.path.exists(prepop_folder):
        os.makedirs(prepop_folder)
    CO_STATUS = response.get("coordinates", [])
    AI_TOTAL_PAGE = len(response["Kyc"])
    for i in range(len(response["Kyc"])):
        kyc_data = {k: v if isinstance(v, str) else str(v) for k, v in response["Kyc"][i].items()}
        cmm_kyc_data = kyc_data.copy()
        try: # if source not in ["LOS"]
            number = re.findall(r'\d+', os.path.splitext(os.path.basename(txt_list[i]))[0])[0]
        except:
            number = i
        document_type = next((key for key, value in doc_type_master.items() if value.lower() == kyc_data["DOCUMENT_TYPE"].lower()), "other")
        print(f"Document type page {i+1}: {kyc_data['DOCUMENT_TYPE']}")
        if document_type != "other":
            mylist = prepop_detect_keylist[document_type]
            sublist0, sublist1, updated_kyc_data, extract_data = mylist[0], mylist[1], {}, {}
            for index, key in enumerate(sublist1):
                if document_type == "16" and "IGOLD" not in source and key in ["PLAIN_BANGLE","NON-STANDARD_ORNAMENTS","BANGLE_AND_SIMILAR","BROAD_BANGLE"]:continue
                if index < len(sublist0):
                    new_key = sublist0[index]  
                    if source not in ["FTA","ISV_OUT_V2"] and new_key == "amountWordNumber" and document_type == "6":continue
                    value = kyc_data.get(key, "").strip()
                    if any(x in new_key for x in DATE_POSSIBLE_KEYNAMES): 
                        value = value.replace("-", "/")
                        if value and value.count("/") == 2 and value[0] != "/" and value[-1] != "/": value = date_formatter(value)
                    if source not in ["ILENS", "MIGRATED_DIGIMATCH"] and new_key == "unmaskedAadhaarNumber" and document_type == "1": value = ""
                    value = "" if value.lower() in ["none", "na"] else value
                    if new_key == "accountHolderName" and document_type == "45" and source == "ISV_OUT_V2": value = "DEMAND DRAFT"
                    extract_data[new_key] = "0" if any(x in new_key.lower() and not value for x in["signature","seal","photograph","amountwordnumber"]) else value
                    if new_key == "amount" and "ISV" in source and value and config.CLIENT_NAME == 'ICICI': value = amountFilterICICI(value)
                    updated_kyc_data[new_key] = {**addon, "value": "0" if any(x in new_key.lower() and not value for x in["signature","seal","photograph","amountwordnumber"]) else value}
                    if CO_STATUS: updated_kyc_data[new_key] = adding_coordinates(key, updated_kyc_data[new_key], CO_STATUS[i].get(key, []))
            kyc_data = updated_kyc_data
            if "documentType" in kyc_data and kyc_data["documentType"]["value"] == "DEMAND DRAFT" and source == "ISV_OUT_V2":
                print(f"Document type page {i+1}: CHANGED FROM DEMAND DRAFT to CHEQUE")
                kyc_data["documentType"]["value"] = "CHEQUE"
            extract_data_v2 = extract_data
        else:
            kyc_data = {"documentType":{**addon, "value" : "other"}}
            if CO_STATUS: kyc_data["documentType"] = adding_coordinates("khanstar", kyc_data["documentType"], "")
            extract_data_v2 = {"documentType":"other"}
        prepop_data = kyc_data.copy()
        prepop_data["pageNo"] = {**addon, "value" : [int(number)+1]}
        if CO_STATUS: prepop_data["pageNo"] = adding_coordinates("khanstar", prepop_data["pageNo"], "")
        extract_data_v2["pageNo"] = int(number)+1
        if source in EXTRA_PREPOP_KEYS: 
            prepop_data.update({EXTRA_PREPOP_KEYS[source]:{**addon, "value" : ""}})
            extract_data_v2.update({EXTRA_PREPOP_KEYS[source]:""})
        ai_dict = {
            "AI_DOCUMENT_TYPE": prepop_data["documentType"]["value"],
            "AI_PAGE_NO": prepop_data["pageNo"]["value"],
            "source": source,
            "txnId": txn_id,
            "AI_TOTAL_PAGE": AI_TOTAL_PAGE
        }
        docai_database({}, "AI_RESPONSE", "PREPOP", ai_dict)
        prepop_response_list.append(prepop_data)
        extract_data_list.append(extract_data_v2)
        res_obj = {"Kyc": [cmm_kyc_data]}
        with open(prepop_folder + f"/output{number}.json", "w") as writer:
            json.dump(res_obj, writer, indent=4)
        main_response[constants.DATA].append(
            config.source + txn_id + "/" + "PREPOP" + f"/output{number}.json")
    with open(prepop_folder + "/key_value_pair.json", "w") as values: json.dump(extract_data_list, values, indent=4)
    if not os.path.exists(prepop_folder + "/single_output.json"):
        with open(prepop_folder + "/single_output.json", "w") as writer:
            json.dump(prepop_response_list, writer, indent=4)
    else:
        with open(prepop_folder + "/single_output.json", "r+") as file:
            json_data = json.load(file)
            if prepop_response_list:
                for i in prepop_response_list:
                    insert_page = i["pageNo"]["value"][0] - 1
                    json_data.insert(insert_page, i)
                    file.seek(0)
                    file.truncate()
                    json.dump(json_data, file, indent=4)     
    main_response[constants.DATA] = [config.source + txn_id + "/" + "PREPOP" + "/single_output" + ".json"]
    return main_response    

def kycDocDetection(response, request, source, db_dict):
    print(f"\nDETECTION RESPONSE: {str(response)[:200]}")
    updated_response = []
    document_type_master = request_validator["SOURCE_DOC"][source]
    AI_TOTAL_PAGE = len(response["DocDetection"])
    for index, each_page in enumerate(response["DocDetection"]):
        print(f"Page {index+1} DocType : {each_page['DOCUMENT_TYPE']}")
        if each_page["DOCUMENT_TYPE"] in document_type_master:
            mydict = {"documentType": {"confidenceScore": "0","value": each_page["DOCUMENT_TYPE"]},
            'pageNo':{"confidenceScore": "0","value": [index+1]}}
            if each_page["DOCUMENT_TYPE"] in ["PAN CARD", "AADHAAR CARD", "DRIVING LICENCE", "VOTER CARD", "PASSPORT"]:
                mydict["subDocumentType"] = {"confidenceScore": "0","value": each_page["SUB_TYPE"]}
        else:
            mydict = {"documentType": {"confidenceScore": "0","value": each_page["DOCUMENT_TYPE"] if each_page["DOCUMENT_TYPE"] != "NA" else "other"},
            'pageNo':{"confidenceScore": "0","value": [index+1]}}
        ai_dict = {
            "AI_DOCUMENT_TYPE": mydict["documentType"]["value"],
            "AI_PAGE_NO": mydict["pageNo"]["value"],
            "source": source,
            "txnId": db_dict["txnId"],
            "AI_TOTAL_PAGE": AI_TOTAL_PAGE
        }
        docai_database({}, "AI_RESPONSE", "DOC_DETECTION", ai_dict)
        updated_response.append(mydict)
    request["DATA"] = updated_response
    doc_detection_folder = config.path + f"{request['TXN_ID']}/" + "DOCDETECTION"
    if not os.path.exists(doc_detection_folder): os.makedirs(doc_detection_folder)
    with open(doc_detection_folder + "/response.json", "w") as outfile: json.dump(request, outfile, indent=4)        
    return request

def nonKycDocDetection(response, request, db_dict):
    print(f"\nDETECTION RESPONSE: {str(response)[:200]}")
    updated_response = []
    AI_TOTAL_PAGE = len(response["DocDetection"])
    for index, each_page in enumerate(response["DocDetection"]):
        print(f"Page {index+1} DocType : {each_page['DOCUMENT_TYPE']}")
        mydict = {"documentType": {**addon,"value": each_page["DOCUMENT_TYPE"] if each_page["DOCUMENT_TYPE"] != "NA" else "other"},
            'pageNo':{**addon,"value": [index+1]}}
        if each_page["DOCUMENT_TYPE"] in ["PAN CARD", "AADHAAR CARD", "DRIVING LICENCE", "VOTER CARD", "PASSPORT"]:
            mydict.update({"subDocumentType": {**addon,"value": each_page.get("SUB_TYPE","")}})
        ai_dict = {
            "AI_DOCUMENT_TYPE": mydict["documentType"]["value"],
            "AI_PAGE_NO": mydict["pageNo"]["value"],
            "source": db_dict["source"],
            "txnId": db_dict["txnId"],
            "AI_TOTAL_PAGE": AI_TOTAL_PAGE
        }
        docai_database({}, "AI_RESPONSE", "DOC_DETECTION", ai_dict)
        updated_response.append(mydict)
    request["DATA"] = updated_response
    prepop_folder = config.path + f"{request['TXN_ID']}/" + "PREPOP"
    doc_detection_folder = config.path + f"{request['TXN_ID']}/" + "DOCDETECTION"
    if not os.path.exists(doc_detection_folder): os.makedirs(doc_detection_folder)
    if not os.path.exists(prepop_folder): os.makedirs(prepop_folder)
    with open(doc_detection_folder + "/response.json", "w") as outfile: json.dump(request, outfile, indent=4)        
    # with open(prepop_folder + "/single_output.json", "w") as outfile: json.dump(request["DATA"], outfile, indent=4)        
    return request


def genericOcrRequest(request):
    request.update({
        "CLIENT": config.CLIENT_NAME,
        "CLIENT_ID": OCR_GENERIC_MASTER["CLIENT_ID"],
        "CLIENT_SECRET": OCR_GENERIC_MASTER["CLIENT_SECRET"],
        "OCR_ENGINE": OCR_GENERIC_MASTER["OCR_ENGINE"],
    })
    request["DATA"] = [{"base64":base64.b64encode(open(i.replace(config.source, config.path), 'rb').read()).decode('utf-8'), "filename": os.path.splitext(os.path.basename(i))[0]} for i in request["DATA"]]
    return request