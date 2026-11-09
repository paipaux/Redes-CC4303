# Estructura a definir:

# 127.0.0.1;8881;hola  

ip_test = bytes([127, 0, 0, 1, 88, 81, 104 ,111 ,108 ,97])

def parse_packet(IP_packet:bytes):
    msg= '' 
    for i in range(4):
        msg += str(IP_packet[i])
        msg += '.'
    msg += ';' 
    for i in range(4,6):
        msg += str(IP_packet[i])
    msg += ';'
    msg += (IP_packet[6:len(IP_packet)]).decode()
    return msg

print(parse_packet(ip_test))



