import os
import cv2
from datetime import datetime


def save_images_to_folder(input_image_np: list):
    #generate directory based on timestamp

    #now = datetime.now() # current date and time
    #date_time = now.strftime("%m_%d_%Y__%H:%M:%S")

    output_folder = os.path.join('output', generate_timestamp_for_image())
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    #save each individual image
    for index, image in enumerate(input_image_np):
        cv2.imwrite(output_folder+'/image_' + str(index) + '.png', image) 

def save_image_to_folder(input_image_np):
    output_folder = os.path.join('output', generate_date_for_output_folder())
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print('saving image in folder: ', output_folder)
    cv2.imwrite(output_folder+'/image_' + generate_timestamp_for_image() + '.png', input_image_np)

def generate_date_for_output_folder():
    now = datetime.now() # current date and time
    date_time = now.strftime("%d_%m_%Y")

    return date_time

def generate_timestamp_for_image():
    now = datetime.now() # current date and time
    date_time = now.strftime("%m_%d_%Y__%H-%M-%S")

    return date_time