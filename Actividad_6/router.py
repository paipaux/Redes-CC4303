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

lista_fragmentos_recibidos = []

Diccionario_fragmentos = {}

while True:



    with open(file, "rb") as f:
        contenido = f.read()
    data, addr = serverSocket.recvfrom(1024)
    data_packet = ippacker.parse_packet(data).split(';')
    ttl_packet = int(data_packet[2])
    data_packet_fdestination = (data_packet[0],int(data_packet[1]))
    route_to_go, mtu = ippacker.check_routes(file,data_packet_fdestination)


    if ttl_packet < 1:
        print(f"Se recibió paquete {data_packet} con TTL 0")

    else:    
        ttl_packet -= 1
        data_packet[2] = str(ttl_packet)
        newdata = ";".join(data_packet)
        data = ippacker.create_packet(newdata)
        
        if data_packet_fdestination == address:
            id_paquete = data_packet[3]
            

            Diccionario_fragmentos.setdefault(id_paquete, []).append(data)
            

            paquete_ensamblado = ippacker.reassemble_IP_packet(Diccionario_fragmentos[id_paquete])


            if paquete_ensamblado is not None:
                mensaje = ippacker.parse_packet(paquete_ensamblado).split(";")[7]
                print("Mensaje recibido:")
                print(mensaje)
                del Diccionario_fragmentos[id_paquete]

        
        elif route_to_go != None:
            
            list_fragpackets = ippacker.fragment_IP_packet(data,int(mtu))
            for packet in list_fragpackets:
                data = packet
                data_packet = ippacker.parse_packet(packet).split(';')
                print(f"Redirigiendo paquete {data_packet} con destino final {data_packet_fdestination} desde {address} hacia {route_to_go} ")
                serverSocket.sendto(data,route_to_go)
                print("Mensaje redirigido")

        else: 
            print(f"No hay rutas hacia {route_to_go} para paquete {data_packet}")




