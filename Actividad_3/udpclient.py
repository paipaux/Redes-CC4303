import socket

address = ('localhost', 8000)

clienteSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print('manda algo :')
x = input()


with open(str(x), "r", encoding="utf-8") as f:
    contenido = f.read()

print(contenido)

clienteSocket.sendto(contenido.encode(), address)



while True:
    data, addr = clienteSocket.recvfrom(16)
    print("Recibido: ", data)