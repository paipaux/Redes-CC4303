from socket import *
import sys
import ippacker

host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
file = sys.argv[3] 

address = (host, port)



serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(address)


#redirigiendo paquete [paquete_ip] 
#con destino final [destination_address] desde [dirección_router_actual] hacia [dirección_next_hop]

while True:
    with open(file, "rb") as f:
        contenido = f.read()
    data, addr = serverSocket.recvfrom(1024)
    data_packet = ippacker.parse_packet(data).split(';')
    data_packet_fdestination = (data_packet[0],int(data_packet[1]))
    route_to_go = ippacker.check_routes(file,data_packet_fdestination)
    if data_packet_fdestination == address:
        print("Mensaje recibido:")
        print(data_packet[2])
    
    elif route_to_go != None:
        print(f"Redirigiendo paquete {data_packet} con destino final {data_packet_fdestination} desde {address} hacia {route_to_go} ")
        serverSocket.sendto(data,route_to_go)
        print("Mensaje redirigido")

    else: 
        print(f"No hay rutas hacia {route_to_go} para paquete {data_packet}")




