from selectors import DefaultSelector, EVENT_WRITE, EVENT_READ
import socket
import re
import urllib.parse
import time


class Future:
    def __init__(self):
        self.result = None
        self._callbacks = []

    def result(self):
        return self.result

    def add_done_callback(self, fn):
        # 只有新建Task的时候，才会调用此方法
        self._callbacks.append(fn)

    def set_result(self, result):
        self.result = result
        for fn in self._callbacks:
            fn(self)

    def __iter__(self):
        # 等待接收信号
        yield self
        return self.result


class Task:
    def __init__(self, coro):
        # coro也是个生成器
        self.coro = coro
        f = Future()
        f.set_result(None)
        self.step(f)

    def step(self, future):
        try:
            next_future = self.coro.send(future.result)
        except StopIteration:
            return

        next_future.add_done_callback(self.step)


urls_seen = set(['/'])
urls_todo = set(['/'])
concurrency_achieved = 0
selector = DefaultSelector()
stopped = False


def connect(sock, address):
    f = Future()
    sock.setblocking(False)
    try:
        sock.connect(address)
    except BlockingIOError:
        pass

    def on_connected():
        f.set_result(None)

    # 如果该套接字可写了，便触发事件，并回调on_connected方法
    selector.register(sock.fileno(), EVENT_WRITE, on_connected)
    # 等待连接完成
    yield from f
    selector.unregister(sock.fileno())


def read(sock):
    f = Future()

    def on_readable():
        f.set_result(sock.recv(4096))  # Read 4k at a time.

    # 如果该套接字可读了，便触发事件，并调用on_readable方法
    selector.register(sock.fileno(), EVENT_READ, on_readable)
    chunk = yield from f
    selector.unregister(sock.fileno())
    return chunk


def read_all(sock):
    response = []
    chunk = yield from read(sock)
    while chunk:
        response.append(chunk)
        chunk = yield from read(sock)

    return b''.join(response)


class Fetcher:
    def __init__(self, url):
        self.response = b''
        self.url = url

    def fetch(self):
        global concurrency_achieved, stopped
        concurrency_achieved = max(concurrency_achieved, len(urls_todo))

        sock = socket.socket()
        # yield from 生成器 等待生成器完成返回
        yield from connect(sock, ('xkcd.com', 80))
        get = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(self.url)
        sock.send(get.encode('ascii'))
        # 等待读取完毕所有信息
        self.response = yield from read_all(sock)

        # 解析页面内容，给新的url建立爬取的task
        self._process_response()
        # 此url的页面爬取任务完成了，去除
        urls_todo.remove(self.url)
        # 如果所有都完成了，则程序停止
        if not urls_todo:
            stopped = True
        print(self.url)

    def body(self):
        # 解码读取的内容
        body = self.response.split(b'\r\n\r\n', 1)[1]
        return body.decode('utf-8')

    def _process_response(self):
        if not self.response:
            print('error: {}'.format(self.url))
            return
        if not self._is_html():
            return
        urls = set(re.findall(r'''(?i)href=["']?([^\s"'<>]+)''',
                              self.body()))

        for url in urls:
            normalized = urllib.parse.urljoin(self.url, url)
            parts = urllib.parse.urlparse(normalized)
            if parts.scheme not in ('', 'http', 'https'):
                continue
            host, port = urllib.parse.splitport(parts.netloc)
            if host and host.lower() not in ('xkcd.com', 'www.xkcd.com'):
                continue
            defragmented, frag = urllib.parse.urldefrag(parts.path)
            if defragmented not in urls_seen:
                urls_todo.add(defragmented)
                urls_seen.add(defragmented)
                # 生成新任务
                Task(Fetcher(defragmented).fetch())

    def _is_html(self):
        # 判断是否是html格式的内容
        head, body = self.response.split(b'\r\n\r\n', 1)
        headers = dict(h.split(': ') for h in head.decode().split('\r\n')[1:])
        return headers.get('Content-Type', '').startswith('text/html')


start = time.time()
fetcher = Fetcher('/')
Task(fetcher.fetch())

while not stopped:
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback()

print('{} URLs fetched in {:.1f} seconds, achieved concurrency = {}'.format(
    len(urls_seen), time.time() - start, concurrency_achieved))
