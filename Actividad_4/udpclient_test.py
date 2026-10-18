from socketTCP_copia import SocketTCP
 
address = ('localhost', 8000)
sizee = 1024

client_socketTCP = SocketTCP()
client_socketTCP.connect(address)
print("handshake OK, ahora le hablo a", client_socketTCP.direcciondestino, "seq:", client_socketTCP.numerosecuencia)
 
x = input("manda algo: ")
congestiooon = input("control de congestión (s/n): ") == "s"
 
client_socketTCP.set_congestion_control(congestiooon)
client_socketTCP.set_debug(True)

with open(x, "rb") as f:
    mensaje = f.read()

client_socketTCP.send(mensaje, mode="go_back_n")
print("largo enviado: ", len(mensaje))