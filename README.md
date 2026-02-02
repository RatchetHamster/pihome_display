# pihome_display
Small pi based display for home data

##  Setup:  
Install pi os (WITH desktop).  
sudo apt update && sudo apt upgrade -y   
sudo nano /boot/firmware/config.txt  
comment out only line: "dtoverlay=vc4-kms-v3d"  
Add to EOF:  

# Enable SPI and Waveshare TFT  
dtparam=spi=on  
dtoverlay=waveshare35a  
dtoverlay=waveshare35a,rotate=0  

# Disable audio (avoid conflicts)  
dtparam=audio=off  

Create Xorg fbdev config:  
  
sudo mkdir -p /etc/X11/xorg.conf.d  
sudo nano /etc/X11/xorg.conf.d/99-fbdev.conf  
  
Section "Device"  
    Identifier "SPI TFT"  
    Driver "fbdev"  
    Option "fbdev" "/dev/fb1"  
    Option "SwapbuffersWait" "true"  
EndSection  

Section "Monitor"  
    Identifier "Monitor0"  
EndSection  

Section "Screen"  
    Identifier "Screen0"  
    Device "SPI TFT"  
    Monitor "Monitor0"  
    DefaultDepth 16  
    SubSection "Display"  
        Depth 16  
        Modes "480x320"  
    EndSubSection  
EndSection  

Consol Boot:  
sudo systemctl set-default multi-user.target  

sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.bak  
sudo sed -i '1 s/$/ fbcon=map:10 fbcon=font:VGA8x8/' /boot/firmware/cmdline.txt  

# Input Touch:  
sudo apt-get update  
sudo apt-get install -y xserver-xorg-input-evdev xinput libinput-tools  
sudo cp /usr/share/X11/xorg.conf.d/10-evdev.conf /usr/share/X11/xorg.conf.d/45-evdev.conf  
sudo nano /usr/share/X11/xorg.conf.d/99-calibration.conf  

Section "InputClass"  
    Identifier      "calibration"  
    MatchProduct    "ADS7846 Touchscreen"  
    Option  "Calibration"   "3932 300 294 3801"  
    Option  "SwapAxes"      "1"  
    Option "EmulateThirdButton" "1"  
    Option "EmulateThirdButtonTimeout" "1000"  
    Option "EmulateThirdButtonMoveThreshold" "300"  
EndSection  

xinput_calibrator  
sudo reboot  

python -m venv /home/pi/venv
source /home/pi/python/venv/bin/activate
Install requirements from pip  
sudo apt-get install python3-tk -y  
sudo apt install git -y  
cd ~  
git clone https://github.com/RatchetHamster/pihome_display.git  
sudo reboot  

# Setup Service:  
sudo mv /home/pi/pihome_display/pihome_display.service /etc/systemd/system/  
sudo systemctl daemon-reload && sudo systemctl enable pihome_display  


Service file handles log automatically and log rotation. To view journals for debug:  
journalctl -u pihome_display.service -f  
