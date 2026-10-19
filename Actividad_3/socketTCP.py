import socket
import random
import time

class SocketTCP:
    headersizee = 5  # 1 byte flags + 4 bytes número de secuencia
    buffsizeeee = 5 + 16  # tamaño fijo exacto: header + 16 bytes de payload
    TIMEOUT = 2.0  # tiempo límite suficiente para tolerar el delay de netem
    INTENTOS_CIERRE = 3  # cantidad de timeouts que se esperan al cerrar

    def __init__(self):
        self.UDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.direccionorigen = None
        self.direcciondestino = None
        self.numerosecuencia = None

        # Variables
        self.bytes_pendientes = 0  # bytes que faltan recibir del mensaje actual
        self.buffer_recibido = b""  # datos ya recibidos pendientes de entregar a recv()
        self.fin_pendiente = None  # seq del FIN si recv() lo recibió (lo usa recv_close)
        self.syn_atendidos = set()  # (direccion, seq) de SYN ya aceptados (socket que escucha)

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

        # 1. Enviar SYN
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

        # 2. Enviar ACK
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
                # un SYN retransmitido de una conexion ya aceptada se ignora:
                # el socket nuevo ya se encarga de reenviar el SYN+ACK
                clave = (direccion, segmento["SEQ"])
                if clave in self.syn_atendidos:
                    continue
                self.syn_atendidos.add(clave)
                break

        seq = segmento["SEQ"]

        # 2. Crear nuevo socket
        nuevo = SocketTCP()
        ip = self.direccionorigen[0]
        nuevo.bind((ip, 0))
        nuevo.direccionorigen = nuevo.UDP.getsockname()
        nuevo.direcciondestino = direccion

        # 3. Enviar syn+ack
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

                # se pierde el ACK final
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
        # 0. Si ya habíamos visto el FIN y no queda nada que entregar, no hay más datos
        if self.fin_pendiente is not None and self.bytes_pendientes == 0 and len(self.buffer_recibido) == 0:
            return b""

        # 1. Si no hay transferencia previa activa, esperamos el segmento con message_length
        if self.bytes_pendientes == 0 and len(self.buffer_recibido) == 0:
            while True:
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                seg = SocketTCP.parse_segment(data)
                if not seg or seg["SYN"] or seg["ACK"]:
                    continue

                # La contraparte inició el cierre: lo guardamos para recv_close y no hay datos
                if seg["FIN"]:
                    self.fin_pendiente = seg["SEQ"]
                    return b""

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
            if not seg or seg["SYN"] or seg["ACK"]:
                continue

            # FIN en medio de la transferencia: lo guardamos y entregamos lo que haya
            if seg["FIN"]:
                self.fin_pendiente = seg["SEQ"]
                break

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


    # Funciones auxiliares 
    def _recibir_hasta(self, limite):
        """Espera un segmento valido hasta el instante `limite` (time.monotonic()).
        Devuelve el segmento parseado, o None si se cumple el timeout."""
        while True:
            restante = limite - time.monotonic()
            if restante <= 0:
                return None
            self.UDP.settimeout(restante)
            try:
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            except socket.timeout:
                return None
            seg = SocketTCP.parse_segment(data)
            if seg:
                return seg

    def _reack_dato_viejo(self, seg):
        """Si llega un segmento de datos ya recibido (su ACK se perdió), se le
        responde el ACK para que el emisor no quede retransmitiendo para siempre."""
        if seg["SYN"] or seg["ACK"] or seg["FIN"]:
            return
        if seg["SEQ"] <= self.numerosecuencia:
            ack = SocketTCP.create_segment({
                "SYN": False, "ACK": True, "FIN": False, "SEQ": seg["SEQ"]
            })
            self.UDP.sendto(ack, self.direcciondestino)

    def close(self):
        self.numerosecuencia += 1
        fin_seq = self.numerosecuencia

        fin_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": False, "FIN": True,
            "SEQ": fin_seq
        })

        # 1. Enviar FIN y esperar ACK
        ack_recibido = False
        fin_b_seq = None
        for intento in range(SocketTCP.INTENTOS_CIERRE):
            self.UDP.sendto(fin_pkt, self.direcciondestino)
            limite = time.monotonic() + SocketTCP.TIMEOUT
            while not ack_recibido:
                seg = self._recibir_hasta(limite)
                if seg is None:
                    break  # timeout: se reenvía el FIN
                if seg["ACK"] and not seg["FIN"] and seg["SEQ"] == fin_seq + 1:
                    ack_recibido = True
                elif seg["FIN"]:
                    # llegó el FIN de B antes que su ACK (el ACK se perdió):
                    # B ya recibió nuestro FIN, así que lo damos por confirmado
                    fin_b_seq = seg["SEQ"]
                    ack_recibido = True
                else:
                    self._reack_dato_viejo(seg)
            if ack_recibido:
                break

        if not ack_recibido:
            # tres timeouts sin respuesta: asumimos que cerró
            self.UDP.close()
            print("Conexión cerrada en Host A (close): la contraparte no respondió.")
            return

        # 2. Esperar el FIN de la contraparte (hasta 3 timeouts)
        if fin_b_seq is None:
            for intento in range(SocketTCP.INTENTOS_CIERRE):
                limite = time.monotonic() + SocketTCP.TIMEOUT
                while fin_b_seq is None:
                    seg = self._recibir_hasta(limite)
                    if seg is None:
                        break
                    if seg["FIN"]:
                        fin_b_seq = seg["SEQ"]
                    else:
                        self._reack_dato_viejo(seg)
                if fin_b_seq is not None:
                    break

        # 3. Enviar el último ACK 3 veces, esperando un timeout entre cada envío
        if fin_b_seq is not None:
            ack_pkt = SocketTCP.create_segment({
                "SYN": False, "ACK": True, "FIN": False,
                "SEQ": fin_b_seq + 1
            })
            for intento in range(3):
                self.UDP.sendto(ack_pkt, self.direcciondestino)
                if intento < 2:
                    limite = time.monotonic() + SocketTCP.TIMEOUT
                    while self._recibir_hasta(limite) is not None:
                        pass  # se descartan retransmisiones hasta cumplir el timeout

        self.UDP.close()
        print("Conexión cerrada exitosamente en Host A (close).")

    def recv_close(self):
        # 1. Esperar el FIN inicial de la contraparte (hasta 3 timeouts)
        fin_a_seq = self.fin_pendiente  # puede que recv() ya lo haya recibido
        if fin_a_seq is None:
            for intento in range(SocketTCP.INTENTOS_CIERRE):
                limite = time.monotonic() + SocketTCP.TIMEOUT
                while fin_a_seq is None:
                    seg = self._recibir_hasta(limite)
                    if seg is None:
                        break
                    if seg["FIN"]:
                        fin_a_seq = seg["SEQ"]
                    else:
                        # dato viejo: su ACK se perdió, hay que responderlo
                        self._reack_dato_viejo(seg)
                if fin_a_seq is not None:
                    break

        if fin_a_seq is None:
            # nunca llegó el FIN: asumimos que la contraparte ya cerró
            self.UDP.close()
            print("Conexión cerrada en Host B (recv_close): no llegó el FIN.")
            return

        # 2. Enviar ACK al FIN recibido
        ack_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False,
            "SEQ": fin_a_seq + 1
        })
        self.UDP.sendto(ack_pkt, self.direcciondestino)

        # 3. Enviar nuestro propio FIN y esperar su ACK (hasta 3 timeouts)
        self.numerosecuencia += 1
        mi_fin_seq = self.numerosecuencia
        fin_pkt = SocketTCP.create_segment({
            "SYN": False, "ACK": False, "FIN": True,
            "SEQ": mi_fin_seq
        })

        ack_final = False
        for intento in range(SocketTCP.INTENTOS_CIERRE):
            self.UDP.sendto(fin_pkt, self.direcciondestino)
            limite = time.monotonic() + SocketTCP.TIMEOUT
            while not ack_final:
                seg = self._recibir_hasta(limite)
                if seg is None:
                    break  # timeout: se reenvía el FIN
                if seg["ACK"] and not seg["FIN"] and seg["SEQ"] == mi_fin_seq + 1:
                    ack_final = True
                elif seg["FIN"] and seg["SEQ"] == fin_a_seq:
                    # A retransmitió su FIN: nuestro ACK se perdió, lo reenviamos
                    self.UDP.sendto(ack_pkt, self.direcciondestino)
                else:
                    self._reack_dato_viejo(seg)
            if ack_final:
                break

        self.UDP.close()
        print("Conexión cerrada exitosamente en Host B (recv_close).")