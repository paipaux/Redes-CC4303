
# Estructura a definir:

#Actividad 6

# IP;Pueto;TTL;ID;Offset;tamaño;FLAG -> 127.0.0.1;8080;10;47;50;240;0;mensajede50bytes


#Para la actividad el offset no se calcula en octetos

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
    msg += str(IP_packet[6]) #TTL
    msg += ';'

    msg += str(IP_packet[7]) #ID de 1 byte
    msg += ';'

    offset = int.from_bytes(IP_packet[8:12], byteorder='big') #Offset de 4 bytes
    msg += str(offset)
    msg += ';'

    size = int.from_bytes(IP_packet[12:16], byteorder='big')  # Tamaño mensaje de 4 bytes
    msg += str(size)
    msg += ';'

    flag = IP_packet[16]    #Flag de 1 byte                               
    msg += str(flag)

    msg += ";"

    msg += IP_packet[17:len(IP_packet)].decode()
    

    return msg





def create_packet(parsed_ip_packet:str):
    packet_in_bytes = bytes([])
    parse_packet_splitted = parsed_ip_packet.split(";") #Puede cortar el mensaje si hay un ";" en el msg
    parsed_ip = parse_packet_splitted[0]
    parsed_port = str(parse_packet_splitted[1])
    parsed_TTL = str(parse_packet_splitted[2])
    parsed_ID = parse_packet_splitted[3]
    parsed_offset = parse_packet_splitted[4]
    parsed_size = parse_packet_splitted[5]
    parsed_FLAG = parse_packet_splitted[6]
    parsed_msg = parse_packet_splitted[7]


    for i in parsed_ip.split("."):
        packet_in_bytes += bytes([int(i)])

    packet_in_bytes += int(parsed_port).to_bytes(2, byteorder='big')
    packet_in_bytes += bytes([int(parsed_TTL)])
    packet_in_bytes += bytes([int(parsed_ID)])
    packet_in_bytes += int(parsed_offset).to_bytes(4, byteorder='big')
    packet_in_bytes += int(parsed_size).to_bytes(4, byteorder='big')
    packet_in_bytes += bytes([int(parsed_FLAG)])
    packet_in_bytes += parsed_msg.encode()

    return packet_in_bytes


# IP;Pueto;TTL;ID;Offset;tamaño;FLAG -> 127.0.0.1;8080;10;47;50;240;0
# frag_testbytes = bytes([127, 0, 0, 1, 31, 144, 10, 47, 0, 0, 0, 50, 0, 0, 0, 240, 0])
# IP_packet_v1 = frag_testbytes

# parsed_IP_packet = parse_packet(IP_packet_v1)
# IP_packet_v2 = create_packet(parsed_IP_packet)
# print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))




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

#print(contar_linea("('127.0.0.1', 8883)","route_logs_rutas_R2_v3_mtu.txt.txt"))

def check_routes(routes_file_name: str, destination_address: tuple[str, int]):
    route_counter = 10000
    log_file_name = f"route_logs_{routes_file_name}.txt"
    nexthop = None
    mtu = None
    with open(routes_file_name) as f:
        for linea in f:
            info = linea.split()
            ip_prefix = int(info[0].split('/')[1])
            binary_route = check_ip_prefix(info[0].split('/')[0],ip_prefix)
            binary_destination = check_ip_prefix(destination_address[0],ip_prefix)
            if (binary_destination == binary_route):
                if (destination_address[1] >= int(info[1])) and (destination_address[1] <= int(info[2])):
                    posibble_nexthop = ((info[3],int(info[4])))
                    posibble_mtu = info[5]
                    route_ocurrences = contar_linea(str(posibble_nexthop),log_file_name)
                    if route_ocurrences < route_counter:
                        route_counter = route_ocurrences
                        nexthop = posibble_nexthop
                        mtu = posibble_mtu


    with open(log_file_name, "a") as f:
        f.write(f"{nexthop}\n")

    with open("logs_complete_routes.txt", "a") as t:
        t.write(f"{nexthop}\n")
    return nexthop, mtu




#Tests
# print(check_routes("rutas_R2_v3.txt", ("127.0.0.1", 8884)))
# print(check_routes("router_rutasR1.txt", ("127.0.0.1", 8885)))
# print(check_routes("router_rutasR1.txt", ("127.0.0.120", 8885)))
# print(check_routes("router_rutasR1.txt", ("127.0.10.1", 8801)))



#tamaño total de los haders en bytes = 17
def fragment_IP_packet(IP_packet, mtu):
    frag_list = []
    parsed_packet = parse_packet(IP_packet).split(";")
    parsed_packet_size = int(parsed_packet[5])
    packet_totalsize = parsed_packet_size + 17
    packet_flag = parsed_packet[6]
    packet_msg = parsed_packet[7]

    if packet_totalsize <= mtu:
        frag_list.append(IP_packet)
        return frag_list
    else:
        new_offset = int(parsed_packet[4])
        i = 0
        new_packet_size = mtu - 17
         
        while i < parsed_packet_size:
            if packet_flag == "0":
                parsed_packet[6] = "1"


            if (i + new_packet_size) >= parsed_packet_size:
                parsed_packet[7] = packet_msg[i:]
                parsed_packet[5] = str(parsed_packet_size - i)
                i = parsed_packet_size
                parsed_packet[4] = str(new_offset)
                parsed_packet[6] = str(packet_flag)
                
                      
            if (i + new_packet_size) < parsed_packet_size:
                parsed_packet[7] = packet_msg[i : i + new_packet_size]
                parsed_packet[5] = str(new_packet_size)
                parsed_packet[4] = str(new_offset)
                new_offset += new_packet_size
                i += new_packet_size
                

            new_packet = ";".join(parsed_packet)
            new_packet = create_packet(new_packet)
            frag_list.append(new_packet)


        return frag_list



# listafrags = fragment_IP_packet(create_packet("127.0.0.1;8885;20;10;0;4;0;hola"),19)
# for i in listafrags:
#     print(parse_packet(i))



def reassemble_IP_packet(fragment_list):
    if len(fragment_list) == 1:
        big_frag = parse_packet(fragment_list[0]).split(";")
        if (big_frag[4] == "0") and (big_frag[6] == "0"):
            return fragment_list[0]
        else:
            return None
    else:
        sorted_frag = sorted(fragment_list, key=lambda x: int(parse_packet(x).split(";")[4]))
        first_sorted = parse_packet(sorted_frag[0]).split(";")
        last_sorted = parse_packet(sorted_frag[-1]).split(";")


        expected_offset = 0
        mensaje_completo = ""
        for i in sorted_frag:
            parsed = parse_packet(i).split(";")
            if int(parsed[4]) != expected_offset:
                return None
            expected_offset += int(parsed[5])
            mensaje_completo += parsed[7]

        first_sorted[4] = "0"
        first_sorted[5] = str(expected_offset)
        first_sorted[6] = last_sorted[6]  
        first_sorted[7] = mensaje_completo

        sorted_packet = ";".join(first_sorted)
        sorted_packet = create_packet(sorted_packet)

        return reassemble_IP_packet([sorted_packet])
        

# listafrags = fragment_IP_packet(create_packet("127.0.0.1;8885;20;10;0;200;0"),100)
# for i in listafrags:
#     print(parse_packet(i))

# print(parse_packet(reassemble_IP_packet(listafrags)))

