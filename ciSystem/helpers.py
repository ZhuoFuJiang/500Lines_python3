import socket


def communicate(host, port, request):
    # socket.AF_INET 基于网络的套接字
    # socket.SOCK_STREAM 有连接的TCP协议
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.send(bytes(request, 'utf-8'))
    response = s.recv(1024)
    s.close()
    return response.decode("utf-8")
