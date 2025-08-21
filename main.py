import cv2
import numpy as np
import time
import signal
import sys
from mqtt_client import EraMqttClient
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOKEN, DEVICE_UID
from yolodetect import YoloDetect
from captureDrive import DriveUploader

def adjust_brightness(image, brightness_factor=1.5):
    adjusted = cv2.convertScaleAbs(image, alpha=brightness_factor, beta=0)
    return adjusted

def adjust_brightness_contrast(image, brightness=0, contrast=1.0):
    adjusted = cv2.convertScaleAbs(image, alpha=contrast, beta=brightness)
    return adjusted

def adjust_brightness_hsv(image, value_scale=1.5):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = cv2.convertScaleAbs(v, alpha=value_scale, beta=0)
    v = np.clip(v, 0, 255).astype('uint8')
    hsv = cv2.merge([h, s, v])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

class FPS:
    def __init__(self):
        self._start = None
        self._end = None
        self._numFrames = 0
        
    def start(self):
        self._start = time.time()
        self._numFrames = 0
        return self
        
    def stop(self):
        self._end = time.time()
        return self
        
    def update(self):
        self._numFrames += 1
        self._end = time.time()
        return self
        
    def elapsed(self):
        return self._end - self._start
        
    def fps(self):
        if self._end is None or self._start is None:
            return 0
        return self._numFrames / self.elapsed()

def init_webcam():
    """Khởi tạo webcam sử dụng OpenCV"""
    camera = cv2.VideoCapture(0)
    
    # Thiết lập độ phân giải
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    # Kiểm tra kết nối camera
    if not camera.isOpened():
        print("ERROR: Không thể mở webcam")
        return None
    
    # Kiểm tra đọc frame
    ret, frame = camera.read()
    if not ret or frame is None:
        print("ERROR: Không thể đọc frame từ webcam")
        camera.release()
        return None
        
    return camera

def main():
    # Initialize MQTT client
    mqtt_client = EraMqttClient(
        broker=MQTT_BROKER, 
        port=MQTT_PORT,
        token=MQTT_TOKEN,
        device_uid=DEVICE_UID
    )
    
    # Connect to MQTT broker
    mqtt_connected = mqtt_client.connect()
    if mqtt_connected:
        print("Connected to E-Ra MQTT broker successfully")
    else:
        print("Failed to connect to E-Ra MQTT broker")
        response = input("MQTT connection failed. Do you want to continue without MQTT? (y/n): ")
        if response.lower() != 'y':
            print("Application terminated")
            return
    
    # Array to store polygon points selected by user
    points = []

    # Initialize Yolo model for person detection and pass MQTT client to it
    model = YoloDetect(detect_class="person", mqtt_client=mqtt_client)

    # Brightness control parameters
    brightness_factor = 1.5  # Default brightness factor
    brightness_mode = 1      # 1: simple, 2: contrast-brightness, 3: HSV

    def signal_handler(sig, frame):
        print("Exiting application...")
        mqtt_client.disconnect()
        video_cap.release()
        cv2.destroyAllWindows()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    def handle_left_click(event, x, y, flags, params):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])
            print(f"Point added: [{x}, {y}]")

    def draw_polygon(frame, points):
        for point in points:
            frame = cv2.circle(frame, (point[0], point[1]), 5, (0, 0, 255), -1)
        
        if len(points) > 1:
            frame = cv2.polylines(frame, [np.int32(points)], False, (255, 0, 0), thickness=2)
        
        return frame

    detect = False

    print("\nHướng dẫn sử dụng:")
    print("- Nhấp chuột trái để chọn các điểm của vùng giám sát")
    print("- Nhấn 'd' để hoàn thành vùng giám sát và bắt đầu phát hiện")
    print("- Nhấn '+' để tăng độ sáng")
    print("- Nhấn '-' để giảm độ sáng")
    print("- Nhấn 'm' để chuyển đổi chế độ điều chỉnh độ sáng")
    print("- Nhấn 'r' để đặt lại vùng giám sát")
    print("- Nhấn 'q' để thoát chương trình")

    mqtt_status = "Connected" if mqtt_connected else "Disconnected"
    print(f"MQTT Status: {mqtt_status}")
    
    # Khởi tạo webcam
    video_cap = init_webcam()
    if not video_cap:
        return
    
    print("Webcam initialized successfully!")
    
    # Initialize FPS counter
    fps = FPS().start()
    
    while True:
        ret, frame = video_cap.read()
        if not ret or frame is None:
            print("Lỗi đọc frame, thử lại...")
            time.sleep(0.1)
            continue
        
        # Lật frame theo chiều ngang cho tự nhiên hơn
        frame = cv2.flip(frame, 1)
        
        # Cập nhật FPS
        fps.update()
        fps.stop()
        
        # Hiển thị FPS
        cv2.putText(frame, f"FPS: {fps.fps():.2f}", 
                    (10, frame.shape[0] - 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Reset FPS định kỳ
        if fps._numFrames % 100 == 0:
            fps = FPS().start()
        
        # Điều chỉnh độ sáng
        if brightness_mode == 1:
            frame = adjust_brightness(frame, brightness_factor)
        elif brightness_mode == 2:
            frame = adjust_brightness_contrast(frame, 10, brightness_factor)
        elif brightness_mode == 3:
            frame = adjust_brightness_hsv(frame, brightness_factor)
        
        # Vẽ vùng giám sát
        frame = draw_polygon(frame, points)
        
        # Xử lý phát hiện đối tượng
        if detect:
            frame, people_count = model.detect(frame=frame, points=points)
            
            # HIỂN THỊ SỐ NGƯỜI LÊN MÀN HÌNH
            cv2.putText(frame, f"People in area: {people_count}", 
                        (10, 80),  # Vị trí (góc trên bên trái)
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7,  # Kích thước font
                        (0, 255, 0),  # Màu xanh lá
                        2)
        
        # Xử lý phím
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('d') and len(points) >= 3:
            points.append(points[0])
            detect = True
            print("Detection started. Monitoring for intrusions...")
        elif key == ord('r'):
            points = []
            detect = False
            print("Reset monitoring area. Please define a new area.")
        elif key == ord('+') or key == ord('='):
            brightness_factor += 0.1
            if brightness_factor > 3.0:
                brightness_factor = 3.0
            print(f"Brightness factor: {brightness_factor:.1f}")
        elif key == ord('-') or key == ord('_'):
            brightness_factor -= 0.1
            if brightness_factor < 0.5:
                brightness_factor = 0.5
            print(f"Brightness factor: {brightness_factor:.1f}")
        elif key == ord('m'):
            brightness_mode = (brightness_mode % 3) + 1
            mode_names = {1: "Simple", 2: "Contrast-Brightness", 3: "HSV"}
            print(f"Brightness mode: {mode_names[brightness_mode]}")
        
        # Hiển thị trạng thái
        if not detect:
            cv2.putText(frame, "Define area and press 'd' to start detection", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
        
        mode_names = {1: "Simple", 2: "Contrast", 3: "HSV"}
        cv2.putText(frame, f"Brightness: {brightness_factor:.1f} | Mode: {mode_names[brightness_mode]}", 
                   (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        mqtt_status = "Connected" if mqtt_client.connected else "Disconnected"
        cv2.putText(frame, f"MQTT: {mqtt_status}", 
                   (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 
                   (0, 255, 0) if mqtt_client.connected else (0, 0, 255), 1)
        
        cv2.imshow("Intrusion Warning", frame)
        cv2.setMouseCallback('Intrusion Warning', handle_left_click, None)

    # Dọn dẹp tài nguyên
    mqtt_client.disconnect()
    video_cap.release()
    cv2.destroyAllWindows()
    print("Application terminated")

if __name__ == "__main__":
    main()