import queue
import time
import cv2
import math
import numpy as np
import socket
import tkinter as tk
import threading
from PIL import Image, ImageTk

print("Numpy Version: ",np.__version__)
print("OpenCV Version: ",cv2.__version__)

# ----------- Receiver Network Configuration ----------------
UDP_IP = "0.0.0.0"
TELEMETRY_UDP_PORT = 5005
VIDEO_UDP_PORT = 5006

# ------------ UDP Socket Setup --------------------
sock_telemetry = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_telemetry.bind((UDP_IP, TELEMETRY_UDP_PORT))
sock_telemetry.settimeout(0.01)

sock_video = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_video.bind((UDP_IP, VIDEO_UDP_PORT))
sock_video.settimeout(0.01)
FRAME_BUFFER_SIZE = 65536 # max UDP packet size
FRAME_QUEUE_SIZE = 2 # keeps only the latest N frames

# ----------- Global Thread Objects ----------------
frame_queue = queue.Queue(maxsize=FRAME_QUEUE_SIZE)
stop_event = threading.Event()

# ------------- GUI Setup -------------------------
set_font = "Helvetica"
root = tk.Tk()
root.title("ROV HUD")
WIDTH, HEIGHT = 800, 600      # 4:3
# WIDTH, HEIGHT = 1024, 576     # 16:9
# WIDTH, HEIGHT = 1024, 768     # 4:3
# WIDTH, HEIGHT = 1280, 720     # 16:9
frame_rate = 120
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
canvas.pack()
# map = tk.Canvas(root, width=800, height=600, bg="gray")
# map.pack()

#  Video Display Configuration 
video_frame = canvas.create_image(0, 0, anchor="nw", image=None)
frame_data = b""
lock = threading.Lock()

# map placeholder
# map_frame = map.create_image(1600, 0, anchor="ne", image=None)


# Compass parameters
center_x = WIDTH // 2
center_y = 50
pixels_per_degree = 16
major_tick_len = 15
minor_tick_len = 8
yaw = 0

# Artificial Horizon
horizon_line = canvas.create_line(0, HEIGHT/2, WIDTH, HEIGHT/2, fill="white", width=2)
# crosshair = canvas.create_line(WIDTH/2-10, HEIGHT/2, WIDTH/2+10, HEIGHT/2, fill="white", width=2)
# crosshair_v = canvas.create_line(WIDTH/2, HEIGHT/2-10, WIDTH/2, HEIGHT/2+10, fill="white", width=2)
crosshair = canvas.create_line(15, HEIGHT//2, 35, HEIGHT//2, fill="white", width=3)
crosshair = canvas.create_line(WIDTH - 35, HEIGHT//2, WIDTH - 15, HEIGHT//2, fill="white", width=3)

# Depth and yaw
yaw_text = canvas.create_text(WIDTH-80, HEIGHT-30, text="Yaw: 0", fill="white", font=(set_font, 16))
depth_text = canvas.create_text(80, HEIGHT-30, text="Depth: 0.0m", fill="white", font = (set_font, 16))

# Telemetry labels
label_counter = tk.Label(root, text="Counter: 0", font=("Helvetica", 16))
label_counter.pack()
label_roll = tk.Label(root, text="ROLL: 0.0", font=("Helvetica", 16))
label_roll.pack()
label_pitch = tk.Label(root, text="PITCH: 0.0", font=("Helvetica", 16))
label_pitch.pack()
label_yaw = tk.Label(root, text="YAW: 0.0", font=("Helvetica", 16))
label_yaw.pack()
label_depth = tk.Label(root, text="DEPTH: 0.0 m", font=("Helvetica", 16))
label_depth.pack()
label_temp = tk.Label(root, text="TEMP: 0.0 °C", font=("Helvetica", 16))
label_temp.pack()

# telemetry globals
telemetry = {
    "counter": 0,
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "depth": 0.0,
    "temp": 0.0
}

# ------------ Update HUD --------------------
def update_hud(counter, roll, pitch, yaw, depth, temp):

    # artificial horizon: roll rotates the horizon, pitch moves it veritically
    #pitch = max(-90, min(90, pitch))
    roll = roll % 360 # normalize roll

    pitch_pixels = (pitch / 45) * (HEIGHT / 4)
    center_y = HEIGHT/2 - pitch_pixels # pitch scale factor

    # horizon line length
    line_len = WIDTH / 2

    roll_rad = math.radians(roll)
    cos_r = math.cos(roll_rad)
    sin_r = math.sin(roll_rad)


    x0 = WIDTH / 2 - line_len * cos_r
    y0 = center_y - line_len * sin_r
    x1 = WIDTH / 2 + line_len * cos_r
    y1 = center_y + line_len * sin_r

    # clamp corrdinates
    """
    x0 = max(0, min(WIDTH, x0))
    x1 = max(0, min(WIDTH, x1))
    y0 = max(0, min(HEIGHT, y0))
    y1 = max(0, min(HEIGHT, y1))
    """
    # update visuals
    canvas.coords(horizon_line, x0, y0, x1, y1)
    canvas.itemconfig(yaw_text, text=f"Yaw: {yaw:.1f}")
    canvas.itemconfig(depth_text, text=f"Depth: {depth:.2f} m")

    
    # update text labels
    label_counter.config(text=f"COUNTER: {counter}")
    label_roll.config(text=f"ROLL: {roll:.1f}")
    label_pitch.config(text=f"PITCH: {pitch:.1f}")
    label_yaw.config(text=f"YAW: {yaw:.1f}")
    label_depth.config(text=f"DEPTH: {depth:.2f} m")
    label_temp.config(text=f"TEMP: {temp:.1f} °C")

# ------------ Update Compass ------------------------
def update_compass(yaw):
    canvas.delete("compass")

    start_deg = int(yaw) - (WIDTH // 3)
    end_deg = int(yaw) + (WIDTH // 3)
    deg_per_tick = 10

    for deg in range(start_deg, end_deg + 1):
        x = center_x + (deg - yaw) * pixels_per_degree
        if 0 <= x <= WIDTH:
        # draw tick
            if deg % deg_per_tick == 0:
                canvas.create_line(x, center_y, x,center_y - major_tick_len, fill="white", width=2, tags="compass")
                label = deg % 360
                if label == 0:
                    text = "N"
                elif label == 90:
                    text = "E"
                elif label == 180:
                    text = "S"
                elif label == 270:
                    text = "W"
                else:
                    text = str(label)
                canvas.create_text(x, center_y - major_tick_len - 10, text=text, fill="white", font=(set_font, 12), tags="compass")
            elif deg % (deg_per_tick/2) == 0:
                canvas.create_line(x,center_y, x,center_y - minor_tick_len, fill="gray", width=1, tags="compass")
    
    canvas.create_line(center_x, center_y - 15, center_x, center_y + 5, fill="white", width=3, tags="compass")
    #canvas.create_polygon(center_x - 5, center_y - 30, center_x + 5, center_y - 30, center_x, center_y - 40, fill="red", tags="compass")

# ------------ UDP Telemetry Receiver -----------------------
def udp_receiver():
    global telemetry
    print("Listening for ROV telemetry on UDP port", TELEMETRY_UDP_PORT)

    while True:
        try:
            data, addr = sock_telemetry.recvfrom(1024)
            line = data.decode('utf-8',errors='ignore').strip()
            parts = line.split(",")

            if len(parts) == 6:
                telemetry["counter"] = int(parts[0])
                telemetry["roll"] = float(parts[1])
                telemetry["pitch"] = float(parts[2])
                telemetry["yaw"] = float(parts[3])
                telemetry["depth"] = float(parts[4])
                telemetry["temp"] = float(parts[5])
        except socket.timeout:
            pass
        except Exception as e:
            print("Telemetry parse error:", e)

# -------------- UDP Video Receiver Thread ------------------------
def udp_video_receiver():
    print("Listening for ROV video feed on UDP port", VIDEO_UDP_PORT)

    while not stop_event.is_set():
        try:
            packet, _ = sock_video.recvfrom(FRAME_BUFFER_SIZE)
            npdata = np.frombuffer(packet, dtype=np.uint8)
            frame = cv2.imdecode(npdata, cv2.IMREAD_UNCHANGED)

            if frame is not None:

                # drop old frames if queue is full
                if not frame_queue.empty():
                    try:
                        frame_queue.get_nowait()
                    except queue.Empty:
                        pass

                frame_queue.put(frame)

        except socket.timeout:
            continue
        except Exception as e:
            print(f"[WARN] Video receive error: {e}")
            time.sleep(0.05)
    
    sock_video.close()
    print("Video receiver thread stopped.")

# -------------- Update Video Frame ------------------------
def update_video():
    try:
        frame = frame_queue.get_nowait()
        # Convert OpenCV frame to Tkinter image
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)

        # Update Video Frame in GUI
        canvas.itemconfig(video_frame, image=imgtk)
        canvas.image = imgtk  # Keep a reference to avoid garbage collection
    except queue.Empty:
        pass
    
# -------------- Update GUI ------------------------------
def update_gui():
    global frame_data
    counter = telemetry["counter"] // (80)
    roll = (telemetry["roll"])
    pitch = (telemetry["pitch"])
    yaw = -(telemetry["yaw"])
    depth = telemetry["depth"]
    temp = telemetry["temp"]

    update_video()
    update_hud(counter, roll, pitch, yaw, depth, temp)
    update_compass(yaw)

    label_counter.config(text=f"COUNTER: {counter:}")
    label_roll.config(text=f"ROLL: {roll:.1f}°")
    label_pitch.config(text=f"PITCH: {pitch:.1f}°")
    label_yaw.config(text=f"YAW: {yaw:.1f}°")
    label_depth.config(text=f"DEPTH: {depth:.1f} m")
    label_temp.config(text=f"TEMP: {temp:.1f} °C")

    root.after(1000//frame_rate, update_gui)

# -------------- Start Threads ------------------------
threading.Thread(target=udp_receiver, daemon=True).start()
threading.Thread(target=udp_video_receiver, daemon=True).start()
update_gui()

# -------------- Start Receiver Main Loop ---------------------------
root.mainloop()