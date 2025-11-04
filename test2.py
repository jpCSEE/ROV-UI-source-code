import cv2
import numpy as np
import pickle
import socket

print(np.__version__)
print(cv2.__version__)

# ----------- Network Configuration ----------------
UDP_IP = "0.0.0.0"
UDP_PORT = 5006
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for ROV video feed on UDP port", UDP_PORT)

frame_data = b""

while True:
    packet, _ = sock.recvfrom(65536)
    if packet == b"FRAME_START":
        frame_data = b""
        continue
    elif packet == b"FRAME_END":
        try:
            frame = pickle.loads(frame_data)
            frame = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # Convert BGR to RGB
            cv2.imshow('ROV Video Feed', frame)
            if cv2.waitKey(1) == 27:  # ESC key to exit
                break
        except Exception as e:
            print("Frame decode error:", e)
        continue

    frame_data += packet

sock.close()
cv2.destroyAllWindows()