import socket
import random

class SocketTCP:
    headersizee = 5  # 1 byte flags y 4 de numero de secuencia
    buffsizeeee = 5 + 16  # tamaño fijo exacto: headers + 16 bytes de payload
    TIMEOUT = 1.0  # tiempo límite para retransmisión

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
        
        # 1. Preparar SYN con seq aleatorio
        seq = random.randint(0, 100)
        syn = SocketTCP.create_segment(
            {"SYN": True, "ACK": False, "FIN": False, "SEQ": seq}
        )

        # 2. Enviar SYN y esperar SYN+ACK usando Stop & Wait (con retransmisiones)
        self.UDP.settimeout(SocketTCP.TIMEOUT)
        while True:
            self.UDP.sendto(syn, address)
            try:
                data, nuevadireccion = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                respuesta = SocketTCP.parse_segment(data)
                
                # Si llega la respuesta esperada (SYN+ACK con SEQ == seq + 1)
                if respuesta and respuesta["SYN"] and respuesta["ACK"] and respuesta["SEQ"] == (seq + 1):
                    self.direcciondestino = nuevadireccion
                    break
            except socket.timeout:
                # Ocurrió pérdida de SYN o SYN+ACK -> retransmite en la siguiente iteración
                continue

        # 3. Enviar ACK final (seq = seq + 2)
        seq = seq + 2
        ack = SocketTCP.create_segment(
            {"SYN": False, "ACK": True, "FIN": False, "SEQ": seq}
        )
        self.numerosecuencia = seq
        self.UDP.sendto(ack, self.direcciondestino)

        # Restauramos el timeout para no afectar llamadas futuras
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

        # 3. Preparar SYN+ACK
        seq = seq + 1
        synack = SocketTCP.create_segment(
            {"SYN": True, "ACK": True, "FIN": False, "SEQ": seq}
        )

        # 4. Enviar SYN+ACK y esperar ACK final con Stop & Wait
        nuevo.UDP.settimeout(SocketTCP.TIMEOUT)
        while True:
            nuevo.UDP.sendto(synack, direccion)
            try:
                data2, _ = nuevo.UDP.recvfrom(SocketTCP.buffsizeeee)
                respuesta = SocketTCP.parse_segment(data2)
                if not respuesta:
                    continue

                # Caso normal: llega el ACK final esperado
                if respuesta["ACK"] and respuesta["SEQ"] == (seq + 1):
                    nuevo.numerosecuencia = respuesta["SEQ"]
                    break

                # CASO BORDE: se perdió el ACK final, pero el cliente ya empezó a mandar datos (message_length)
                if not respuesta["SYN"] and not respuesta["ACK"] and not respuesta["FIN"]:
                    nuevo.numerosecuencia = respuesta["SEQ"]
                    # Respondemos el ACK a ese primer segmento de datos para destrabar al cliente
                    ack_primer_dato = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": nuevo.numerosecuencia
                    })
                    nuevo.UDP.sendto(ack_primer_dato, nuevo.direcciondestino)
                    # Registramos el largo del mensaje que el cliente envió
                    nuevo.bytes_pendientes = int(respuesta["DATA"].decode("utf-8"))
                    break

            except socket.timeout:
                # Ocurrió pérdida de SYN+ACK o de ACK -> retransmite el SYN+ACK
                continue

        # Limpiamos timeout del socket nuevo antes de entregarlo
        nuevo.UDP.settimeout(None)
        return nuevo, nuevo.direccionorigen

    def _send_trozo_stop_and_wait(self, payload: bytes):
        """Envía un segmento y espera el ACK correspondiente con timeout y retransmisión."""
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
                # Verificamos que sea un ACK con el número de secuencia correspondiente
                if ack_seg and ack_seg["ACK"] and ack_seg["SEQ"] == self.numerosecuencia:
                    break
            except socket.timeout:
                # Ocurrió pérdida de paquete o de ACK -> se retransmite en el siguiente ciclo
                continue
        self.UDP.settimeout(None)

    def send(self, message: bytes):
        """
        Envía message:
        1. Primer segmento: informa el largo total (message_length).
        2. Siguientes segmentos: trozos de máximo 16 bytes.
        """
        if isinstance(message, str):
            message = message.encode("utf-8")

        message_length = len(message)

        # 1. Enviar el largo del mensaje como texto en bytes
        largo_bytes = str(message_length).encode("utf-8")
        self._send_trozo_stop_and_wait(largo_bytes)

        # 2. Enviar el contenido en trozos de hasta 16 bytes
        offset = 0
        while offset < message_length:
            trozo = message[offset:offset + 16]
            self._send_trozo_stop_and_wait(trozo)
            offset += len(trozo)

    def recv(self, buff_size: int) -> bytes:
        """
        Recibe hasta buff_size bytes. Si no hay una transferencia en curso,
        espera primero el segmento con message_length.
        """
        # Si no quedan datos pendientes de una llamada anterior, esperamos un nuevo mensaje
        if self.bytes_pendientes == 0 and len(self.buffer_recibido) == 0:
            # 1. Recibir segmento con message_length
            while True:
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                seg = SocketTCP.parse_segment(data)
                if seg and not seg["SYN"] and not seg["ACK"] and not seg["FIN"]:
                    self.numerosecuencia = seg["SEQ"]
                    # Responder ACK confirmando la recepción
                    ack_seg = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": self.numerosecuencia
                    })
                    self.UDP.sendto(ack_seg, self.direcciondestino)
                    
                    self.bytes_pendientes = int(seg["DATA"].decode("utf-8"))
                    break

        # 2. Recibir trozos de datos mientras no tengamos suficientes para satisfacer min(bytes_pendientes, buff_size)
        while len(self.buffer_recibido) < buff_size and self.bytes_pendientes > 0:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if not seg or seg["SYN"] or seg["ACK"]:
                continue

            # Si es el paquete que esperamos (secuencia nueva)
            if seg["SEQ"] == self.numerosecuencia + 1:
                self.numerosecuencia = seg["SEQ"]
                chunk = seg["DATA"]
                self.buffer_recibido += chunk
                self.bytes_pendientes -= len(chunk)

                # Confirmar recepción
                ack_seg = SocketTCP.create_segment({
                    "SYN": False, "ACK": True, "FIN": False,
                    "SEQ": self.numerosecuencia
                })
                self.UDP.sendto(ack_seg, self.direcciondestino)

            # Si es un duplicado (llegó un SEQ viejo porque nuestro ACK anterior se perdió)
            elif seg["SEQ"] <= self.numerosecuencia:
                ack_duplicado = SocketTCP.create_segment({
                    "SYN": False, "ACK": True, "FIN": False,
                    "SEQ": seg["SEQ"]
                })
                self.UDP.sendto(ack_duplicado, self.direcciondestino)

        # 3. Retornar hasta buff_size bytes y conservar el remanente en buffer_recibido
        cantidad_a_entregar = min(len(self.buffer_recibido), buff_size)
        datos_retorno = self.buffer_recibido[:cantidad_a_entregar]
        self.buffer_recibido = self.buffer_recibido[cantidad_a_entregar:]

        return datos_retorno

    def close(self):
        self.numerosecuencia += 1
        fin_seq = self.numerosecuencia

        # 1. Enviar FIN
        fin_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": False, "FIN": True,
            "SEQ": fin_seq
        })
        self.UDP.sendto(fin_pkt, self.direcciondestino)

        # 2. Esperar ACK del FIN
        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["ACK"] and seg["SEQ"] == fin_seq + 1:
                break

        # 3. Esperar FIN de Host B
        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["FIN"]:
                fin_b_seq = seg["SEQ"]
                break

        # 4. Enviar ACK final y cerrar
        ack_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False,
            "SEQ": fin_b_seq + 1
        })
        self.UDP.sendto(ack_pkt, self.direcciondestino)
        self.UDP.close()
        print("Conexión cerrada exitosamente en Host A (close).")

    def recv_close(self):
        # 1. Esperar FIN de Host A
        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["FIN"]:
                fin_a_seq = seg["SEQ"]
                break

        # 2. Enviar ACK al FIN de Host A
        ack_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False,
            "SEQ": fin_a_seq + 1
        })
        self.UDP.sendto(ack_pkt, self.direcciondestino)

        # 3. Enviar propio FIN
        self.numerosecuencia += 1
        mi_fin_seq = self.numerosecuencia
        fin_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": False, "FIN": True,
            "SEQ": mi_fin_seq
        })
        self.UDP.sendto(fin_pkt, self.direcciondestino)

        # 4. Esperar ACK final de Host A
        while True:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if seg and seg["ACK"] and seg["SEQ"] == mi_fin_seq + 1:
                break

        self.UDP.close()
        print("Conexión cerrada exitosamente en Host B (recv_close).")