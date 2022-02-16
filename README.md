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
