import socket
import sys
from socketTCP import SocketTCP

host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

server_socketTCP = SocketTCP()
server_socketTCP.bind((host, port))

connection_socketTCP, new_address = server_socketTCP.accept()
print("handshake OK, nuevo socket en", new_address)


n = 16 # se cambia a 25 para el otro test
contador = 1

while True:
    data = connection_socketTCP.recv(n)
    if data == b"":
        break
    print(f"[Iteración {contador}] recv({n}) devolvió {len(data)} bytes -> Contenido: '{data.decode()}'")
    contador += 1

connection_socketTCP.recv_close()
server_socketTCP.UDP.close()