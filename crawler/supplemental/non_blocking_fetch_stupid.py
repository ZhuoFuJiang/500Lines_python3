import socket


sock = socket.socket()
sock.setblocking(False)

try:
    sock.connect(('xkcd.com', 80))
except BlockingIOError:
    pass


request = 'GET /353/ HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'
encoded = request.encode('ascii')

# 由于不知道什么时候连接上了，因此需要无限循环判断
i = 0
while True:
    i += 1
    try:
        print("发送第%d次数: " % i)
        sock.send(encoded)
        print("成功\n")
        break
    except OSError as e:
        print("失败\n")
        pass

print('sent')
