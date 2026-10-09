import socket
from socketTCP import SocketTCP
 
address = ('localhost', 8000)
sizee = 16
 
client_socketTCP = SocketTCP()
client_socketTCP.connect(address)
print("handshake OK, ahora le hablo a", client_socketTCP.direcciondestino, "seq:", client_socketTCP.numerosecuencia)
 
print('manda algo :')
x = input()
 
with open(x, "rb") as f:
    while True:
        trozo = f.read(sizee)
        if not trozo:
            # se acabó el archivo
            break
        client_socketTCP.send(trozo)

client_socketTCP.close()