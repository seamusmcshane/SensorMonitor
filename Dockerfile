FROM debian:bookworm-slim

RUN apt update && apt install -y python3 \
    && apt install -y pip fonts-noto-core fonts-noto-mono fonts-noto-extra python3-numpy python3-flask python3-smbus python3-pil \
    && apt -y clean autoclean \
    && apt autoremove -y

RUN python3 -m pip install ltr559 st7735 ads1015 python-tsl2591 gpiod gpiodevice RPi.GPIO --break-system-packages

COPY . /home/SensorMonitor

ENV BOARDNAME=$BOARDNAME

WORKDIR /home/SensorMonitor

CMD python3 SensorMon.py -boardname "$BOARDNAME"