import socket
import random

class SocketTCP:
    headersizee = 5 # 1 byte flags y 4 de numero de secuencia
    buffsizeeee = 1024

    def __init__(self):
        # inicializamos las variables que definen un socket
        # los datos que aun no sabemos se ponen como None
        self.UDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.direccionorigen = None
        self.direcciondestino = None
        self.numerosecuencia = None

    # recordatoriooo es static cuando no usa self :p
    @staticmethod
    def parse_segment(segment):
        # recibe segmento bytes y retorna diccionario
        flags = segment[0]
        seq = int.from_bytes(segment[1:5], byteorder='big')
        data = segment[SocketTCP.headersizee:]
        return {
            "SYN": (flags >> 2) % 2 == 1,
            "ACK": (flags >> 1) % 2 == 1,
            "FIN": (flags % 2) == 1,
            "SEQ": seq,
            "DATA": data,
        }

    @staticmethod
    def create_segment(diccionarioo):
        flags = (
            (int(diccionarioo["SYN"]) << 2)
            | (int(diccionarioo["ACK"]) << 1)
            | int(diccionarioo["FIN"])
        )
        header = bytes([flags]) + diccionarioo["SEQ"].to_bytes(4, byteorder="big")
        return header + diccionarioo.get("DATA", b"")
    
    def bind(self, address):
        self.UDP.bind(address)
        self.direccionorigen = address
        return print("bind correctooo")

    def connect(self, address):
        # lado cliente: (SYN, seq=x) y después que responda el servidor (ACK, seq=x+2)
        self.direcciondestino = address
        
        # (SYN, seq=x)

        seq = random.randint(0, 100)
        syn = SocketTCP.create_segment(
            {"SYN": True, "ACK": False, "FIN": False, "SEQ": seq}
        )
        # se envia al servidor el SYN y seq
        self.UDP.sendto(syn, address)

        # recibimos (SYN+ACK, seq=x+1)
        data, nuevadireccion = self.UDP.recvfrom(SocketTCP.buffsizeeee)
        respuesta = SocketTCP.parse_segment(data)
        if not (respuesta["SYN"] and respuesta["ACK"] and respuesta["SEQ"]==(seq+1)):
            raise ConnectionError("handshake fallido")

        # (ACK, seq=x+2)

        seq = seq + 2
        self.direcciondestino = nuevadireccion
        ack = SocketTCP.create_segment(
            {"SYN": False, "ACK": True, "FIN": False, "SEQ": seq}
        )
        self.numerosecuencia = seq
        self.UDP.sendto(ack, self.direcciondestino)

        

    def accept(self):
        # lado servidor: recibimos (SYN, seq) y enviamos (SYN+ACK, seq=x+1)
        # y despues esperamos el ACK finaaal

        # esperamos recibir el (SYN, seq)
        while True:
            data, direccion = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            segmento = SocketTCP.parse_segment(data)
            if segmento["SYN"] and not segmento["ACK"]:
                break
        
        seq = segmento["SEQ"]

        # creamos el nuevo socket
        nuevo = SocketTCP()
        ip = self.direccionorigen[0]
        nuevo.bind((ip, 0)) 
        nuevo.direccionorigen = nuevo.UDP.getsockname()
        nuevo.direcciondestino = direccion

        # enviamos el (SYN+ACK, seq=x+1)
        seq = seq + 1
        synack = SocketTCP.create_segment(
            {"SYN": True, "ACK": True, "FIN": False, "SEQ": seq}
        )
        nuevo.UDP.sendto(synack, direccion)

        # (ACK) final
        data2, _ = nuevo.UDP.recvfrom(SocketTCP.buffsizeeee)
        respuesta = SocketTCP.parse_segment(data2)
        if not (respuesta["ACK"] and respuesta["SEQ"]==(seq+1)):
            raise ConnectionError("handshake fallidoo")
        
        nuevo.numerosecuencia = respuesta["SEQ"]
        return nuevo, nuevo.direccionorigen


    def send(message):
        message_length = len(message)
        pass

    def recv(buff_size):
        while True:
            if (len(message_received) - min(message_length, buff_size) >= 0):
                break
        pass

    def close():
        pass

    def recv_close():
        pass