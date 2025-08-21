from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import cv2
import numpy as np
from telegram_utils import send_telegram
import datetime
import threading
from captureDrive import DriveUploader

def isInside(points, centroid):
    polygon = Polygon(points)
    centroid = Point(centroid)
    return polygon.contains(centroid)

class YoloDetect():
    def __init__(self, detect_class="person", frame_width=1280, frame_height=720, mqtt_client=None):
        # Parameters
        self.classnames_file = "model/classnames.txt"
        self.weights_file = "model/yolov4-tiny.weights"
        self.config_file = "model/yolov4-tiny.cfg"
        self.conf_threshold = 0.5
        self.nms_threshold = 0.4
        self.detect_class = detect_class
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.scale = 1 / 255
        self.model = cv2.dnn.readNet(self.weights_file, self.config_file)
        self.classes = None
        self.output_layers = None
        self.last_people_count = -1 
        self.inside_count = 0
        self.read_class_file()
        self.get_output_layers()
        self.last_alert = None
        self.alert_telegram_each = 15  # seconds
        self.last_people_count_send = None  # Thời gian gửi số người lần cuối
        self.people_count_interval = 1.0  # Gửi số người mỗi 1 giây
        self.mqtt_client = mqtt_client
        self.mqtt_connected = False
        if self.mqtt_client is not None:
            self.mqtt_connected = self.mqtt_client.connected
            print(f"MQTT client connection status: {'Connected' if self.mqtt_connected else 'Disconnected'}")

        # Thêm biến theo dõi trạng thái LED
        self.last_led_state = -1  # -1 là trạng thái chưa xác định, 0: tắt, 1: bật

        self.intrusion_active = False
        self.drive_uploader = DriveUploader(
        folder_id="____your_folder_id____",
        credentials_file="____your_credentials_file____"
        )

    def read_class_file(self):
        with open(self.classnames_file, 'r') as f:
            self.classes = [line.strip() for line in f.readlines()]

    def get_output_layers(self):
        layer_names = self.model.getLayerNames()
        self.output_layers = [layer_names[i - 1] for i in self.model.getUnconnectedOutLayers()]

    def draw_prediction(self, img, class_id, x, y, x_plus_w, y_plus_h, points):
        label = str(self.classes[class_id])
        color = (0, 255, 0)
        cv2.rectangle(img, (x, y), (x_plus_w, y_plus_h), color, 2)
        cv2.putText(img, label, (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Calculate centroid
        centroid = ((x + x_plus_w) // 2, (y + y_plus_h) // 2)
        cv2.circle(img, centroid, 5, (color), -1)

        # Check if person is inside the defined area
        person_inside = isInside(points, centroid)
        
        if person_inside:
            img = self.alert(img)
            
        return person_inside

    def alert(self, img):
        cv2.putText(img, "ALARM!!!!", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        if (self.last_alert is None) or (
                (datetime.datetime.utcnow() - self.last_alert).total_seconds() > self.alert_telegram_each):
            self.last_alert = datetime.datetime.utcnow()
            
            # Tạo tên file và lưu ảnh
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alert_{timestamp}.jpg"
            cv2.imwrite(filename, cv2.resize(img, dsize=None, fx=0.2, fy=0.2))
            
            # Upload lên Drive
            upload_thread = threading.Thread(
                target=self.drive_uploader.upload_image,
                args=(filename, "human", "21040202")  
            )
            upload_thread.start()
            
            # Gửi Telegram
            send_telegram_thread = threading.Thread(target=send_telegram)
            send_telegram_thread.start()
            
        return img

    def detect(self, frame, points):
        blob = cv2.dnn.blobFromImage(frame, self.scale, (416, 416), (0, 0, 0), True, crop=False)
        self.model.setInput(blob)
        outs = self.model.forward(self.output_layers)

        class_ids = []
        confidences = []
        boxes = []
        
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if (confidence >= self.conf_threshold) and (self.classes[class_id] == self.detect_class):
                    center_x = int(detection[0] * self.frame_width)
                    center_y = int(detection[1] * self.frame_height)
                    w = int(detection[2] * self.frame_width)
                    h = int(detection[3] * self.frame_height)
                    x = center_x - w / 2
                    y = center_y - h / 2
                    class_ids.append(class_id)
                    confidences.append(float(confidence))
                    boxes.append([x, y, w, h])

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.nms_threshold)

        inside_count = 0
        # Draw bounding boxes and count people inside the area
        for i in indices:
            # Handle differences between OpenCV versions
            if isinstance(i, (list, tuple)):
                i = i[0]  # For older OpenCV versions
                
            box = boxes[i]
            x = box[0]
            y = box[1]
            w = box[2]
            h = box[3]
            person_inside = self.draw_prediction(frame, class_ids[i], round(x), round(y), round(x + w), round(y + h), points)
            if person_inside:
                inside_count += 1

        # Xử lý trạng thái đèn LED
        new_led_state = 1 if inside_count > 0 else 0
        
        # Chỉ gửi MQTT khi trạng thái LED thay đổi
        if self.mqtt_client and self.mqtt_connected and new_led_state != self.last_led_state:
            thread = threading.Thread(target=self._send_mqtt_alert, args=(new_led_state,))
            thread.start()
            self.last_led_state = new_led_state

        # Gửi số người với throttling 1 giây
        if self.mqtt_client and self.mqtt_connected:
            current_time = datetime.datetime.now()
            # Gửi nếu chưa từng gửi hoặc đã quá 1 giây từ lần gửi cuối
            should_send = (self.last_people_count_send is None or 
                          (current_time - self.last_people_count_send).total_seconds() >= self.people_count_interval)
            
            if should_send:
                try:
                    self.mqtt_client.publish_people_count(inside_count)
                    self.last_people_count_send = current_time
                except Exception as e:
                    print(f"Lỗi gửi số người: {e}")
        
        return frame, inside_count

    def _send_mqtt_alert(self, state):
        """Gửi trạng thái LED đến E-Ra"""
        try:
            # Sử dụng hàm publish_intrusion_alert của mqtt_client
            if self.mqtt_client:
                self.mqtt_client.publish_intrusion_alert(state)
        except Exception as e:
            print(f"Lỗi gửi trạng thái LED: {e}")