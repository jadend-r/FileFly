#AudioFlyServer
#Author: Jaden Reid

#Server utilizes two TCP sockets to talk to clients
#Socket on port 7888 for transfer of text-based commands
#Socket on port 7889 for transfer of files and file-based commands

'''
AudioFly Server Commands:
    LOGIN [username]
    SEND [receip ipAdrr] [message]
    GETUSERLIST
    SENDFILE [receipAddr] [fileName]|fileData bytes
    GETFILE [filename]|
'''

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

#Socket for receiving, sending text-based commands on port 7888
serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP 
serverSock.bind(('', servPORT)) #socket.gethostname() #The bind() method of Python's socket class assigns an IP address and a port number to a socket instance
serverSock.listen(50) #Calling listen() makes a socket ready for accepting connections.

#Socket for receiving, sending files on port 7889
serverFileSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverFileSock.bind(('', servFILEPORT))
serverFileSock.listen(50)

#loginUser method receives userName of user to login, ip address of user, and
#client socket the server has to that user and
#stores in our user dictionary collection using the ip address as the key
def loginUser(userName, ipAddr, cs): #Stores username, IP, and connection server has with client 
    userDict [ipAddr] = (userName, cs) # Creates tuple of username and connection that is tied to client IP
    print("Logged in user: " + userName + " " + ipAddr)

#removeUser removes a user in our user dictionary collection
#given: user's ip address to remove
def removeUser(addr):
    if addr in userDict.keys():
        print("Removing user: ", addr)
        connection = userDict[addr][1]
        connection.close()
        del userDict[addr]
    
#sendMsg method receives ip address of person to send to, the message contents, and
#the sender's ip address
def sendMsg(ipAddr,message,senderIP):
    recpInfo = userDict[ipAddr] # Reference to the receipient's stored info
    senderInfo = userDict[senderIP] # Reference to the senders's stored info
    jsonData = json.dumps({ #Server forms a JSON string for easy encoding/decoding and we can send it over the socket
        'type': 'text',
        'sender': senderInfo[0], #Sender's username
        'msg': message #Message contents
    })
    recpInfo[1].sendall(jsonData.encode()) # Use client socket for receipient to send encoded JSON string to receipient

#getUserList method sends a JSON string version of server's user dictionary collection to a requesting client
#given: client socket for requesting client
def getUserList(cs):
    newDict = {}
    for key in userDict: #We need to make a new dictionary that maps ip: username without the socket objects
        newDict[key] = userDict[key][0] #newDict[ipAddr] = userName
    userList = json.dumps(newDict) #Convert modified user dict into JSON String
    print (userList) 
    cs.sendall(userList.encode()) #Send encoded JSON string to requesting client over socket

#respond method is the method that decodes all text-based commands from clients on port 7888
#given: client socket of user to respond to, ip address of user to respond to, and 
#the user's command to be executed
def respond(cs, addr, clientMsg):
    print(clientMsg)
    
    #Splits clientMsg string into the command and its following components
    #Commands are expected to be space-delimited: e.g 'LOGIN username'
    '''
    COMMAND STRUCTURES:
        LOGIN [username]
        SEND [receip ipAdrr] [message]
        GETUSERLIST
    '''
    commandComponents = clientMsg.split() 
    command = commandComponents[0] 
    
    def switch(command):
        if command == 'LOGIN': 
            userName = commandComponents[1]
            loginUser(userName, addr, cs) #Call loginUser method for further processing...
        if command == 'SEND':
            receipAddr = commandComponents[1]
            message = ' '.join(commandComponents[2:])
            sendMsg(receipAddr, message, addr) #Call sendMsg method for further processing...
        if command == 'GETUSERLIST':
            getUserList(cs) #Call getUserList method method for further processing...
    
    switch(command)

#clientThread method is a thread spawned for each connected client to receive 
#text-based commands from them on port 7888
def clientThread(cs, addr):
    try:
        while True: #Keep receiving messages from connected client
            clientMsg = cs.recv(1024) 
            if not clientMsg: #Connection has been broken by client .close()
                break
            clientMsg = clientMsg.decode() #Convert message from client into String
            respond(cs, addr, clientMsg) #Call respond method for further processing...
    except Exception as e:
        print(e)
        
    removeUser(addr) #If we've broken out of the listen loop, user has closed their connection
 
#forwardFileLink method sends the receipient of a file transfer a hyperlink with the file name
#given: sender's ip address, receipients ip address, filename
def forwardFileLink(senderAddr, recipAddr, filename):
    jsonData = {
        'type': 'file',
        'sender': userDict[senderAddr][0], #sender's username
        'filename': filename
    }
    jsonData = json.dumps(jsonData)
    userDict[recipAddr][1].sendall(jsonData.encode()) #Send file info over socket to receipient
    
#recvFileThread method is spawned for every client who wishes to send/download a file to/from server
#responds to GETFILE and SENDFILE commands from client on port 7889
#given: socket to requesting client, ip address of requesting client
def recvFileThread(cs, addr):
    fileInfo = ''
    data = cs.recv(1).decode() #Receive data from client byte by byte until
    while data != "|": #this seperator is reached to seperate command from file data
        fileInfo += data
        data = cs.recv(1).decode()
        
    #After reaching seperator, we have the full command, parse it
    fileCommand = fileInfo.split()
    if fileCommand[0] == "GETFILE":
        fileName = fileCommand[1]
        cs.sendfile(open("FileFlyServerFiles/"+fileName, "rb")) #Send the requested file over socket to client
    elif fileCommand[0] == "SENDFILE":
        #SENFILE command will create new file with given name on server and write received data to copy file from client
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
        forwardFileLink(addr, receipAddr, fileName) #After file receive completed, send a link to the receipient 
                                                    #So they may later download the file
    cs.close() #File transfer complete, close this socket

   
    
#-------------------------------------------SERVER MAIN ENTRY POINT------------------------------------------------
#------------------------------------------------------------------------------------------------------------------

#mainListen method listens on port 7888 for connections from clients,
#spawns new clientThread for every connected client
def mainListen():
    while True:
        cs,addr=serverSock.accept() # Accept a connection. The socket must be bound to an address and listening for connections.
        print (addr)
        newThread = threading.Thread(target=clientThread, args=(cs, addr[0]))
        newThread.start()

#fileConnTransferListen method listens on port 7889 for connections from clients,
#spawns new recvFileThread for every connected client
def fileConnTransferListen():
    while True:
        csFile, addrFile = serverFileSock.accept()
        print("Receiving file data from", addrFile)
        fileThread = threading.Thread(target=recvFileThread, args=(csFile, addrFile[0]))
        fileThread.start()

#Start two listener threads
threading.Thread(target = mainListen).start()
threading.Thread(target = fileConnTransferListen).start()
