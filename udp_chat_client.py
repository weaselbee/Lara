import sys
import socket
import struct
import ipaddress
import select

# Usage for the user
def help():
    print('Usage: \n'
    + 'Command line call: \n'
    + 'python3 udp_chat_client.py --user <user> --serv <addr> --port <port> \n'
    + 'With: \n'
    + '--user <user>: User name. Only alphanumeric characters are allowed, with a maximum of 20 characters. \n'
    + '--serv <addr>: Hostname/IPv4 address which should look like: xxx.xxx.xxx.xxx \n'
    + '--port <port>: Port number. Only numeric characters are allowed with a maximum of 65535. \n')

# check if given username is valid
def username_check(username):
    name_length  = True
    alphanumeric = True

    # constrain user names to a maximum of 20 characters
    if len(username) > 20:
        name_length = False

    # check each character of user for alphanumeric chars
    for c in username:
        if not ((ord(c) >= 65 and ord(c) <= 90) 
            or  (ord(c) >= 97 and ord(c) <= 122)
            or  (ord(c) >= 48 and ord(c) <= 57)):
            alphanumeric = False
    
    if name_length and alphanumeric:
        return True
    else:
        return False

# task 1.2
def starting_the_client():

    # no user input or user looks for help
    if len(sys.argv) == 1:
        help()
        sys.exit(0)
    elif sys.argv[1] == '--help':
        help()
        sys.exit(0)

    # check number of arguments
    if len(sys.argv) != 7:
        help()
        sys.exit(0)

    # make parameters order flexible
    check_count = 0
    for i in range(1, 7):
        if i == 2 or i == 4 or i == 6:
            pass
        # User check
        elif sys.argv[i] == '--user':
            user = sys.argv[i + 1]
            check_count = check_count + 1
            
            if not username_check(user):
                help()
                sys.exit(0)

        # Adress check
        elif sys.argv[i] == '--serv':
            
            # try to create an ip address 
            try:
                ipv4 = ipaddress.ip_address(sys.argv[i + 1])
                check_count = check_count + 1
            except:
                help()
                sys.exit(0)

            # only an ipv4 address is valid
            if ipv4.version != 4:
                help()
                sys.exit(0)
            
            # the address must be a string
            ipv4 = sys.argv[i + 1]

        # Port check
        elif sys.argv[i] == '--port':
            port = sys.argv[i + 1]
            check_count = check_count + 1

            # check each character of port
            for c in port:
                if not (ord(c) >= 48 and ord(c) <= 57):
                    help()
                    sys.exit(0)

            # valid port numbers for useres are from 1024 to 65535
            if int(port) > 65535 or int(port) < 1024:
                help()
                sys.exit(0)    

            # cast port to integer
            port = int(port)

        else:
            help()
            sys.exit(0)

    if check_count == 3:
        return user, ipv4, port
    else:
        help()
        sys.exit(0)

# task 1.3
def connection_setup(sock, user, ipv4, port):
    
    CL_CON_REQ = struct.pack('!BH{}s'.format(len(user)), 1, len(user),
                                bytes(user, encoding='utf-8'))

    sock.settimeout(4)

    for i in range(3):
        # send message
        sock.sendto(CL_CON_REQ, (ipv4, port))

        # Textoutput of CL_CON_REQ
        print('[STATUS] Connecting as ' + user
            + ' to ' + str(ipv4) + ' (' + socket.gethostbyaddr(ipv4)[0] + '): '
            + str(port) + '.')

        try:
            # receive message
            buffer, addr = sock.recvfrom(1400)
            break
        except:
            # third timeout
            if i == 2:
                print('[STATUS] Connection rejected. Server does not answer.')
                sys.exit(0)
            
    
    # unpack the answer of the server, if the connection is accepted
    try:
        SV_CON_REP = struct.unpack('!BBH', buffer)
    except:
        print('[STATUS] Connection rejected by server.')
        sys.exit(0)

    # server detected error
    if SV_CON_REP[1] == 13:
        msg_len  = struct.unpack('!I', buffer[1:5])[0]
        msg      = struct.unpack('!{}s'.format(msg_len), buffer[5:])[0]
        print('[SERVER] ' + msg.decode(encoding='utf-8'))
    
    new_port = SV_CON_REP[2]

    print('[STATUS] Connection accepted. Please use port ' + str(new_port) + ' for further communication.')

    # send a first ping because the server needs a first message
    CL_PING_REP = struct.pack('!B', 5)
    sock.sendto(CL_PING_REP, (ipv4, new_port))
  
    return new_port

#task 1.4
def connection_monitoring(sock, ipv4, new_port):
    sock.settimeout(3 * 4)
    CL_PING_REP = struct.pack('!B', 5)
    buffer, addr = sock.recvfrom(1400)
    
    # unpack the received message to get the message type
    id = struct.unpack('!B', buffer[0:1])[0]

    # an other user connected to the chat
    if id == 3:
        usr_len  = struct.unpack('!H', buffer[1:3])[0]
        usr_name = struct.unpack('!{}s'.format(usr_len), buffer[3:])[0]
        print('[CHAT] Hi, my name is <' + usr_name.decode(encoding='utf-8') + '>!')

    # the server sent a ping and expects ping as answer
    if id == 4:
        sock.sendto(CL_PING_REP, (ipv4, new_port))

    # the client lost the connection to the server and gets removed
    if id == 6:
        print('[STATUS] Lost connection to the server. Timeout.')

    # an user left the chat with '/disconnect'
    if id == 8:
        usr_len  = struct.unpack('!H', buffer[1:3])[0]
        usr_name = struct.unpack('!{}s'.format(usr_len), buffer[3:])[0]
        print('[CHAT] <' + usr_name.decode(encoding='utf-8') + '> left the chat.')

    # receive messages from other useres to chat
    if id == 12:
        usr_len  = struct.unpack('!H', buffer[1:3])[0]
        usr_name = struct.unpack('!{}s'.format(usr_len), buffer[3:(3 + usr_len)])[0] 
        msg_len  = struct.unpack('!I', buffer[(3 + usr_len):(3 + usr_len + 4)])[0]
        msg      = struct.unpack('!{}s'.format(msg_len), buffer[(3 + usr_len + 4):])[0]
        print('[CHAT] <' + usr_name.decode(encoding='utf-8') + '>: ' + msg.decode(encoding='utf-8'))

    # server detected error
    if id == 13:
        msg_len  = struct.unpack('!I', buffer[1:5])[0]
        msg      = struct.unpack('!{}s'.format(msg_len), buffer[5:])[0]
        print('[SERVER] ' + msg.decode(encoding='utf-8'))

# task 1.5
def connection_teardown(sock, ipv4, new_port):        
    CL_DISC_REQ = struct.pack('!B', 7)
    
    # timeout of five seconds
    sock.settimeout(5)

    # try 2 times, otherwise the teardown failed
    for i in range(3):
        sock.sendto(CL_DISC_REQ, (ipv4, new_port))

        print('[STATUS] Disconnecting from ' + socket.gethostbyaddr(ipv4)[0] + ' (' + ipv4 + ').')
        buffer, addr = sock.recvfrom(1400)

        if buffer:
            id = struct.unpack('!B', buffer[0:1])[0]
            if id == 6:
                print('[STATUS] Connection was terminated successfully.')
                sys.exit(0)
            if i == 2:
                print('[STATUS] Could not tear down the connection. Timeout.')
                sys.exit(0)

# task 1.6
def user_query(sock, ipv4, new_port, name):

    # username the user asked for
    CL_USER_REQ = struct.pack('!BH{}s'.format(len(name)), 9, len(name), bytes(name, encoding='utf-8'))
    sock.sendto(CL_USER_REQ, (ipv4, new_port))
    print('[STATUS] Asking for availability of ' + name + '.')
    buffer, addr = sock.recvfrom(1400)
    
    # answer of the server
    SV_USER_REP = struct.unpack('!BB', buffer[0:2])
    
    # the username is not connected to the server
    if SV_USER_REP[1] == 0 and SV_USER_REP[0] == 10:
        print('[STATUS] User', name, 'was not found on this server.')
    
    # the username is connected
    elif SV_USER_REP[1] == 1 and SV_USER_REP[0] == 10:
        name_len = struct.unpack('!H', buffer[2:4])[0]
        user_name = struct.unpack('!H{}s'.format(name_len), buffer[2:])
        user_name = user_name[1]
        print('[STATUS] User', user_name.decode(encoding='utf-8'), 'is here!')



def main():

    user, ipv4, port = starting_the_client()

    # create UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:

        new_port = connection_setup(sock, user, ipv4, port)
        
        while True:

            # descriptors for select()
            read_descriptor = []
            read_descriptor.append(sock.fileno())
            read_descriptor.append(sys.stdin.fileno())
            write_descriptor = []
            exceptions_descriptor = []

            # call select()
            in_ready, out_ready, except_ready = select.select(read_descriptor,
                                                            write_descriptor,
                                                            exceptions_descriptor)

            for a in in_ready:

                # socket handling
                if a is sock.fileno(): 
                    connection_monitoring(sock, ipv4, new_port)
                
                # input
                if a is sys.stdin.fileno():
                    data = input()

                    # no input
                    if data == '':
                        break

                    # commands
                    if data[0] == '/':
                        if data == '/disconnect':
                            connection_teardown(sock, ipv4, new_port)
                        else:
                            try:
                                data = data.split(' ')
                                search = data[0]
                                name   = data[1]
                                
                                # command to ask for other users on the server
                                if search == '/search':
                                    if username_check(name):
                                        user_query(sock, ipv4, new_port, name)
                                    else:
                                        print('[WARNING] Invalid username was entered.')
                            except:
                                # ignore invalid commands
                                pass
                    # chat message
                    else:
                        if sys.getsizeof(data) <= 1400:
                            CL_MSG = struct.pack('!BI{}s'.format(len(data)), 11, len(data), bytes(data, encoding='utf-8'))
                            sock.sendto(CL_MSG, (ipv4, new_port))
                        else:
                            print('[WARNING] Message is too big.')
    
if __name__ == '__main__':
    main()
    
