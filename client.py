#! /usr/bin/python3

import socket
import ssl
import threading
import sys
import traceback

HEADER = 64 #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Size in bytes of header used to communicate message size
PORT = 33333 #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Port the server will run on (integer, not string)
HOSTNAME = "sub.domain.tld" #>>>>>>>>>>>>>>>>> Returns the hostname of the host chat server is running on
server = socket.gethostbyname(HOSTNAME) #>>>>>> Returns the server's IP address
# server = '10.10.10.10' #>>>>>>>>>>>>>>>>>>>>> Alternatively you can enter a specific IP
ADDR = (server, PORT) #>>>>>>>>>>>>>>>>>>>>>>>> Tuple holding socket info
FORMAT = 'utf-8' #>>>>>>>>>>>>>>>>>>>>>>>>>>>>> self.FORMAT text will be transmitted in
DISCONNECT_MESSAGE = "#!@!DISCONNECT!@!#" #>>>> Message the client will send to disconnect
KEEPALIVE = "#!@!KEEPALIVE!@!#" #>>>>>>>>>>>>>> Message sent to client to confirm socket is up
GIVECLIENTS = "#!@!GIVECLIENT!@!#" #>>>>>>>>>>> Message triggers server to send client list
context = ssl.create_default_context() #>>>>>>> Context wrapper to apply TLS over sockets

# !*!*!*!*!* WARNING: INSECURE! For testing/dev use only! *!*!*!*!*!
# context = ssl.SSLContext(ssl.PROTOCOL_TLS)
# context.verify_mode = ssl.CERT_NONE
# context.check_hostname = False

disconnect = threading.Event() # Event object to signal when a disconnect has triggered



def send_msg(msg):
    """ Function that sends the user's message """
    try:
        message = msg.encode(FORMAT) # Encode the message in the format specified above
        msg_length = len(message) # Calculate the length of the message
        send_length = str(msg_length).encode(FORMAT) # Encode that
        send_length += b' ' * (HEADER - len(send_length)) # Pad the remaining bits in the header
        tlsclient.sendall(send_length) # Send the length header
        tlsclient.sendall(message) # Send the message
        return True
    except Exception as err:
        handle_error(err)

def handle_error(err):
    """ Does what it says on the tin """
    if disconnect.is_set(): # If the user or server requested disconnect, no need to worry
        return None
    if err.args[0] != 9: # I can't remember what this specific error was but it happened too often
        print('[UNEXPECTED ERROR]', err)
        print(traceback.format_exc())
        sys.exit()
    else:
        print("\n[ERROR: ABRUPT DISCONNECT] Connection to CLIc broke unexpectedly")
        print(traceback.format_exc())
        sys.exit()

def receive_messages(conn):
    "Handles message reception"
    while True:
        try: 
            msg_length = conn.recv(HEADER).decode(FORMAT) # Receives the header detailing the message length
            if msg_length == '': # if the message length is blank, ignore it
                break
            msg_length = int(msg_length) # Determine message length from headerr
            msg = conn.recv(msg_length).decode(FORMAT) # Receive a message of that length
            print(msg)
            if "[DISCONNECTED]" in msg[1:18]: # If the client has been disconnected, or chose to, close connection
                conn.shutdown(2)
                conn.close()
                disconnect.set()
                print("[DISCONNECTED] Press 'Enter' to quit")
                return False
            if msg == KEEPALIVE: # If it's a keepalive message checking in, just carry on
                continue
        except Exception as err:
            handle_error(err)

def get_help():
    """Prints all the available server commands"""
    print("\nAvailable commands are:")
    print("'/q' ......... Shutdown (quit) server")
    print("'/u' ......... See who is online")
    print("\n")
    return None

def client_input():
    while True:
        speak = input()
        if disconnect.is_set():
            sys.exit()
        if speak == "":
            get_help()
        if speak == "/q":
            send_msg(DISCONNECT_MESSAGE)
            print("\nDisconnecting. Goodbye!")
        if speak == "/u":
            send_msg(GIVECLIENTS)

        else:
            send_msg(speak)
            continue

def check_disco():
    try:
        while True:
            if disconnect.is_set():
                tlsclient.shutdown(2) # Removes the socket's read/write ability
                tlsclient.close() # Closes the socket
                sys.exit()
    except Exception as err:
        handle_error(err)

# TLS context "wraps" the socket an all operations are performed on the new TLS socket.
tlsclient = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=HOSTNAME)
tlsclient.connect(ADDR)
print(tlsclient.getpeercert())

# Creates a thread to listen for and print messages from the server
server_listen = threading.Thread(name="listen",target=receive_messages, args=(tlsclient,), daemon=True)
server_listen.start()

client_input()

