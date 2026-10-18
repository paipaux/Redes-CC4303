import socket
import random
from socketUDP import SocketUDP
from slidingWindowCC import SlidingWindowCC
from CongestionControl import CongestionControl

class SocketTCP:
    MSS = 8
    headersizee = 5  # 1 byte flags + 4 bytes número de secuencia
    buffsizeeee = 5 + 16  # tamaño fijo exacto: header + 16 bytes de payload
    ventanasizeee = 8
    TIMEOUT = 2.0  # tiempo límite suficiente para tolerar el delay de netem

    def __init__(self):
        self.UDP = SocketUDP()
        self.direccionorigen = None
        self.direcciondestino = None
        self.numerosecuencia = None
        
        # Variables de estado para recv
        self.bytes_pendientes = 0  # Bytes que faltan recibir del mensaje actual
        self.buffer_recibido = b""  # Datos ya recibidos pendientes de entregar a recv()

        # congestiooon
        self.congestion_controler = CongestionControl(SocketTCP.MSS)
        self.congestion_control_on = False
        self.debug = False
    
    def set_congestion_control(self, value: bool):
        self.congestion_control_on = value

    def set_debug(self, value: bool):
        self.debug = value
    
    def _debug(self, evento, ventana):
        if not self.debug:
            return
        cc = self.congestion_controler
        estado = "slow start" if cc.is_state_slow_start() else "congestion avoidance"
        print(f"[{evento}] cwnd={cc.get_cwnd()} ({cc.get_MSS_in_cwnd()} MSS) "
              f"ssthresh={cc.get_ssthresh()} estado={estado} "
              f"window_size={ventana.window_size}")
        print(ventana)
    
    def enviarnuevooos(self, ventana, proximo):
        enviados = 0
        for i in range(ventana.window_size):
            d = ventana.get_data(i)
            if d is None:
                break
            seq = ventana.get_sequence_number(i)
            if seq >= proximo:
                seg = SocketTCP.create_segment({
                    "SYN": False, "ACK": False, "FIN": False,
                    "SEQ": seq, "DATA": d
                })
                self.UDP.sendto(seg, self.direcciondestino)
                proximo = seq + len(d)
                enviados += 1
        return proximo, enviados
    
    def moverventanaaa(self, ventana, ack):
        while True:
            d0 = ventana.get_data(0)
            if d0 is None or ventana.get_sequence_number(0) + len(d0) > ack:
                return
            k = 0
            for i in range(ventana.window_size):
                d = ventana.get_data(i)
                if d is None or ventana.get_sequence_number(i) + len(d) > ack:
                    break
                k += 1
            ventana.move_window(k)
    
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
                    self.UDP.stop_timer(0)
                    self.direcciondestino = nuevadireccion
                    break
            except socket.timeout:
                self.UDP.stop_timer(0)
                continue

        # 2. Enviar ACK final
        seq = seq + 2
        ack = SocketTCP.create_segment({
            "SYN": False, "ACK": True, "FIN": False, "SEQ": seq
        })
        self.numerosecuencia = seq
        self.UDP.settimeout(-1)
        self.UDP.sendto(ack, self.direcciondestino)

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
        nuevo.direccionorigen = nuevo.UDP.socket_udp.getsockname()
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
                    nuevo.UDP.stop_timer(0)
                    nuevo.numerosecuencia = respuesta["SEQ"]
                    break

                # Caso borde: se perdió el ACK final, pero el cliente ya mandó el largo del mensaje
                if not respuesta["SYN"] and not respuesta["ACK"] and not respuesta["FIN"]:
                    nuevo.UDP.stop_timer(0)
                    nuevo.numerosecuencia = respuesta["SEQ"]
                    ack_primer_dato = SocketTCP.create_segment({
                        "SYN": False, "ACK": True, "FIN": False,
                        "SEQ": nuevo.numerosecuencia
                    })
                    nuevo.UDP.settimeout(-1)
                    nuevo.UDP.sendto(ack_primer_dato, nuevo.direcciondestino)
                    nuevo.bytes_pendientes = int(respuesta["DATA"].decode("utf-8"))
                    break

            except socket.timeout:
                nuevo.UDP.stop_timer(0)
                continue

        nuevo.UDP.settimeout(-1)
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
                    self.UDP.stop_timer(0)
                    break
            except socket.timeout:
                self.UDP.stop_timer(0)
                continue
        self.UDP.settimeout(-1)

    def send_using_stop_and_wait(self, message):
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
    
    def send_using_go_back_n(self, message):
        cc = self.congestion_controler
        mss = cc.MSS
        largo = str(len(message)).encode("utf-8")
        trozos = [message[i:i + mss] for i in range(0, len(message), mss)]
        initial_seq = self.numerosecuencia + 1

        if self.congestion_control_on:
            window_size = cc.get_MSS_in_cwnd()
        else:
            window_size = SocketTCP.ventanasizeee
        ventana = SlidingWindowCC(window_size, [largo] + trozos, initial_seq)
        self._debug("inicio", ventana)

        self.UDP.settimeout(SocketTCP.TIMEOUT)
        proximo, _ = self.enviarnuevooos(ventana, initial_seq)

        while ventana.get_data(0) is not None:
            try: 
                data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            except TimeoutError:
                self.UDP.stop_timer(0)
                if self.congestion_control_on:
                    cc.event_timeout()
                    ventana.update_window_size(cc.get_MSS_in_cwnd())
                # go back-n retransmite toda la ventanaa
                proximo, _ = self.enviarnuevooos(ventana, ventana.get_sequence_number(0))
                self._debug("timeout", ventana)
                continue

            seg = SocketTCP.parse_segment(data)
            if not seg or not seg["ACK"] or seg["SYN"]:
                continue
            ack = seg["SEQ"]

            d0 = ventana.get_data(0)
            if ack < ventana.get_sequence_number(0) + len(d0):
                continue

            self.UDP.stop_timer(0)
            self.moverventanaaa(ventana, ack)
            proximo = max(proximo, ack)

            if self.congestion_control_on:
                cc.event_ack_received()
                ventana.update_window_size(cc.get_MSS_in_cwnd())

            if ventana.get_data(0) is None:
                self._debug("ack (fin)", ventana)
                break

            proximo, enviados = self.enviarnuevooos(ventana, proximo)
            if enviados == 0:
                # quedan segmentos sin confirmar pero no entró nada neuvo :p
                proximo, _ = self.enviarnuevooos(ventana, ventana.get_sequence_number(0))
            self._debug("ack", ventana)

        self.UDP.settimeout(-1)

        self.numerosecuencia = initial_seq + len(largo) + len(message) - 1

    def send(self, message: bytes, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            return self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            return self.send_using_go_back_n(message)

    def recv_using_stop_and_wait(self, buff_size):
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

    def recv_using_go_back_n(self, buff_size):
        esperando_largo = (self.bytes_pendientes == 0 and len(self.buffer_recibido) == 0)

        while esperando_largo or (len(self.buffer_recibido) < buff_size and self.bytes_pendientes > 0):
            data, _ = self.UDP.recvfrom(SocketTCP.buffsizeeee)
            seg = SocketTCP.parse_segment(data)
            if not seg or seg["SYN"] or seg["ACK"] or seg["FIN"]:
                continue

            esperado = self.numerosecuencia + 1
            if seg["SEQ"] == esperado:
                self.numerosecuencia = esperado + len(seg["DATA"]) - 1
                if esperando_largo:
                    self.bytes_pendientes = int(seg["DATA"].decode("utf-8"))
                    esperando_largo = False
                else:
                    self.buffer_recibido += seg["DATA"]
                    self.bytes_pendientes -= len(seg["DATA"])

            ack = SocketTCP.create_segment({
                "SYN": False, "ACK": True, "FIN": False,
                "SEQ": self.numerosecuencia + 1
            })
            self.UDP.sendto(ack, self.direcciondestino)

        n = min(len(self.buffer_recibido), buff_size)
        datos = self.buffer_recibido[:n]
        self.buffer_recibido = self.buffer_recibido[n:]
        return datos
    
    def recv(self, buff_size: int, mode="stop_and_wait") -> bytes:
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)        
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)
        
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