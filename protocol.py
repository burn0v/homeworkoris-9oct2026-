import struct

COMMAND_SIZE = 4
HEADER_FORMAT = "!4sI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024


def recv_exact(sock, size):
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("соединение закрыто до получения всех данных")
        chunks.extend(chunk)
    return bytes(chunks)


def send_message(sock, command, payload=b""):
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError(f"payload слишком большой: {len(payload)} байт")
    command_bytes = command.encode("ascii").ljust(COMMAND_SIZE)[:COMMAND_SIZE]
    header = struct.pack(HEADER_FORMAT, command_bytes, len(payload))
    sock.sendall(header + payload)


def recv_message(sock):
    try:
        header = recv_exact(sock, HEADER_SIZE)
    except ConnectionError:
        return None
    command_bytes, length = struct.unpack(HEADER_FORMAT, header)
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(f"заявленная длина {length} превышает лимит")
    payload = recv_exact(sock, length) if length else b""
    return command_bytes.decode("ascii").strip(), payload
