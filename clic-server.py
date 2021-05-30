#! /usr/bin/python3

import socket
import ssl
import threading
import select
import traceback
import re
from sys import exit
from time import time

class Clicserver:
    """The base class for a Clic (Command line chat) server"""

    def __init__(self):              
        """Init class for Clic server. """
        self.HEADER = 64 #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Size in bytes of header used to communicate message size
        self.hname = socket.gethostname() #>>>>>>>>>>>>>>>>> Returns the hostname of the host chat server is running on
        self.server_ip = socket.gethostbyname(self.hname) #> Returns server host IP via DNS. Comment, then uncomment below if used.
        # self.server_ip = "10.13.69.71" #>>>>>>>>>>>>>>>>>>>>>> Manually set server IP. Uncomment line above if using.
        self.server_port = 33333 #>>>>>>>>>>>>>>>>>>>>>>>>>>> Port the server will run on (integer, not string)
        self.server_tuple = (self.server_ip, self.server_port) #> Tuple holding socket info
        self.FORMAT = "utf-8" #>>>>>>>>>>>>>>>>>>>>>>>>>>>>> self.FORMAT text will be transmitted in
        self.DISCONNECT_MESSAGE = "#!@!DISCONNECT!@!#" #>>>> Message the client will send to disconnect
        self.USER_TIMEOUT = 30 #>>>>>>>>>>>>>>>>>>>>>>>>>>>> Time to wait for blocking sockets (especially when waiting for username)
        self.KEEPALIVE = "#!@!KEEPALIVE!@!#" #>>>>>>>>>>>>>> Message sent to client to confirm socket is up
        self.shutdown_flag = threading.Event() #>>>>>>>>>>>> Flag indicating a server shutdown has been triggered
        self.kicked_user_flag = threading.Event() #>>>>>>>>> Flag indicating a user was kicked off
        self.kicked_by = None #>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Holds the name of the thread that closed the user's connection
        self.user_vanished = threading.Event() #>>>>>>>>>>>> Flag set by user_heartbeat() to indicate dropped connection
        self.user_list = {} #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Dictionary containing list of active users
        
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH) # Context wrapper to apply TLS over sockets
        self.context.load_cert_chain(certfile='acme_chain.pem', keyfile="acme_key.pem")
        
        # self.context.load_default_certs(ssl.Purpose.CLIENT_AUTH)
        #!*!*!*!*!* WARNING: INSECURE! For testing/dev only! *!*!*!*!*!
        # self.context = ssl.SSLContext(ssl.PROTOCOL_TLS, ssl.VerifyMode(ssl.CERT_NONE))
        # self.context.load_cert_chain(certfile='cert.pem')



    def start_server(self):
        """starts the main server thread"""
        # The main server is run as its own thread to allow for user input without the server's code blocking
        #
        # 'server_handler_func' is the function for the server handler.
        # Should always be server_handler unless you're making pretty heavy changes.
        print("\n[SERVER IS STARTING]")
        self.server_socket = (socket.socket(socket.AF_INET, socket.SOCK_STREAM)) # Creates the server socket
        self.server_socket.bind(self.server_tuple) # Binds the server socket to the given IP and port
        server = threading.Thread(target=self.server_handler, daemon=True)
        server.start()

    def server_handler(self):
        """Main function running the server."""
        self.server_socket.listen() # Listens on the server socket
        print(f"\n[LISTENING] Server is listening on {self.server_tuple}")
        client_poll = select.poll() # Polling object is created to check if a client tries to connect.
                                    # Note: polling does not work on Windows. Supposedly it works with 
                                    # sockets only, but I've never managed that. Either run the server 
                                    # on Linux, or re-write the polling functions with select()
        client_poll.register(self.server_socket) # Polling object assigned to check the server socket
        while True:
            if self.shutdown_flag.is_set(): # If user triggers a shutdown, this will end the function.
                return False
            client_accept = client_poll.poll() # This is where the polling object checks the sock
            if self.shutdown_flag.is_set(): # Another shutdown check. There are many places are an unclean shutdown
                return False                # could cause errors.
            if client_accept: # If the polling object detects a connection attempt this allows it and spawns its own thread
                conn, addr = self.server_socket.accept()
                tlsconn = self.context.wrap_socket(conn, server_side=True)
                clients = threading.Thread(name=conn, target = self.client_handler, args = (tlsconn, addr))
                clients.start()
                print(f"\n[ACTIVE CONNECTIONS] {threading.activeCount() - 2}")

    def client_handler(self, conn, addr):
        """Main client management function. It is spun off by server_handler in a separate thread for each client."""
        # 'conn' is the connection object for the connecting client
        # 'addr' is the socket tuple for the connecting client.
        try:
            print(f"\n[NEW CONNECTION] {addr} connected.")
            if self.get_username(conn, addr) == True: # Calls the get_username() function. If a valid username is
                                                 # returned before timing out, client_handler proceeds.
                connected = True
                username = self.user_list[conn]['username']
                new_user_notify = f"[NEW CONNECTION] {username} has joined the chat\n"
                self.disseminate(conn, new_user_notify)
                conn_check = select.poll() # A polling object is created to check if the connection to the client
                                           # is still up. It's registered to the client connection and checks for
                                           # errors.
                conn_check.register(conn, select.POLLERR | select.POLLHUP | select.POLLNVAL)
                msg_listen = select.poll() # A polling object to check for messages from the client.
                msg_listen.register(conn, select.POLLIN) # Registered to client connection and checks for inbound messages
                while connected == True:
                    conn_confirm = conn_check.poll(100) # This is where the connection check happens every 100ms
                    if conn_confirm: # If the connection has an error, first we check if the user was kicked out.
                        if self.kicked_user_flag.is_set():
                            return False
                        print("\n[ABRUPT DISCONNECT] User \"{username}\" ({addr}) improperly disconnected.")
                        self.disconnect_user(conn) # If the user wasn't kicked out, the server closes the connection as best it can.
                        self.disconnect_user.clear()
                        connected = False
                        return False
                    msg_ready = msg_listen.poll(100) # This is where the polling object checks for inbound messages every 100ms
                    if self.shutdown_flag.is_set(): # If a server shutdown was triggered this ends the function to avoid errors.
                        return False
                    if msg_ready: # If a message is received checks to make sure the user hasn't been kicked.
                        if self.kicked_user_flag.is_set():
                            return False
                        msg_length = conn.recv(self.HEADER).decode(self.FORMAT) # Receives the header that communicates the
                        if msg_length == '':                                    # length of message server should expect.
                            msg_length = 0
                        msg_length = int(msg_length)
                        msg = conn.recv(msg_length).decode(self.FORMAT)
                        if msg == self.DISCONNECT_MESSAGE: # If the user has issued a nice disconnect request, this executes it.
                            self.send_msg("\n[DISCONNECTED] See you again soon!\n\n", conn)
                            conn.shutdown(2) # Removes the socket's read/write ability
                            conn.close() # Closes the socket                
                            print(f"\n[DISCONNECT] User \"{self.user_list[conn]}\" {addr} has disconnected.\n")
                            self.disseminate(conn, f"[DISCONNECT] {username} has disconnected.\n")
                            del self.user_list[conn] # Removes the connection from active user list
                            connected = False
                            return False
                        if msg[0:3] == "/dm":
                            self.send_dm(msg, conn)
                            continue 
                        if msg: # If a message is not a disconnect, prints it to the server log and relays to other users
                            print(f"\n[NEW MESSAGE] {username}: {msg}")
                            share_msg = f"\n[{username}]: {msg}"
                            self.disseminate(conn, share_msg)
                            continue
            else:
                print("\n[ABRUPT DISCONNECT] Could not complete connection.")
                print(f"\n[ABRUPT DISCONNECT] Connection: {conn}")
                conn.shutdown(2) # Removes the socket's read/write ability
                conn.close() # Closes the socket
                return False

        except(ConnectionResetError):
            print(f"\n[ERROR] CONNECTION RESET ERROR {addr}")
            conn.shutdown(2) # Removes the socket's read/write ability
            conn.close() # Closes the socket
            connected = False
            return False

        except Exception as err:
            if err.args[0] == 9:
                print("\n[ERROR] Errno 9 BAD FILE DESCRIPTOR")
                print("\n[ERROR] Connection already closed")
                print(traceback.format_exc())
                return False
            else:
                print('[ERROR] UNEXPECTED ERROR', err)
                print(f"err.args[0] = {err.args[0]}")
                print(traceback.format_exc())
                return False

    def get_username(self, conn, addr):
        """Attempts to receive a username from the connection. If attempt times out, closes connection."""
        # 'conn' is the connection object for the connecting client
        # 'addr' is the socket tuple for the connecting client.
        print(f"\n[WAITING FOR USERNAME] Awaiting username from {addr}")
        self.send_msg("\n[SERVER] Hello! What is your username?", conn)
        timeout = time() + self.USER_TIMEOUT # Creates a final time based on current time plus the USER_TIMEOUT length
        conn.settimeout(self.USER_TIMEOUT) # Assigns the timeout period to the connection.
        while True:
            try:
                msg_length = conn.recv(self.HEADER).decode(self.FORMAT) # Receives the header that communicates the
                if msg_length == '':                                    # length of message server should expect.
                    msg_length = 0
                msg_length = int(msg_length)
                username = conn.recv(msg_length).decode(self.FORMAT)
                for user in self.user_list:
                    if self.user_list[user]['username'].lower() == username.lower():
                        self.send(f"\n[SERVER] The username {username} is currently in use.")
                        self.send(f"\n[SERVER] Please choose another.\n")
                        continue
                if len(username) > 64: # Rejects username if longer than 64 bytes
                    self.send_msg("\n[SERVER] Please choose a username with less than 64 characters.", conn)
                    self.send_msg(f"{int(timeout - time())} seconds remaining.", conn)
                    continue
                elif len(username) == '': # Rejects empty usernames
                    self.send_msg("[SERVER] Choose a username. Any username.", conn)
                    self.send_msg(f"{int(timeout - time())} seconds remaining.", conn)
                    continue

                # except BrokenPipeError:
                #     print("\n[ABRUPT DISCONNECT] User improperly disconnected.")
                #     print(f"\n[ABRUPT DISCONNECT] Connection: {conn}")
                #     conn.shutdown(2) # Removes the socket's read/write ability
                #     conn.close() # Closes the socket
                #     return False
                
                else: # If the username is successful they are registered in the userlist and welcomed@
                    print(f"\n[NEW USERNAME] Username '{username}' belongs to {addr}")
                    self.user_list[conn] = {"username": username, "addr": addr}
                    self.send_msg(f"\n[SERVER] Welcome, {username}!", conn)
                    return True

            except socket.timeout: # Closes the connection if the socket times out.
                self.send_msg("\n[SERVER] No response received. Disconnecting.", conn)
                self.send_msg("\n\n[DISCONNECTED] You have been disconnected by the server.\n\n", conn)
                self.kicked_user_flag.set() # Sets the kicked user flag to indicate to other functions that this was intentional
                print(f"\n[USERNAME TIMEOUT] The user timed out:")
                print(f"[USERNAME TIMEOUT] {conn}")
                conn.shutdown(2) # Removes the socket's read/write ability
                conn.close() # Closes the socket
                return False
            
            except Exception as err:
                self.handle_errors(err)
                return False

    def send_msg(self, msg, conn):
        """Sends messages to users"""
        # 'msg' is the message text to be sent
        # 'conn' is the connection object for the connecting client
        try:
            message = msg.encode(self.FORMAT) # Encodes the message as a bytes object using the specified format
            msg_length = len(message) # Gets the length of the message
            send_length = str(msg_length).encode(self.FORMAT) # Gets a byte-encoded string of the message length
            send_length += b' ' * (self.HEADER - len(send_length)) # Fills out the header to the full 64 bytes
            conn.sendall(send_length) # Sends the header
            conn.sendall(message) # sends the full message

        except Exception as err:
            self.handle_errors(self, err)
    
    def send_dm(self, msg, sender_conn):
        """Sends a direct message from one user to another"""
        # 'sender_conn' is the connection object for the message sender
        # 'msg' is the sender's message (including dm tag and recipient username)
        try:
            sender = self.user_list[sender_conn]['username']
            # Uses regex to parse the single message received.
            # Regex is:
            # \s* - 0 or more whitespace characters in case message starts with leading spaces
            # (/dm) - Capture group with the prefix indicating the message is a dm
            # \s+ - One or more whitespace characters to separate the prefix from recipient username
            # (\S+) - Capture group of one or more non-whitespace characters indicating recipient username
            # \s+ - One or more whitespace characters to separate the recipient username from message
            # (\S+[\s\S]*) - Capture group of one or more non-whitespace characters comprising the message to be sent
            #                followed by 0 or more whitespace or not-whitespace characters (depending on messge)
            dm_parse = re.match(r"\s*(/dm)\s+(\S+)\s+(\S+[\s\S]*)", msg)       
            target_username = dm_parse.group(2) # Recipient username is the second capture group
            for conn in self.user_list: # Search through the connection list for that username
                found = False # Flag for if username is found
                if self.user_list[conn]['username'] == target_username:
                    target = conn # If the username is found assign that connection to 'target'
                    found = True #  and set 'found' to True
                    break
            if found == False: # If the username is not found, log it and notify sender
                print(f"[*DM*] Error: {sender} tried to send to '{target_username}'")
                dm_not_found = (f"[*DM*] Error: '{target_username}' is not a valid user")
                print(dm_not_found)
                self.send_msg(dm_not_found, sender_conn)
                return False
            message = dm_parse.group(3) # If the username is valid log message and send to target
            print(f"\n[*DM*] {sender} to {target_username}: {message}")
            dm_msg = f"\n[*DM*] [{sender}]: {message}"
            self.send_msg(dm_msg, target)
            return True
        except Exception as err:
            print(Exception)
            self.handle_errors(self, err) 


    def disseminate(self, sender_conn, message):
        """Sends received messages to all users."""
        # 'sender_conn' is the connection object for message sender
        # 'message' is the text content of the sender's message
        for conn in self.user_list:
            try:
                if conn != sender_conn: # Sends the message to everyone but the sender
                    self.send_msg(message, conn)
            except Exception as err:
                print('[UNEXPECTED ERROR]', err , f'for {conn}')
                print(traceback.format_exc())
        return True

    def disconnect_query(self):
        """When attempting to kick out a user this confirms, and passes them to the disconnect function"""
        while True:
            kick = input("\n[DISCONNECT] Which user would you like to disconnect? (blank returns to menu):  ")
            if kick == '':
                return None
            else:
                user_found = False
                for conn in self.user_list: # Check if the user is in the active user list
                    username = self.user_list[conn]['username']
                    if kick == username: # If so, passes them to disconnect function
                        self.disconnect_user(conn)
                        user_found = True
                        return True
                if user_found == False: # If the provided username isn't found informs the server operator
                    print(f"\n[DISCONNECT] User '{kick}' doesn't seem to be connected.")
                    continue

    def disconnect_user(self, conn):
        """Forcibly disconnects the provided connection"""
        username = self.user_list[conn]['username']
        try:
            # 'conn' is the connection object for the connecting client
            self.send_msg("\n\n[DISCONNECTED] You have been disconnected by the server.\n\n", conn)
            self.kicked_user_flag.set() # Sets the kicked user flag to indicate to other functions that this was intentional
            conn.shutdown(2) # Removes the socket's read/write ability
            conn.close() # Closes the socket
            print(f"\n[DISCONNECT] User {username} has been forcibly disconnected.")
            self.disseminate(conn, f"\n[DISCONNECT] User \"{username}\" has been disconnected by the server")
            if self.shutdown_flag.is_set():
                return True
            del self.user_list[conn] # Removes the connection from active user list
            return True
        except Exception as err:
            self.handle_errors(err)
            return None

    def list_users(self):
        """Prints all the users currently in the active user list"""
        print("Current users are:")
        for user in self.user_list:
            print(f"{self.user_list[user]['username']} at {self.user_list[user]['addr']}")
        return True

    def server_shutdown(self):
        """Disconnects all users, closes the server socket, then ends the server process"""
        try:
            print("\n\n\n[SHUTDOWN] Server will shut down. Are you sure?")
            print("[SHUTDOWN] Type YES to shut down.\n")
            yes_shut = input("[SHUTDOWN] ")
            if yes_shut == "YES": # Shutdown must be confirmed with the word 'YES' in all caps
                self.shutdown_flag.set() # Set the shutdown flag to cleanly end running functions and threads
                print("\n[SHUTDOWN] Disconnecting all users.")
                for conn in self.user_list: # Disconnect all connected users
                    self.disconnect_user(conn)
                self.user_list = {}
                print("\n[SHUTDOWN] Shutting down. Goodbye.\n\n")
                self.server_socket.shutdown(2) # Removes the socket's read/write ability
                self.server_socket.close() # Closes the socket
                exit()
            else: # Any confirmation reply other than 'YES' aborts the shutdown
                print("[SHUTDOWN] Shutdown aborted.")
                return False
        except Exception as err:
            self.handle_errors(err)

    def handle_errors(self, err, third):
        print(f"Mysterious third argument: {third}")
        if self.kicked_user_flag.is_set():
            print(f"\n[DISCONNECT] Connection for user was closed after being disconnected.")
        if err.args[0] == 9:
            print("\n[ERROR] Errno 9 BAD FILE DESCRIPTOR")
            print("\n[ERROR] Connection already closed")
            print(traceback.format_exc())
            return True
        else:
            print('[ERROR] UNEXPECTED ERROR', err)
            print(traceback.format_exc())
            print(f"err.args[0] = {err.args[0]}")
            return False

    def get_help(self):
        """Prints all the available server commands"""
        print("\nAvailable commands are:")
        print("'/q' ......... Shutdown (quit) server")
        print("'/u' ......... Print a list of users")
        print("'/d' ......... Disconnect a user")
        print("\n")

    def server_control(self):
        """Takes user input for controlling the server."""
        while True:
            cmd = input("\n")
            if cmd == '/q': # 'q' shuts down the server
                self.server_shutdown()
            elif cmd == '/u': # 'u' prints the list of users
                self.list_users()
                continue
            elif cmd == '/d': # 'd' begins the process of disconnecting a user
                self.disconnect_query()
                self.kicked_user_flag.clear()
                continue
            else: # Any input not assigned to a command prints the help menu
                self.get_help()
                continue 


if __name__ == "__main__":
    clic = Clicserver() #>>> Instantiate a Clicserver on port 33333
    clic.start_server() #>>>>>>>> Start the server
    clic.server_control() #>>>>>> Start the server controls
