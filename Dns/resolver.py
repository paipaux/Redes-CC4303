import socket
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE
from collections import Counter
import dnslib
import dnslibEJEMPLO




cache = []
top_3 = []
def checkcache(address, ip):
    if len(cache) >= 20:
        cache.pop()
    dnspair = (address,ip)
    cache.insert(0,dnspair)
    contador = Counter(cache)
    top_3.clear()
    for i in contador.most_common(3):
        top_3.append(i)





def parsedns(dnsmsg):
    dnsparsed = DNSRecord.parse(dnsmsg)
    Qname = str(dnsparsed.get_q().get_qname())
    ancount = dnsparsed.header.a
    nscount = dnsparsed.header.auth
    arcount = dnsparsed.header.ar
    seccion_answer = dnsparsed.rr
    seccion_authority = dnsparsed.auth
    seccion_additional = dnsparsed.ar

    parse = {
        "qname": Qname,
        "ancount": ancount,
        "nscount": nscount,
        "arcount": arcount,
        "answer_section": seccion_answer,
        "authority_section": seccion_authority,
        "additional_section": seccion_additional,
    }

    return parse


ip_original = '198.41.0.4'

def resolver(mensaje_consulta, ip_addr):
    Answer = False
    ip_a_revisar = ip_addr
    ns_name = "."
    msjparsed = parsedns(mensaje_consulta)
    while not Answer:
        server_address = (ip_a_revisar, 53)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            print("(debug) Consultando: ", msjparsed["qname"], " a ", ns_name, "con direccion IP: ", ip_a_revisar)
            sock.sendto(mensaje_consulta, server_address)
            data, _ = sock.recvfrom(4096)
            datadicc = parsedns(data)
            if datadicc["ancount"] != 0:
                Answer = True
                return data

            else:
                found_a = False
                for i in datadicc["additional_section"]:
                    ar_type = QTYPE.get(i.rtype)
                    if ar_type == 'A':
                        ip_a_revisar = str(i.rdata)
                        ns_name = str(i.rname)
                        found_a = True
                        break

                if not found_a:
                    for i in datadicc["authority_section"]:
                        auth_type = QTYPE.get(i.rtype)
                        typeA = False
                        if auth_type == 'NS':
                            auth_domain = str(i.rdata)
                            q = DNSRecord.question(auth_domain)
                            bytesq = bytes(q.pack())
                            bytesqparsed = parsedns(resolver(bytesq, ip_original))

                            lista_ips = bytesqparsed["answer_section"]
                            for j in lista_ips:
                                ip_type = QTYPE.get(j.rtype)
                                if ip_type == 'A':
                                    ip_a_revisar = str(j.rdata)
                                    ns_name = str(j.rname)
                                    typeA = True
                                    break
                        if typeA:
                            break

        finally:
            sock.close()

    return data


server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('192.168.64.9', 8800))

while True:

    message, address = server_socket.recvfrom(4096)
    cache_address = str(parsedns(message)["qname"])
    print(cache_address)
    in_cache = False
    for pair in top_3:
        print(pair)
        if len(top_3) > 0:
            print((top_3[0])[0][0])
    for par in top_3:
        if par[0][0] == cache_address:
            in_cache = True
            print("CACHE USADO")
            answer = par[0][1]
            id_original = DNSRecord.parse(message).header.id
            answer_modificada = DNSRecord.parse(answer)
            answer_modificada.header.id = id_original
            answer = bytes(answer_modificada.pack())

    if in_cache == False:
        answer = resolver(message, '198.41.0.4')
        cache_data_address = answer
        checkcache(cache_address,cache_data_address)   

    for pair in top_3:
            print(pair)
    server_socket.sendto(answer, address)