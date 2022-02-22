# Sensor Monitor

A small expandable Python3 sensor daemon for RaspberryPI (or compatible) SBC's.

Sensor Monitor reads data from sensor boards and provides a simple JSON REST API from which you can capture the readings in your prefered storage mechanism.

Data is internally sampled once per second and made available via JSON as a rolling average over the previous 10 second window.

## Installation

Clone the repo to the PI or download and extract a compresed snapshot.

Change to the SensorMon directory.

chmod a+x SensorMon.py

## Usage

./SensorMon.py -boardname BoardName

Access data via http://IP-Address/values

EnviroPlus JSON Example

```json
{ "values" :{"proximity": 0.3, "lux": 7.9485, "temperature": 23.822164891392717, "humidity": 21.84497014828306, "pressure": 1014.5156068612221, "reducing": 532923.0769230772, "oxidising": 100623.65508066287, "nh3": 106876.96667643895}}
```
EnviroPlus Display Modes

![Sensors, sensors mode](/images/enviroplus_sensors.jpg)   ![Clock, clock mode](/images/enviroplus_clock.jpg)

WaveshareESH JSON Example

```json
{ "values" :{"temperature": 14.478260589506146, "humidity": 36.774254188532026, "pressure": 1015.4887851182655, "fullspectrum": 2047, "infrared": 902, "lux1": 46.325952, "als": 3841.4, "lux2": 128.04666666666665, "uvs": 3.4, "uvi": 0.0014782608695652175, "voci": 25.0}}
```

### List supported boards

./SensorMon.py -bl


### Help

./SensorMon.py -h

## Dependencies

These dependencies are based whats needed after a fresh Raspbian/PI OS GNU/Linux 10/11 install.

For other distributions you will need to substitute equivilant commands and packages.

### Sensor Monitor

Requires Python 3.7 or above

apt install python3-numpy

apt install python3-flask

### Sensor Boards

You only need the dependencies for you board you do not need to install everything.

Each sensor board has its own dependencies. To save space install just what is needed for the board you are going to use.

#### Pimoroni EnviroPlus

python3 -m pip install ltr559

python3 -m pip install st7735

python3 -m pip install ads1015

###### EnviroPlus OLED display Fonts

apt install fonts-noto-core fonts-noto-mono fonts-noto-extra

#### Waveshare Enviroment Sensor HAT

pip install python-tsl2591