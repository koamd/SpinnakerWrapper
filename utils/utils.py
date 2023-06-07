import base64
import cv2
import numpy as np

def b64str_to_image(b64_str: str) -> np.array:
    decoded_data = base64.b64decode(b64_str)
    np_data = np.frombuffer(decoded_data, np.uint8)
    return cv2.imdecode(np_data, cv2.IMREAD_UNCHANGED)


def path_to_b64str(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string.decode('utf-8')

def numpy_to_b64(np_image):
    s = base64.b64encode(np_image)
    
    return s

def b64_to_numpy(b64: str):
    r = base64.decodebytes(b64)
    q = np.frombuffer(r, dtype=np.float64)

    return q
