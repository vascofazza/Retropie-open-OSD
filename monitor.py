#!/usr/bin/env python
#sudo apt-get install python-serial

#
# This file originates from Vascofazza's Retropie open OSD project.
# Author: Federico Scozzafava
#
# THIS HEADER MUST REMAIN WITH THIS FILE AT ALL TIMES
#
# This firmware is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This firmware is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this repo. If not, see <http://www.gnu.org/licenses/>.
#

import RPi.GPIO as GPIO
import time
import os,signal,sys
import serial
from subprocess import Popen, PIPE, check_output
import re
import logging
import logging.handlers
import thread
import threading

# Config variables
bin_dir         = '/home/pi/Retropie-open-OSD/'
osd_path        = bin_dir + 'osd/osd'
rfkill_path     = bin_dir + 'rfkill/rfkill'

# Hardware variables
pi_charging = 26
pi_charged = 25
pi_shdn = 27
serport = '/dev/ttyACM0'

# Init GPIO pins
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(pi_charging, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pi_charged, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pi_shdn, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Batt variables
voltscale = 118.0 #ADJUST THIS
currscale = 640.0
resdivmul = 4.0
resdivval = 1000.0
dacres = 33.0
dacmax = 1023.0

batt_threshold = 4
batt_full = 410
batt_low = 330
batt_shdn = 320

temperature_max = 70.0
temperature_threshold = 5.0

# Wifi variables
wifi_state = 'UNKNOWN'
wif = 0
wifi_off = 0
wifi_warning = 1
wifi_error = 2
wifi_1bar = 3
wifi_2bar = 4
wifi_3bar = 5

# Set up a port
try:
    ser = serial.Serial(
    port=serport,
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1)
except Exception as e:
    logging.exception("ERROR: Failed to open serial port");
    sys.exit(1);


# Set up OSD service
try:
    osd_proc = Popen(osd_path, shell=False, stdin=PIPE, stdout=None, stderr=None)
    osd_in = osd_proc.stdin
    time.sleep(1)
    osd_poll = osd_proc.poll()
    if (osd_poll):
        logging.error("ERROR: Failed to start OSD, got return code [" + str(osd_poll) + "]\n")
        sys.exit(1)
except Exception as e:
    logging.exception("ERROR: Failed start OSD binary");
    sys.exit(1);

# Check for charge state
def checkCharge():
    return not GPIO.input(pi_charging) and GPIO.input(pi_charged)

# Check for shutdown state
def checkShdn():
    state = GPIO.input(pi_shdn)
    if (state):
        logging.info("SHUTDOWN")
        doShutdown()

# Read brightness
def getBrightness():
    ser.write('l')
    ser.flush()

# Read brightness
def getVoltage():
    ser.write('b')
    ser.flush()

# Read voltage
def readVoltage(voltVal):
    #volt = int(500.0/1023.0*voltVal)
    volt = int((( voltVal * voltscale * dacres + ( dacmax * 5 ) ) / (( dacres * resdivval ) / resdivmul)))
    logging.info("VoltVal [" + str(voltVal) + "]")
    logging.info("Volt    [" + str(volt) + "]V")
    return volt

# Get voltage percent
def getVoltagepercent(volt):
    return clamp(int( float(volt - batt_shdn)/float(batt_full - batt_shdn)*100 ), 0, 100)

# Read wifi (Credits: kite's SAIO project)
def readModeWifi(toggle = False):
    global wif
    ret = wif
    wifiVal = not os.path.exists(osd_path+'wifi')# int(ser.readline().rstrip('\r\n'))
    if toggle:
        wifiVal = not wifiVal
    global wifi_state
    if (wifiVal):
        if os.path.exists(osd_path+'wifi'):
            os.remove(osd_path+'wifi')
        if (wifi_state != 'ON'):
            wifi_state = 'ON'
            logging.info("Wifi    [ENABLING]")
            try:
                out = check_output([ 'sudo', rfkill_path, 'unblock', 'wifi' ])
                logging.info("Wifi    [" + str(out) + "]")
                out = check_output([ 'sudo', rfkill_path, 'unblock', 'bluetooth' ])
                logging.info("BT      [" + str(out) + "]")
            except Exception, e:
                logging.info("Wifi    : " + str(e))
                ret = wifi_warning    # Get signal strength

    else:
        with open(osd_path+'wifi', 'a'):
            n = 1
        if (wifi_state != 'OFF'):
            wifi_state = 'OFF'
            logging.info("Wifi    [DISABLING]")
            try:
                out = check_output([ 'sudo', rfkill_path, 'block', 'wifi' ])
                logging.info("Wifi    [" + str(out) + "]")
                out = check_output([ 'sudo', rfkill_path, 'block', 'bluetooth' ])
                logging.info("BT      [" + str(out) + "]")
            except Exception, e:
                logging.info("Wifi    : " + str(e))
                ret = wifi_error
        return ret
#check signal
    raw = check_output([ 'cat', '/proc/net/wireless'] )
    strengthObj = re.search( r'.wlan0: \d*\s*(\d*)\.\s*[-]?(\d*)\.', raw, re.I )
    if strengthObj:
        strength = 0
        if (int(strengthObj.group(1)) > 0):
            strength = int(strengthObj.group(1))
        elif (int(strengthObj.group(2)) > 0):
            strength = int(strengthObj.group(2))
        logging.info("Wifi    [" + str(strength) + "]strength")
        if (strength > 55):
            ret = wifi_3bar
        elif (strength > 40):
            ret = wifi_2bar
        elif (strength > 5):
            ret = wifi_1bar
        else:
            ret = wifi_warning
    else:
        logging.info("Wifi    [---]strength")
        ret = wifi_error
    return ret
# Read CPU temp
def getCPUtemperature():
    res = os.popen('vcgencmd measure_temp').readline()
    return float(res.replace("temp=","").replace("'C\n",""))

# Do a shutdown
def doShutdown(channel = None):
    ser.write('s7')#shuts the screen off
    ser.flush()
    os.system("sudo poweroff")
    try:
        sys.stdout.close()
    except:
            pass
    try:
        sys.stderr.close()
    except:
        pass
    sys.exit(0)

# Signals the OSD binary
def updateOSD(volt = 0,bat = 0, temp = 0, wifi = 0, brightness = 0, info = False, charge = False):
    commands = "v"+str(volt)+" b"+str(bat)+" t"+str(temp)+" w"+str(wifi)+" l"+str(brightness)+" "+("on " if info else "off ")+("charge" if charge else "ncharge")+"\n"
    #print commands
    osd_proc.send_signal(signal.SIGUSR1)
    osd_in.write(commands)
    osd_in.flush()

# Misc functions
def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

brightness = -1
info = False
volt = -1
wifi = 2
charge = 0

condition = threading.Condition()

def reading():
    global brightness
    global volt
    global info
    global wifi
    global charge
    while(1):
        readval = ser.readline().strip('\n')
        condition.acquire()
        if len(readval) < 2:
            condition.release()
            continue
    #print readval
        if readval == 'c0':
            wifi = readModeWifi(True)
        elif readval[0] == 'l':
            brightness = int(readval[1:])
        elif readval == 'mod_on':
            info = True
        elif readval == 'mod_off':
            info = False
        elif readval[0] == 'b':
            volt = readVoltage(int(readval[1:]))
        if info:
            condition.notify()
        updateOSD(volt, bat, temp, wifi, brightness, info, charge)
        condition.release()

reading_thread = thread.start_new_thread(reading, ())

def lambdaCharge(channel):
    condition.acquire()
    condition.notify();
    condition.release();

#interrupts
GPIO.add_event_detect(pi_shdn, GPIO.FALLING, callback=doShutdown, bouncetime=500)
GPIO.add_event_detect(pi_charging, GPIO.BOTH, callback=lambdaCharge, bouncetime=100)
GPIO.add_event_detect(pi_charged, GPIO.FALLING, callback=lambdaCharge, bouncetime=100)

# Main loop
try:
    print "STARTED!"
    while 1:
        #checkShdn()
        charge = checkCharge()
        condition.acquire()
        getVoltage()
        bat = getVoltagepercent(volt)
        temp = getCPUtemperature()
        wifi = readModeWifi()
        if brightness < 0:
            getBrightness()
        condition.wait(4.5)
        condition.release()
        time.sleep(0.5)
#print 'WAKE'

except KeyboardInterrupt:
  GPIO.cleanup
  osd_proc.terminate()
