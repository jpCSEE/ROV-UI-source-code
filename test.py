import socket, time, random

UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    roll = random.uniform(-180, 180)
    pitch = random.uniform(-45, 45)
    yaw = random.uniform(0, 360)
    depth = random.uniform(0, 30)
    msg = f"ROLL:{roll:.1f},PITCH:{pitch:.1f},YAW:{yaw:.1f},DEPTH:{depth:.2f}"
    sock.sendto(msg.encode(), (UDP_IP, UDP_PORT))
    time.sleep(0.1)