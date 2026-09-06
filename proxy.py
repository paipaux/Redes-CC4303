import socket

cosas_prohibidas = 'prohibido.jsn'
imagen_bloqueo = 'gato-truco.jpg'


def receive_full_message(connection_socket, buff_size):

    end_sequence = b'\r\n\r\n'
    full_message = b''

    while end_sequence not in full_message:
        recv_message = connection_socket.recv(buff_size)
        if not recv_message:
            return full_message
        full_message += recv_message
        
    head, _, resto = full_message.partition(end_sequence)
    
    # vemps cuanto body falta
    largo = 0
    for linea in head.decode().split('\r\n'):
        if ':' in linea:
            llave, valor = linea.split(':', 1)
            if llave.strip().lower() == 'content-length':
                largo = int(valor.strip())

    body = resto

    while len(body) < largo:
        recv_message = connection_socket.recv(buff_size)
        if not recv_message:
            break
        body += recv_message
    
    return head + end_sequence + body


def parse_HTTP_message(http_message: bytes):
    head, _, body = http_message.partition(b'\r\n\r\n')
    lineaas = head.decode().split('\r\n')
    
    tipo = lineaas[0] 

    headeers = {}
    for linea in lineaas[1:]:
        if linea == '':
            continue
        llave, valor = linea.split(':', 1)
        headeers[llave.strip()] = valor.strip()
    
    return {
        "tipo de solicitud": tipo,
        "headers": headeers,
        "body": body
    }


def create_HTTP_message(http):
    tipo = http["tipo de solicitud"]
    headers = http["headers"]
    body = http["body"]

    
    if isinstance(body, str):
        body = body.encode()

    headeeer = ''
    for llave, valor in headers.items():
        headeeer += f'{llave}: {valor}\r\n'

    head_final = f'{tipo}\r\n{headeeer}\r\n'

    return head_final.encode() + body

def get_server_address_from_request(parsed_request):
    hosst = parsed_request["headers"]["Host"]

    if ":" in hosst:
        host, puerto = hosst.split(":")
        puerto = int(puerto)
    else:
        host = hosst
        puerto = 80

    return host, puerto

def extraer2(requeeest):
    metodo, target, version = requeeest.split(' ')

    if target.startswith('http://') or target.startswith('https://'):
        despues_esquema = target.split('://', 1)[1]
        if '/' in despues_esquema:
            path = '/' + despues_esquema.split('/', 1)[1]
        else:
            path = '/'
    else:
        path = target
    
    return path

def extraer(contenido, llave):
    marcador = f'"{llave}"'
    aa = contenido.find(marcador)
    if aa == -1:
        return ''
    
    inicio = contenido.find('[', aa)

    oo = 0
    estaono = False
    fin = inicio

    i = inicio
    while i < len(contenido):
        c = contenido[i]
        if c == '"' and contenido[i-1] != '\\':
            estaono = not estaono
        elif not estaono:
            if c == '[':
                oo += 1
            elif c == ']':
                oo -= 1
                if oo == 0:
                    fin = i
                    break
        i += 1
    
    return contenido[inicio+1:fin]

def load_blocked(filee):
    with open(filee, 'r') as f:
        contenido = f.read()

    seccon = extraer(contenido, 'blocked')
    partes = seccon.split('"')
    entradas = [partes[i].strip() for i in range(1, len(partes),2)]

    return entradas

def load_forbiddeen(filee):
    with open(filee, 'r') as f:
        contenido = f.read()
    
    seccion = extraer(contenido, 'forbidden_words')
    obejtos = seccion.split('{')[1:]

    palabras = {}
    for obj in obejtos:
        obj = obj.split('}')[0]
        partes = obj.split('"')
        valores = [partes[i] for i in range (1, len(partes), 2)]
        if len(valores) >= 2:
            clave, valor = valores[0], valores[1]
            palabras[clave] = valor

    return palabras

def is_blocked(host, path, blocked):
    host = host.lower().strip()

    for entrada in blocked:
        if '/' in entrada:
            dominio, ruta = entrada.split('/', 1)
            ruta = '/' + ruta
            if host == dominio.lower().strip() and path.startswith(ruta):
                return True
        else:
            if host == entrada.lower().strip():
                return True
    
    return False

def build_blocked_response():
    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"es\">\n"
        "<head><meta charset=\"UTF-8\"><title>Página prohibida</title></head>\n"
        "<body>\n"
        "<img src=\"/blocked_image\" alt=\"gato-bloq\">\n"
        "</body>\n"
        "</html>"
    )
    html_bytes = html.encode('utf-8')

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": str(len(html_bytes)),
        "Connection": "keep-alive"
    }

    response_dict = {
        "tipo de solicitud": "HTTP/1.1 403 Forbidden",
        "headers": headers,
        "body": html_bytes
    }

    return create_HTTP_message(response_dict)

def build_image_response(filee):
    with open(filee, 'rb') as f:
        image_bytes = f.read()

    headers = {
        "Content-Type": "image/jpeg",
        "Content-Length": str(len(image_bytes)),
        "Connection": "keep-alive"
    }

    response_dict = {
        "tipo de solicitud": "HTTP/1.1 200 OK",
        "headers": headers,
        "body": image_bytes
    }

    return create_HTTP_message(response_dict)

if __name__ == "__main__":
    # definimos el tamaño del buffer de recepción y la secuencia de fin de mensaje
    buff_size = 8
    
    # hay que ir cambiandoloo, tuve que cambiarlo al mio para que corriera :p
    new_socket_address = ('192.168.56.1', 8800)

    lista_bloqueados = load_blocked(cosas_prohibidas)
    lista_prohibidos = load_forbiddeen(cosas_prohibidas)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.bind(new_socket_address)

    server_socket.listen(3)

    while True:
        try: 
            new_socket, new_socket_address = server_socket.accept()
            recv_message = receive_full_message(new_socket, buff_size)
            print(recv_message)

            responseparsed = parse_HTTP_message(recv_message)
            target_host, target_puertoo = get_server_address_from_request(responseparsed)
            path_solicitadoo = extraer2(responseparsed["tipo de solicitud"])
            print(f"reenviandooo: {target_host}:{target_puertoo}")
        


            if path_solicitadoo == "/blocked_image":
                response_bytes = build_image_response(imagen_bloqueo)
                new_socket.send(response_bytes)
                new_socket.close()
                continue

            if is_blocked(target_host, path_solicitadoo, lista_bloqueados):
                response_bytes = build_blocked_response()
                new_socket.send(response_bytes)
                new_socket.close()
                continue

            responseparsed["headers"]["X-ElQuePregunta"] = "BonziBuddies (Felipe y Cali)"
            # para que pueda ver la palabraa
            responseparsed["headers"]["Accept-Encoding"] = "identity"
            mensaje_a_enviar = create_HTTP_message(responseparsed)

            server_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket2.connect((target_host, target_puertoo))
            server_socket2.send(mensaje_a_enviar)

            respooonse = receive_full_message(server_socket2, buff_size)
            print(respooonse)

            # reemplazo de palabras prohibidas
            respuesta_parsed = parse_HTTP_message(respooonse)
            body_texto = respuesta_parsed["body"].decode()

            for palabra, reemplazo in lista_prohibidos.items():
                body_texto = body_texto.replace(palabra, reemplazo)

            nuevo_body = body_texto.encode()
            respuesta_parsed["body"] = nuevo_body
            respuesta_parsed["headers"]["Content-Length"] = str(len(nuevo_body))

            respuesta_final = create_HTTP_message(respuesta_parsed)
            new_socket.send(respuesta_final)

            server_socket2.close()
            new_socket.close()
            print(f"conexión con {new_socket_address} ha sido cerrada")

        # para que no se caiga por https :c
        except Exception as e:
            print(f"error procesando {new_socket_address}: {e}")
            new_socket.close()

    

