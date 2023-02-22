# Spinnaker Wrapper

Download the following packages from FLIR:

spinnaker-3.0.0.118-amd64-pkg

spinnaker_python-3.0.0.118-cp38-cp38-linux_x86_64.tar.gz


1. Install Spinnaker library and camera drivers for desktop. Follow the installation instructions inside

spinnaker-3.0.0.118-amd64-pkg/spinnaker-3.0.0.118-amd64/README

2. Install Spinnaker library for python. Follow the Readme.txt inside:

spinnaker_python-3.0.0.118-cp38-cp38-linux_x86_64/Readme.txt


## 1. Using the Wrapper

The wrapper class is located inside PolarCam.py

To Initiate the camera:

```python
import FLIRPolarCam.PolarCam

polar_cam = FLIRPolarCam.PolarCam()
polar_cam.start_acquisition()

```

To Grab a frame (polarized8 format):

```python
image_result = polar_cam.grab_image()
```


To Convert frame to the respective filtered images and deglare output in numpy.

```python
image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared = polar_cam.grab_all_polarized_image(image_result)
```


To append all the images to a single image:

```python
image_display = FLIRPolarCam.PolarCam.append_images_to_panel(image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared)
  
```
