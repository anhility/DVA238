#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Rpi script for imbedded systems project.
#
# @author: Mikael Andersson <man16057@student.mdh.se>

### Imports ###
import os, time, socket, threading, random, sys
import RPi.GPIO as GPIO

### Global Variables ###
## Connectivity ##
SKT_U           = None                # UDP socket anchor
SKT_T           = None                # TCP socket anchor
IP_SRC          = "192.168.4.1"       # Local IP
IP_TRG          = "192.168.4.2"       # Remote IP
UDP_PORT        = 5005                # UDP send/recieve port
TCP_PORT        = 5005                # TCP send port
MSG_UDP         = None                # UDP message variable
ENC_TYPE        = 'UTF-8'             # Message encoding
SKT_TO          = 0.1                 # Timeout for socket listening

## Timers ##
TIMER_HELLO     = None                # Timer for sending hello
T_HELLO_UPDATE  = 0.5                 # Update frequency

TIMER_DEAD      = None                # Timer for check if remore is dead
T_DEAD_MAX      = 4                   # Max time before assumed remote is dead

## Variables ##
MSG_HELLO       = "hello"             # Hello message
MSG_TAKEPIC     = "takePic"           # Take picture message
MSG_TAKEPICF    = "takePicF"          # Take picture with flash message
POLL_TIME       = 10                  # ms to wait between each loop cycle
PIN_B1          = 17                  # BCM pin number for button 1
PIN_B2          = 27                  # BCM pin number for button 2

### Error Flags ###
ERR_A_DEAD     = False                # Will be set to true if remote is dead.

### Functions ###

# Sends the given data to remote host with UDP.
#
# @param {string} data - String to send over UDP packet.
#
def sendUDP(data):
    lock = threading.Lock()
    lock.acquire()
    # Simple transmission with encoding to target ip/port
    SKT_U.sendto(bytes(data, ENC_TYPE), (IP_TRG, UDP_PORT))
    lock.release()
    return

# Continiously listens after UDP-packets from remote host.
# Acts depending of what is recieved.
#
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
            print("Camera alive")
            ERR_A_DEAD = False
    elif time.time() - TIMER_DEAD > T_DEAD_MAX and ERR_A_DEAD == False:
        # If no hello and timer maxed out, set error
        print("Camera is not responding.")
        ERR_A_DEAD = True

    MSG_UDP = None
    return

# Small function for receiving TCP packets.
# Unpacks the frame and returns the data if from correct remote host.
#
def recieveTCP():
    lock = threading.Lock()
    lock.acquire()
    data, conn_address = SKT_T.recvfrom(1024)
    lock.release()
    if str(conn_address[0]) == IP_TRG and int(conn_address[1]) == TCP_PORT:
        return data
    else:
        return None

# Threaded function, requests a file for remote host depending on
# which button is pressed.
#
def threadRequestFile():
    G_COUNTER = 0
    
    while True:
        b1 = GPIO.input(PIN_B1)
        b2 = GPIO.input(PIN_B2)
        if b1 == False: # Without flash
            G_COUNTER += 1
            print("Counter:", G_COUNTER)
            # Adds timestamp to UDP message for transfer information.
            mess = MSG_TAKEPIC + '_t' + str(time.time())
            # Timestamp for just before request is sent.
            # Used to measure the whole function.
            t_UT = time.time()
            sendUDP(mess)
            # Tries open or create file.
            with open("image.jpg", 'wb') as picFile:
                # Waiting to accept remote connection.
                conn, IP_TRG = SKT_T.accept()
                # Second timestamp when connection is established.
                t_T = time.time()
                # Short loop that writes recieved data to file.
                while True:
                    data = conn.recv(1024)
                    if not data: break
                    picFile.write(data)

                print("Picture saved.")
                
            # Closes file and socket.
            picFile.close()
            conn.close()
            # Final timestamp to measure function time before
            # writing it to the log.
            t_end = time.time()
            t_UT = t_end - t_UT
            t_T = t_end - t_T
            #print("UDP+TCP:", t_UT, # debug output
            #    "\nTCP:    ", t_T)  # debug output
            
            # Creates string for log
            str_L = "\"tcpL\"," + str(t_T) +
                    ",\"udpL+tcpL\"," + str(t_UT) + "\n"
            writeLog(str_L)
            print("Done")

        if b2 == False: # With flash
            G_COUNTER += 1
            print("Counter:", G_COUNTER)
            # Adds timestamp to UDP message for transfer information.
            mess = MSG_TAKEPICF + '_t' + str(time.time())
            # Timestamp for just before request is sent.
            # Used to measure the whole function.
            t_UT = time.time()
            sendUDP(mess)
            # Tries open or create file.
            with open("imageF.jpg", 'wb') as picFile:
                # Waiting to accept remote connection.
                conn, IP_TRG = SKT_T.accept()
                # Second timestamp when connection is established.
                t_T = time.time()
                # Short loop that writes recieved data to file.
                while True:
                    data = conn.recv(1024)
                    if not data: break
                    picFile.write(data)

                print("Picture with flash saved.")
                
            # Closes file and socket.
            picFile.close()
            conn.close()
            # Final timestamp to measure function time before
            # writing it to the log.
            t_end = time.time()
            t_UT = t_end - t_UT
            t_T = t_end - t_T
            #print("UDP+TCP:", t_UT, # debug output
            #    "\nTCP:    ", t_T)  # debug output
            
            # Creates string for log
            str_L = "\"tcpL\"," + str(t_T) +
                    ",\"udpL+tcpL\"," + str(t_UT) + "\n"
            writeLog(str_L)
            print("Done")

        time.sleep(POLL_TIME / 1000.0)

# Threaded function, listens for UDP packets.
#
def threadListenUDP():
    # Listen for UDP packets
    while True:
        listenUDP()

# Threaded function, continiously sends hello packets to remote host.
#
def threadSendHello():
    # Sends hello packets on a timer
    while True:
        global TIMER_HELLO
        if time.time() - TIMER_HELLO > T_HELLO_UPDATE:
            sendUDP(MSG_HELLO)
            TIMER_HELLO = time.time()

# Writes given string to log file.
#
# @param {string} string - Line of text to append to log file.
#
def writeLog(string):
    with open('log_remote.csv', 'a+') as f_log:
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

    SKT_T = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SKT_T.bind((IP_SRC, TCP_PORT))
    #SKT_T.settimeout(SKT_TO)
    SKT_T.listen(5)

    ## GPIO Setup ##
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_B1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_B2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    ### Initialization Complete ###

    ### Creating and startup of threads ###

    # Thread to send hello messages
    t1 = threading.Thread(
            target=threadSendHello, name="SendHello", daemon=True)

    # Thread to listen for UDPs
    t2 = threading.Thread(
            target=threadListenUDP, name="ListenUDP", daemon=True)

    # Thread for input and requesting files.
    t3 = threading.Thread(
            target=threadRequestFile, name="RequestFile", daemon=True
            )

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
