from socketTCP_copia import SocketTCP

address = ('localhost', 8000)
sizee = 1024

server_socketTCP = SocketTCP()
server_socketTCP.bind(address)
connection_socketTCP, new_address = server_socketTCP.accept()
print("handshake OK, nuevo socket en", new_address, "seq:", connection_socketTCP.numerosecuencia)

recibido = b""
while True:
    recibido += connection_socketTCP.recv(sizee, mode="go_back_n")
    if connection_socketTCP.bytes_pendientes == 0 and len(connection_socketTCP.buffer_recibido) == 0:
        break
    

with open("recibido.bin", "wb") as f:
    f.write(recibido)

print("largo recibido:", len(recibido))