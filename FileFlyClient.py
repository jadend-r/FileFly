# -*- coding: utf-8 -*-
"""
Created on Tue Oct 25 11:06:41 2022

@author: palmera3
"""

from PyQt5 import QtWidgets, uic, QtGui, QtCore
import sys
import json
import socket
import threading
import subprocess
from qt_thread_updater import get_updater

import tkinter as tk
from tkinter import *
from tkinter import ttk, filedialog
from tkinter.filedialog import askopenfile
import os
import io
from threading import Event

root = tk.Tk()
root.withdraw()

Host = "10.12.40.165"
Port = 7888

clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
clientSocket.connect((Host,Port))

recipIP = ""
recvMsgThread = None

stopEvent = Event()

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('FileFly.ui', self)
        
        self.refresh = self.findChild(QtWidgets.QPushButton,"refresh")
        self.refresh.clicked.connect(self.refreshUsers)
        
        
        self.users = self.findChild(QtWidgets.QStackedWidget, 'pages')
        
        self.vlayout = self.findChild(QtWidgets.QVBoxLayout,"vlayout")
        
        self.login = self.findChild(QtWidgets.QPushButton, 'logInButton')
        self.login.clicked.connect(self.logIn)
        
        self.loginBox = self.findChild(QtWidgets.QTextEdit, "nameBox")
    
        self.send = self.findChild(QtWidgets.QPushButton, "sendButton")
        self.send.clicked.connect(self.sendMsg)
        
        self.textField = self.findChild(QtWidgets.QTextBrowser, "textField")
        self.textField.anchorClicked.connect(self.downloadFile)
        
        self.files = self.findChild(QtWidgets.QPushButton, "fileButton")
        self.files.clicked.connect(self.sendFile)
        
        self.goBack = self.findChild(QtWidgets.QPushButton, "backButton")
        self.goBack.clicked.connect(self.back)
        
        self.show()
    
        
    def logIn(self):
        Name = self.loginBox.toPlainText()
        command = "LOGIN " + Name
        clientSocket.sendall(command.encode())
        self.getList()
        self.users.setCurrentIndex(1)
        
    def clearLayout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def getList(self):
        self.clearLayout(self.vlayout)
        command = "GETUSERLIST"
        clientSocket.sendall(command.encode())
        userList = clientSocket.recv(1024).decode()
        userDict = json.loads(userList)
        for key in userDict.keys():
            name = userDict[key]
            userButton = QtWidgets.QPushButton(self)
            self.vlayout.addWidget(userButton)
            userButton.clicked.connect(lambda state, x = key: self.userButtonClicked(x))
            userButton.setText(name)
            
    def getFile(self, filename):
        print("getting file from server size")
        command = "GETFILE " + filename + "|"
        file = open(filename, 'wb')
        fileRecvSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        fileRecvSock.connect((Host, 7889))
        fileRecvSock.sendall(command.encode())
        fileData = fileRecvSock.recv(1024)
        while fileData:
            file.write(fileData)
            fileData = fileRecvSock.recv(1024)
        print("Finished recv file from server")  
        file.close()
        fileRecvSock.close()
        
    def downloadFile(self, filename):
        self.textField.setSource(QtCore.QUrl()) #Stop page from changing
        print("downloading", filename.fileName())
        self.getFile(filename.fileName())
        
  
    def recvMsgThread(self):
        global stopEvent
        clientSocket.setblocking(0) #Socket cannot block or else recv() will wait forever and we wont be able to terminate the thread when we click back button
        while not stopEvent.is_set(): #stopEvent is set when we click the back button; we want to kill this thread and stop receiving data from socket
           # print("Thread is running")
            try:
                msgData = clientSocket.recv(1024).decode()
                print(msgData)
                msgData = json.loads(msgData)
                messageType = msgData['type']
                if messageType == "text":
                    message = msgData['sender'] + ": " + msgData['msg']
                    get_updater().call_in_main(self.textField.insertHtml, "<p>"+message+"</p>")
                    get_updater().call_in_main(self.textField.insertHtml, "<br>")
                elif messageType == "file":
                    get_updater().call_in_main(self.textField.insertHtml, "<p>" + msgData['sender'] + ": "+ "</p>")
                    get_updater().call_in_main(self.textField.insertHtml, "<br>")
                    get_updater().call_in_main(self.textField.insertHtml, "<a href='" + msgData['filename'] + "'>" + msgData['filename']+ "</a>")
                    get_updater().call_in_main(self.textField.insertHtml, "<br>")
            except Exception as e:
                pass
                #print(e)
                 
        print("Thread is exiting")
        clientSocket.setblocking(1)
            
    def userButtonClicked(self, ipAddr):
        self.users.setCurrentIndex(2)
        global recipIP
        global recvMsgThread
        recipIP = ipAddr
        recvMsgThread = threading.Thread(target = self.recvMsgThread) 
        recvMsgThread.start()

        
    def refreshUsers(self):
        self.getList()
    
    def closeEvent(self,event):
        global stopEvent
        stopEvent.set()
        clientSocket.close()
        
    def sendMsg(self):  
        global recipIP
        msg = self.msgField.toPlainText()
        self.textField.insertHtml("<p>You: " + msg + "</p>")
        self.textField.insertHtml("<br>")
        command = "SEND " + recipIP + " " + msg
        clientSocket.sendall(command.encode())
        self.msgField.setText("")
        
    def sendFile(self):
        file = filedialog.askopenfile(mode='rb', filetypes=[('All Files', '*.*')])
        if file:
            nameExtension = os.path.splitext(os.path.basename(os.path.normpath(file.name)))
            
            newFileName = nameExtension[0] + "_FILEFLY" + nameExtension[1]
            
            #SENDFILE command must have | seperator at the end to distinguish file header info from file data
            command = "SENDFILE " + recipIP + " " + nameExtension[0] + "_FILEFLY" + nameExtension[1] + "|"
            
            self.textField.insertHtml("<p>You:</p>")
            self.textField.insertHtml("<br>")
            self.textField.insertHtml("<a href='" + newFileName + "'>" + newFileName + "</a>")
            self.textField.insertHtml("<br>")
    
            clientFileSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            clientFileSock.connect((Host, 7889))
            clientFileSock.sendall(command.encode())
            clientFileSock.sendfile(file)
            clientFileSock.close()
    
    def openfile(self,name):
        path = name
        os.startfile(path, 'open')
        
    def back(self):
        global recvMsgThread
        global stopEvent
        global recipIP
        stopEvent.set() #Set event that will tell the recvMsgThread to terminate
        recvMsgThread.join() #Wait for the recvMsgThread to terminate
        stopEvent.clear()
        recipIP = ""
        self.users.setCurrentIndex(1)
        self.refreshUsers()
        
app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()