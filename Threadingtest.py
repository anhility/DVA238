#!/usr/bin/python3
import socket
import sys
import RPi.GPIO as GPIO
import time
import threading

LOCAL_IP = '192.168.4.1'
KEEP_ALIVE_PORT = 15000
BUTTON_PORT     = 10000

TCP_PORT = 5005

# Remote host
HOST_TO = '192.168.4.2'



class keepAliveThread(threading.Thread):
	def run(self):
		Thread1_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		server_address = (LOCAL_IP, KEEP_ALIVE_PORT)

		Thread1_socket.bind(server_address)

		while True:
			keepAlive = "hello"

			sentKeepAlive = Thread1_socket.sendto(keepAlive.encode(), (HOST_TO, KEEP_ALIVE_PORT))
			print("{Thread1: sent {} bytes".format(sentKeepAlive))

			print("Thread1: Waiting for answer..")
			recv = Thread1_socket.recv(1024).decode()
			print("Thread1 received: {}".format(recv))
			time.sleep(10)



class buttonThread(threading.Thread):
	def run(self):
		Thread2_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		server_address = (LOCAL_IP, BUTTON_PORT)

		Thread2_socket.bind(server_address)
		while True:
			if GPIO.input(butPin):
				#print("Button is not pushed down")
				time.sleep(2)
			else:
				print("Thread2: Button is pushed down, sending a '1' ")
				msgButton = "takePic"

				sentButton = Thread2_socket.sendto(msgButton.encode(), (HOST_TO, BUTTON_PORT))
				print("Thread2: sent {} bytes".format(sentButton))

				print("Thread2: Waiting for answer..")
				recv = Thread2_socket.recv(1024).decode()
				print("Thread2 received: {}".format(recv))

				time.sleep(2)


class tcpClientThread(threadin.Thread):

	def __init__(self, socket, ip):
		self.clientSocket = socket
		self.clientIP = ip



	def run(self):
		while True:

			# 1 ta emot filstorlek
			# 2 skicka ack på det
			# 3 börja ta emot fil
			# 4 skicka ack på att samtliga bytes har tagits emot
			# 5 Avsluta anslutningen.





GPIO.setmode(GPIO.BCM)

butPin = 17

GPIO.setup(butPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

thread1 = keepAliveThread()
thread2 = buttonThread()



thread1.start()
thread2.start()




# Start listening for connection attempts
TCP_SOCKET_SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

TCP_SOCKET_SERVER.bind((LOCAL_IP, TCP_PORT))
TCP_SOCKET_SERVER.listen(5)


while True:
	(clientsocket, address) = TCP_SOCKET_SERVER.accept()

	# Init faze
	clientThread = tcpClientThread( clientSocket, remoteAddress )

	# Start faze
	clientThread.start()





