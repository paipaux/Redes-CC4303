import socket

class SocketTCP:
    headersizee = 5 # 1 byte flags y 4 de numero de secuencia

    def __init__(self):
        # inicializamos las variables que definen un socket
        # los datos que aun no sabemos se ponen como None
        self.UDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.direccionorigen = None
        self.direcciondestino = None
        self.numerosecuencia = None

    @staticmethod
    def parse_segment(segment):
        # recibe segmento bytes y retorna diccionario
        flags = segment[0]
        seq = int.from_bytes(segment[1:5], byteorder='big')
        data = segment[SocketTCP.headersizee:]
        return {
            "SYN": bool(flags & 0b100),
            "ACK": bool(flags & 0b010),
            "FIN": bool(flags & 0b001),
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
