# Retropie-open-OSD
A powerful, informative, native, efficient, super cool, on-screen display software for Raspberry Pi.

![demo](/images/test1.png)
![demo2](/images/test.png)

This OSD is designed to be fast and informative, it uses low level gpu system calls as well as signals and interrupts to keep the resources consuption low.
The software is intendeed for mobile application as it features:

* battery meter (w\ charge indicator)
* wifi meter
* date/time
* CPU temperature
* battery voltage

## Build instructions:

* make

## How to use it:

* Configure (edit) the monitor script accordingly to your hardware configuration

* python monitor.py

### or...

* run the osd binary giving instruction through stdin:

The program sleeps until the SIGUSR1 signal is fired and then reads from stdin. The string can contains the following tokens separated by space (' ') and terminated by '\n'.

* b[int] sets the battery percentage
* v[float] sets the battery voltage
* t[float] sets the cpu temperature
* l[int] sets the screen brigthness level
* w[int] sets the wifi status
* on enables the information screen
* off disables the information screen
* charge sets the chage statu
* ncharge set the charge status off
* quit exits the program

