from socket import *
import sys
import ippacker


#Recibe Ip_final Puerto_final mensaje Ip Puerto  


hostfinal = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
portfinal = (sys.argv[2]) if len(sys.argv) > 2 else 8000
ttl = (sys.argv[3]) if len(sys.argv) > 2 else 10
data = sys.argv[4] 
host = sys.argv[5] if len(sys.argv) > 1 else 'localhost'
port = (sys.argv[6]) if len(sys.argv) > 2 else 8000


msg = ippacker.create_packet(hostfinal + ';' + portfinal + ';' + ttl + ';' + data)

#Dirección la cual se va a mandar el msg (host y port)
address = (host, int(port))
clientSocket = socket(AF_INET, SOCK_DGRAM)

clientSocket.sendto(msg, address)