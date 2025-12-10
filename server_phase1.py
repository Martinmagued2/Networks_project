import socket
import struct
import datetime

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 1024
def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    return sock

def receive_packet(sock):
    return sock.recvfrom(BUFFER_SIZE)

