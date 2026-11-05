from socket import *
import sys

host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
file = sys.argv[3] 

address = (host, port)



serverSocket = socket(AF_INET, SOCK_DGRAM)

while True:
    with open(file, "rb") as f:
        contenido = f.read()
    print(contenido)
    message, address = serverSocket.recvfrom(1024)
    print(file)
    serverSocket.sendto(message, address)