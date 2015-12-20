import socket
import os
import sys
import RPi.GPIO as GPIO
import MFRC522
import signal
import threading
import time
import requests

start_time = time.time()
is_running = 1

class NFCReader(threading.Thread):
	checkpointReach = 0
	MIFAREReader = ''
	socket = ''
	myCards = {
			1: [135, 11 ,47, 0],
			2: [33, 186, 20, 219],
			3: [29, 223, 228, 117],
			4: [250, 5, 37, 0]
		}

	def setSocket(self, socket):
		self.socket = socket;
		
	def __init__(self):
		threading.Thread.__init__(self)
		self.MIFAREReader = MFRC522.MFRC522()

	def checkpointReached(self, index):
		if self.checkpointReach == 4:
			self.socket.send("You have reached maximum level!\r\n")
			payload = { 'pos' : '90000' }
			r = requests.get('http://192.168.1.100/HACKFMI/change_where.php', params = payload)
			global is_running
			is_running = 0
			return
		if self.checkpointReach+1 != int(index):
			self.socket.send("You have failed! You should not SKIP checkpoints\r\n")
		else:
			self.socket.send("Good job! You reached checkpoint {0} \r\n".format(index))
			payload = { 'pos' : index }
			r = requests.get('http://192.168.1.100/HACKFMI/change_where.php', params = payload)
			self.checkpointReach = index
	
	def run(self):
		def checkMyCard(row):
			i = 0
			realValues = row[0:4]
			for index, value in self.myCards.iteritems():
				if value == realValues:
					self.checkpointReached(index)
					break;
		# Scan for cards

		global is_running
		self.socket.send("Started readin stuff\r\n")
		while is_running:    
			(status,TagType) = self.MIFAREReader.MFRC522_Request(self.MIFAREReader.PICC_REQIDL)

			# Get the UID of the card
			(status,uid) = self.MIFAREReader.MFRC522_Anticoll()

			# If we have the UID, continue
			if status == self.MIFAREReader.MI_OK:
				checkMyCard(uid)

'''
The controller should send a function 
	l r f b t -> left right forward backward turbo
on click and 
	sl sr sf sb st -> stop left stop right stop forward stop backward stop turbo
on release

Run the NFC module and make it count
	Make it in a separate thread -> One for the server communication, one for the NFC reading
	Off to threads we go :)

Run the camera and send data to the controller
'''


GPIO.setmode(GPIO.BOARD)
GPIO.setup(3, GPIO.OUT, initial = 0) #backwards
GPIO.setup(5, GPIO.OUT, initial = 0) #forward
GPIO.setup(7, GPIO.OUT, initial = 0) #left
GPIO.setup(8, GPIO.OUT, initial = 0) #right
print("Starting!")
nfcreader = NFCReader()

def executeCommand(param):
	if param == 'l':
		GPIO.output(7, 1)
		socket.send("turn left\r\n")
	if param == 'r':
		GPIO.output(8, 1)
		socket.send("turn right\r\n")
	if param == 'f':
		GPIO.output(5, 1)
		socket.send("forward\r\n")
	if param == 'b':
		GPIO.output(3, 1)
		socket.send("go back\r\n")
	if param == 'sl':
		GPIO.output(7, 0)
		socket.send("stop going left\r\n")
	if param == 'sr':
		GPIO.output(8, 0)
		socket.send("stop going right\r\n")
	if param == 'sf':
		GPIO.output(5, 0)
		socket.send("stop going forward\r\n")
	if param == 'sb':
		GPIO.output(3, 0)
		socket.send("stop going backward\r\n")

HOST = ''
PORT = 8000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("socket created")
try:
	s.bind((HOST, PORT))
except socket.error as msg:
	print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
	sys.exit()

print 'Socket bind complete'

s.listen(2)
print 'Socket now listening'

socket, addr = s.accept()
print 'Connected with ' + addr[0] + ':' + str(addr[1])
nfcreader.setSocket(socket)
nfcreader.start()

while is_running:
	data = socket.recv(8)
	data = data.rstrip()
	if data == "close":
		is_running = 0
	executeCommand(data)
s.close()
elapsed_time = time.time() - start_time
print(str(elapsed_time))
GPIO.cleanup()
