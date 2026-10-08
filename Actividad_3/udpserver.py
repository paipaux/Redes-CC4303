import socket
import time

address = ('localhost', 8000)
Message = "hola pipe"


server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(address)

recibido = b""

while True:
    data, direccion = server_socket.recvfrom(500)
    print("Recibido: ", data.decode("utf-8"))
    if data == b"":
        # está vacioo, es el fin
        recibido = b""
        continue
    recibido += data
    server_socket.sendto(Message.encode(), direccion)
