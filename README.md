# pihome_display
Small pi based display for home data

##  Setup:  
Install pi os (WITH desktop) and get the screen working from here (one I ahve is SPI waveshare 3.5in(A)):  
sudo apt update && sudo apt upgrade -y  
Run this: https://www.waveshare.com/wiki/3.5inch_RPi_LCD_(A)  

Make working python folder dir, glone github and install venv:  
mkdir /home/pi/python
python -m venv /home/pi/python/venv
source /home/pi/python/venv/bin/activate
Install requirements  
sudo apt-get install python3-tk -y
sudo apt install git -y  
cd /home/pi/python
git clone https://github.com/RatchetHamster/pihome_display.git  
sudo reboot


# Run  
/home/pi/python/venv/bin/python /home/pi/python/pihome_display/testing.py  
/home/pi/python/venv/bin/python /home/pi/python/pihome_display/main.py  

# To Build   
config.py file - holds all colours, fonts and sizes  

main.py - script to be run  

screens.py - building of each screen  
frames.py - building of each of the frames peiced together to make a screen  
	holds info in memory until update called which triggers the get_info.py classes/functions  
get_info.py - does the leg work of fetching the info for each of the frames  
