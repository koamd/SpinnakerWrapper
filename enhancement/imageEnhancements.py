import cv2

#helper file containing some useful image enhancement techniques


def exposureFusion( images: list):

    # Align input images
    alignMTB = cv2.createAlignMTB()
    
    #convert images to bgr
    color_img_list = []
    for image in images:
        color_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        color_img_list.append(color_img)
        
    alignMTB.process(color_img_list, color_img_list)

    mergeMertens = cv2.createMergeMertens()
    exposureFusion = mergeMertens.process(color_img_list)
    
    gray_img = cv2.cvtColor(exposureFusion*255, cv2.COLOR_BGR2GRAY)

    return gray_img

def clahe(image, clip_limit=2, tile_grid_size=(8, 8)):
    
    # Create equaliser using input parameters
    equaliser = cv2.createCLAHE(clipLimit=clip_limit, 
                                tileGridSize=tile_grid_size)
    
    return equaliser.apply(image)


if __name__ == '__main__':
    
    #read a image
    parcel_label_filepath = '../data/1 ChangiSingPost_01_20230203123108680_2096.jpg'

    parcel_numpy = cv2.imread(parcel_label_filepath, cv2.IMREAD_GRAYSCALE)

    out_img = clahe(parcel_numpy)

    cv2.imwrite('../data/cleanup.jpg', out_img)