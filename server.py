import socket
import threading
import protocol as proto

HOST = "0.0.0.0"
PORT = 5555

clients = {}
clients_lock = threading.Lock()

tasks = {}
next_task_id = 1
tasks_lock = threading.Lock()


def broadcast(command, text, exclude=None):
    payload = text.encode("utf-8")

    with clients_lock:
        targets = [s for s in clients if s is not exclude]

    for sock in targets:
        try:
            proto.send_message(sock, command, payload)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


def handle_client(sock, addr):
    username = None
    global next_task_id

    try:
        first = proto.recv_message(sock)
        if first is None or first[0] != "JOIN":
            proto.send_message(sock, "ERRO", b"first command must be JOIN")
            return

        username = first[1].decode("utf-8", errors="replace").strip()
        with clients_lock:
            if not username or username in clients.values():
                proto.send_message(sock, "ERRO", b"invalid or taken username")
                return
            clients[sock] = username

        proto.send_message(sock, "TEXT", f"* вы вошли как {username}".encode())
        broadcast("TEXT", f"* {username} присоединился", exclude=sock)
        print(f"[+] {username} присоединился ({addr})")

        while True:
            msg = proto.recv_message(sock)
            if msg is None:
                print(f"[i] {username} отключился без QUIT")
                break

            command, payload = msg
            if command == "TEXT":
                text = payload.decode("utf-8", errors="replace")
                broadcast("TEXT", f"{username}: {text}", exclude=sock)
            elif command == "LIST":
                with tasks_lock:
                    tasks_names = [f"#{task_id}, {task_name} - {'выполенна 'if task['done'] else 'не выполнена'}"
                                   for task_id, task in tasks.items()]
                proto.send_message(sock, "LIST", "\n".join(tasks_names).encode())
            elif command == "QUIT":
                proto.send_message(sock, "TEXT", b"* bye")
                print(f"[-] {username} вышел через QUIT")
                break
            elif command == "ADDT":
                task_name = payload.decode("utf-8", errors="replace").strip()
                if not task_name:
                    proto.send_message(sock, "ERRO", "Название задачи не может быть пустым".encode("utf-8"))
                else:
                    with tasks_lock:
                        task_id = next_task_id
                        tasks[task_id] = {"name": task_name, "done": False}
                        next_task_id += 1
                    proto.send_message(sock, "TEXT", f"Добавлена задача #{task_id} {task_name}".encode())
            elif command == "DONE":
                str_task_id = payload.decode("utf-8", errors="replace").strip()
                task_id = int(str_task_id)
                if not task_id:
                    proto.send_message(sock, "ERRO", "Номер задачи не может быть пустым".encode("utf-8"))
                else:
                    with tasks_lock:
                        task = tasks.get(task_id)
                        if task == None:
                            proto.send_message(sock, "ERRO", "Задача не найдена".encode("utf-8"))
                        elif task["done"]:
                            proto.send_message(sock, "ERRO", "Задача уже выполнена".encode("utf-8"))
                        else:
                            task["done"] = True
                            proto.send_message(sock, "TEXT", "Задача отмечена выполненой".encode("utf-8"))
            # elif command == "DELT":
            #     str_task_id = payload.decode("utf-8", errors="replace").strip()
            #     task_id = int(str_task_id)
            #     if not task_id:
            #         proto.send_message(sock, "ERRO", "Номер задачи не может быть пустым")
            #     else:
            #         task = tasks.get(task_id)
            #         with tasks_lock:
            #             if task in tasks:
            #                 del tasks[task]
            #                 proto.send_message(sock, "TEXT", f"Задача {task_id} {task_name} была удалена".encode("utf-8"))
            #             else:
            #                 proto.send_message(sock, "ERRO", "Задача не существует.".encode("utf-8"))    
            else:
                proto.send_message(sock, "ERRO", f"unknown command {command}".encode())

    except ConnectionResetError:
        print(f"[!] {username or addr} - соединение сброшено (RST)")
    except BrokenPipeError:
        print(f"[!] {username or addr} - не удалось отправить, соединение разорвано")
    finally:
        with clients_lock:
            clients.pop(sock, None)
        sock.close()
        if username:
            broadcast("TEXT", f"* {username} покинул чат")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"[*] сервер слушает {HOST}:{PORT}")
        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] сервер остановлен")
