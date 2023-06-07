from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QThread
from pathlib import Path
import sys
import os 
import cv2
import numpy as np
import requests

#add root folder to path.  
currentFilePath = os.path.dirname(os.path.abspath(__file__))  #this will be controller folder
topSrcFolder = str(Path(currentFilePath).parents[1]) #<root> folder
sys.path.append(topSrcFolder)
sys.path.append(os.path.join(topSrcFolder, 'camera'))

from gui.generated.ui_polarcam import Ui_PolarCam
from camera.FLIRPolarCam import PolarCam
from utils.imageUtils import save_images_to_folder, save_image_to_folder
from enhancement.imageEnhancements import exposureFusion, clahe
from enhancement.textLossDisplay import craft_text_characters

import utils.utils

class VideoPreviewCapture(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = False

    def run(self):

        self._run_flag = True
        # capture from web cam
        cap = cv2.VideoCapture(0)
        while self._run_flag:
            ret, cv_img = cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)
        # shut down capture system
        cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.wait()

class VideoSequenceCapture(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray, list)

    def __init__(self, polar_cam, num_frames):
        super().__init__()
        
        self.polar_cam = polar_cam
        self.num_frames_in_seq = num_frames

    def run(self):

        # capture from web cam
        print("Start Acquisition")
        self.polar_cam.start_acquisition()

        #display and resize images
        #concat image to a column. 
         #perform sequence capture. 
        image_result_array = self.polar_cam.grab_sequence(self.num_frames_in_seq)

        if len(image_result_array) > 0:
            np_top_pair = image_result_array[0]

            for i in range(1, self.num_frames_in_seq):
                np_top_pair = np.concatenate((np_top_pair, image_result_array[i]), axis=1)

            self.change_pixmap_signal.emit(np_top_pair, image_result_array) #emit signal. 
        
        print('Stop Acquisition')

        self.polar_cam.stop_acquisition()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self.wait()

        print('Thread Stop')

class VideoPreviewPolarCam(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, polar_cam):
        super().__init__()
        
        self.polar_cam = polar_cam

    def run(self):

        self._run_flag = True
        # capture from web cam

        #set mode 
        self.polar_cam.configure_camera_to_polarized8_format()

        print("Start Thread")
        self.polar_cam.start_acquisition()

        while self._run_flag:
            image_result = self.polar_cam.grab_image()

            if image_result == None:
                print("No image received")
                continue
            
            #extract polarized image
            image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared = self.polar_cam.grab_all_polarized_image(image_result)
            image_display = PolarCam.append_images_to_panel(image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared)
        
            self.change_pixmap_signal.emit(image_display)
        
        # shut down capture system
        self.polar_cam.stop_acquisition()

        print('Stop Acquisition')

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.wait()

        print('Thread Stop')

        
class PolarCamMainApp(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PolarCamMainApp, self).__init__(parent)

        self.ui = Ui_PolarCam() #link to the UI class
        self.ui.setupUi(self)

        self.polar_cam = PolarCam()

        #define config variables
        self.imageParams = {}

        self.sequence = []
        self.loadPredefinedSequence('gui/config/sequence_config.txt')

        #define other forms and menus
        self.addMenuItems()
        self.setupEventHandlers()

        self.setupConfigUI()

        #create thread
        self.thread = VideoPreviewPolarCam(self.polar_cam)
        self.thread_sequence = VideoSequenceCapture(self.polar_cam, len(self.sequence))

        # connect its signal to the update_image slot
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread_sequence.change_pixmap_signal.connect(self.update_image_seq)

        self.bCaptureImgFlag = False
        self.sequence_images = []

        self.bDisplayCapture = False
        self.last_deglared_image = np.zeros([])
        self.filtered_polarized_image = np.zeros([])

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Window Close', 'Are you sure you want to close the window?',
				QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
            print('Window closed')
        else:
            event.ignore()

        self.thread.stop()
        self.thread_sequence.stop()
        self.polar_cam.release()

    def setupEventHandlers(self):
        self.ui.startCameraBtn.clicked.connect(self.startCameraPreview)
        self.ui.stopCameraBtn.clicked.connect(self.stopCameraPreview)

        self.ui.ConfigureSequenceBtn.clicked.connect(self.setupSequenceCapture)
        self.ui.startSequenceBtn.clicked.connect(self.startSequenceCapture)
        self.ui.resetSequenceBtn.clicked.connect(self.resetSequence)
        self.ui.saveSeqToFileBtn.clicked.connect(self.saveSequence)
        self.ui.sendImageToOCR_Btn.clicked.connect(self.clean_up_image)

        self.ui.GainAuto_chkBox.stateChanged.connect(self.gainAutoStateChanged)
        self.ui.shutterAuto_chkBox.stateChanged.connect(self.shutterAutoStateChanged)
        self.ui.frameRateAuto_chkbox.stateChanged.connect(self.fpsAutoStateChanged)
        self.ui.captureImg_btn.clicked.connect(self.performImageCapture)

        self.ui.view_captureCheckBox.stateChanged.connect(self.displayCaptureStateChanged)

    def setupConfigUI(self):
        
        #*************** Add shutter slider ******************
        #get min, max gain value
        self.polar_cam.set_exposure_auto(False)
        self.setSliderBar('shutter', 0, 100, 1)

        #get current exposure value
        min_shutter_val = self.polar_cam.min_shutter_speed_us
        max_shutter_val = min(self.polar_cam.max_shutter_speed_us, 500000)
        curr_exposure_value = self.polar_cam.get_curr_exposure_value() 

        target_shutter_slider_val = (curr_exposure_value - min_shutter_val)/(max_shutter_val - min_shutter_val) * 100

        #determine position of exposure value in slider bar and update it
        self.ui.shutterSlider.setValue((int)(target_shutter_slider_val))
        formatted_float = "{:.2f}".format(curr_exposure_value)
        self.ui.shutter_us_textlabel.setText(formatted_float)

        #add slots for shutter
        self.ui.shutterSlider.valueChanged.connect(self.shutterSliderValuechange)

        #*************** Add gain slider ******************

        #get min, max shutter value
        self.polar_cam.set_gain_auto(False)
        self.setSliderBar('gain', 0, 100, 1) #100 steps
        curr_gain_value = self.polar_cam.get_curr_gain_value() 

        target_gain_slider_val = (curr_gain_value - self.polar_cam.min_gain)/(self.polar_cam.max_gain - self.polar_cam.min_gain) * 100
        self.ui.gainSlider.setValue((int)(target_gain_slider_val))

        formatted_gain_float = "{:.2f}".format(curr_gain_value)
        self.ui.gain_db_textlabel.setText(formatted_gain_float)

        self.ui.gainSlider.valueChanged.connect(self.gainSliderValuechange)

        #*************** Add fps slider ******************
        self.polar_cam.set_fps_auto(True)
        # self.setSliderBar('fps', 0, 100, 1) #100 steps
        curr_fps_value = self.polar_cam.get_fps_value() 
        # target_fps_slider_val = (curr_fps_value - self.polar_cam.min_fps)/(self.polar_cam.max_fps - self.polar_cam.min_fps) * 100

        # print('target_fps_slider_val', target_fps_slider_val)
        # self.ui.frameRateSlider.setValue((int)(target_fps_slider_val))

        formatted_fps_float = "{:.2f}".format(curr_fps_value)
        self.ui.fps_textLabel.setText(formatted_fps_float)

        #self.ui.frameRateSlider.valueChanged.connect(self.fpsSliderValuechange)

        

    def loadPredefinedSequence(self, configName):

        with open(configName, 'r') as f: 
            Lines = f.readlines()
            for line in Lines:
                width, height, exposure_us, gain_db = line.split(',')
                self.sequence.append( (int(width), int(height), int(exposure_us), int(gain_db)) )

    def addMenuItems(self):
        """Create Top Menu items
        """

        pass

    def displayImageOnQLabel(self, opencvImage: cv2.Mat):
        #load image into qimage
        #load qimage into qpixmap
        #load qpixmap into qlabel

        #perform resizing first, before we do color conversion. 
        h = 0
        w = 0
        ch = 1

        if len(opencvImage.shape) == 3:
            h, w, ch = opencvImage.shape
        else:
            h, w = opencvImage.shape

        #print(h,w,ch)
        #resize the image we have to the maximum size allowed.

        scaling_factor_y = float(h) / self.ui.cameraFeedLabel.maximumSize().height()        
        display_width = int(w / scaling_factor_y)
        self.imageParams['scale_factor'] = scaling_factor_y


        # scaling_factor_x = float(w) / self.ui.cameraFeedLabel.maximumSize().width()        
        # display_height = int(h / scaling_factor_x)
        # self.imageParams['scale_factor'] = scaling_factor_x
        
        dim = (display_width, self.ui.cameraFeedLabel.maximumSize().height())
        resized = cv2.resize(opencvImage, dim, interpolation = cv2.INTER_AREA)

        rgb_image = np.zeros((1,1))
        if(ch == 3):
            rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)

        bytes_per_line = 3 * display_width
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, display_width, 
                                            self.ui.cameraFeedLabel.maximumSize().height(), bytes_per_line, QtGui.QImage.Format_RGB888)

        self.ui.cameraFeedLabel.setPixmap(QtGui.QPixmap.fromImage(convert_to_Qt_format)) 

    def startCameraPreview(self):
        # start the thread
        self.thread.start()

    def stopCameraPreview(self):
        self.thread.stop()

    def performImageCapture(self): 
        self.bCaptureImgFlag = True
        print('Prepare to Capture Image')

    @pyqtSlot(np.ndarray, list)
    def update_image_seq(self, cv_img, cv_img_seq):
        #display on label
        self.displayImageOnQLabel(cv_img)
        self.sequence_images = cv_img_seq

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        #display on label
        h, w = cv_img.shape

        right_image = cv_img[0:h, (2*w)//3 : w].copy()

        if self.bCaptureImgFlag:
            #extract first 4 quarter.     
            
            #run through text loss
            self.filtered_polarized_image = right_image[h//2:h, 0:w].copy()
            self.last_deglared_image = craft_text_characters(right_image)

            #output_img = cv_img[0:h, 0:(2*w)//3]
            #save_image_to_folder(output_img)

            save_image_to_folder(cv_img)

            self.bCaptureImgFlag = False
        
        self.drawTextOnImage(right_image, "Original", origin=(100, h//2 - 30), font = cv2.FONT_HERSHEY_SIMPLEX, fontScale=3, color=(255, 0, 0), thickness=2)
        self.drawTextOnImage(right_image, "Deglare", origin=(100, h - 30), font = cv2.FONT_HERSHEY_SIMPLEX, fontScale=3, color=(255, 0, 0), thickness=2)

        if not self.bDisplayCapture:
            self.displayImageOnQLabel(right_image)
        else:
            self.displayImageOnQLabel(self.last_deglared_image) #run through craft model GPU

    def drawTextOnImage(self, input_img, text_str: str, origin: tuple, font, fontScale, color, thickness):

        input_img = cv2.putText(input_img, text_str, origin, font, 
                   fontScale, color, thickness, cv2.LINE_AA)
        

    def clean_up_image(self):
        """cleans up a received image and sends them to OCR

        Args:
            cv_img (_type_): _description_
        """

        print('Performing cleanup')

        #convert self.last_deglared_image to byte array
        #send to flask endpoint for image cleanup. Pack image to byte array and send. 

        print(self.filtered_polarized_image.shape)
        h, w = self.filtered_polarized_image.shape

        clip_limit_1 = 3
        tile_grid_size_1 = (20, 20)
        clahe_1 = clahe(self.filtered_polarized_image, clip_limit_1, tile_grid_size_1)

        #save image to file. To be tested.. 
        cv2.imwrite(os.path.join(topSrcFolder, 'tmp/tempImg.png'), clahe_1)

        files = {
            'file': open(os.path.join(topSrcFolder, 'tmp/tempImg.png'), 'rb')
        }

        response = requests.post('http://192.168.1.101:8080/', files=files) 

        if response.status_code == 200: 
            print('[Info] Sent Deglared image to OCR Reader Success ')
        else:
            print('[Error] Failed to send request. Error Code: ', response.status_code)


    def setSliderBar(self, slider_type, min_val, max_val, single_step):
        if slider_type == 'gain':
            self.ui.gainSlider.setMinimum(min_val)
            self.ui.gainSlider.setMaximum(max_val)
            self.ui.gainSlider.setSingleStep(single_step)

        elif slider_type == 'shutter':
            self.ui.shutterSlider.setMinimum(min_val)
            self.ui.shutterSlider.setMaximum(max_val)
            self.ui.shutterSlider.setSingleStep(single_step)

        elif slider_type == 'fps':
            self.ui.shutterSlider.setMinimum(min_val)
            self.ui.shutterSlider.setMaximum(max_val)
            self.ui.shutterSlider.setSingleStep(single_step)

    def setupSequenceCapture(self):
        self.polar_cam.configure_image_sequence(self.sequence)

    def startSequenceCapture(self):
        self.polar_cam.configure_image_sequence(self.sequence)
        self.thread_sequence.start()

    def resetSequence(self):
        #return camera back to auto gain and auto exposure
        self.polar_cam.reset_sequencer()

    def saveSequence(self):
        fused_img = exposureFusion(self.sequence_images)
        self.sequence_images.append(fused_img)
        save_images_to_folder(self.sequence_images)
    
    def displayCaptureStateChanged(self):
        self.bDisplayCapture = self.ui.view_captureCheckBox.isChecked()

    def gainAutoStateChanged(self):
        self.polar_cam.set_gain_auto(self.ui.GainAuto_chkBox.isChecked())
        self.ui.gainSlider.setEnabled(not self.ui.GainAuto_chkBox.isChecked())


    def shutterAutoStateChanged(self):
        self.polar_cam.set_exposure_auto(self.ui.shutterAuto_chkBox.isChecked())
        self.ui.shutterSlider.setEnabled(not self.ui.shutterAuto_chkBox.isChecked())

    def shutterSliderValuechange(self):
        new_value = self.ui.shutterSlider.value()
        self.polar_cam.set_exposure_time_from_step(new_value)
        
        #modify the polarcam value. 
        curr_exposure_value = self.polar_cam.get_curr_exposure_value() 

        #convert float to string value
        formatted_float = "{:.2f}".format(curr_exposure_value)
        self.ui.shutter_us_textlabel.setText(formatted_float)

        #update fps also
        curr_fps_value = self.polar_cam.get_fps_value() 

        print('fps: ', curr_fps_value)
        #convert float to string value
        formatted_fps_float = "{:.2f}".format(curr_fps_value)
        self.ui.fps_textLabel.setText(formatted_fps_float)

    def gainSliderValuechange(self):
        new_value = self.ui.gainSlider.value()
        self.polar_cam.set_gain_value_from_step(new_value)
        
        #modify the polarcam value. 
        curr_gain_value = self.polar_cam.get_curr_gain_value() 

        #convert float to string value
        formatted_float = "{:.2f}".format(curr_gain_value)
        self.ui.gain_db_textlabel.setText(formatted_float)

    def fpsAutoStateChanged(self):
        self.polar_cam.set_fps_auto(self.ui.frameRateAuto_chkbox.isChecked())
        self.ui.frameRateSlider.setEnabled(not self.ui.frameRateAuto_chkbox.isChecked())

    def fpsSliderValuechange(self):
        new_value = self.ui.frameRateSlider.value()
        self.polar_cam.set_fps_value_from_step(new_value)

        #modify the polarcam value. 
        curr_fps_value = self.polar_cam.get_fps_value() 

        #convert float to string value
        formatted_float = "{:.2f}".format(curr_fps_value)
        self.ui.fps_textLabel.setText(formatted_float)


def main():
    app = QApplication(sys.argv)
    form = PolarCamMainApp()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()