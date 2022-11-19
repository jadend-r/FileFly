# FileFly
Very bare bones chat application with ability to send unencrypted text messages and files over TCP sockets.

FlileFlyServer.py is the central server listening for client connections on port 7888.
Server also is listening on port 7889 for connections to transfer files.
Clients maintain persistent TCP connection on port 7888 for sending and receiving messages.
Clients use port 7889 for file transfer.
