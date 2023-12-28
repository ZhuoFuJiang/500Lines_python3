import argparse
import os
import re
import socket
import socketserver
import time
import threading
import helpers


def dispatch_tests(server, commit_id):
    while True:
        print("trying to dispatch to runners")
        # 轮询问每个runner是否有空闲资源
        # 后续可以让每个服务器自行报告状态
        for runner in server.runners:
            response = helpers.communicate(runner['host'],
                                           int(runner['port']),
                                           "runtest:%s" % commit_id)
            if response == "OK":
                print("adding id %s" % commit_id)
                server.dispatched_commits[commit_id] = runner
                if commit_id in server.pending_commits:
                    server.pending_commits.remove(commit_id)
                return
        time.sleep(2)


class ThreadingTCServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # 注册的所有服务器
    runners = []
    # 当前服务器的状态
    dead = False
    # 已经分配的任务记录
    dispatched_commits = {}
    # 待分配的任务
    pending_commits = []


class DispatcherHandler(socketserver.BaseRequestHandler):
    command_re = re.compile(r"(\w+)(:.+)*")
    BUF_SIZE = 1024

    def handle(self):
        self.data = self.request.recv(self.BUF_SIZE).decode("utf-8").strip()
        command_groups = self.command_re.match(self.data)
        if not command_groups:
            self.request.sendall(bytes("Invalid command", 'utf-8'))
            return
        command = command_groups.group(1)
        if command == "status":
            print("in status")
            self.request.sendall(bytes("OK", 'utf-8'))
        elif command == "register":
            print("register")
            address = command_groups.group(2)
            host, port = re.findall(r":(\w*)", address)
            runner = {"host": host, "port": port}
            self.server.runners.append(runner)
            self.request.sendall(bytes("OK", 'utf-8'))
        elif command == "dispatch":
            print("going to dispatch")
            commit_id = command_groups.group(2)[1:]
            if not self.server.runners:
                self.request.sendall(bytes("No runners are registered", 'utf-8'))
            else:
                self.request.sendall(bytes("OK", 'utf-8'))
                dispatch_tests(self.server, commit_id)
        elif command == "results":
            print("go test results")
            results = command_groups.group(2)[1:]
            results = results.split(":")
            commit_id = results[0]
            length_msg = int(results[1])
            remaining_buffer = self.BUF_SIZE - (len(command) + len(commit_id) + len(results[1]) + 3)
            if length_msg > remaining_buffer:
                # 此处有个问题是万一还是不够呢
                self.data += self.request.recv(length_msg - remaining_buffer).decode("utf-8").strip()
            del self.server.dispatched_commits[commit_id]
            if not os.path.exists("test_results"):
                os.makedirs("test_results")
            with open("test_results/%s" % commit_id, "w") as f:
                data = self.data.split(":")[3:]
                data = "\n".join(data)
                f.write(data)
            self.request.sendall(bytes("OK", 'utf-8'))
        else:
            self.request.sendall(bytes("Invalid command", 'utf-8'))


def serve():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host",
                        help="dispatcher's host, by default it uses localhost",
                        default="localhost",
                        action="store")
    parser.add_argument("--port",
                        help="dispatcher's port, by default it uses 8888",
                        default=8888,
                        action="store")
    args = parser.parse_args()
    # 创建服务器
    server = ThreadingTCServer((args.host, int(args.port)), DispatcherHandler)
    print("serving on %s: %s" % (args.host, int(args.port)))

    # 创建一个线程检查服务器池
    def runner_checker(server):
        def manage_commit_lists(runner):
            for commit, assigned_runner in server.dispatched_commits.items():
                if assigned_runner == runner:
                    del server.dispatched_commits[commit]
                    server.pending_commits.append(commit)
                    break
            server.runners.remove(runner)

        while not server.dead:
            time.sleep(1)
            for runner in server.runners:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    response = helpers.communicate(runner['host'],
                                                   int(runner['port']),
                                                   'ping')
                    if response != "pong":
                        print("removing runner %s" % runner)
                        manage_commit_lists(runner)
                except socket.error as e:
                    manage_commit_lists(runner)

    # 重新分配失败的测试任务
    def redistribute(server):
        while not server.dead:
            for commit in server.pending_commits:
                print("所有待运行的任务列表", server.pending_commits)
                print("running redistribute: %s" % commit)
                dispatch_tests(server, commit)
                time.sleep(5)

    runner_heartbeat = threading.Thread(target=runner_checker, args=(server, ))
    redistributor = threading.Thread(target=redistribute, args=(server, ))
    try:
        runner_heartbeat.start()
        redistributor.start()
        server.serve_forever()
    except (KeyboardInterrupt, Exception):
        server.dead = True
        # 阻塞主线程，等到runner_heartbeat结束
        runner_heartbeat.join()
        # 阻塞主线程，等到redistributor结束
        redistributor.join()


if __name__ == "__main__":
    serve()
