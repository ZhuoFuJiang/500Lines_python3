import os
from http import server
import subprocess
# python3的版本用server替代


class ServerException(Exception):
    '''For internal error reporting.'''
    pass


class case_no_file(object):
    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException("'{0}' not found".format(handler.path))


class case_existing_file(object):
    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        handler.handle_file(handler.full_path)


class case_always_fail(object):

    def test(self, handler):
        return True

    def act(self, handler):
        raise ServerException("Unknown object '{0}'".format(handler.path))


class case_directory_index_file(object):
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
               os.path.isfile(self.index_path(handler))

    def act(self, handler):
        handler.handle_file(self.index_path(handler))


class case_directory_no_index_file(object):
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
               not os.path.isfile(self.index_path(handler))

    def act(self, handler):
        handler.list_dir(handler.full_path)


class case_cgi_file(object):
    def test(self, handler):
        return os.path.isfile(handler.full_path) and \
               handler.full_path.endswith('.py')

    def act(self, handler):
        handler.run_cgi(handler.full_path)


class RequestHandler(server.BaseHTTPRequestHandler):
    '''Handle HTTP requests by returning a fixed 'page'.'''

    # Page to send back.
    Page = '''\
    <html>
    <body>
    <table>
    <tr>  <td>Header</td>         <td>Value</td>          </tr>
    <tr>  <td>Date and time</td>  <td>{date_time}</td>    </tr>
    <tr>  <td>Client host</td>    <td>{client_host}</td>  </tr>
    <tr>  <td>Client port</td>    <td>{client_port}s</td> </tr>
    <tr>  <td>Command</td>        <td>{command}</td>      </tr>
    <tr>  <td>Path</td>           <td>{path}</td>         </tr>
    </table>
    </body>
    </html>'''

    Error_Page = """\
        <html>
        <body>
        <h1>Error accessing {path}</h1>
        <p>{msg}</p>
        </body>
        </html>
        """

    Listing_Page = '''\
        <html>
        <body>
        <ul>
        {0}
        </ul>
        </body>
        </html>
        '''

    Cases = [case_no_file(), case_cgi_file(), case_existing_file(), case_directory_index_file(),
             case_directory_no_index_file(),
             case_always_fail()]

    # Handle a GET request.
    def do_GET(self):
        try:
            self.full_path = os.getcwd() + self.path

            for case in self.Cases:
                handler = case
                if handler.test(self):
                    handler.act(self)
                    break

        except Exception as msg:
            self.handle_error(msg)

    def run_cgi(self, full_path):
        cmd = "python " + full_path
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.send_content(result.stdout.read())

    def list_dir(self, full_path):
        try:
            entries = os.listdir(full_path)
            bullets = ['<li>{0}</li>'.format(e) for e in entries if not e.startswith('.')]
            page = str.encode(self.Listing_Page.format('\n'.join(bullets)))
            self.send_content(page)
        except OSError as msg:
            msg = "'{0}' cannot be listed: {1}".format(self.path, msg)
            self.handle_error(msg)

    def handle_file(self, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            print(content)
            self.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(self.path, msg)
            self.handle_error(msg)

    def handle_error(self, msg):
        content = str.encode(self.Error_Page.format(path=self.path, msg=msg))
        self.send_content(content, 404)

    def create_page(self):
        values = {
            'date_time': self.date_time_string(),
            'client_host': self.client_address[0],
            'client_port': self.client_address[1],
            'command': self.command,
            'path': self.path
        }
        page = self.Page.format(**values)
        return page

    def send_content(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        # write方法在python3的版本里只能写字节流
        self.wfile.write(content)


if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = server.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()
