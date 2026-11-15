from socket import *
import sys

host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
file = sys.argv[3] 

address = (host, port)



serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(address)

while True:
    with open(file, "rb") as f:
        contenido = f.read()
    data, addr = serverSocket.recvfrom(1024)
    print(data)