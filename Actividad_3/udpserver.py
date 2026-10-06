import socket
import time

address = ('localhost', 8000)
Message = "hola pipe"


server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(address)



while True:

    data, direccion = server_socket.recvfrom(16)
    conten = data.decode()
    print(conten)

    server_socket.sendto(Message.encode(), direccion)


