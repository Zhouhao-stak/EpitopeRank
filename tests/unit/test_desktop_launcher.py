import socket

from serve_ui import _free_port


def test_free_port_falls_back_to_system_assignment():
    port = _free_port(8800, attempts=0)
    assert 0 < port < 65536
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', port))
