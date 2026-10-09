from socketTCP import SocketTCP

address = ('localhost', 8000)

client_socketTCP = SocketTCP()
client_socketTCP.connect(address)

# test 1
message = "Mensje de len=16".encode()
client_socketTCP.send(message)

# test 2
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)

# test 3
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)

# --- FIN DE CONEXIÓN (Host A) ---
print("\nIniciando cierre ")
client_socketTCP.close()
print("Cliente terminado.")