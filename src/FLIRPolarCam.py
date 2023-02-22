import PySpin
import sys
import numpy as np
import matplotlib.pyplot as plt

class PolarCam:

    def __init__(self):
        self.system = PySpin.System.GetInstance()
        # Get current library version
        version = self.system.GetLibraryVersion()
        print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

        self.cam_list = self.system.GetCameras()
        num_cameras = self.cam_list.GetSize()

        print('Number of cameras detected: %d' % num_cameras)

        if num_cameras == 0:

            print('Not enough cameras!')

            # Clear camera list before releasing system
            self.cam_list.Clear()

            # Release system instance
            self.system.ReleaseInstance()

            return

        #set the default settings. 
        for i, cam in enumerate(self.cam_list):
            self.configure_default_settings(cam)

    def __del__(self):

        for i, cam in enumerate(self.cam_list):
            del cam

        # Clear camera list before releasing system
        self.cam_list.Clear()

        # Release system instance
        self.system.ReleaseInstance()


    def configure_default_settings(self, cam):
        
        cam.Init()
        #configure stream
        self.configure_stream_settings(cam)
        self.configure_exposure_control(cam)
        self.configure_acquisition_control(cam)

    def configure_exposure_control(self, cam):

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        node_exposure_lighting_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AutoExposureLightingMode'))
        if not PySpin.IsReadable(node_exposure_lighting_mode) or not PySpin.IsWritable(node_exposure_lighting_mode):
            print('\nUnable to set Exposure Lighting Mode. Aborting...\n')
            return False

        exposure_mode_front_light = node_exposure_lighting_mode.GetEntryByName('Frontlight')
        if not PySpin.IsReadable(exposure_mode_front_light):
            print('\nUnable to set Exposure Front Light. Aborting...\n')
            return False

        lighting_front_light = exposure_mode_front_light.GetValue()
        node_exposure_lighting_mode.SetIntValue(lighting_front_light)

        #TODO: Likely need to set upper and lower limit of exposure or modify actual exposure. 

    def configure_acquisition_control(self, cam):
        
        #set the width and height. 
        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        #Set camera to get image in polarized8 format. 
        if cam.PixelFormat.GetAccessMode() == PySpin.RW:
            cam.PixelFormat.SetValue(PySpin.PixelFormat_Polarized8)
            print('Pixel format set to %s...' % cam.PixelFormat.GetCurrentEntry().GetSymbolic())
        else:
            print('Pixel format not available...')
            result = False

         # Set maximum width
        node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
        if PySpin.IsReadable(node_width) and PySpin.IsWritable(node_width):

            width_to_set = node_width.GetMax()
            node_width.SetValue(width_to_set)
            print('Width set to %i...' % node_width.GetValue())

        else:
            print('Width not readable or writable...')

        # Set maximum height
        #
        # *** NOTES ***
        # A maximum is retrieved with the method GetMax(). A node's minimum and
        # maximum should always be a multiple of its increment.
        node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
        if  PySpin.IsReadable(node_height) and PySpin.IsWritable(node_height):

            height_to_set = node_height.GetMax()
            node_height.SetValue(height_to_set)
            print('Height set to %i...' % node_height.GetValue())

        else:
            print('Height not readable or writable...')

        print('*** Setting IMAGE ACQUISITION Mode ***\n')

        try:
            node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
            if not PySpin.IsReadable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
                print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
                return False

            # Retrieve entry node from enumeration node
            node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
            if not PySpin.IsReadable(node_acquisition_mode_continuous):
                print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
                return False
            
            # Retrieve integer value from entry node
            acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

            # Set integer value from entry node as new value of enumeration node
            node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

            print('Acquisition mode set to continuous...')

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False
    
    def configure_stream_settings(self, cam):
        """Configure stream settings. Default: Set Stream to Newest Only

        Args:
            cam (_type_): _description_

        Returns:
            _type_: _description_
        """
        sNodemap = cam.GetTLStreamNodeMap()

        # Change bufferhandling mode to NewestOnly
        node_bufferhandling_mode = PySpin.CEnumerationPtr(sNodemap.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsReadable(node_bufferhandling_mode) or not PySpin.IsWritable(node_bufferhandling_mode):
            print('Unable to set stream buffer handling mode.. Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_newestonly = node_bufferhandling_mode.GetEntryByName('NewestOnly')
        if not PySpin.IsReadable(node_newestonly):
            print('Unable to set stream buffer handling mode.. Aborting...')
            return False

        # Retrieve integer value from entry node
        node_newestonly_mode = node_newestonly.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_bufferhandling_mode.SetIntValue(node_newestonly_mode)

    def start_acquisition(self):
        for i, cam in enumerate(self.cam_list):
            self.start_acquisition_cam(cam)

    def start_acquisition_cam(self, cam):
        cam.BeginAcquisition()

    def stop_acquisition(self):
        for i, cam in enumerate(self.cam_list):
            self.stop_acquisition_cam(cam)

    def stop_acquisition_cam(self, cam):
        try:
            # Initialize camera
            cam.EndAcquisition()
            cam.DeInit()

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)

    @staticmethod
    def append_images_to_panel(image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared):
        np_top_pair = np.concatenate((image_polarized_i0, image_polarized_i45), axis=1)
        np_bottom_pair = np.concatenate((image_polarized_i90, image_polarized_i135), axis=1)
        
        np_top_row = np.concatenate((np_top_pair, image_dolp), axis=1)
        np_bot_row = np.concatenate((np_bottom_pair, image_deglared), axis=1)
        image_data = np.concatenate((np_top_row, np_bot_row), axis=0)

        return image_data
        
    def grab_all_polarized_image(self, image_result):
        """Extract the polarization images from the raw polarized 8 image. 

        Args:
            image_result (_type_): ImagePtr. Polarized8 format. 
        """
        image_polarized_i0 = PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I0).GetNDArray()
        image_polarized_i45 = PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I45).GetNDArray()
        image_polarized_i90= PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I90).GetNDArray()
        image_polarized_i135 = PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I135).GetNDArray()

        image_dolp = PySpin.ImageUtilityPolarization.CreateDolp(image_result)
        dolpNormalizedImage = PySpin.ImageUtility.CreateNormalized(image_dolp, PySpin.PixelFormat_Mono8, PySpin.SPINNAKER_SOURCE_DATA_RANGE_ABSOLUTE_DATA_RANGE)
        image_dolp = dolpNormalizedImage.GetNDArray()
        image_deglared = PySpin.ImageUtilityPolarization.CreateGlareReduced(image_result).GetNDArray()

        return image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared

    def grab_image(self):
        for i, cam in enumerate(self.cam_list):
            return self.grab_image_cam(cam)
        
        return None
        
    def grab_image_cam(self, cam):
        
        image_result = cam.GetNextImage(1000)
        if image_result.IsIncomplete():
            print('Image incomplete with image status %d ...' % image_result.GetImageStatus())
            return None
        
        image_copy = PySpin.Image.Create()
        image_copy.DeepCopy(image_result)
        return image_copy

    def run_single_camera(self, cam):

        try:
            nodemap_tldevice = cam.GetTLDeviceNodeMap()

            # Initialize camera
            cam.Init()
            
            # Retrieve GenICam nodemap
            nodemap = cam.GetNodeMap()


            cam.DeInit()

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)

def handle_close(evt):
    """
    This function will close the GUI when close event happens.

    :param evt: Event that occurs when the figure closes.
    :type evt: Event
    """

    global start_capturing
    start_capturing = False

def main():

    polar_cam = PolarCam()
    polar_cam.start_acquisition()

    fig = plt.figure(1)
    fig.canvas.mpl_connect('close_event', handle_close)

    counter = 0
    global start_capturing
    start_capturing = True

    #put a while loop. Grab the frames. 
    while start_capturing:

        print("Counter: ", counter)
        #grab image
        image_result = polar_cam.grab_image()

        if image_result == None:
            print("[Error] Unable to capture image")
            break
        
        #extract polarized image
        image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared = polar_cam.grab_all_polarized_image(image_result)
        image_display = PolarCam.append_images_to_panel(image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared)
        
                    # If user presses enter, close the program
        
        plt.imshow(image_display, cmap='gray')
        plt.pause(0.001)
        plt.clf()

        counter+=1


    polar_cam.stop_acquisition()


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
