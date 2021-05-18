import sys
import socket
import struct
import ipaddress
import socketserver
import select

# method to print a usage
def help():
    print('Command line call: \n'
    + 'python3 udp_chat_client.py --user <user> --serv <addr> --port <port> \n'
    + 'With: \n'
    + '--user <user>: User name. Only alphanumeric characters are allowed, with a maximum of 20 characters. \n'
    + '--serv <addr>: Hostname/IPv4 address which should look like: xxx.xxx.xxx.xxx \n'
    + '--port <port>: Port number. Only numeric characters are allowed with a maximum of 65535. \n')

def starting_the_client():
    # check number of arguments
    if len(sys.argv) != 7:
        help()
        sys.exit(-1)

    # User check
    if sys.argv[1] == '--user':
        user = sys.argv[2]

        # constrain user names to a maximum of 20 characters
        if len(user) > 20:
            help()
            sys.exit(-1)

        # check each character of user for alphanumeric chars
        for c in user:
            if not ((ord(c) >= 65 and ord(c) <= 90) 
                or  (ord(c) >= 97 and ord(c) <= 122)
                or  (ord(c) >= 48 and ord(c) <= 57)):
                help()
                sys.exit(-1)
    else:
        help()
        sys.exit(-1)

    # Adress check
    if sys.argv[3] == '--serv':
        
        # try to create an ip address 
        try:
            ipv4 = ipaddress.ip_address(sys.argv[4])

        except:
            help()
            sys.exit(-1)

        # only an ipv4 address is valid
        if ipv4.version != 4:
            help()
            sys.exit(-1)
        
        # the address must be a string
        ipv4 = sys.argv[4]

    else:
        help()
        sys.exit(-1)

    # Port check
    if sys.argv[5] == '--port':
        port = sys.argv[6]

        # check each character of port
        for c in port:
            if not (ord(c) >= 48 and ord(c) <= 57):
                help()
                sys.exit(-1)

        # valid port numbers for useres are from 1024 to 65535
        if int(port) > 65535 or int(port) < 1024:
            help()
            sys.exit(-1)    

        # cast port to integer
        port = int(port)

    else:
        help()
        sys.exit(-1)

    return user, ipv4, port

def connection_setup(sock, user, ipv4, port):
    # struct.pack(...) returns a bytes object
    CL_CON_REQ = struct.pack('!BH{}s'.format(len(user)), 1, len(user),bytes(user, encoding='utf-8'))

    # timeout of four seconds
    sock.settimeout(4)

    for i in range(3):

        # send message
        sock.sendto(CL_CON_REQ, (ipv4,port))

        # receive message
        buffer, addr = sock.recvfrom(1400)
        # check if anser came in
        if buffer:
            break
        
        # third timeout
        if i == 2:
            print('[STATUS] Connection rejected. Server does not answer.')
            sys.exit(-1)

    # Textoutput of CL_CON_REQ
    print('[STATUS] Connecting as ' + user + ' to ' + ipv4 + ' ' + socket.gethostbyaddr(ipv4)[0] + ' ' + str(port) + '.')
    
    # unpack the answer of the server, if the connection is accepted
    try:
        SV_CON_REP = struct.unpack('!BBH', buffer)
    except:
        print('[STATUS] Connection rejected by server.')
        sys.exit(-1)

    if SV_CON_REP[1] == 0:
        print('[STATUS] Connection rejected by server.')
        sys.exit(-1)
    
    new_port = SV_CON_REP[2]
    print('[STATUS] Connection accepted. Please use port', new_port, 'for further communication.')

    return new_port


def main():

    user, ipv4, port = starting_the_client()

    # create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        new_port = connection_setup(sock, user, ipv4, port)
    except:
        sys.exit(-1)
    
    # send a first ping because the server needs a first message
    CL_PING_REP = struct.pack('!B', 5)
    sock.sendto(CL_PING_REP, (ipv4, new_port))

    while True:
        sock.settimeout(3 * 4)
        buffer, addr = sock.recvfrom(1400)
        
        # unpack the received message to get the message type
        id = struct.unpack('!B', buffer[0:1])[0]


        # an other user connected to the chat
        if id == 3:
            usr_len  = struct.unpack('!H', buffer[1:3])[0]
            usr_name = struct.unpack('!{}s'.format(usr_len), buffer[3:])[0]
            print('[CHAT] Hi, my name is ' + usr_name.decode(encoding='utf-8') + '!')

        # the server sent a ping and expects ping as answer
        if id == 4:
            sock.sendto(CL_PING_REP, (ipv4, new_port))

        # the client lost the connection to the server and gets removed
        if id == 6:
            print('[STATUS] Lost connection to the server. Timeout.')

        if id == 8:
            usr_len  = struct.unpack('!H', buffer[1:3])[0]
            usr_name = struct.unpack('!{}s'.format(usr_len), buffer[3:])[0]
            print('[CHAT] ' + usr_name.decode(encoding='utf-8') + ' left the chat.')

        read_descriptor = []
        read_descriptor.append(sock.fileno())
        read_descriptor.append(sys.stdin.fileno())

        write_descriptor = []
        exceptions_descriptor = []
        in_ready, out_ready, except_ready = select.select(read_descriptor,
                                                          write_descriptor,
                                                          exceptions_descriptor)
        for a in in_ready:
            if a is sock.fileno():
                break
            if a is sys.stdin.fileno():
                data = input()
                if data == '/disconnect':
                    CL_DISC_REQ = struct.pack('!B', 7)
                    
                    # timeout of five seconds
                    sock.settimeout(5)

                    for i in range(3):
                        sock.sendto(CL_DISC_REQ, (ipv4, new_port))
                        buffer, addr = sock.recvfrom(1400)

                        if buffer:
                            id = struct.unpack('!B', buffer[0:1])[0]
                            if id == 6:
                                print('[STATUS] Connection was terminated successfully.')
                                sys.exit(-1)
                        if i == 2:
                            print('[STATUS] Could not tear down the connection. Timeout.')
                            sys.exit(-1)

    # HIER WEITER MACHEN LARA!!!! nicht nach dem CLOSE!!!
    sock.close()

    
if __name__ == '__main__':
    main()
    
