from socket import *
import sys
import ippacker


#Recibe Ip_final Puerto_final mensaje Ip Puerto  

#Se desabilitan los sys.arfv para probar 
# IP;Pueto;TTL;ID;Offset;tamaño;FLAG -> 127.0.0.1;8080;10;47;50;240;1
msg = ippacker.create_packet("127.0.0.1;8881;20;1;0;150;0;123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890")
msg2 = ippacker.create_packet("127.0.0.1;8881;20;2;0;150;0;223456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890")
msg3 = ippacker.create_packet("127.0.0.1;8881;20;3;0;150;0;323456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890")

# hostfinal = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
# portfinal = (sys.argv[2]) if len(sys.argv) > 2 else 8000
# ttl = (sys.argv[3]) if len(sys.argv) > 2 else 10
# data = sys.argv[4] 
host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
port = (sys.argv[2]) if len(sys.argv) > 2 else 8000


# msg = ippacker.create_packet(hostfinal + ';' + portfinal + ';' + ttl + ';' + data)


#Dirección la cual se va a mandar el msg (host y port)

address = (host, int(port))
clientSocket = socket(AF_INET, SOCK_DGRAM)

clientSocket.sendto(msg, address)
clientSocket.sendto(msg2, address)
clientSocket.sendto(msg3, address)
