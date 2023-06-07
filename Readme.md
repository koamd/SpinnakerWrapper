# 1. Spinnaker Wrapper

## Requirements
* python 3.8 and above
* FLIR Spinnaker 3.0.0
* QT libraries (Refer to Section 2)

Download the following packages from FLIR:

spinnaker-3.0.0.118-amd64-pkg

spinnaker_python-3.0.0.118-cp38-cp38-linux_x86_64.tar.gz

1. Install Spinnaker library and camera drivers for desktop. Follow the installation instructions inside

spinnaker-3.0.0.118-amd64-pkg/spinnaker-3.0.0.118-amd64/README

2. Install Spinnaker library for python. Follow the Readme.txt inside:

spinnaker_python-3.0.0.118-cp38-cp38-linux_x86_64/Readme.txt

# 2. Qt Setup for GUI

Run the following setup scripts to install the libraries required for qt

```
sudo apt update -q
sudo apt install -y -q build-essential libgl1-mesa-dev

sudo apt install -y -q libxkbcommon-x11-0
sudo apt install -y -q libxcb-image0
sudo apt install -y -q libxcb-keysyms1
sudo apt install -y -q libxcb-render-util0
sudo apt install -y -q libxcb-xinerama0
sudo apt install -y -q libxcb-icccm4

sudo apt install -y qttools5-dev-tools
sudo apt install -y qttools5-dev

```

# 3. Creating the pip virtual environment from scratch

Create a virtual environment if you havent. In the project root folder: 

```
python3 -m venv venv
. venv/bin/activate
```

In the requirements.txt file, note that spinnaker-python path needs to point to the exact folder where the spinnaker-python *.whl file is located. 

After modification, install the requirements via inside your (venv) environment:

```
pip install requirements.txt
```

# 4. Modification of QT GUI

QT gui files are located in mot_labeller/gui/qt_ui folder.

If we have modified any of the UI files using Qt Designer, we will need to generate their python equivalent source file. Go into the `<root>`/gui/qt_ui folder

```pyuic5
pyuic5 polarcam.ui -o ../generated/ui_polarcam.py
```

# 5. Using the Wrapper

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

To Convert frame to the respective filtered images and deglared output in numpy.

```python
image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared = polar_cam.grab_all_polarized_image(image_result)
```

To append all the images to a single image:

```python
image_display = FLIRPolarCam.PolarCam.append_images_to_panel(image_polarized_i0, image_polarized_i45, image_polarized_i90, image_polarized_i135, image_dolp, image_deglared)
  
```

## Using the QT GUI For Image Capture


1. Activate virtual environment in the root project folder in terminal:

```
. venv/bin/activate
```

2. Ensure that the Polarization camera is connected. 
Run the GUI in the terminal: 

```
sudo -E python3.8 gui/controller/qt_polarcam_controller.py
```

### 3. To use the app. 

Click on "Start Camera Preview" button to start the video streaming. You should see the glare and deglared image. 

Click on "Capture" button to capture an image. 

Click on "Send to OCR" button to send the captured image to our OCR reader. 

