# Estructura a definir:

# 127.0.0.1;8881;hola  

ip_test = bytes([127, 0, 0, 1, 88, 81, 104 ,111 ,108 ,97])


msg = '127.0.0.1;8881;hola esta es una prueba de que el mensaje puede ser largo'

#son toditos iguales 
holabytes = "hola".encode()
holabytes2 = bytes([104, 111, 108 ,97])
holabytes3 = b'hola'
holabytes4 = 'hola'.encode()
# print(holabytes == holabytes2)

def parse_packet(IP_packet:bytes):
    msg= '' 
    for i in range(4):
        msg += str(IP_packet[i])
        if i < 3:
            msg += '.'
    msg += ';' 
    for i in range(4,6):
        msg += str(IP_packet[i])
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

    packet_in_bytes += bytes([int(parsed_port[:len(parsed_port)//2])])
    packet_in_bytes += bytes([int(parsed_port[len(parsed_port)//2:])])

    packet_in_bytes += parsed_msg.encode()
    return packet_in_bytes


#mini test

print(create_packet(msg))
print(parse_packet(create_packet(msg)))
print(create_packet(parse_packet(create_packet(msg)))) 

#ip:
print(parse_packet(create_packet(msg)).split(";")[0])
#puerto:
print(parse_packet(create_packet(msg)).split(";")[1])
#mensaje:
print(parse_packet(create_packet(msg)).split(";")[2])


#test de EOL check

IP_packet_v1 = ip_test
parsed_IP_packet = parse_packet(IP_packet_v1)
IP_packet_v2 = create_packet(parsed_IP_packet)
print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))


