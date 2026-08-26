import socket

response = "HTTP/1.1 200 OK\r\nServer:192.168.64.9:8800\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 141\r\nConnection: keep-alive\r\nAccess-Control-Allow-Origin: *\r\n\r\n<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>CC4303</title>\n</head>\n<body>\n    <h1>holi</h1>\n</body>\n</html>"

html = "<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>CC4303</title>\n</head>\n<body>\n    <h1>holi</h1>\n</body>\n</html>"




def receive_full_message(connection_socket, buff_size, end_sequence):

    recv_message = connection_socket.recv(buff_size)
    full_message = recv_message

    is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    while not is_end_of_message:

        recv_message = connection_socket.recv(buff_size)
        full_message += recv_message
        is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    return full_message

def contains_end_of_message(message, end_sequence):
    return message.endswith(end_sequence)




def parse_HTTP_message(http_message: bytes):
    message = http_message.decode()
    headers = message.split('\r\n')
    Headers_list = []
    for i in headers:
        if i != '':
            Headers_list.append(str(i))
    
    return Headers_list


def create_HTTP_message(http):
    Headers_list = http
    Http_created = ''
    for i in Headers_list:
        Http_created = Http_created + i
        Http_created = Http_created + '\r\n'

    Http_created = Http_created + '\r\n'
    Http_created_coded = Http_created.encode()
    return Http_created_coded


if __name__ == "__main__":
    # definimos el tamaño del buffer de recepción y la secuencia de fin de mensaje
    buff_size = 4
    end_of_message = "\r\n\r\n"
    new_socket_address = ('192.168.64.9', 8800)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.bind(new_socket_address)

    server_socket.listen(3)

    while True:

        new_socket, new_socket_address = server_socket.accept()
        recv_message = receive_full_message(new_socket, buff_size, end_of_message)
        responseparsed = parse_HTTP_message(response.encode())
        
        headerToAdd = 'X-ElQuePregunta: TEST'

        responseparsed.insert(len(responseparsed) - 1, headerToAdd + "\r\n")

        msgtosend =create_HTTP_message(responseparsed)

        print(response.encode())
        print(msgtosend)
        new_socket.send(msgtosend)

        # cerramos la conexión
        # notar que la dirección que se imprime indica un número de puerto distinto al 5000
        new_socket.close()
        print(f"conexión con {new_socket_address} ha sido cerrada")

    

