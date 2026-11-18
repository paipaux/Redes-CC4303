from socket import *
import sys
import ippacker


# esto lo saca del archivo 

# hostfinal = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
# portfinal = (sys.argv[2]) if len(sys.argv) > 2 else 8000
# ttl = (sys.argv[3]) if len(sys.argv) > 2 else 10
# data = sys.argv[4] #string de la forma ip:puerto:mensaje

headers_file = sys.argv[1]
host = sys.argv[2] 
port = sys.argv[3] 

with open(headers_file,"r") as f:
    address = (host, int(port))
    headers_list = f.read().splitlines()
    for i in headers_list:
        clientSocket = socket(AF_INET, SOCK_DGRAM)
        data = ippacker.create_packet(i)
        print(data)
        clientSocket.sendto(data, address)

