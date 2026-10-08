import socket

address = ('localhost', 8000)
sizee = 16

clienteSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print('manda algo :')
x = input()


with open(x, "rb") as f:
    while True:
        trozo = f.read(sizee)
        if not trozo:
            # se acabó el archivo
            break
        clienteSocket.sendto(trozo, address)




while True:
    data, addr = clienteSocket.recvfrom(16)
    print("Recibido: ", data)