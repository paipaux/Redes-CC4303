from collections import Counter
# Estructura a definir:

# 127.0.0.1;8881;hola  

# ip_test = bytes([127, 0, 0, 1, 88, 81, 104 ,111 ,108 ,97])


# msg = '127.0.0.1;8801;hola esta es una prueba de que el mensaje puede ser largo'

#son toditos iguales 
#holabytes = "hola".encode()
# holabytes2 = bytes([104, 111, 108 ,97])
# holabytes3 = b'hola'
# holabytes4 = 'hola'.encode()
# print(holabytes == holabytes2)


#Punto 4 
def parse_packet(IP_packet:bytes):
    msg= '' 
    for i in range(4):
        msg += str(IP_packet[i])
        if i < 3:
            msg += '.'
    msg += ';' 
    puerto = int.from_bytes(IP_packet[4:6], byteorder='big') #soluciona bug que omite los 0's, 8801 -> 881 
    msg += str(puerto)
    msg += ';'
    msg += (IP_packet[6:len(IP_packet)]).decode()
    return msg




def create_packet(parsed_ip_packet:str):
    packet_in_bytes = bytes([])
    parse_packet_splitted = parsed_ip_packet.split(";") #Puede cortar el mensaje si hay un ";" en el msg
    parsed_ip = parse_packet_splitted[0]
    parsed_port = str(parse_packet_splitted[1])
    parsed_msg = parse_packet_splitted[2]

    for i in parsed_ip.split("."):
        packet_in_bytes += bytes([int(i)])

    packet_in_bytes += int(parsed_port).to_bytes(2, byteorder='big')

    packet_in_bytes += parsed_msg.encode()
    return packet_in_bytes


#mini test
    # print(create_packet(msg))
    # print(parse_packet(create_packet(msg)))
    # print(create_packet(parse_packet(create_packet(msg)))) 

    # #ip:
    # print(parse_packet(create_packet(msg)).split(";")[0])
    # #puerto:
    # print(parse_packet(create_packet(msg)).split(";")[1])
    # #mensaje:
    # print(parse_packet(create_packet(msg)).split(";")[2])


    # #test de EOL check1

    # IP_packet_v1 = ip_test
    # parsed_IP_packet = parse_packet(IP_packet_v1)
    # IP_packet_v2 = create_packet(parsed_IP_packet)
    # print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))


#Punto 6

#retorna lo primeros n digitos de la ip en binario
def check_ip_prefix(ip: str, n: int):
    ip_list = ip.split('.')
    ip_list = [format(int(i), '08b') for i in ip_list]
    ipinbytes = ("").join(ip_list)
    return(ipinbytes[:n])


def contar_linea(objetivo, log_file_name):
    contador = 0
    objetivo = objetivo.strip()
    try:
        with open(log_file_name, "r") as f:
            for linea in f:
                if linea.strip() == objetivo:
                    contador += 1
    except FileNotFoundError:
        pass

    return contador

def check_routes(routes_file_name: str, destination_address: tuple[str, int]):
    route_counter = 10000
    log_file_name = f"route_logs_{routes_file_name}.txt"
    nexthop = None
    with open(routes_file_name) as f:
        for linea in f:
            info = linea.split()
            ip_prefix = int(info[0].split('/')[1])
            binary_route = check_ip_prefix(info[0].split('/')[0],ip_prefix)
            binary_destination = check_ip_prefix(destination_address[0],ip_prefix)
            if (binary_destination == binary_route):
                if (destination_address[1] >= int(info[1])) and (destination_address[1] <= int(info[2])):
                    posibble_nexthop = ((info[3],int(info[4])))
                    route_ocurrences = contar_linea(str(posibble_nexthop),log_file_name)
                    if route_ocurrences < route_counter:
                        route_counter = route_ocurrences
                        nexthop = posibble_nexthop

    with open(log_file_name, "a") as f:
        f.write(f"{nexthop}\n")
    return nexthop







           

            


#(info[3],int(info[4]))


#Tests
# print(check_routes("rutas_R2_v3.txt", ("127.0.0.1", 8884)))
# print(check_routes("router_rutasR1.txt", ("127.0.0.1", 8885)))
# print(check_routes("router_rutasR1.txt", ("127.0.0.120", 8885)))
# print(check_routes("router_rutasR1.txt", ("127.0.10.1", 8801)))






