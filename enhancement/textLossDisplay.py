import torch
import torch.optim as optim
import utils
from torchvision import transforms
import math
import numpy as np
import cv2 as cv
import os, sys
from pathlib import Path

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("Using device: {}".format(device))

currentFilePath = os.path.dirname(os.path.abspath(__file__))  #this will be removalNet folder
topSrcFolder = str(Path(currentFilePath).parents[0]) #import root folder path.

#print('topSrcFolder: ', topSrcFolder)
sys.path.append(topSrcFolder)


import model.Craft.craft as Craft

craft_model = Craft.CRAFT(pretrained=True, freeze=True).to(device)
pretrained_model_path = os.path.join(topSrcFolder,'pretrained_models/craft/craft_mlt_25k.pth') #should be added into config

craft_model.load_state_dict(Craft.copyStateDict(torch.load(pretrained_model_path)))

def cvt2HeatmapImg(img):
    img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    img = cv.applyColorMap(img, cv.COLORMAP_JET)
    return img

def create_heatmap_blended_image(original_image, text_score_image):
    score_text = text_score_image[0,:,:,0].cpu().data.numpy()
    render_img = score_text.copy()
    ret_score_text = cvt2HeatmapImg(render_img)

    dim = (original_image.shape[1], original_image.shape[0])  
    ret_score_text_resized = cv.resize(ret_score_text, dim, interpolation = cv.INTER_AREA)
    
    img_blend1 = cv.addWeighted(original_image, 0.6, ret_score_text_resized, 0.4, 0)
    concat_row_image = np.hstack((original_image, img_blend1))

    return concat_row_image

def normalize_mean_variance_tensor(in_img, mean=(0.485*255.0, 0.456*255.0, 0.406*255.0), variance=(0.229*255.0, 0.224*255.0, 0.225*255.0)):
    in_img = transforms.functional.normalize(in_img, mean=mean, std=variance) 
    return in_img

def normalize_mean_variance_tensor_single_channel(in_img, mean=(0.485+0.456+0.406), variance=(0.229*0.229 + 0.224*0.224 + 0.225*255.0)):
    in_img = transforms.functional.normalize(in_img, mean=mean*255.0, std=math.sqrt(variance) * 255.0) 
    return in_img

def craft_text_characters(img1):
    """Returns number of characters detected

    Args:
        craft_model (_type_): _description_
        img1 (_type_): _description_
        device (_type_): _description_

    Returns:
        _type_: _description_
    """
    convert_tensor = transforms.ToTensor()

    #convert CxHxW image to BxCxHxW image
    img1_bchw = convert_tensor(img1).to(device)
    img1_bchw = img1_bchw.unsqueeze(0)
    
    clamped_img1 = torch.clamp(img1_bchw, min=0, max=1)
    clamped_img1 = clamped_img1 * 255

    if img1_bchw.shape[1] == 3:
        out_image1 = normalize_mean_variance_tensor(clamped_img1)
    else:
        out_image1 = normalize_mean_variance_tensor_single_channel(clamped_img1)

    with torch.no_grad():
        craft_model.eval()
        img1_pred, _ = craft_model(out_image1)

    # out_text = img1_pred[0,:,:,0]
    # print('converting out_text to cpu ', out_text.shape)
    # out_text = out_text.cpu().data.numpy()

    rgb_draw = None

    if (len(img1.shape) == 3) and (img1.shape[2] == 3):
        rgb_draw = create_heatmap_blended_image(img1, img1_pred)
    else:
        gray_rgb = cv.cvtColor(img1 ,cv.COLOR_GRAY2BGR)
        rgb_draw = create_heatmap_blended_image(gray_rgb, img1_pred)

    return rgb_draw