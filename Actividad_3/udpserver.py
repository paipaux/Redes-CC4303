import socket
import time
from socketTCP import SocketTCP

address = ('localhost', 8000)

server_socketTCP = SocketTCP()
server_socketTCP.bind(address)
connection_socketTCP, new_address = server_socketTCP.accept()
print("handshake OK, nuevo socket en", new_address, "seq:", connection_socketTCP.numerosecuencia)

while True:
    data = connection_socketTCP.recv(16)
    if data == b"":
        break
    print("Recibido: ", data.decode("utf-8", errors="replace"))

connection_socketTCP.close()
server_socketTCP.close()