import socket
import sys
from socketTCP import SocketTCP

address = ('localhost', 8000)
sizee = 16
 
client_socketTCP = SocketTCP()
client_socketTCP.connect(address)
print("handshake OK, ahora le hablo a", client_socketTCP.direcciondestino, "seq:", client_socketTCP.numerosecuencia)

# Detecta si se pasa por redirección de terminal (< carprueba/archivo.txt) o si se pide la ruta por consola
if not sys.stdin.isatty():
    contenido = sys.stdin.buffer.read()
else:
    print('manda algo :')
    x = input()
    with open(x, "rb") as f:
        contenido = f.read()

# SocketTCP fragmenta internamente en trozos de 16 bytes usando Stop & Wait
client_socketTCP.send(contenido)

client_socketTCP.close()