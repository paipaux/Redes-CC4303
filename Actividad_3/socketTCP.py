import socket
import random
import time

class SocketTCP:
    headersizee = 5  # 1 byte flags + 4 bytes número de secuencia
    buffsizeeee = 5 + 16  # tamaño fijo exacto: header + 16 bytes de payload
    TIMEOUT = 2.0  # tiempo para el netem
    INTENTOS_CIERRE = 3  # cantidad de timeouts que se esperan al cerrar
    DEBUG = False

    def _log(self, mensaje):
        if SocketTCP.DEBUG:
            print(f"[DEBUG] {mensaje}")
    
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

        self._log(f"Iniciando Handshake -> Enviando SYN (SEQ={seq}) a {address}")
        self.UDP.settimeout(SocketTCP.TIMEOUT)
        while True:
            self.UDP.sendto(syn, address)
            try:
                data, nuevadireccion = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                respuesta = SocketTCP.parse_segment(data)
                if respuesta and respuesta["SYN"] and respuesta["ACK"] and respuesta["SEQ"] == (seq + 1):
                    self.direcciondestino = nuevadireccion
                    self._log(f"SYN+ACK recibido correctamente desde {nuevadireccion}")
                    break
            except socket.timeout:
                self._log(f"[PÉRDIDA DETECTADA] Timeout esperando SYN+ACK (SEQ={seq}). Retransmitiendo SYN...")
                continue

        # 2. Enviar ACK
        seq = seq + 2
        ack = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False, "SEQ": seq
        })
        self.numerosecuencia = seq
        self.UDP.sendto(ack, self.direcciondestino)
        self._log(f"Enviando ACK final de handshake (SEQ={seq}). Conexión establecida.")
        self.UDP.settimeout(None)

    def accept(self):
        # 1. Esperar SYN
        self._log("Esperando paquete SYN...")
        while True:
            data, direccion = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            segmento = SocketTCP.parse_segment(data)
            if segmento and segmento["SYN"] and not segmento["ACK"]:
                clave = (direccion, segmento["SEQ"])
                if clave in self.syn_atendidos:
                    self._log(f"SYN duplicado recibido de {direccion} (SEQ={segmento['SEQ']}). Ignorando...")
                    continue
                self.syn_atendidos.add(clave)
                self._log(f"SYN recibido de {direccion} (SEQ={segmento['SEQ']})")
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

        nuevo._log(f"Enviando SYN+ACK (SEQ={seq}) desde nuevo socket {nuevo.direccionorigen}")
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
                    nuevo._log(f"ACK final de handshake recibido (SEQ={respuesta['SEQ']}). Conexión lista.")
                    break

                # se pierde el ACK final
                if not respuesta["SYN"] and not respuesta["ACK"] and not respuesta["FIN"]:
                    nuevo.numerosecuencia = respuesta["SEQ"]
                    nuevo._log(f"Caso borde: Pérdida de ACK final, pero llegó primer dato (SEQ={respuesta['SEQ']}).")
                    ack_primer_dato = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": nuevo.numerosecuencia
                    })
                    nuevo.UDP.sendto(ack_primer_dato, nuevo.direcciondestino)
                    nuevo.bytes_pendientes = int(respuesta["DATA"].decode("utf-8"))
                    nuevo._log(f"Confirmado message_length={nuevo.bytes_pendientes} bytes desde caso borde.")
                    break

            except socket.timeout:
                nuevo._log(f"[PÉRDIDA DETECTADA] Timeout esperando ACK final del Handshake. Retransmitiendo SYN+ACK...")
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
            self._log(f"Enviando paquete SEQ={self.numerosecuencia} ({len(payload)} bytes)")
            self.UDP.sendto(segmento, self.direcciondestino)
            try:
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                ack_seg = SocketTCP.parse_segment(data)
                if ack_seg and ack_seg["ACK"] and ack_seg["SEQ"] == self.numerosecuencia:
                    self._log(f"ACK recibido para SEQ={self.numerosecuencia}")
                    break
            except socket.timeout:
                self._log(f"[PÉRDIDA DETECTADA] Timeout en SEQ={self.numerosecuencia}. Retransmitiendo paquete...")
                continue
        self.UDP.settimeout(None)

    def send(self, message: bytes):
        if isinstance(message, str):
            message = message.encode("utf-8")

        message_length = len(message)
        self._log(f"Iniciando envío de mensaje completo ({message_length} bytes)")

        # 1. Enviar tamaño del mensaje
        largo_bytes = str(message_length).encode("utf-8")
        self._send_trozo_stop_and_wait(largo_bytes)

        # 2. Enviar datos en trozos de máx 16 bytes
        offset = 0
        while offset < message_length:
            trozo = message[offset:offset + 16]
            self._send_trozo_stop_and_wait(trozo)
            offset += len(trozo)

        self._log("Envío de mensaje completado exitosamente.")

    def recv(self, buff_size: int) -> bytes:
        # 0. Si ya habíamos visto el FIN y no queda nada que entregar, no hay más datos
        if self.fin_pendiente is not None and self.bytes_pendientes == 0 and len(self.buffer_recibido) == 0:
            self._log("FIN previo detectado y buffer vacío. Retornando b''")
            return b""

        # 1. Si no hay transferencia previa activa, esperamos el segmento con message_length
        if self.bytes_pendientes == 0 and len(self.buffer_recibido) == 0:
            self._log("Sin transferencia activa. Esperando segmento message_length...")
            while True:
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
                seg = SocketTCP.parse_segment(data)
                if not seg or seg["SYN"] or seg["ACK"]:
                    continue

                # La contraparte inició el cierre: lo guardamos para recv_close y no hay datos
                if seg["FIN"]:
                    self._log(f"FIN recibido en recv() (SEQ={seg['SEQ']}). Guardando para recv_close.")
                    self.fin_pendiente = seg["SEQ"]
                    return b""

                # Si es un duplicado viejo atrasado en la red, respondemos ACK y lo ignoramos
                if seg["SEQ"] <= self.numerosecuencia:
                    self._log(f"[DUPLICADO/REDUPLICADO] Paquete rezagado detectado (SEQ={seg['SEQ']} <= {self.numerosecuencia}). Reenviando ACK...")
                    ack_duplicado = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": seg["SEQ"]
                    })
                    self.UDP.sendto(ack_duplicado, self.direcciondestino)
                    continue

                # Si es el segmento nuevo esperado, contiene el message_length
                if seg["SEQ"] == self.numerosecuencia + 1:
                    self.numerosecuencia = seg["SEQ"]
                    self.bytes_pendientes = int(seg["DATA"].decode("utf-8"))
                    self._log(f"message_length recibido: {self.bytes_pendientes} bytes (SEQ={self.numerosecuencia})")
                    
                    ack_seg = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": self.numerosecuencia
                    })
                    self.UDP.sendto(ack_seg, self.direcciondestino)
                    break

        # 2. Recibir trozos de datos
        while len(self.buffer_recibido) < buff_size and self.bytes_pendientes > 0:
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if not seg or seg["SYN"] or seg["ACK"]:
                continue

            # FIN en medio de la transferencia: lo guardamos y entregamos lo que haya
            if seg["FIN"]:
                self._log(f"FIN recibido durante transferencia de datos (SEQ={seg['SEQ']})")
                self.fin_pendiente = seg["SEQ"]
                break

            # Segmento nuevo en secuencia
            if seg["SEQ"] == self.numerosecuencia + 1:
                self.numerosecuencia = seg["SEQ"]
                chunk = seg["DATA"]
                self.buffer_recibido += chunk
                self.bytes_pendientes -= len(chunk)
                self._log(f"Segmento en orden recibido (SEQ={self.numerosecuencia}, {len(chunk)} bytes). Pendientes: {self.bytes_pendientes} bytes")

                ack_seg = SocketTCP.create_segment({
                    "SYN": False, "ACK": True, "FIN": False,
                    "SEQ": self.numerosecuencia
                })
                self.UDP.sendto(ack_seg, self.direcciondestino)

            # Segmento duplicado (retransmisión vieja por pérdida de ACK anterior)
            elif seg["SEQ"] <= self.numerosecuencia:
                self._log(f"[PÉRDIDA/DUPLICADO] Paquete duplicado recibido (SEQ={seg['SEQ']} <= {self.numerosecuencia}). Reenviando ACK y descartando payload.")
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
            self._log(f"[CIERRE] Re-confirmando ACK de paquete de datos viejo recibido durante cierre (SEQ={seg['SEQ']})")
            ack = SocketTCP.create_segment({
                "SYN": False, "ACK": True, "FIN": False, "SEQ": seg["SEQ"]
            })
            self.UDP.sendto(ack, self.direcciondestino)

    def close(self):
        self._log("Iniciando secuencia de cierre activa (close)...")
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
            self._log(f"Enviando FIN (SEQ={fin_seq}) - Intento {intento + 1}/{SocketTCP.INTENTOS_CIERRE}")
            self.UDP.sendto(fin_pkt, self.direcciondestino)
            limite = time.monotonic() + SocketTCP.TIMEOUT
            while not ack_recibido:
                seg = self._recibir_hasta(limite)
                if seg is None:
                    self._log(f"[PÉRDIDA EN CIERRE] Timeout esperando ACK al FIN (Intento {intento + 1})")
                    break  # timeout: se reenvía el FIN
                if seg["ACK"] and not seg["FIN"] and seg["SEQ"] == fin_seq + 1:
                    self._log("ACK a nuestro FIN recibido.")
                    ack_recibido = True
                elif seg["FIN"]:
                    # llegó el FIN de B antes que su ACK (el ACK se perdió):
                    # B ya recibió nuestro FIN, así que lo damos por confirmado
                    fin_b_seq = seg["SEQ"]
                    self._log(f"FIN recibido directamente desde B (SEQ={fin_b_seq}). ACK asimilado.")
                    ack_recibido = True
                else:
                    self._reack_dato_viejo(seg)
            if ack_recibido:
                break

        if not ack_recibido:
            # tres timeouts sin respuesta: asumimos que cerró
            self._log("Tres timeouts transcurridos sin respuesta. Cerrando socket unilateralmente.")
            self.UDP.close()
            print("Conexión cerrada en Host A (close): la contraparte no respondió.")
            return

        # 2. Esperar el FIN de la contraparte (hasta 3 timeouts)
        if fin_b_seq is None:
            self._log("Esperando FIN de la contraparte...")
            for intento in range(SocketTCP.INTENTOS_CIERRE):
                limite = time.monotonic() + SocketTCP.TIMEOUT
                while fin_b_seq is None:
                    seg = self._recibir_hasta(limite)
                    if seg is None:
                        self._log(f"[PÉRDIDA EN CIERRE] Timeout esperando FIN de contraparte (Intento {intento + 1})")
                        break
                    if seg["FIN"]:
                        fin_b_seq = seg["SEQ"]
                        self._log(f"FIN de contraparte recibido (SEQ={fin_b_seq})")
                    else:
                        self._reack_dato_viejo(seg)
                if fin_b_seq is not None:
                    break

        # 3. Enviar el último ACK 3 veces, esperando un timeout entre cada envío
        if fin_b_seq is not None:
            self._log("Enviando el último ACK 3 veces para asegurar el cierre...")
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
        self._log("Iniciando secuencia de cierre pasiva (recv_close)...")
        # 1. Esperar el FIN inicial de la contraparte (hasta 3 timeouts)
        fin_a_seq = self.fin_pendiente  # puede que recv() ya lo haya recibido
        if fin_a_seq is None:
            self._log("Esperando FIN inicial de la contraparte...")
            for intento in range(SocketTCP.INTENTOS_CIERRE):
                limite = time.monotonic() + SocketTCP.TIMEOUT
                while fin_a_seq is None:
                    seg = self._recibir_hasta(limite)
                    if seg is None:
                        self._log(f"[PÉRDIDA EN CIERRE] Timeout esperando FIN inicial (Intento {intento + 1})")
                        break
                    if seg["FIN"]:
                        fin_a_seq = seg["SEQ"]
                        self._log(f"FIN inicial recibido (SEQ={fin_a_seq})")
                    else:
                        # dato viejo: su ACK se perdió, hay que responderlo
                        self._reack_dato_viejo(seg)
                if fin_a_seq is not None:
                    break

        if fin_a_seq is None:
            # nunca llegó el FIN: asumimos que la contraparte ya cerró
            self._log("No se recibió FIN tras 3 timeouts. Cerrando socket unilateralmente.")
            self.UDP.close()
            print("Conexión cerrada en Host B (recv_close): no llegó el FIN.")
            return

        # 2. Enviar ACK al FIN recibido
        self._log(f"Enviando ACK al FIN recibido (SEQ={fin_a_seq + 1})")
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
            self._log(f"Enviando nuestro FIN (SEQ={mi_fin_seq}) - Intento {intento + 1}/{SocketTCP.INTENTOS_CIERRE}")
            self.UDP.sendto(fin_pkt, self.direcciondestino)
            limite = time.monotonic() + SocketTCP.TIMEOUT
            while not ack_final:
                seg = self._recibir_hasta(limite)
                if seg is None:
                    self._log(f"[PÉRDIDA EN CIERRE] Timeout esperando ACK a nuestro FIN (Intento {intento + 1})")
                    break  # timeout: se reenvía el FIN
                if seg["ACK"] and not seg["FIN"] and seg["SEQ"] == mi_fin_seq + 1:
                    self._log("ACK a nuestro FIN recibido.")
                    ack_final = True
                elif seg["FIN"] and seg["SEQ"] == fin_a_seq:
                    # A retransmitió su FIN: nuestro ACK se perdió, lo reenviamos
                    self._log("FIN de contraparte retransmitido por pérdida de nuestro ACK. Reenviando ACK...")
                    self.UDP.sendto(ack_pkt, self.direcciondestino)
                else:
                    self._reack_dato_viejo(seg)
            if ack_final:
                break

        self.UDP.close()
        print("Conexión cerrada exitosamente en Host B (recv_close).")