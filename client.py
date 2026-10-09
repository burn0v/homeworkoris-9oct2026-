import socket
import threading
import protocol as proto

HOST = "127.0.0.1"
PORT = 5555


def listen_loop(sock, stop_event):
    while not stop_event.is_set():
        try:
            msg = proto.recv_message(sock)
        except (ConnectionResetError, OSError):
            msg = None
        if msg is None:
            print("\n[!] соединение с сервером потеряно")
            stop_event.set()
            break
        command, payload = msg
        text = payload.decode("utf-8", errors="replace")
        if command == "LIST":
            print(f"\n[текущие задачи]\n{text}\n> ", end="")
        elif command == "ERRO":
            print(f"\n[ошибка] {text}\n> ", end="")
        else:
            print(f"\n{text}\n> ", end="")


def main():
    username = input("Введите имя: ").strip()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        proto.send_message(sock, "JOIN", username.encode())
    except (ConnectionRefusedError, OSError) as e:
        print(f"Не удалось подключиться: {e}")
        return

    stop_event = threading.Event()
    threading.Thread(target=listen_loop, args=(sock, stop_event), daemon=True).start()

    print("Команды: /list, /quit, /addt, /done. Остальной текст - сообщение в чат.")
    try:
        while not stop_event.is_set():
            line = input("> ")
            if line == "/quit":
                proto.send_message(sock, "QUIT")
                break
            elif line == "/list":
                proto.send_message(sock, "LIST")
            elif line[:5] == "/addt":
                c, task_name = line.split()
                proto.send_message(sock, "ADDT", task_name.encode())
            elif line[:5] == "/done":
                c, task_name = line.split()
                proto.send_message(sock, "DONE", task_name.encode())
            # elif line[:5] == "/delt":
            #     c, task_name = line.split()
            #     proto.send_message(sock, "DELT", task_name.encode())

            elif line:
                proto.send_message(sock, "TEXT", line.encode())
    except (EOFError, KeyboardInterrupt, BrokenPipeError, OSError):
        pass
    finally:
        stop_event.set()
        sock.close()


if __name__ == "__main__":
    main()
