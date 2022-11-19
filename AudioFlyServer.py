#LOGIN: Username will show up for others to message
#SEND: Send "Username: Message" to sourceClient and  destinationClient 

import socket
import json
import threading
import os

servPORT = 7888
servFILEPORT = 7889
HOST = ''
PORT = ''
userDict = {} 
fileQueue = {}
'''
{
    "127.0.0.1" : ("Jaden", cs)
}
'''
serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP 
serverSock.bind(('', servPORT)) #socket.gethostname() #The bind() method of Python's socket class assigns an IP address and a port number to a socket instance
serverSock.listen(50) #Calling listen() makes a socket ready for accepting connections.

serverFileSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverFileSock.bind(('', servFILEPORT))
serverFileSock.listen(50)

def loginUser(userName, ipAddr, cs): #Stores username, IP, and connection server has with client 
    userDict [ipAddr] = (userName, cs) # Creates touple of username and connection that is tied to client IP
    print("Logged in user: " + userName + " " + ipAddr)

def removeUser(addr):
    if addr in userDict.keys():
        print("Removing user: ", addr)
        connection = userDict[addr][1]
        connection.close()
        del userDict[addr]
    
def sendMsg(ipAddr,message,senderIP):
    recpInfo = userDict[ipAddr] # Creates variable and stores the recipients username and connection to it
    senderInfo = userDict[senderIP]
    jsonData = json.dumps({
        'type': 'text',
        'sender': senderInfo[0],
        'msg': message
    })
    recpInfo[1].sendall(jsonData.encode()) # recpInfo[1] is the second element in the touple which corresponds to the connetion

def getUserList(cs):
    newDict = {}
    for key in userDict:
        newDict[key] = userDict[key][0]
    userList = json.dumps(newDict) #Convert UserDict into JSON String
    print (userList) 
    cs.sendall(userList.encode())

def respond(cs, addr, clientMsg):
    print(clientMsg)
    commandComponents = clientMsg.split() # Splits string into the Command and its following components
    command = commandComponents[0]

    def switch(command): #commandComponents[0] is the command, [1], and [2] are components of the command ex(SEND[0], destinationIP[1], clientMessage[2])
        if command == 'LOGIN': 
            userName = commandComponents[1]
            loginUser(userName, addr, cs) 
        if command == 'SEND':
            receipAddr = commandComponents[1]
            message = ' '.join(commandComponents[2:])
            sendMsg(receipAddr, message, addr)
        if command == 'GETUSERLIST':
            getUserList(cs)
    
    switch(command)

def clientThread(cs, addr):
    try:
        while True: #Second loop to recieve messages from client, keeping TCP connection open 
            clientMsg = cs.recv(1024) #clients sent message, need to update UI to show sent message
            if not clientMsg: #Connection has been broken by client .close()
                break
            clientMsg = clientMsg.decode() #Convert message from client into String
            respond(cs, addr, clientMsg)
    except Exception as e:
        print(e)
        
    removeUser(addr)
 
def forwardFileLink(senderAddr, recipAddr, filename):
    jsonData = {
        'type': 'file',
        'sender': userDict[senderAddr][0],
        'filename': filename
    }
    jsonData = json.dumps(jsonData)
    userDict[recipAddr][1].sendall(jsonData.encode())
    
def recvFileThread(cs, addr):
    fileInfo = ''
    data = cs.recv(1).decode()
    while data != "|":
        fileInfo += data
        data = cs.recv(1).decode()
    fileCommand = fileInfo.split()
    if fileCommand[0] == "GETFILE":
        fileName = fileCommand[1]
        cs.sendfile(open("FileFlyServerFiles/"+fileName, "rb"))
    elif fileCommand[0] == "SENDFILE":
        receipAddr = fileCommand[1]
        fileName = fileCommand[2]
        if not os.path.exists("FileFlyServerFiles"):
            os.makedirs("FileFlyServerFiles")
        file = open("FileFlyServerFiles/"+fileName, "wb")
        fileData = cs.recv(1024)
        print("Writing data to file...")
        while fileData:
            file.write(fileData)
            fileData = cs.recv(1024)
        file.close()
        print("Finished receiving file from", addr)
        forwardFileLink(addr, receipAddr, fileName)
    cs.close()
    #os.remove(fileName)
     
def mainListen():
    while True:
        cs,addr=serverSock.accept() # Accept a connection. The socket must be bound to an address and listening for connections.
        print (addr)
        newThread = threading.Thread(target=clientThread, args=(cs, addr[0]))
        newThread.start()
    
def fileConnTransferListen():
    while True:
        csFile, addrFile = serverFileSock.accept()
        print("Receiving file data from", addrFile)
        fileThread = threading.Thread(target=recvFileThread, args=(csFile, addrFile[0]))
        fileThread.start()

threading.Thread(target = mainListen).start()
threading.Thread(target = fileConnTransferListen).start()
    
    
    


