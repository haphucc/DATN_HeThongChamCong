import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import imutils
import pickle
import time
import tensorflow as tf
import mediapipe as mp
import facenet
from sklearn.svm import SVC
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import json
import hashlib 
import random
import smtplib
import mysql.connector
from mysql.connector import Error

load_dotenv('Database/.env_file_mysql')
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(otp_code, to_email):
    try:
        with open('Database/email_config.json', 'r') as f:
            config = json.load(f)
        sender_email = config["email"]
        sender_password = config["password"]
        subject = "Mã xác thực OTP đổi mật khẩu"
        body = f"Mã OTP của bạn là: {otp_code}"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[ERROR] Không gửi được email OTP: {e}")
        return False

class FaceRecognitionSystem:
    def __init__(self, video_label):
        self.INPUT_IMAGE_SIZE = 160
        self.CLASSIFIER_PATH = 'Models/facemodel.pkl'
        self.FACENET_MODEL_PATH = 'Models/20170512-110547.pb'
        self.CHECKIN_MIN_GAP = 30
        
        self.EMPLOYEE_CSV = 'Database/employees.csv'
        self.TIMEKEEPING_CSV = 'Database/timekeeping.csv'        
        os.makedirs("Database", exist_ok=True)
        
        if not os.path.exists(self.EMPLOYEE_CSV):
            pd.DataFrame(columns=['employee_id', 'name', 'position']).to_csv(self.EMPLOYEE_CSV, index=False)
        if not os.path.exists(self.TIMEKEEPING_CSV):
            pd.DataFrame(columns=['employee_id', 'name', 'position', 'date', 'time']).to_csv(self.TIMEKEEPING_CSV, index=False)
        
        self.time_interval = 1
        self.photo_interval = 5
        self.probability_threshold = 0.7
        self.sync_interval = 60  # seconds

        self.graph = tf.Graph()
        self.sess = tf.compat.v1.Session(graph=self.graph)

        self.collecting_data = False
        self.new_person_id = ""
        self.new_person_name = ""
        self.new_person_position = ""
        self.photo_count = 0
        self.raw_path = "Dataset/FaceData/raw"
        self.processed_path = "Dataset/FaceData/processed"
        self.last_checkin_times = {}
        
        self.last_update_time = 0
        self.last_flash_time = 0

        self.lock = threading.Lock()
        self.video_label = video_label
        self.running = True
        self.recognition_active = False
        self.retrain_needed = False
        self.cap = None
        
        self.db_connection = None
        self.db_cursor = None
        self.db_config = {
            'host': os.getenv("MYSQL_HOST"),
            'port': os.getenv("MYSQL_PORT"),
            'user': os.getenv("MYSQL_USER"),
            'password': os.getenv("MYSQL_PASSWORD"),
            'database': os.getenv("MYSQL_DB")
        }
        self.employee_data = {}

        # Khởi tạo kết nối cơ sở dữ liệu và đồng bộ
        self.initialize_db_connection()
        self.load_employee_data()
        if self.db_cursor:
            self.initialize_db_tables()
            self.sync_csv_to_mysql()
        else:
            print("[TB] Bỏ qua tạo bảng và đồng bộ vì chưa có kết nối MySQL.")

        # Thử mở camera
        try:
            self.cap = cv2.VideoCapture(0)  # Thay đổi chỉ số thành 0 hoặc kiểm tra chỉ số đúng
            if not self.cap.isOpened():
                raise Exception("Không thể mở camera")
        except Exception as e:
            messagebox.showerror("Lỗi Camera", f"Không thể mở camera: {str(e)}. Vui lòng kiểm tra kết nối camera.")
            print(f"[ERROR] Không thể mở camera: {e}")
            self.running = False  # Ngăn update_video chạy nếu camera không mở được
        
        if self.running:
            self.initialize_system()
            self.update_video()
            self.start_mysql_sync_thread()

    def initialize_db_connection(self):
        try:
            import socket
            socket.setdefaulttimeout(2)
            self.db_connection = mysql.connector.connect(
                connection_timeout=2,
                **self.db_config
            )
            if self.db_connection.is_connected():
                self.db_cursor = self.db_connection.cursor(buffered=True)
                print("[TB] Đã kết nối thành công đến MySQL database!")
            else:
                raise Exception("Không thể kết nối đến MySQL.")
        except Exception as e:
            print(f"[CANH_BAO] Không thể kết nối đến MySQL: {e}")
            self.db_connection = None
            self.db_cursor = None

    def close_db_connection(self):
        if hasattr(self, 'db_cursor') and self.db_cursor:
            try:
                self.db_cursor.close()
            except:
                pass
            self.db_cursor = None
        if hasattr(self, 'db_connection') and self.db_connection:
            try:
                if self.db_connection.is_connected():
                    self.db_connection.close()
            except:
                pass
            self.db_connection = None
            print("[TB] Đã đóng kết nối MySQL")

    def initialize_db_tables(self):
        if self.db_cursor is None or self.db_connection is None:
            print("[TB] Không thể tạo bảng: Kết nối MySQL chưa được thiết lập.")
            return
        try:
            create_employees_table = """
            CREATE TABLE IF NOT EXISTS employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                employee_id VARCHAR(10) NOT NULL,
                name VARCHAR(50) NOT NULL,
                position VARCHAR(50) NOT NULL,
                UNIQUE KEY unique_employee_id (employee_id)
            )
            """
            self.db_cursor.execute(create_employees_table)
            create_timekeeping_table = """
            CREATE TABLE IF NOT EXISTS timekeeping (
                id INT AUTO_INCREMENT PRIMARY KEY,
                employee_id VARCHAR(10) NOT NULL,
                name VARCHAR(50) NOT NULL,
                position VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
            )
            """
            self.db_cursor.execute(create_timekeeping_table)
            self.db_connection.commit()
            print("[TB] Đã kiểm tra/tạo bảng trong MySQL!")
        except Error as e:
            print(f"[ERROR] Lỗi khi tạo bảng trong MySQL: {e}")

    def start_mysql_sync_thread(self):
        def sync_loop():
            while True:
                try:
                    time.sleep(self.sync_interval)
                    print("[TB] Bắt đầu đồng bộ MySQL...")
                    self.initialize_db_connection()
                    if self.db_connection and self.db_connection.is_connected():
                        try:
                            self.sync_csv_to_mysql()
                            self.load_employee_data()
                            print("[TB] Đã đồng bộ CSV sang MySQL.")
                        except Exception as e:
                            print(f"[ERROR] Lỗi đồng bộ MySQL: {e}")
                        finally:
                            self.close_db_connection()
                    else:
                        print("[CANH_BAO] Không thể kết nối MySQL để đồng bộ.")
                except Exception as e:
                    print(f"[CANH_BAO] Lỗi không mong muốn trong thread đồng bộ MySQL: {e}")
                    time.sleep(2)
        threading.Thread(target=sync_loop, daemon=True).start()

    def sync_csv_to_mysql(self):
        if not self.db_cursor or not self.db_connection.is_connected():
            print("[TB] Không thể đồng bộ CSV vì chưa có kết nối MySQL.")
            return
        try:
            with self.lock:
                # --- Đồng bộ employees ---
                try:
                    df_employees = pd.read_csv(self.EMPLOYEE_CSV)
                    # Duyệt theo thứ tự dòng trong CSV
                    csv_employees = []
                    for _, row in df_employees.iterrows():
                        csv_employees.append((
                            str(row['employee_id']),
                            str(row['name']),
                            str(row['position'])
                        ))
                    self.db_cursor.execute("SELECT employee_id, name, position FROM employees")
                    mysql_employees = {
                        str(row[0]): {
                            'name': str(row[1]),
                            'position': str(row[2])
                        }
                        for row in self.db_cursor.fetchall()
                    }
                except Exception as e:
                    print(f"[CANH_BAO] Lỗi truy vấn MySQL (employees): {e}")
                    return

                # Xóa nhân viên không còn trong CSV khỏi MySQL
                csv_ids = set([emp[0] for emp in csv_employees])
                delete_ids = set(mysql_employees.keys()) - csv_ids
                delete_count = 0
                for employee_id in delete_ids:
                    self.db_cursor.execute("DELETE FROM timekeeping WHERE employee_id = %s", (employee_id,))
                    self.db_cursor.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
                    delete_count += 1
                if delete_count > 0:
                    print(f"[TB] Đã xóa {delete_count} nhân viên không còn trong CSV khỏi MySQL.")

                # Thêm/cập nhật nhân viên từ CSV vào MySQL (theo thứ tự dòng)
                employee_count = 0
                update_count = 0
                for employee_id, name, position in csv_employees:
                    if employee_id in mysql_employees:
                        if (mysql_employees[employee_id]['name'] != name or
                            mysql_employees[employee_id]['position'] != position):
                            self.db_cursor.execute(
                                "UPDATE employees SET name = %s, position = %s WHERE employee_id = %s",
                                (name, position, employee_id)
                            )
                            update_count += 1
                    else:
                        self.db_cursor.execute(
                            "INSERT INTO employees (employee_id, name, position) VALUES (%s, %s, %s)",
                            (employee_id, name, position)
                        )
                        employee_count += 1
                    self.db_cursor.fetchall()
                print(f"[TB] Đã thêm {employee_count} nhân viên mới, cập nhật {update_count} nhân viên trong MySQL.")

                # --- Đồng bộ timekeeping ---
                try:
                    df_timekeeping = pd.read_csv(self.TIMEKEEPING_CSV)
                    # Duyệt theo thứ tự dòng trong CSV
                    csv_timekeeping = []
                    for _, row in df_timekeeping.iterrows():
                        csv_timekeeping.append((
                            str(row['employee_id']),
                            str(row['name']),
                            str(row['position']),
                            str(row['date']),
                            str(row['time'])
                        ))
                    self.db_cursor.execute("SELECT employee_id, name, position, date, time FROM timekeeping")
                    mysql_timekeeping = {
                        (str(row[0]), str(row[3]), str(row[4])): {
                            'name': str(row[1]),
                            'position': str(row[2])
                        }
                        for row in self.db_cursor.fetchall()
                    }
                except Exception as e:
                    print(f"[CANH_BAO] Lỗi truy vấn MySQL (timekeeping): {e}")
                    return

                # Xóa bản ghi không còn trong CSV khỏi MySQL
                csv_timekeeping_keys = set((emp[0], emp[3], emp[4]) for emp in csv_timekeeping)
                delete_records = set(mysql_timekeeping.keys()) - csv_timekeeping_keys
                for employee_id, date, time_val in delete_records:
                    self.db_cursor.execute(
                        "DELETE FROM timekeeping WHERE employee_id = %s AND date = %s AND time = %s",
                        (employee_id, date, time_val)
                    )

                # Thêm mới và cập nhật bản ghi từ CSV vào MySQL (theo thứ tự dòng)
                timekeeping_insert_count = 0
                timekeeping_update_count = 0
                for employee_id, name, position, date, time_val in csv_timekeeping:
                    key = (employee_id, date, time_val)
                    if key in mysql_timekeeping:
                        mysql_info = mysql_timekeeping[key]
                        if (mysql_info['name'] != name or
                            mysql_info['position'] != position):
                            self.db_cursor.execute(
                                "UPDATE timekeeping SET name = %s, position = %s WHERE employee_id = %s AND date = %s AND time = %s",
                                (name, position, employee_id, date, time_val)
                            )
                            timekeeping_update_count += 1
                    else:
                        self.db_cursor.execute(
                            "INSERT INTO timekeeping (employee_id, name, position, date, time) VALUES (%s, %s, %s, %s, %s)",
                            (employee_id, name, position, date, time_val)
                        )
                        timekeeping_insert_count += 1
                    self.db_cursor.fetchall()
                print(f"[TB] Đã thêm {timekeeping_insert_count} bản ghi mới, cập nhật {timekeeping_update_count} bản ghi chấm công trong MySQL.")

                try:
                    self.db_connection.commit()
                except Exception as e:
                    print(f"[CANH_BAO] Lỗi commit MySQL: {e}")
                print("[TB] Đã hoàn tất đồng bộ CSV sang MySQL.")
        except Exception as e:
            print(f"[ERROR] Đồng bộ CSV sang MySQL thất bại: {e}")

    def initialize_system(self):
        with self.graph.as_default():
            print("[TB] Đang tải mô hình FaceNet...")
            with self.sess.as_default():
                with tf.io.gfile.GFile(self.FACENET_MODEL_PATH, 'rb') as f:
                    graph_def = tf.compat.v1.GraphDef()
                    graph_def.ParseFromString(f.read())
                    tf.import_graph_def(graph_def, name='')

                self.images_placeholder = self.graph.get_tensor_by_name("input:0")
                self.embeddings = self.graph.get_tensor_by_name("embeddings:0")
                self.phase_train_placeholder = self.graph.get_tensor_by_name("phase_train:0")

            print("[TB] Đang tải bộ phân loại...")
            if os.path.exists(self.CLASSIFIER_PATH):
                with open(self.CLASSIFIER_PATH, 'rb') as f:
                    self.model, self.class_names = pickle.load(f)
            else:
                self.model, self.class_names = None, []

        self.mp_face_detection = mp.solutions.face_detection        
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) 

        print("[TB] Hệ thống đã khởi tạo và sẵn sàng!")
        
    def load_employee_data(self):
        self.employee_data = {}
        try:
            df_csv = pd.read_csv(self.EMPLOYEE_CSV)
            for _, row in df_csv.iterrows():
                employee_id = str(row['employee_id'])
                self.employee_data[employee_id] = {'name': row['name'], 'position': row['position']}
            print("[TB] Đã tải dữ liệu nhân viên từ employee.csv")
        except Exception as e:
            print(f"[ERROR] Lỗi khi đọc employee.csv: {e}")
            if self.db_cursor and self.db_connection.is_connected():
                try:
                    self.db_cursor.execute("SELECT employee_id, name, position FROM employees")
                    for row in self.db_cursor.fetchall():
                        employee_id = str(row[0])
                        self.employee_data[employee_id] = {'name': row[1], 'position': row[2]}
                    print("[TB] Đã tải dữ liệu nhân viên từ MySQL")
                except Error as e:
                    print(f"[ERROR] Lỗi khi đọc dữ liệu nhân viên từ MySQL: {e}")
        if not self.employee_data:
            print("[CANH_BAO] Không có dữ liệu nhân viên từ cả CSV và MySQL")

    def save_employee(self, employee_id, name, position):
        with self.lock:
            self.employee_data[str(employee_id)] = {'name': name, 'position': position}
            try:
                df = pd.read_csv(self.EMPLOYEE_CSV)
                # Không sort, chỉ append cuối
                df = pd.concat([df, pd.DataFrame({
                    'employee_id': [employee_id],
                    'name': [name],
                    'position': [position]
                })], ignore_index=True)
                df.to_csv(self.EMPLOYEE_CSV, index=False)
                print(f"[TB] Đã lưu nhân viên {employee_id} vào CSV")
            except Exception as e:
                print(f"[ERROR] CSV: {e}")

    def get_employee_info(self, employee_id):
        employee_id = str(employee_id)
        if employee_id in self.employee_data:
            return self.employee_data[employee_id]['name'], self.employee_data[employee_id]['position']
        return None, None

    def log_attendance(self, employee_id, face_img=None):
        name, position = self.get_employee_info(employee_id)
        if name is None or position is None:
            print(f"[ERROR] Không tìm thấy thông tin nhân viên ID {employee_id}")
            return
    
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d") 
        current_time = now.strftime("%H:%M:%S")
    
        if str(employee_id) in self.last_checkin_times:
            last_time = self.last_checkin_times[str(employee_id)]
            time_diff = (now - last_time).total_seconds()
            if time_diff < self.CHECKIN_MIN_GAP:
                return

        with self.lock:
            try:
                df = pd.read_csv(self.TIMEKEEPING_CSV)
                df['employee_id'] = df['employee_id'].astype(int)
                # Không sort, chỉ append cuối
                df = pd.concat([df, pd.DataFrame({
                    'employee_id': [int(employee_id)],
                    'name': [name],
                    'position': [position], 
                    'date': [current_date],
                    'time': [current_time]
                })], ignore_index=True)
                df.to_csv(self.TIMEKEEPING_CSV, index=False)
                print(f"[TB] Đã ghi chấm công vào CSV cho ID {employee_id}")
                
                self.last_checkin_times[str(employee_id)] = now
            
            except Exception as e:
                print(f"[ERROR] Lỗi ghi chấm công: {e}")
    
        if hasattr(self, "show_user_info"):
            self.show_user_info(employee_id, name, position, 
                               f"{current_date} {current_time}", face_img)

    def check_employee_id_exists(self, employee_id):
        employee_id = str(employee_id)
        if employee_id in self.employee_data:
            return True
        try:
            df = pd.read_csv(self.EMPLOYEE_CSV)
            return str(employee_id) in df['employee_id'].astype(str).values
        except Exception as e:
            print(f"[ERROR] Lỗi khi kiểm tra employee.csv: {e}")
            return False

    def toggle_recognition(self):
        self.recognition_active = not self.recognition_active
        state = "BẬT" if self.recognition_active else "TẮT"
        print(f"[TB] Nhận diện khuôn mặt hiện đang {state}.")

    def update_video(self):
        if not self.running or not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            self.video_label.after(20, self.update_video)
            return
        frame = imutils.resize(frame, width=700)
        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        if self.collecting_data:
            self.collect_new_data(frame, display_frame)
            if self.photo_count >= self.photo_interval:
                self.collecting_data = False
                print(f"[TB] Đã hoàn tất thu thập dữ liệu cho {self.new_person_id}")
                threading.Thread(target=self.align_faces, daemon=True).start()
                self.retrain_needed = True
        elif self.recognition_active:
            display_frame = self.recognize_faces(display_frame)
        current_time = time.time()
        if current_time - self.last_update_time >= 1/50:
            frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            self.last_update_time = current_time
        self.video_label.after(20, self.update_video)

    def recognize_faces(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_frame)
        if not results.detections:
            return frame
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = frame.shape
            x1 = int(bboxC.xmin * iw)
            y1 = int(bboxC.ymin * ih)
            x2 = int((bboxC.xmin + bboxC.width) * iw)
            y2 = int((bboxC.ymin + bboxC.height) * ih)
            if (y2 - y1) / ih > 0.35:
                cropped = frame[y1:y2, x1:x2]
                if cropped.size == 0:
                    continue
                scaled = cv2.resize(cropped, (self.INPUT_IMAGE_SIZE, self.INPUT_IMAGE_SIZE))
                scaled = facenet.prewhiten(scaled)
                scaled_reshape = scaled.reshape(-1, self.INPUT_IMAGE_SIZE, self.INPUT_IMAGE_SIZE, 3)
                feed_dict = {
                    self.images_placeholder: scaled_reshape,
                    self.phase_train_placeholder: False
                }
                emb_array = self.sess.run(self.embeddings, feed_dict=feed_dict)
                predictions = self.model.predict_proba(emb_array)
                best_class_indices = np.argmax(predictions, axis=1)
                best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
                
                if best_class_probabilities[0] > self.probability_threshold:
                    employee_id = self.class_names[best_class_indices[0]]
                    prob = best_class_probabilities[0]
                    name, position = self.get_employee_info(employee_id)
                    if name and position:
                        self.log_attendance(employee_id, frame[y1:y2, x1:x2])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"ID: {employee_id}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(frame, f"{prob:.3f}", (x1, y2 + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        return frame

    def collect_new_data(self, frame, display_frame):
        current_time = time.time()
        if hasattr(self, 'last_capture_time') and current_time - self.last_capture_time <= self.time_interval:
            countdown = round(self.time_interval - (current_time - self.last_capture_time), 1)
            cv2.putText(display_frame, f"Next capture in: {countdown}s", (20, frame.shape[0] - 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            return False
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{self.new_person_id}_{timestamp}_{self.photo_count}.jpg"
        raw_file = os.path.join(self.raw_path, self.new_person_id, filename)
        cv2.imwrite(raw_file, frame)
        self.photo_count += 1
        self.last_capture_time = current_time
        self.last_flash_time = current_time
        self.last_saved_filename = filename
        if current_time - self.last_flash_time < 0.3:
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (display_frame.shape[1], display_frame.shape[0]), (255, 255, 255), -1)
            alpha = 0.5
            cv2.addWeighted(overlay, alpha, display_frame, 1 - alpha, 0, display_frame)
        return True

    def collect_data(self):
        print("[TB] Đang thu thập dữ liệu...")
        if not self.new_person_id:
            print("[ERROR] Employee ID không được để trống.")
            return
        person_path = os.path.join(self.raw_path, self.new_person_id)
        if not os.path.exists(person_path):
            os.makedirs(person_path)
        self.save_employee(self.new_person_id, self.new_person_name, self.new_person_position)
        self.collecting_data = True
        self.photo_count = 0
        print(f"[TB] Bắt đầu thu thập dữ liệu cho ID {self.new_person_id}...")

    def align_faces(self):
        print("[TB] Đang căn chỉnh khuôn mặt...")
        for person in os.listdir(self.raw_path):
            raw_dir = os.path.join(self.raw_path, person)
            processed_dir = os.path.join(self.processed_path, person)
            if not os.path.exists(processed_dir):
                os.makedirs(processed_dir)
            for img_name in os.listdir(raw_dir):
                img_path = os.path.join(raw_dir, img_name)
                img = cv2.imread(img_path)
                if img is None:
                    continue
                results = self.face_detection.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                if not results.detections:
                    continue
                bboxC = results.detections[0].location_data.relative_bounding_box
                ih, iw, _ = img.shape
                x1 = int(bboxC.xmin * iw)
                y1 = int(bboxC.ymin * ih)
                x2 = int((bboxC.xmin + bboxC.width) * iw)
                y2 = int((bboxC.ymin + bboxC.height) * ih)
                face_img = img[y1:y2, x1:x2]
                if face_img.size == 0:
                    continue
                face_img = cv2.resize(face_img, (self.INPUT_IMAGE_SIZE, self.INPUT_IMAGE_SIZE))
                save_path = os.path.join(processed_dir, img_name)
                cv2.imwrite(save_path, face_img)
        print("[TB] Hoàn tất căn chỉnh.")

    def train_model(self):
        print("[TB] Đang huấn luyện mô hình...")
        dataset = facenet.get_dataset(self.processed_path)
        paths, labels = facenet.get_image_paths_and_labels(dataset)
        facenet.load_model(self.FACENET_MODEL_PATH)
        images_placeholder = self.graph.get_tensor_by_name("input:0")
        embeddings = self.graph.get_tensor_by_name("embeddings:0")
        phase_train_placeholder = self.graph.get_tensor_by_name("phase_train:0")
        embedding_size = embeddings.get_shape()[1]
        emb_array = np.zeros((len(paths), embedding_size))
        for idx in range(0, len(paths), 100):
            batch_paths = paths[idx:idx+100]
            images = facenet.load_data(batch_paths, False, False, self.INPUT_IMAGE_SIZE)
            feed_dict = {images_placeholder: images, phase_train_placeholder: False}
            emb_array[idx:idx+len(images)] = self.sess.run(embeddings, feed_dict=feed_dict)
            
        model = SVC(kernel='linear', probability=True)
        
        model.fit(emb_array, labels)
        class_names = [cls.name for cls in dataset]
        with open(self.CLASSIFIER_PATH, 'wb') as f:
            pickle.dump((model, class_names), f)
        self.load_classifier()
        print("[TB] Hoàn tất huấn luyện mô hình.")

    def load_classifier(self):
        with open(self.CLASSIFIER_PATH, 'rb') as f:
            self.model, self.class_names = pickle.load(f)

    def delete_user_data(self, employee_id):
        if not employee_id:
            print("[TB] Chưa nhập Employee ID.")
            return
        raw_path = os.path.join(self.raw_path, employee_id)
        processed_path = os.path.join(self.processed_path, employee_id)
        with self.lock:
            if str(employee_id) in self.employee_data:
                del self.employee_data[str(employee_id)]
            try:
                df = pd.read_csv(self.EMPLOYEE_CSV)
                initial_len = len(df)
                df['employee_id'] = df['employee_id'].astype(str)
                df = df[df['employee_id'] != str(employee_id)]
                if len(df) < initial_len:
                    df.to_csv(self.EMPLOYEE_CSV, index=False)
                    print(f"[TB] Đã xóa ID {employee_id} khỏi employee.csv")
                else:
                    print(f"[CANH_BAO] Không tìm thấy ID {employee_id} trong employee.csv")

                df_timekeeping = pd.read_csv(self.TIMEKEEPING_CSV)
                initial_len_timekeeping = len(df_timekeeping)
                df_timekeeping['employee_id'] = df_timekeeping['employee_id'].astype(str)
                df_timekeeping = df_timekeeping[df_timekeeping['employee_id'] != str(employee_id)]
                if len(df_timekeeping) < initial_len_timekeeping:
                    df_timekeeping.to_csv(self.TIMEKEEPING_CSV, index=False)
                    print(f"[TB] Đã xóa ID {employee_id} khỏi timekeeping.csv")
                else:
                    print(f"[CANH_BAO] Không tìm thấy ID {employee_id} trong timekeeping.csv")
            except Exception as e:
                print(f"[ERROR] Xóa CSV: {e}")

            if employee_id in self.last_checkin_times:
                del self.last_checkin_times[employee_id]

        for path in [raw_path, processed_path]:
            if os.path.exists(path):
                for root, dirs, files in os.walk(path, topdown=False):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for dir in dirs:
                        os.rmdir(os.path.join(root, dir))
                os.rmdir(path)
                print(f"[TB] Đã xóa dữ liệu của ID: {employee_id}")
            else:
                print(f"[TB] Không tìm thấy dữ liệu cho ID: {employee_id}")

    def close_db_connection(self):
        # Xóa hoàn toàn hàm này vì không còn kết nối MySQL
        pass

edit_input_frame = None

def load_admin_password():
    pw_file = 'Database/admin_password.json'
    if not os.path.exists(pw_file):
        print("[ERROR] File admin_password.json không tồn tại. Vui lòng tạo file này trước khi chạy.")
        return None
    try:
        with open(pw_file, 'r') as f:
            return json.load(f)["password"]
    except Exception as e:
        print(f"[ERROR] Lỗi khi đọc file admin_password.json: {e}")
        return None

def check_admin_password(input_password):
    hashed = hashlib.sha256(input_password.encode('utf-8')).hexdigest()
    return hashed == load_admin_password()

def is_valid_id(employee_id):
    return employee_id.strip().isdigit()

def start_gui():
    root = tk.Tk()
    root.last_tab_index = 0 
    root.title("Hệ Thống Chấm Công")
    root.geometry("1100x500")
    root.state('zoomed')
    # root.attributes('-zoomed', True)
    style = ttk.Style()
    
    style.configure("TNotebook.Tab", padding=[20, 8], font=("Arial", 12))

    left_frame = tk.Frame(root, width=300, bg="white")
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right_frame = tk.Frame(root, width=900, bg="white")
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
    
    top_left_frame = tk.Frame(left_frame, bg="lightgray")
    top_left_frame.pack(side=tk.TOP, fill=tk.X, expand=False)

    bottom_left_frame = tk.Frame(left_frame, bg="white")
    bottom_left_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    notebook = ttk.Notebook(top_left_frame)
    notebook.pack(fill=tk.X, expand=False, padx=0, pady=(0, 0))
    tab_main = ttk.Frame(notebook)
    tab_add_employee = ttk.Frame(notebook)
    tab_delete_employee = ttk.Frame(notebook)
    tab_edit_employee = ttk.Frame(notebook)
    tab_change_password = ttk.Frame(notebook)
    notebook.add(tab_main, text="Chấm Công")
    notebook.add(tab_add_employee, text="Thêm Nhân Viên")
    notebook.add(tab_delete_employee, text="Xóa Nhân Viên")
    notebook.add(tab_edit_employee, text="Sửa Thông Tin")
    notebook.add(tab_change_password, text="Đổi Mật Khẩu")

    admin_password_hash = load_admin_password()
    if not admin_password_hash:
        print("[ERROR] Không thể tải mật khẩu admin. Chương trình sẽ thoát.")
        root.destroy()
        return

    is_admin_logged_in = {
        1: tk.BooleanVar(value=False),
        2: tk.BooleanVar(value=False),
        3: tk.BooleanVar(value=False)
    }

    empty_img = Image.new("RGB", (175, 175), color="gray")
    empty_imgtk = ImageTk.PhotoImage(empty_img)

    def create_login_frame(tab, tab_index, show_content_callback):
        login_frame = tk.Frame(tab)
        login_frame.pack(pady=20, fill=tk.BOTH, expand=True)

        tk.Label(login_frame, text="Mật khẩu quản trị:", font=("Arial", 12)).pack(pady=10)
        password_entry = tk.Entry(login_frame, font=("Arial", 12), show="*")
        password_entry.pack(pady=5)
        login_warning_label = tk.Label(login_frame, text="", fg="red", font=("Arial", 12))
        login_warning_label.pack(pady=5)

        def verify_login():
            password = password_entry.get().strip()
            if check_admin_password(password):
                is_admin_logged_in[tab_index].set(True)
                login_frame.destroy()
                show_content_callback()
                write_log("[TB] Đăng nhập admin thành công.")
            else:
                login_warning_label.config(text="Mật khẩu không đúng!")
                write_log("[ERROR] Đăng nhập admin thất bại.")

        tk.Button(login_frame, text="Đăng Nhập", font=("Arial", 12), command=verify_login).pack(pady=20)
        return login_frame

    def on_tab_change(event):
        selected_tab = notebook.index(notebook.select())
        if hasattr(root, "last_tab_index"):
            if root.last_tab_index in [1, 2, 3] and getattr(frs, "retrain_needed", False):
                threading.Thread(target=frs.train_model, daemon=True).start()
                frs.retrain_needed = False
        root.last_tab_index = selected_tab
        for tab_index in [1, 2, 3]:
            is_admin_logged_in[tab_index].set(False)
        if selected_tab in [1, 2, 3]:
            tab = {1: tab_add_employee, 2: tab_delete_employee, 3: tab_edit_employee}[selected_tab]
            for widget in tab.winfo_children():
                widget.destroy()
            create_login_frame(tab, selected_tab, {
                1: show_add_employee_content,
                2: show_delete_employee_content,
                3: show_edit_employee_content
            }[selected_tab])
        elif selected_tab == 4:
            show_change_password_content()

    notebook.bind("<<NotebookTabChanged>>", on_tab_change)

    toggle_button = tk.Button(tab_main, text="Bật/Tắt Chấm Công", font=("Arial", 12),
                             command=lambda: frs.toggle_recognition())
    toggle_button.pack(pady=(30, 30))

    info_frame = tk.Frame(tab_main, bg="white", relief=tk.RIDGE, bd=2)
    info_frame.pack(pady=(10, 10), padx=(20, 0), anchor="w")
 
    img_frame = tk.Frame(info_frame, width=175, height=175, bg="gray")
    img_frame.pack_propagate(False)
    img_frame.pack(side=tk.LEFT, padx=10, pady=10)
    user_img_label = tk.Label(img_frame, bg="gray")
    user_img_label.place(relx=0.5, rely=0.5, anchor="center")

    info_box_frame = tk.Frame(info_frame, bg="white")
    info_box_frame.pack(side=tk.LEFT, padx=12, pady=12)

    id_label1 = tk.Label(info_box_frame, text="  ID: ", anchor="w", font=("Arial", 14), bg="white", 
                         relief=tk.RIDGE, width=40, height=1)
    name_label1 = tk.Label(info_box_frame, text="  Họ tên: ", anchor="w", font=("Arial", 14), bg="white", 
                           relief=tk.RIDGE, width=40, height=1)
    position_label1 = tk.Label(info_box_frame, text="  Chức vụ: ", anchor="w", font=("Arial", 14), bg="white", 
                               relief=tk.RIDGE, width=40, height=1)
    time_label = tk.Label(info_box_frame, text="  Thời gian: ", anchor="w", font=("Arial", 14), bg="white", 
                          relief=tk.RIDGE, width=40, height=1)

    id_label1.pack(fill=tk.X, pady=0, ipady=8)
    name_label1.pack(fill=tk.X, pady=0, ipady=8)
    position_label1.pack(fill=tk.X, pady=0, ipady=8)
    time_label.pack(fill=tk.X, pady=0, ipady=8)

    def show_user_info(employee_id, name, position, time_str, face_img=None):
        id_label1.config(text=f"  ID: {employee_id}")
        name_label1.config(text=f"  Họ tên: {name}")
        position_label1.config(text=f"  Chức vụ: {position}")
        time_label.config(text=f"  Thời gian: {time_str}")

        if face_img is not None:
            img = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)).resize((175, 175))
            imgtk = ImageTk.PhotoImage(img)
            user_img_label.imgtk = imgtk
            user_img_label.config(image=imgtk)
        else:
            user_img_label.config(image="", bg="gray")

    def show_add_employee_content():
        id_label = tk.Label(tab_add_employee, text="ID:", font=("Arial", 12))
        id_entry = tk.Entry(tab_add_employee, font=("Arial", 12))    
        name_label = tk.Label(tab_add_employee, text="Họ tên:", font=("Arial", 12))
        name_entry = tk.Entry(tab_add_employee, font=("Arial", 12))
        position_label = tk.Label(tab_add_employee, text="Chức vụ:", font=("Arial", 12))
        position_entry = tk.Entry(tab_add_employee, font=("Arial", 12))
        warning_label = tk.Label(tab_add_employee, text="", fg="red", font=("Arial", 12))
        add_button = tk.Button(tab_add_employee, text="Xác nhận thêm", font=("Arial", 12),
                               command=lambda: start_collection(id_entry, name_entry, position_entry, frs, warning_label))
        id_label.pack(pady=5)
        id_entry.pack(pady=5) 
        name_label.pack(pady=5)
        name_entry.pack(pady=5)
        position_label.pack(pady=5)
        position_entry.pack(pady=5)
        warning_label.pack(pady=5)
        add_button.pack(pady=10)

    create_login_frame(tab_add_employee, 1, show_add_employee_content)

    def show_delete_employee_content():
        def show_delete_info():
            employee_id = delete_name_entry.get().strip()
            if not employee_id:
                delete_warning_label.config(text="Vui lòng nhập ID!", fg="red")
                delete_id_label.config(text="  ID: ")
                delete_name_label_info.config(text="  Họ tên: ")
                delete_position_label.config(text="  Chức vụ: ")
                delete_img_label.config(image=empty_imgtk)
                delete_img_label.imgtk = empty_imgtk
                delete_button.config(state=tk.DISABLED)
                return
            if not is_valid_id(employee_id):
                delete_warning_label.config(text="ID phải là số!", fg="red")
                delete_id_label.config(text="  ID: ")
                delete_name_label_info.config(text="  Họ tên: ")
                delete_position_label.config(text="  Chức vụ: ")
                delete_img_label.config(image=empty_imgtk)
                delete_img_label.imgtk = empty_imgtk
                delete_button.config(state=tk.DISABLED)
                return
                
            name, position = frs.get_employee_info(employee_id)

            if not name:
                delete_warning_label.config(text="Không tìm thấy nhân viên!", fg="red")
                delete_id_label.config(text="  ID: ")
                delete_name_label_info.config(text="  Họ tên: ")
                delete_position_label.config(text="  Chức vụ: ")
                delete_img_label.config(image=empty_imgtk)
                delete_img_label.imgtk = empty_imgtk
                delete_button.config(state=tk.DISABLED)
                return
            else:
                delete_warning_label.config(text="")
                delete_button.config(state=tk.NORMAL)

            delete_id_label.config(text=f"  ID: {employee_id}")
            delete_name_label_info.config(text=f"  Họ tên: {name}")
            delete_position_label.config(text=f"  Chức vụ: {position}")

            img_path = None
            person_dir = os.path.join(frs.processed_path, employee_id)
            if os.path.exists(person_dir):
                files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.jpg', '.png'))]
                if files:
                    img_path = os.path.join(person_dir, files[0])
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path).resize((175, 175))
                imgtk = ImageTk.PhotoImage(img)
                delete_img_label.imgtk = imgtk
                delete_img_label.config(image=imgtk)
            else:
                delete_img_label.config(image="", bg="gray")

        def reset_delete_info():
            delete_warning_label.config(text="")
            delete_id_label.config(text="  ID: ")
            delete_name_label_info.config(text="  Họ tên: ")
            delete_position_label.config(text="  Chức vụ: ")
            delete_img_label.config(image=empty_imgtk)
            delete_img_label.imgtk = empty_imgtk
            delete_name_entry.delete(0, tk.END)
            delete_button.config(state=tk.DISABLED)  

        delete_action_frame = tk.Frame(tab_delete_employee)
        delete_action_frame.pack(pady=(30, 0))

        delete_name_label = tk.Label(delete_action_frame, text="Nhập ID nhân viên:", font=("Arial", 12))
        delete_name_entry = tk.Entry(delete_action_frame, font=("Arial", 12))
        view_button = tk.Button(delete_action_frame, text="Xem", font=("Arial", 12), command=show_delete_info)
        delete_button = tk.Button(delete_action_frame, text="Xác nhận xóa", font=("Arial", 12),
                                command=lambda: delete_user(delete_name_entry, frs, delete_warning_label, reset_delete_info),
                                state=tk.DISABLED)

        delete_name_label.pack(side=tk.LEFT, padx=(8, 25))
        delete_name_entry.pack(side=tk.LEFT, padx=(8, 40))
        view_button.pack(side=tk.LEFT, padx=(8, 8))
        delete_button.pack(side=tk.LEFT, padx=(8, 8))

        delete_warning_label = tk.Label(tab_delete_employee, text="", fg="red", font=("Arial", 12))
        delete_warning_label.pack(fill=tk.X, pady=(0, 5))

        delete_info_frame = tk.Frame(tab_delete_employee, bg="white", relief=tk.RIDGE, bd=2)
        delete_info_frame.pack(pady=(0, 10))

        delete_img_frame = tk.Frame(delete_info_frame, bg="gray", width=175, height=175)
        delete_img_frame.pack_propagate(False)
        delete_img_frame.pack(side=tk.LEFT, padx=10, pady=10)

        delete_img_label = tk.Label(delete_img_frame, bg="gray", image=empty_imgtk, width=175, height=175)
        delete_img_label.imgtk = empty_imgtk
        delete_img_label.place(relx=0.5, rely=0.5, anchor="center")

        delete_box_frame = tk.Frame(delete_info_frame, bg="white")
        delete_box_frame.pack(side=tk.LEFT, padx=12, pady=12)

        delete_id_label = tk.Label(delete_box_frame, text="  ID: ", anchor="w", font=("Arial", 14), 
                                   bg="white", relief=tk.RIDGE, width=40, height=1)
        delete_name_label_info = tk.Label(delete_box_frame, text="  Họ tên: ", anchor="w", font=("Arial", 14), 
                                          bg="white", relief=tk.RIDGE, width=40, height=1)
        delete_position_label = tk.Label(delete_box_frame, text="  Chức vụ: ", anchor="w", font=("Arial", 14), 
                                         bg="white", relief=tk.RIDGE, width=40, height=1)

        delete_id_label.pack(fill=tk.X, pady=5, ipady=12)
        delete_name_label_info.pack(fill=tk.X, pady=5, ipady=12)
        delete_position_label.pack(fill=tk.X, pady=5, ipady=12)

    create_login_frame(tab_delete_employee, 2, show_delete_employee_content)

    def show_edit_employee_content():
        def show_edit_info():
            employee_id = edit_name_entry.get().strip()
            if not employee_id:
                edit_warning_label.config(text="Vui lòng nhập ID!", fg="red")
                edit_id_entry.delete(0, tk.END)
                edit_name_entry_info.delete(0, tk.END)
                edit_position_entry.delete(0, tk.END)
                edit_img_label.config(image=empty_imgtk)
                edit_img_label.imgtk = empty_imgtk
                return
            if not is_valid_id(employee_id):
                edit_warning_label.config(text="ID phải là số!", fg="red")
                edit_id_entry.delete(0, tk.END)
                edit_name_entry_info.delete(0, tk.END)
                edit_position_entry.delete(0, tk.END)
                edit_img_label.config(image=empty_imgtk)
                edit_img_label.imgtk = empty_imgtk
                return
                
            name, position = frs.get_employee_info(employee_id)

            if not name:
                edit_warning_label.config(text="Không tìm thấy nhân viên!", fg="red")
                edit_id_entry.delete(0, tk.END)
                edit_name_entry_info.delete(0, tk.END)
                edit_position_entry.delete(0, tk.END)
                edit_img_label.config(image=empty_imgtk)
                edit_img_label.imgtk = empty_imgtk
                return
            else:
                edit_warning_label.config(text="")

            edit_id_entry.delete(0, tk.END)
            edit_id_entry.insert(0, employee_id)
            edit_name_entry_info.delete(0, tk.END)
            edit_name_entry_info.insert(0, name)
            edit_position_entry.delete(0, tk.END)
            edit_position_entry.insert(0, position)

            img_path = None
            person_dir = os.path.join(frs.processed_path, employee_id)
            if os.path.exists(person_dir):
                files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.jpg', '.png'))]
                if files:
                    img_path = os.path.join(person_dir, files[0])
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path).resize((175, 175))
                imgtk = ImageTk.PhotoImage(img)
                edit_img_label.imgtk = imgtk
                edit_img_label.config(image=imgtk)
            else:
                edit_img_label.config(image=empty_imgtk, bg="gray")

        def reset_edit_info():
            edit_warning_label.config(text="")
            edit_id_entry.delete(0, tk.END)
            edit_name_entry_info.delete(0, tk.END)
            edit_position_entry.delete(0, tk.END)
            edit_name_entry.delete(0, tk.END)
            edit_img_label.config(image=empty_imgtk)
            edit_img_label.imgtk = empty_imgtk

        def edit_user(frs):
            old_employee_id = edit_name_entry.get().strip()
            new_employee_id = edit_id_entry.get().strip()
            new_name = edit_name_entry_info.get().strip()
            new_position = edit_position_entry.get().strip()
            
            name, position = frs.get_employee_info(old_employee_id)

            if not old_employee_id:
                edit_warning_label.config(text="Vui lòng nhập ID!", fg="red")
                return
            if not is_valid_id(old_employee_id) or not is_valid_id(new_employee_id):
                edit_warning_label.config(text="ID phải là số!", fg="red")
                return
            if not all([new_employee_id, new_name, new_position]):
                edit_warning_label.config(text="Vui lòng nhập đầy đủ thông tin!", fg="red")
                return

            if new_employee_id != old_employee_id and frs.check_employee_id_exists(new_employee_id):
                edit_warning_label.config(text="ID mới đã tồn tại!", fg="red")
                return

            if not frs.get_employee_info(old_employee_id):
                edit_warning_label.config(text="Không tìm thấy nhân viên!", fg="red")
                return

            try:
                df_employees = pd.read_csv(frs.EMPLOYEE_CSV)
                df_employees['employee_id'] = df_employees['employee_id'].astype(str)
                mask = df_employees['employee_id'] == old_employee_id
                if not mask.any():
                    edit_warning_label.config(text="Không tìm thấy nhân viên trong CSV!", fg="red")
                    return
                df_employees.loc[mask, ['employee_id', 'name', 'position']] = [new_employee_id, new_name, new_position]
                df_employees.to_csv(frs.EMPLOYEE_CSV, index=False)
                print(f"[TB] Đã cập nhật thông tin nhân viên {old_employee_id} trong employees.csv")

                df_timekeeping = pd.read_csv(frs.TIMEKEEPING_CSV)
                df_timekeeping['employee_id'] = df_timekeeping['employee_id'].astype(str)
                mask_timekeeping = df_timekeeping['employee_id'] == old_employee_id
                if mask_timekeeping.any():
                    df_timekeeping.loc[mask_timekeeping, ['employee_id', 'name', 'position']] = [new_employee_id, new_name, new_position]
                    df_timekeeping = df_timekeeping.sort_values('employee_id')
                    df_timekeeping.to_csv(frs.TIMEKEEPING_CSV, index=False)
                    print(f"[TB] Đã cập nhật thông tin nhân viên {old_employee_id} trong timekeeping.csv")

                # XÓA TOÀN BỘ ĐOẠN LIÊN QUAN ĐẾN MYSQL Ở ĐÂY

                if new_employee_id != old_employee_id:
                    old_raw_path = os.path.join(frs.raw_path, old_employee_id)
                    new_raw_path = os.path.join(frs.raw_path, new_employee_id)
                    old_processed_path = os.path.join(frs.processed_path, old_employee_id)
                    new_processed_path = os.path.join(frs.processed_path, new_employee_id)

                    if os.path.exists(old_raw_path):
                        if os.path.exists(new_raw_path):
                            for root, dirs, files in os.walk(new_raw_path, topdown=False):
                                for file in files:
                                    os.remove(os.path.join(root, file))
                                for dir in dirs:
                                    os.rmdir(os.path.join(root, dir))
                            os.rmdir(new_raw_path)
                            print(f"[TB] Đã xóa thư mục raw_path {new_employee_id} để thay thế")
                        os.rename(old_raw_path, new_raw_path)
                        print(f"[TB] Đã đổi tên thư mục raw_path từ {old_employee_id} thành {new_employee_id}")

                    if os.path.exists(old_processed_path):
                        if os.path.exists(new_processed_path):
                            for root, dirs, files in os.walk(new_processed_path, topdown=False):
                                for file in files:
                                    os.remove(os.path.join(root, file))
                                for dir in dirs:
                                    os.rmdir(os.path.join(root, dir))
                            os.rmdir(new_processed_path)
                            print(f"[TB] Đã xóa thư mục processed_path {new_employee_id} để thay thế")
                        os.rename(old_processed_path, new_processed_path)
                        print(f"[TB] Đã đổi tên thư mục processed_path từ {old_employee_id} thành {new_employee_id}")

                if old_employee_id in frs.employee_data:
                    del frs.employee_data[old_employee_id]
                frs.employee_data[new_employee_id] = {'name': new_name, 'position': new_position}

                # Kiểm tra nếu có thay đổi thông tin
                if (old_employee_id != new_employee_id) or (name != new_name) or (position != new_position):
                    frs.retrain_needed = True  
                    print(f"[TB] Đã đánh dấu cần huấn luyện lại mô hình sau khi sửa thông tin nhân viên {old_employee_id} thành {new_employee_id}")                
                else:
                    print(f"[TB] Không có thay đổi thông tin, không cần huấn luyện lại mô hình.")
                reset_edit_info()

            except Exception as e:
                edit_warning_label.config(text=f"Lỗi khi sửa thông tin: {str(e)}", fg="red")
                print(f"[ERROR] Lỗi khi sửa thông tin nhân viên: {e}")
        
        edit_action_frame = tk.Frame(tab_edit_employee)
        edit_action_frame.pack(pady=(30, 0))

        edit_name_label = tk.Label(edit_action_frame, text="Nhập ID nhân viên:", font=("Arial", 12))
        edit_name_entry = tk.Entry(edit_action_frame, font=("Arial", 12))
        edit_view_button = tk.Button(edit_action_frame, text="Xem", font=("Arial", 12), command=show_edit_info)
        edit_confirm_button = tk.Button(edit_action_frame, text="Xác nhận sửa", font=("Arial", 12),
                                        command=lambda: edit_user(frs))

        edit_name_label.pack(side=tk.LEFT, padx=(8, 25))
        edit_name_entry.pack(side=tk.LEFT, padx=(8, 40))
        edit_view_button.pack(side=tk.LEFT, padx=(8, 8))
        edit_confirm_button.pack(side=tk.LEFT, padx=(8, 8))

        edit_warning_label = tk.Label(tab_edit_employee, text="", fg="red", font=("Arial", 12))
        edit_warning_label.pack(fill=tk.X, pady=(0, 5))

        edit_info_frame = tk.Frame(tab_edit_employee, bg="white", relief=tk.RIDGE, bd=2)
        edit_info_frame.pack(pady=(0, 10))

        edit_img_frame = tk.Frame(edit_info_frame, bg="gray", width=175, height=175)
        edit_img_frame.pack_propagate(False)
        edit_img_frame.pack(side=tk.LEFT, padx=10, pady=10)

        edit_img_label = tk.Label(edit_img_frame, bg="gray", image=empty_imgtk, width=175, height=175)
        edit_img_label.imgtk = empty_imgtk
        edit_img_label.place(relx=0.5, rely=0.5, anchor="center")

        edit_box_frame = tk.Frame(edit_info_frame, bg="white")
        edit_box_frame.pack(side=tk.LEFT, padx=12, pady=12)

        edit_id_frame = tk.Frame(edit_box_frame, bg="white")
        edit_id_frame.pack(fill=tk.X, pady=5)
        edit_id_label_prefix = tk.Label(edit_id_frame, text="  ID: ", anchor="w", font=("Arial", 14), bg="white", width=10)
        edit_id_label_prefix.pack(side=tk.LEFT)
        edit_id_entry = tk.Entry(edit_id_frame, font=("Arial", 14), relief=tk.RIDGE, width=30)
        edit_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        edit_name_frame = tk.Frame(edit_box_frame, bg="white")
        edit_name_frame.pack(fill=tk.X, pady=5)
        edit_name_label_prefix = tk.Label(edit_name_frame, text="  Họ tên: ", anchor="w", font=("Arial", 14), bg="white", width=10)
        edit_name_label_prefix.pack(side=tk.LEFT)
        edit_name_entry_info = tk.Entry(edit_name_frame, font=("Arial", 14), relief=tk.RIDGE, width=30)
        edit_name_entry_info.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        edit_position_frame = tk.Frame(edit_box_frame, bg="white")
        edit_position_frame.pack(fill=tk.X, pady=5)
        edit_position_label_prefix = tk.Label(edit_position_frame, text="  Chức vụ: ", anchor="w", font=("Arial", 14), bg="white", width=10)
        edit_position_label_prefix.pack(side=tk.LEFT)
        edit_position_entry = tk.Entry(edit_position_frame, font=("Arial", 14), relief=tk.RIDGE, width=30)
        edit_position_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

    create_login_frame(tab_edit_employee, 3, show_edit_employee_content)

    log_text = tk.Text(bottom_left_frame, wrap=tk.WORD, font=("Arial", 10), bg="white", state=tk.DISABLED)
    log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def write_log(message):
        def insert_log():
            log_text.config(state=tk.NORMAL)
            if message.startswith("[CANH_BAO]") or message.startswith("[ERROR]"):
                log_text.insert("1.0", message + "\n", "error")
            else:
                log_text.insert("1.0", message + "\n", "normal")
            log_text.see("1.0")
            log_text.config(state=tk.DISABLED)
        # Đảm bảo luôn gọi từ main thread
        log_text.after(0, insert_log)

    log_text.tag_configure("error", foreground="red")
    log_text.tag_configure("normal", foreground="black")

    video_label = tk.Label(right_frame, bg="white")
    video_label.pack(fill=tk.X, expand=False, pady=(40, 0))
    
    realtime_clock_label = tk.Label(right_frame, font=("Arial", 24), bg="white", fg="black")
    realtime_clock_label.pack(pady=(20, 10))

    def update_realtime_clock():
        now = time.strftime("%H:%M:%S  %d/%m/%Y")
        realtime_clock_label.config(text=now)
        realtime_clock_label.after(1000, update_realtime_clock)
    update_realtime_clock()

    import builtins
    original_print = builtins.print
    def custom_print(*args, **kwargs):
        message = " ".join(map(str, args))
        write_log(message)
        original_print(*args, **kwargs)
    builtins.print = custom_print    
        
    frs = FaceRecognitionSystem(video_label)

    frs.show_user_info = show_user_info

    def start_collection(id_entry, name_entry, position_entry, frs, warning_label):
        if not is_admin_logged_in[1].get():
            messagebox.showerror("Lỗi", "Bạn cần đăng nhập với tư cách admin để thêm nhân viên!")
            return
        frs.new_person_id = id_entry.get().strip()
        frs.new_person_name = name_entry.get().strip()
        frs.new_person_position = position_entry.get().strip()
        if not all([frs.new_person_id, frs.new_person_name, frs.new_person_position]):
            warning_label.config(text="Vui lòng nhập đầy đủ thông tin!", fg="red")
            return
        if not is_valid_id(frs.new_person_id):
            warning_label.config(text="ID phải là số!", fg="red")
            return
        if frs.check_employee_id_exists(frs.new_person_id):
            warning_label.config(text=f"ID '{frs.new_person_id}' đã tồn tại!", fg="red")
            return
        raw_person_path = os.path.join(frs.raw_path, frs.new_person_id)
        processed_person_path = os.path.join(frs.processed_path, frs.new_person_id)
        if os.path.exists(raw_person_path) or os.path.exists(processed_person_path):
            warning_label.config(text="Dữ liệu khuôn mặt đã tồn tại!", fg="red")
            return
        threading.Thread(target=frs.collect_data, daemon=True).start()
        frs.retrain_needed = True
        print(f"[TB] Đã đánh dấu cần huấn luyện lại mô hình ")                
        warning_label.config(text="")
        id_entry.delete(0, tk.END)
        name_entry.delete(0, tk.END)
        position_entry.delete(0, tk.END)

    def delete_user(id_entry, frs, delete_warning_label, reset_delete_info_func):
        if not is_admin_logged_in[2].get():
            messagebox.showerror("Lỗi", "Bạn cần đăng nhập với tư cách admin để xóa nhân viên!")
            return
        employee_id = id_entry.get().strip()
        if not employee_id:
            delete_warning_label.config(text="Vui lòng nhập ID!", fg="red")
            return
        if not is_valid_id(employee_id):
            delete_warning_label.config(text="ID phải là số!", fg="red")
            return
        raw_person_path = os.path.join(frs.raw_path, employee_id)
        processed_person_path = os.path.join(frs.processed_path, employee_id)
        if not os.path.exists(raw_person_path) and not os.path.exists(processed_person_path):
            delete_warning_label.config(text="Không tìm thấy nhân viên!", fg="red")
            return
        threading.Thread(target=lambda: frs.delete_user_data(employee_id), daemon=True).start()
        frs.retrain_needed = True 
        print(f"[TB] Đã đánh dấu cần huấn luyện lại mô hình ")                
        reset_delete_info_func()

    def show_change_password_content():
        for widget in tab_change_password.winfo_children():
            widget.destroy()

        change_pw_frame = tk.Frame(tab_change_password)
        change_pw_frame.pack(fill=tk.BOTH, expand=True, pady=50)

        old_pw_label = tk.Label(change_pw_frame, text="Mật khẩu cũ:", font=("Arial", 12))
        old_pw_entry = tk.Entry(change_pw_frame, font=("Arial", 12), show="*")
        new_pw_label = tk.Label(change_pw_frame, text="Mật khẩu mới:", font=("Arial", 12))
        new_pw_entry = tk.Entry(change_pw_frame, font=("Arial", 12), show="*")
        confirm_pw_label = tk.Label(change_pw_frame, text="Nhập lại mật khẩu mới:", font=("Arial", 12))
        confirm_pw_entry = tk.Entry(change_pw_frame, font=("Arial", 12), show="*")
        send_otp_button = tk.Button(change_pw_frame, text="Gửi mã OTP", font=("Arial", 12))
        change_pw_status = tk.Label(change_pw_frame, text="", font=("Arial", 10), fg="red")

        otp_label = tk.Label(change_pw_frame, text="Nhập mã OTP:", font=("Arial", 12))
        otp_entry = tk.Entry(change_pw_frame, font=("Arial", 12))
        verify_otp_button = tk.Button(change_pw_frame, text="Xác nhận đổi mật khẩu", font=("Arial", 12))
        otp_label.pack_forget()
        otp_entry.pack_forget()
        verify_otp_button.pack_forget()

        old_pw_label.pack(pady=5)
        old_pw_entry.pack(pady=5)
        new_pw_label.pack(pady=5)
        new_pw_entry.pack(pady=5)
        confirm_pw_label.pack(pady=5)
        confirm_pw_entry.pack(pady=5)
        send_otp_button.pack(pady=10)
        change_pw_status.pack(pady=5)

        otp_code = [None]

        def send_otp():
            old_pw = old_pw_entry.get().strip()
            new_pw = new_pw_entry.get().strip()
            confirm_pw = confirm_pw_entry.get().strip()
            if not old_pw or not new_pw or not confirm_pw:
                change_pw_status.config(text="Vui lòng nhập đầy đủ thông tin!", fg="red")
                return
            if new_pw != confirm_pw:
                change_pw_status.config(text="Mật khẩu mới không khớp!", fg="red")
                return
            if len(new_pw) < 4:
                change_pw_status.config(text="Mật khẩu mới phải có ít nhất 4 ký tự!", fg="red")
                return
            if not check_admin_password(old_pw):
                change_pw_status.config(text="Mật khẩu cũ không đúng!", fg="red")
                return
            otp = str(random.randint(100000, 999999))
            otp_code[0] = otp
            try:
                with open('Database/email_config.json', 'r') as f:
                    config = json.load(f)
                to_email = config["email"]
            except Exception as e:
                change_pw_status.config(text=f"Lỗi đọc email: {e}", fg="red")
                return
            if send_otp_email(otp, to_email):
                change_pw_status.config(text="Đã gửi mã OTP tới email admin. Vui lòng kiểm tra và nhập mã OTP.", fg="green")
                old_pw_label.pack_forget()
                old_pw_entry.pack_forget()
                new_pw_label.pack_forget()
                new_pw_entry.pack_forget()
                confirm_pw_label.pack_forget()
                confirm_pw_entry.pack_forget()
                send_otp_button.pack_forget()
                otp_label.pack(pady=5)
                otp_entry.pack(pady=5)
                verify_otp_button.pack(pady=10)
                otp_entry.focus_set()
            else:
                change_pw_status.config(text="Không gửi được mã OTP. Kiểm tra cấu hình email.", fg="red")

        def verify_otp():
            user_otp = otp_entry.get().strip()
            if user_otp == otp_code[0]:
                hashed_new = hashlib.sha256(new_pw_entry.get().strip().encode('utf-8')).hexdigest()
                try:
                    with open('Database/admin_password.json', 'w') as f:
                        json.dump({"password": hashed_new}, f)
                    change_pw_status.config(text="Đổi mật khẩu thành công!", fg="green")
                    otp_entry.delete(0, tk.END)
                    verify_otp_button.config(state=tk.DISABLED)
                    otp_label.pack_forget()
                    otp_entry.pack_forget()
                    verify_otp_button.pack_forget()
                    old_pw_entry.delete(0, tk.END)
                    new_pw_entry.delete(0, tk.END)
                    confirm_pw_entry.delete(0, tk.END)
                    old_pw_label.pack(pady=5)
                    old_pw_entry.pack(pady=5)
                    new_pw_label.pack(pady=5)
                    new_pw_entry.pack(pady=5)
                    confirm_pw_label.pack(pady=5)
                    confirm_pw_entry.pack(pady=5)
                    send_otp_button.pack(pady=10)
                except Exception as e:
                    change_pw_status.config(text=f"Lỗi khi lưu: {e}", fg="red")
            else:
                change_pw_status.config(text="Mã OTP không đúng!", fg="red")

        send_otp_button.config(command=send_otp)
        verify_otp_button.config(command=verify_otp)

    show_change_password_content()

    def on_closing():
        if 'frs' in globals():
            frs.close_db_connection()
        if hasattr(frs, 'cap') and frs.cap is not None:
            frs.cap.release()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    from PIL import Image, ImageTk
    start_gui()