response = "HTTP/1.1 200 OK\r\nServer:192.168.64.9:8800\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 237\r\nConnection: keep-alive\r\nAccess-Control-Allow-Origin: *\r\n\r\n<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>CC4303</title>\n</head>\n<body>\n    <h1>Bienvenide ... oh? no puedo ver tu nombre :c!</h1>\n    <h3><a href=\"replace\">¿Qué es un proxy?</a></h3>\n</body>\n</html>"

html = "<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>CC4303</title>\n</head>\n<body>\n    <h1>holi</h1>\n</body>\n</html>"


print(len(html.encode()))




