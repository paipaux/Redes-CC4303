import time
from socketTCP_copia import SocketTCP
 
SocketTCP.TIMEOUT = 0.5

address = ('localhost', 8000)
sizee = 1024

client_socketTCP = SocketTCP()
client_socketTCP.connect(address)
print("handshake OK, ahora le hablo a", client_socketTCP.direcciondestino, "seq:", client_socketTCP.numerosecuencia)
 
x = input("manda algo: ")
congestiooon = input("control de congestión (s/n): ") == "s"
 
client_socketTCP.set_congestion_control(congestiooon)
client_socketTCP.set_debug(False) # para que no afecte el tiempo :p

with open(x, "rb") as f:
    mensaje = f.read()

inicio = time.perf_counter()
client_socketTCP.send(mensaje, mode="go_back_n")
tiempo = time.perf_counter() - inicio

print("resultado: ", "cc" if congestiooon else "nocc", len(mensaje), 
      round(tiempo, 2), client_socketTCP.number_of_sent_segments)