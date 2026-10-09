import socket
import random

class SocketTCP:
    headersizee = 5  # 1 byte flags + 4 bytes número de secuencia
    buffsizeeee = 5 + 16  # tamaño fijo exacto: header + 16 bytes de payload
    TIMEOUT = 2.0  # tiempo límite suficiente para tolerar el delay de netem

    def __init__(self):
        self.UDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.direccionorigen = None
        self.direcciondestino = None
        self.numerosecuencia = None
        
        # Variables de estado para recv
        self.bytes_pendientes = 0  # Bytes que faltan recibir del mensaje actual
        self.buffer_recibido = b""  # Datos ya recibidos pendientes de entregar a recv()

    @staticmethod
    def parse_segment(segment):
        if len(segment) < SocketTCP.headersizee:
            return None
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
            (int(diccionarioo.get("SYN", False)) << 2)
            | (int(diccionarioo.get("ACK", False)) << 1)
            | int(diccionarioo.get("FIN", False))
        )
        header = bytes([flags]) + diccionarioo["SEQ"].to_bytes(4, byteorder="big")
        return header + diccionarioo.get("DATA", b"")
    
    def bind(self, address):
        self.UDP.bind(address)
        self.direccionorigen = address
        print("bind correctooo")

    def connect(self, address):
        self.direcciondestino = address
        
        # 1. Enviar SYN con retransmisión Stop & Wait
        seq = random.randint(0, 100)
        syn = SocketTCP.create_segment({
            "SYN": True, "ACK": False, "FIN": False, "SEQ": seq
        })

        self.UDP.settimeout(SocketTCP.TIMEOUT)
        while True:
            self.UDP.sendto(syn, address)
            try:
                data, nuevadireccion = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                respuesta = SocketTCP.parse_segment(data)
                if respuesta and respuesta["SYN"] and respuesta["ACK"] and respuesta["SEQ"] == (seq + 1):
                    self.direcciondestino = nuevadireccion
                    break
            except socket.timeout:
                continue

        # 2. Enviar ACK final
        seq = seq + 2
        ack = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False, "SEQ": seq
        })
        self.numerosecuencia = seq
        self.UDP.sendto(ack, self.direcciondestino)
        self.UDP.settimeout(None)

    def accept(self):
        # 1. Esperar SYN
        while True:
            data, direccion = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            segmento = SocketTCP.parse_segment(data)
            if segmento and segmento["SYN"] and not segmento["ACK"]:
                break
        
        seq = segmento["SEQ"]

        # 2. Crear nuevo socket
        nuevo = SocketTCP()
        ip = self.direccionorigen[0]
        nuevo.bind((ip, 0)) 
        nuevo.direccionorigen = nuevo.UDP.getsockname()
        nuevo.direcciondestino = direccion

        # 3. Enviar SYN+ACK con Stop & Wait y manejo del caso borde
        seq = seq + 1
        synack = SocketTCP.create_segment({
            "SYN": True, "ACK": True, "FIN": False, "SEQ": seq
        })

        nuevo.UDP.settimeout(SocketTCP.TIMEOUT)
        while True:
            nuevo.UDP.sendto(synack, direccion)
            try:
                data2, _ = nuevo.UDP.recvfrom(SocketTCP.buffsizeeee)
                respuesta = SocketTCP.parse_segment(data2)
                if not respuesta:
                    continue

                # Caso normal: llega el ACK final
                if respuesta["ACK"] and respuesta["SEQ"] == (seq + 1):
                    nuevo.numerosecuencia = respuesta["SEQ"]
                    break

                # Caso borde: se perdió el ACK final, pero el cliente ya mandó el largo del mensaje
                if not respuesta["SYN"] and not respuesta["ACK"] and not respuesta["FIN"]:
                    nuevo.numerosecuencia = respuesta["SEQ"]
                    ack_primer_dato = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": nuevo.numerosecuencia
                    })
                    nuevo.UDP.sendto(ack_primer_dato, nuevo.direcciondestino)
                    nuevo.bytes_pendientes = int(respuesta["DATA"].decode("utf-8"))
                    break

            except socket.timeout:
                continue

        nuevo.UDP.settimeout(None)
        return nuevo, nuevo.direccionorigen

    def _send_trozo_stop_and_wait(self, payload: bytes):
        """Envía un segmento y espera el ACK exacto, retransmitiendo por timeout."""
        self.numerosecuencia += 1
        segmento = SocketTCP.create_segment({
            "SYN": False,
            "ACK": False,
            "FIN": False,
            "SEQ": self.numerosecuencia,
            "DATA": payload
        })

        self.UDP.settimeout(SocketTCP.TIMEOUT)
        while True:
            self.UDP.sendto(segmento, self.direcciondestino)
            try:
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                ack_seg = SocketTCP.parse_segment(data)
                if ack_seg and ack_seg["ACK"] and ack_seg["SEQ"] == self.numerosecuencia:
                    break
            except socket.timeout:
                continue
        self.UDP.settimeout(None)

    def send(self, message: bytes):
        if isinstance(message, str):
            message = message.encode("utf-8")

        message_length = len(message)

        # 1. Enviar tamaño del mensaje
        largo_bytes = str(message_length).encode("utf-8")
        self._send_trozo_stop_and_wait(largo_bytes)

        # 2. Enviar datos en trozos de máx 16 bytes
        offset = 0
        while offset < message_length:
            trozo = message[offset:offset + 16]
            self._send_trozo_stop_and_wait(trozo)
            offset += len(trozo)

    def recv(self, buff_size: int) -> bytes:
        # 1. Si no hay transferencia previa activa, esperamos el segmento con message_length
        if self.bytes_pendientes == 0 and len(self.buffer_recibido) == 0:
            while True:
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                seg = SocketTCP.parse_segment(data)
                if not seg or seg["SYN"] or seg["ACK"] or seg["FIN"]:
                    continue

                # Si es un duplicado viejo atrasado en la red, respondemos ACK y lo ignoramos
                if seg["SEQ"] <= self.numerosecuencia:
                    ack_duplicado = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": seg["SEQ"]
                    })
                    self.UDP.sendto(ack_duplicado, self.direcciondestino)
                    continue

                # Si es el segmento nuevo esperado, contiene el message_length
                if seg["SEQ"] == self.numerosecuencia + 1:
                    self.numerosecuencia = seg["SEQ"]
                    ack_seg = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": self.numerosecuencia
                    })
                    self.UDP.sendto(ack_seg, self.direcciondestino)
                    self.bytes_pendientes = int(seg["DATA"].decode("utf-8"))
                    break

        # 2. Recibir trozos de datos
        while len(self.buffer_recibido) < buff_size and self.bytes_pendientes > 0:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if not seg or seg["SYN"] or seg["ACK"] or seg["FIN"]:
                continue

            # Segmento nuevo en secuencia
            if seg["SEQ"] == self.numerosecuencia + 1:
                self.numerosecuencia = seg["SEQ"]
                chunk = seg["DATA"]
                self.buffer_recibido += chunk
                self.bytes_pendientes -= len(chunk)

                ack_seg = SocketTCP.create_segment({
                    "SYN": False, "ACK": True, "FIN": False,
                    "SEQ": self.numerosecuencia
                })
                self.UDP.sendto(ack_seg, self.direcciondestino)

            # Segmento duplicado (retransmisión vieja por pérdida de ACK anterior)
            elif seg["SEQ"] <= self.numerosecuencia:
                ack_duplicado = SocketTCP.create_segment({
                    "SYN": False, "ACK": True, "FIN": False,
                    "SEQ": seg["SEQ"]
                })
                self.UDP.sendto(ack_duplicado, self.direcciondestino)

        # 3. Retornar hasta buff_size bytes
        cantidad_a_entregar = min(len(self.buffer_recibido), buff_size)
        datos_retorno = self.buffer_recibido[:cantidad_a_entregar]
        self.buffer_recibido = self.buffer_recibido[cantidad_a_entregar:]

        return datos_retorno

    def close(self):
        self.numerosecuencia += 1
        fin_seq = self.numerosecuencia

        fin_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": False, "FIN": True,
            "SEQ": fin_seq
        })
        self.UDP.sendto(fin_pkt, self.direcciondestino)

        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["ACK"] and seg["SEQ"] == fin_seq + 1:
                break

        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["FIN"]:
                fin_b_seq = seg["SEQ"]
                break

        ack_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False,
            "SEQ": fin_b_seq + 1
        })
        self.UDP.sendto(ack_pkt, self.direcciondestino)
        self.UDP.close()
        print("Conexión cerrada exitosamente en Host A (close).")

    def recv_close(self):
        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["FIN"]:
                fin_a_seq = seg["SEQ"]
                break

        ack_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False,
            "SEQ": fin_a_seq + 1
        })
        self.UDP.sendto(ack_pkt, self.direcciondestino)

        self.numerosecuencia += 1
        mi_fin_seq = self.numerosecuencia
        fin_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": False, "FIN": True,
            "SEQ": mi_fin_seq
        })
        self.UDP.sendto(fin_pkt, self.direcciondestino)

        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["ACK"] and seg["SEQ"] == mi_fin_seq + 1:
                break

        self.UDP.close()
        print("Conexión cerrada exitosamente en Host B (recv_close).")