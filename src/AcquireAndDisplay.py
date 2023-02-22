# coding=utf-8
# =============================================================================
# Copyright (c) 2001-2021 FLIR Systems, Inc. All Rights Reserved.
#
# This software is the confidential and proprietary information of FLIR
# Integrated Imaging Solutions, Inc. ("Confidential Information"). You
# shall not disclose such Confidential Information and shall use it only in
# accordance with the terms of the license agreement you entered into
# with FLIR Integrated Imaging Solutions, Inc. (FLIR).
#
# FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
# SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
# SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
# THIS SOFTWARE OR ITS DERIVATIVES.
# =============================================================================
#
# This AcquireAndDisplay.py shows how to get the image data, and then display images in a GUI.
# This example relies on information provided in the ImageChannelStatistics.py example.
#
# This example demonstrates how to display images represented as numpy arrays.
# Currently, this program is limited to single camera use.
# NOTE: keyboard and matplotlib must be installed on Python interpreter prior to running this example.

import os
import PySpin
import matplotlib.pyplot as plt
import sys
import keyboard
import time
import numpy as np


global continue_recording
continue_recording = True


def handle_close(evt):
    """
    This function will close the GUI when close event happens.

    :param evt: Event that occurs when the figure closes.
    :type evt: Event
    """

    global continue_recording
    continue_recording = False

def print_device_info(cam):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param cam: Camera to get device information from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    print('\n*** DEVICE INFORMATION ***\n')

    try:
        result = True
        nodemap = cam.GetTLDeviceNodeMap()

        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not readable.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex.message)
        return False

    return result

def acquire_and_display_images(cam, nodemap, nodemap_tldevice):
    """
    This function continuously acquires images from a device and display them in a GUI.

    :param cam: Camera to acquire images from.
    :param nodemap: Device nodemap.
    :param nodemap_tldevice: Transport layer device nodemap.
    :type cam: CameraPtr
    :type nodemap: INodeMap
    :type nodemap_tldevice: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    global continue_recording

    sNodemap = cam.GetTLStreamNodeMap()

    #set camera to get image in polarized8 format. 
    if cam.PixelFormat.GetAccessMode() == PySpin.RW:
        cam.PixelFormat.SetValue(PySpin.PixelFormat_Polarized8)
        print('Pixel format set to %s...' % cam.PixelFormat.GetCurrentEntry().GetSymbolic())
    else:
        print('Pixel format not available...')
        result = False

    node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
    width_to_set = 2048
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
    height_to_set = 2448
    if  PySpin.IsReadable(node_height) and PySpin.IsWritable(node_height):

        height_to_set = node_height.GetMax()
        node_height.SetValue(height_to_set)
        print('Height set to %i...' % node_height.GetValue())

    else:
        print('Height not readable or writable...')

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
    
    print('*** IMAGE ACQUISITION ***\n')
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

        #  Begin acquiring images
        #
        #  *** NOTES ***
        #  What happens when the camera begins acquiring images depends on the
        #  acquisition mode. Single frame captures only a single image, multi
        #  frame catures a set number of images, and continuous captures a
        #  continuous stream of images.
        #
        #  *** LATER ***
        #  Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()

        print('Acquiring images...')

        #  Retrieve device serial number for filename
        #
        #  *** NOTES ***
        #  The device serial number is retrieved in order to keep cameras from
        #  overwriting one another. Grabbing image IDs could also accomplish
        #  this.
        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print('Device serial number retrieved as %s...' % device_serial_number)

        # Close program
        print('Press enter to close the program..')

        # Figure(1) is default so you can omit this line. Figure(0) will create a new window every time program hits this line
        fig = plt.figure(1)

        # Close the GUI when close event happens
        fig.canvas.mpl_connect('close_event', handle_close)

        # Retrieve and display images
        while(continue_recording):
            try:

                #  Retrieve next received image
                #
                #  *** NOTES ***
                #  Capturing an image houses images on the camera buffer. Trying
                #  to capture an image that does not exist will hang the camera.
                #
                #  *** LATER ***
                #  Once an image from the buffer is saved and/or no longer
                #  needed, the image must be released in order to keep the
                #  buffer from filling up.
                
                image_result = cam.GetNextImage(1000)

                #  Ensure image completion
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

                else:                    

                    # Getting the image data as a numpy array
                    image_polarized_i0 = PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I0).GetNDArray()
                    image_polarized_i45 = PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I45).GetNDArray()
                    image_polarized_i90= PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I90).GetNDArray()
                    image_polarized_i135 = PySpin.ImageUtilityPolarization.ExtractPolarQuadrant(image_result, PySpin.SPINNAKER_POLARIZATION_QUADRANT_I135).GetNDArray()

                    #append np array together
                    np_top_pair = np.concatenate((image_polarized_i0, image_polarized_i45), axis=1)
                    np_bottom_pair = np.concatenate((image_polarized_i90, image_polarized_i135), axis=1)
                    

                    #create original intensity image
                    #original_intensity = ((image_polarized_i0 + image_polarized_i45 + image_polarized_i90 + image_polarized_i135)/2.0).astype(np.uint8)
                    
                    image_dolp = PySpin.ImageUtilityPolarization.CreateDolp(image_result)
                    print("Bits per pixel DOLP: ", image_dolp.GetBitsPerPixel())
                    print("DOLP Pixel Format Name: ", image_dolp.GetPixelFormatName())
                    print("Height: ", image_dolp.GetHeight())
                    print("Width: ", image_dolp.GetWidth())
                    print("Channels: ", image_dolp.GetNumChannels())

                    dolp_float_array = image_dolp.GetData()
                    print("dolp max: ", np.max(dolp_float_array))

                    dolpNormalizedImage = PySpin.ImageUtility.CreateNormalized(image_dolp, PySpin.PixelFormat_Mono8, PySpin.SPINNAKER_SOURCE_DATA_RANGE_ABSOLUTE_DATA_RANGE)
                    print("dolpNormalizedImage Bits per pixel DOLP: ", dolpNormalizedImage.GetBitsPerPixel())
                    print("DOLP Pixel Format Name: ", dolpNormalizedImage.GetPixelFormatName())
                    print("Height: ", dolpNormalizedImage.GetHeight())
                    print("Width: ", dolpNormalizedImage.GetWidth())
                    print("Channels: ", dolpNormalizedImage.GetNumChannels())

                    image_dolp = dolpNormalizedImage.GetNDArray()

                    #get the min max in the dolp


                    #print(type(image_dolp))
                    original_intensity = ((image_polarized_i0 + image_polarized_i90)/2.0).astype(np.uint8)
                    
                    #image_data = np.concatenate((np_top_pair, np_bottom_pair), axis=0)
                    image_deglared = PySpin.ImageUtilityPolarization.CreateGlareReduced(image_result).GetNDArray()

                    #print(original_intensity.dtype)
                    np_top_row = np.concatenate((np_top_pair, image_dolp), axis=1)
                    np_bot_row = np.concatenate((np_bottom_pair, image_deglared), axis=1)

                    image_data = np.concatenate((np_top_row, np_bot_row), axis=0)

                    # Draws an image on the current figure
                    plt.imshow(image_data, cmap='gray')

                    # Interval in plt.pause(interval) determines how fast the images are displayed in a GUI
                    # Interval is in seconds.
                    plt.pause(0.001)

                    # Clear current reference of a figure. This will improve display speed significantly
                    plt.clf()
                    
                    # If user presses enter, close the program
                    # if keyboard.is_pressed('ENTER'):
                    #     print('Program is closing...')
                        
                    #     # Close figure
                    #     plt.close('all')             
                    #     input('Done! Press Enter to exit...')
                    #     continue_recording=False                        

                #  Release image
                #
                #  *** NOTES ***
                #  Images retrieved directly from the camera (i.e. non-converted
                #  images) need to be released in order to keep from filling the
                #  buffer.
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                break
                

        #  End acquisition
        #
        #  *** NOTES ***
        #  Ending acquisition appropriately helps ensure that devices clean up
        #  properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return True


def run_single_camera(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        # Initialize camera
        cam.Init()
        
        #print_device_info(cam)

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Acquire images
        result &= acquire_and_display_images(cam, nodemap, nodemap_tldevice)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def main():
    """
    Example entry point; notice the volume of data that the logging event handler
    prints out on debug despite the fact that very little really happens in this
    example. Because of this, it may be better to have the logger set to lower
    level in order to provide a more concise, focused log.

    :return: True if successful, False otherwise.
    :rtype: bool
    """
    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # Run example on each camera
    for i, cam in enumerate(cam_list):

        print('Running example for camera %d...' % i)

        result &= run_single_camera(cam)
        print('Camera %d example complete... \n' % i)

    # Release reference to camera
    # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
    # cleaned up when going out of scope.
    # The usage of del is preferred to assigning the variable to None.
    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    input('Done! Press Enter to exit...')
    return result


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
