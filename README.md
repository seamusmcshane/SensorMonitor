# Sensor Monitor

A small expandable Python3 sensor daemon for RaspberryPI (or compatible) SBC's.

It read data from sensor boards and provides a simple JSON REST API from which you can capture the readings in your prefered storage mechanism.

Data is by internally sampled once per second and made available via JSON as average over the previous 10 second window.

## Dependancies
These dependancies are based whats needed after a fresh Raspbian GNU/Linux 11 install.

For other distributions you will need to substitute equivilant commands and packages.

## Sensor Monitor
apt install python3

apt install python3-numpy

apt install python3-flask

### Sensor Boards
You only need the dependancies for you board you do not need to install everything.

Each sensor board has its own dependancies. To save space install just what is needed for the board you are going to use.

#### Pimoroni EnviroPlus
python3 -m pip install ltr559
python3 -m pip install st7735
python3 -m pip install ads1015
###### Fonts used for the OLED display
apt install fonts-noto-core fonts-noto-mono fonts-noto-extra

#### Waveshare Enviroment HAT
pip install python-tsl2591