import os
from http import server
import subprocess
# python3的版本用server替代


class ServerException(Exception):
    '''For internal error reporting.'''
    pass


class base_case(object):
    '''Parent for case handlers.'''

    def handle_file(self, handler, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            handler.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(full_path, msg)
            handler.handle_error(msg)

    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        assert False, 'Not implemented.'

    def act(self, handler):
        assert False, 'Not implemented.'


class case_no_file(base_case):
    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException("'{0}' not found".format(handler.path))


class case_existing_file(base_case):
    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        self.handle_file(handler, handler.full_path)


class case_always_fail(base_case):

    def test(self, handler):
        return True

    def act(self, handler):
        raise ServerException("Unknown object '{0}'".format(handler.path))


class case_directory_index_file(base_case):
    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
               os.path.isfile(self.index_path(handler))

    def act(self, handler):
        self.handle_file(handler, self.index_path(handler))


class case_directory_no_index_file(base_case):
    Listing_Page = '''\
            <html>
            <body>
            <ul>
            {0}
            </ul>
            </body>
            </html>
            '''

    def list_dir(self, handler, full_path):
        try:
            entries = os.listdir(full_path)
            bullets = ['<li>{0}</li>'.format(e) for e in entries if not e.startswith('.')]
            page = str.encode(self.Listing_Page.format('\n'.join(bullets)))
            handler.send_content(page)
        except OSError as msg:
            msg = "'{0}' cannot be listed: {1}".format(handler.path, msg)
            handler.handle_error(msg)

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
               not os.path.isfile(self.index_path(handler))

    def act(self, handler):
        self.list_dir(handler, handler.full_path)


class case_cgi_file(base_case):
    def run_cgi(self, handler):
        cmd = "python " + handler.full_path
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        handler.send_content(result.stdout.read())

    def test(self, handler):
        return os.path.isfile(handler.full_path) and \
               handler.full_path.endswith('.py')

    def act(self, handler):
        self.run_cgi(handler)


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

    # def handle_file(self, full_path):
    #     try:
    #         with open(full_path, 'rb') as reader:
    #             content = reader.read()
    #         print(content)
    #         self.send_content(content)
    #     except IOError as msg:
    #         msg = "'{0}' cannot be read: {1}".format(self.path, msg)
    #         self.handle_error(msg)

    def handle_error(self, msg):
        content = str.encode(self.Error_Page.format(path=self.path, msg=msg))
        self.send_content(content, 404)

    # def create_page(self):
    #     values = {
    #         'date_time': self.date_time_string(),
    #         'client_host': self.client_address[0],
    #         'client_port': self.client_address[1],
    #         'command': self.command,
    #         'path': self.path
    #     }
    #     page = self.Page.format(**values)
    #     return page

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
