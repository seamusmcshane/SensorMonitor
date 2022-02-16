# Sensor Monitor

A small expandable Python3 sensor daemon for RaspberryPI (or compatible) SBC's.

It read data from sensor boards and provides a simple JSON REST API from which you can capture the readings in your prefered storage mechanism.

Data is by internally sampled once per second and made available via JSON as average over the previous 10 second window.

