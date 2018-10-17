#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Rpi script for imbedded systems project.
#
# @author: Mikael Andersson <man16057@student.mdh.se>

### Imports ###
import os, time, socket, threading, random, sys
import RPi.GPIO as GPIO
from picamera import PiCamera

### Global Variables ###
## Connectivity ##
SKT_U           = None                # UDP socket anchor
SKT_T           = None                # TCP socket anchor
IP_SRC          = "192.168.4.2"       # Local IP
IP_TRG          = "192.168.4.1"       # Remote IP
UDP_PORT        = 5005                # UDP send/recieve port
TCP_PORT        = 5005                # TCP send port
MSG_UDP         = None                # UDP message variable
ENC_TYPE        = 'UTF-8'             # Message encoding
#PKT_COPY        = 3                   # Number of copies to send
SKT_TO          = 0.1                 # Timeout for socket listening

## Timers ##
TIMER_HELLO     = None                # Timer for sending hello
T_HELLO_UPDATE  = 0.5                 # Update frequency

TIMER_DEAD      = None                # Timer for check if remore is dead
T_DEAD_MAX      = 4                   # Max time before assumed remote is dead

## Variables ##
LED_STATE       = False
LED_VALUE       = None                # The value given by remote
MSG_HELLO       = "hello"             # Hello message
#MSG_VALUE       = "value"             # Value message
MSG_TAKEPIC     = "takePic"           # Take picture message
MSG_TAKEPICF    = "takePicF"          # Take picture with flash message
POLL_TIME       = 10                  # ms to wait between each loop cycle
PIN_LED         = 17                  # BCM pin number for LED
#RAND_TYPE       = True                # True: drop 1 of n packets.
                                      # False: send 1 of n packet.
#RAND_MOD        = 1                   # Modulo for randrange where n >= 1.
                                      # Set to 1 to always send packets.

### Error Flags ###
ERR_A_DEAD     = False                # Will be set to true if remote is dead.

### Functions ###

def sendUDP(data):
    lock = threading.Lock()
    lock.acquire()
    # Simple transmission with encoding to target ip/port
    SKT_U.sendto(bytes(data, ENC_TYPE), (IP_TRG, UDP_PORT))
    lock.release()
    return

def listenUDP():
    global MSG_UDP, TIMER_DEAD, ERR_A_DEAD

    # Ugly try-except test to let the socket time-out
    # without breaking the script
    try:
        lock = threading.Lock()
        lock.acquire()
        data, conn_address = SKT_U.recvfrom(1024)
        lock.release()
        if str(conn_address[0]) == IP_TRG and int(conn_address[1]) == UDP_PORT:
            global MSG_UDP
            MSG_UDP = data.decode(ENC_TYPE)
    except:
        pass

    if MSG_UDP == MSG_HELLO:
        # If hello, reset timer and error
        TIMER_DEAD = time.time()
        if ERR_A_DEAD == True:
            print("Remote is alive.")
            ERR_A_DEAD = False
    elif str(MSG_UDP)[:8] == MSG_TAKEPICF:
        u_L = time.time() - float(str(MSG_UDP)[10:])
        print("UDP latency:", u_L)
        s_log = "\"udpL\"," + str(u_L) + "\n"
        writeLog(s_log)
        takeAndSendPic(True)
    elif str(MSG_UDP)[:7] == MSG_TAKEPIC:
        u_L = time.time() - float(str(MSG_UDP)[9:])
        print("UDP latency:", u_L)
        s_log = "\"udpL\"," + str(u_L) + "\n"
        writeLog(s_log)
        takeAndSendPic()
    elif time.time() - TIMER_DEAD > T_DEAD_MAX and ERR_A_DEAD == False:
        # If no hello and timer maxed out, set error
        print("Remote is not responding.")
        ERR_A_DEAD = True

    MSG_UDP = None
    return

def updateLamp(state):
    GPIO.output(PIN_LED, state)
    return

def takeAndSendPic(LED = False):
    global LED_STATE

    if LED == True:
        LED_STATE = True
    # Takes a picture
    camera = PiCamera()
    camera.resolution = (1920, 1080)
    camera.rotation = 180
    camera.capture('.image.jpg')
    camera.close()
    # Flash off
    if LED == True:
        LED_STATE = False

    print("Picture created.")

    with open('.image.jpg', 'rb') as f:
        global SKT_T
        SKT_T = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SKT_T.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        SKT_T.bind((IP_SRC, TCP_PORT))

        SKT_T.connect((IP_TRG, TCP_PORT))
        l = f.read(1024)
        while (l):
            SKT_T.send(l)
            l = f.read(1024)
        f.close()
        SKT_T.close()

    os.remove(".image.jpg")

    print("Picture sent and deleted.")
    return

def threadListenUDP():
    # Listen for UDP packets
    while True:
        listenUDP()

def threadSendHello():
    # Sends hello packets on a timer
    while True:
        global TIMER_HELLO
        if time.time() - TIMER_HELLO > T_HELLO_UPDATE:
            sendUDP(MSG_HELLO)
            TIMER_HELLO = time.time()

def threadLampUpdate():
    # Updates the lamp
    while True:

        time.sleep(POLL_TIME / 1000.0)

        # Blink if remote is dead
        if ERR_A_DEAD == True:
            if (time.time() - TIMER_DEAD)%1 > 0.5:
                updateLamp(True)
            else:
                updateLamp(False)
        elif ERR_A_DEAD == False:
            updateLamp(LED_STATE)

def writeLog(string):
    with open('car_log.csv','a+') as f_log:
        f_log.write(string)
    f_log.close()
    return

### Main Function ###
def main():

    ### Initialization ###
    ## Calling Globals ##
    global SKT_U, SKT_T, TIMER_HELLO, TIMER_DEAD

    ## Timer Setup ##
    initTime    = time.time()
    print("initTime: ", initTime)
    TIMER_HELLO = initTime
    TIMER_DEAD  = initTime

    ## Print initTime to log ##
    initL = "\"initT\"," + str(initTime) + "\n"
    writeLog(initL)

    ## Socket Setupd ##
    SKT_U = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SKT_U.bind((IP_SRC, UDP_PORT))
    SKT_U.settimeout(SKT_TO)

    #SKT_T = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #SKT_T.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #SKT_T.bind((IP_SRC, TCP_PORT))
    #SKT_T.settimeout(SKT_TO)

    ## GPIO Setup ##
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_LED, GPIO.OUT)
    GPIO.output(PIN_LED, False)

    ### Initialization Complete ###

    ### Creating and startup of threads ###

    # Thread to send hello messages
    t1 = threading.Thread(
            target=threadSendHello, name="SendHello", daemon=True)

    # Thread for lamp control
    t2 = threading.Thread(
            target=threadLampUpdate, name="LampUpdate", daemon=True)

    # Thread to listen for UDPs
    t3 = threading.Thread(
            target=threadListenUDP, name="ListenUDP", daemon=True)

    # Start of threads
    t1.start()
    t2.start()
    t3.start()


    ## Exit gracefully with ^C or ^D ##
    while True:
        try:
            _ = input()
        except (KeyboardInterrupt, EOFError) as err:
            SKT_U.close()
            SKT_T.close()
            GPIO.cleanup()
            print("Script terminated.")
            sys.exit()

print("Script activated.")
main()
