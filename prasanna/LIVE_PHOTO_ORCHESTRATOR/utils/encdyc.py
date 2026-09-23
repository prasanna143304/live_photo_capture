from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
import base64, hashlib, secrets
from flask import request
import json, os
from utils import config

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

def get_decryption_data(data):
    try:
        # data = request.json
        enc_keys = ["encryptedData","iv","encryptedKey"]
        for i in enc_keys:
            if i not in data:
                return [{"status": False, "errorMessage": f"{i} key is missing"}]
        decrypted_data = decrypt_data(data["encryptedData"], data["iv"], data["encryptedKey"], config.XBIZ_PRIVATE_KEY_PATH)
        if decrypted_data is None: return [{"status": False, "errorMessage": "Decryption failed"}]
        return decrypted_data
    except Exception as e:
        return [{"status": False, "errorMessage": e}]
    
def get_encryption_data(json_data):
    try:
        public_key_path = config.XBIZ_PUBLIC_KEY_PATH
        # public_key_path = config.APIGATEWAY_PUBLIC_KEY_PATH
        decoded_encrypted_data, iv, encrypted_symmetric_key = encrypt_data(json_data, public_key_path)
        result_data = {
            "encryptedData": decoded_encrypted_data,
            "iv": iv,
            "encryptedKey": encrypted_symmetric_key,
        }
        return result_data
    except Exception as e:
        return [{"status": False, "message": e}]