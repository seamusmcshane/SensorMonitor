# Sensor Monitor

A small expandable Python3 sensor daemon for RaspberryPI (or compatible) SBC's.

Sensor Monitor reads data from sensor boards and provides a simple JSON REST endpoint from which you can capture the readings in your preferred storage mechanism.

## Supported Raspberry PIs
For direct installation, all PI's with PI OS should work.

For Docker installation, you can install on a PI Zero W for now, until Docker drops support for Raspberry Pi OS 32-bit.

After which a PI Zero W 2 running Raspberry Pi OS 64-bit be the lowest viable device.

### Enable i2c (and spi for EnviroPlus display)

```
sudo raspi-config
```
In `Interface Options>I2C` choose yes
In `Interface Options>SPI` choose yes
Then exit and reboot the PI

## Installation directly on the PI

The first set of dependencies can be fetched via apt
```Bash
sudo apt update
sudo apt install python3 pip fonts-noto-core fonts-noto-mono fonts-noto-extra python3-numpy python3-flask python3-smbus python3-pil
```
The second can be installed via pip (you may need to add --break-system-packages)
```Bash
sudo python3 -m pip install ltr559 st7735 ads1015 python-tsl2591 gpiod gpiodevice RPi.GPIO
```

Then clone this repo on the PI and run SensorMon
```
sudo apt install git
git clone https://github.com/seamusmcshane/SensorMonitor.git
cd SensorMonitor/
./SensorMon.py -boardname EnviroPlus # For EnviroPlus
```

## Installation via Docker

First install Docker - https://docs.docker.com/engine/install/raspberry-pi-os/

Then clone this repo on the PI
```
sudo apt install git
git clone https://github.com/seamusmcshane/SensorMonitor.git
cd SensorMonitor
```
Edit the docker-compose.yml and change ```EnviroPlus``` if needed to ```WaveshareESH```
```
      - BOARDNAME=EnviroPlus
```
Then run
```
sudo docker compose up -d
```
The docker image build speed will depend on the PI used, typically 15mins~ on a PI Zero W, 10mins~ on a PI Zero 2 W and significantly faster on PI 3/4/5.

# Data

Once up and running via either of the above methods, captured data can be accessed via http://IP-Address/values

### EnviroPlus JSON Example

```json
{
  "values": {
    "proximity": 0.0,
    "lux": 1.8610899999999997,
    "temperature": 14.634216096467402,
    "humidity": 38.24351512456366,
    "pressure": 1017.9983317778026,
    "reducing": 572571.4285714284,
    "oxidising": 79087.71929824562,
    "nh3": 86559.66127790608
  }
}
```

### EnviroPlus Display Modes

A very simple alternating display (to reduce OLED image burn), with live values for a period, then switching to a clock before repeating.
The proximity sensor can be used to change modes, just place you hand in front of the board near the sensor.

![Sensors, sensors mode](/images/enviroplus_sensors.jpg)   ![Clock, clock mode](/images/enviroplus_clock.jpg)

### WaveshareESH JSON Example

```json
{
  "values": {
    "temperature": 14.901711471422788,
    "humidity": 46.70172555595024,
    "pressure": 1019.1875099708435,
    "fullspectrum": 62,
    "infrared": 14,
    "lux1": 3.1856640000000005,
    "als": 189.5,
    "lux2": 6.316666666666666,
    "uvs": 0.0,
    "uvi": 0.0,
    "voci": 110.0
  }
}
```

### List supported boards

```bash 
./SensorMon.py -bl
```
Currently just two configs matching the EnviroPlus and WaveshareESH sensors.
But a config could be made to match what ever you have on the i2c bus.

### Help

```bash
./SensorMon.py -h
```
