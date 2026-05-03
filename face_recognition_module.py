"""
face_recognition_module.py
Week 12 - Smart Home Project

Sources used:
  [1] dev.to - Simple Face Recognizing System using python and openCV
      https://dev.to/pranay749254/simple-face-recognizing-system-using-python-and-opencv
  [2] OpenCV docs - Face Recognition with OpenCV (LBPH)
      https://docs.opencv.org/4.x/da/d60/tutorial_face_main.html
  [3] Claude AI - helped connect parts together for smart home use

Install:
    pip install opencv-contrib-python numpy requests python-dotenv
"""

import cv2
import os
import sys
import time
import glob
import sqlite3
import numpy as np
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# settings
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DB_PATH          = "smart_home.db"
FACES_FOLDER     = "known_faces"   # put photos here, name file after person e.g. John.jpg
THRESHOLD        = 70.0            # [2] LBPH confidence score - lower = more similar face
COOLDOWN         = 30              # seconds before we send another alert for same person
CAMERA           = 0              # [1] 0 means default webcam - same as dev.to

# [1] dev.to line: faceDetect = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
# [2] opencv docs also uses this same xml file for detecting faces
CASCADE = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

os.makedirs(FACES_FOLDER, exist_ok=True)


# ==============================
# send telegram alert
# my own addition for smart home notifications
# ==============================
def send_telegram(text, photo_path=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[face] telegram not set up")
        return
    try:
        if photo_path and os.path.exists(photo_path):
            # send photo with caption
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open(photo_path, "rb") as f:
                requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": text}, files={"photo": f}, timeout=10)
        else:
            # send text only
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"[face] telegram error: {e}")


# ==============================
# save event to database
# [1] dev.to line: conn = sqlite3.connect("FaceBase.db")  <- same idea, different db name
# [1] dev.to line: conn.close()  <- same way to close connection
# my own addition - storing events instead of face data
# ==============================
def save_to_db(name, event, confidence=None):
    try:
        conn = sqlite3.connect(DB_PATH)   # [1] same pattern as dev.to
        conn.execute("CREATE TABLE IF NOT EXISTS face_events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, name TEXT, event TEXT, confidence REAL)")
        conn.execute("INSERT INTO face_events (timestamp, name, event, confidence) VALUES (?,?,?,?)",
                     (datetime.now().isoformat(), name, event, confidence))
        conn.commit()
        conn.close()   # [1] dev.to line: conn.close()
    except Exception as e:
        print(f"[face] db error: {e}")


# ==============================
# load face photos and train the model
# [1] dev.to line: faceDetect = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
# [1] dev.to line: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# [1] dev.to line: faces = faceDetect.detectMultiScale(gray, 1.3, 5)
# [2] opencv docs: model = LBPHFaceRecognizer::create(); model->train(images, labels)
# ==============================
def train_model():
    detector = cv2.CascadeClassifier(CASCADE)   # [1] same as dev.to faceDetect line
    images, labels, names = [], [], {}
    label_id = 0

    all_files = glob.glob(f"{FACES_FOLDER}/*.jpg") + glob.glob(f"{FACES_FOLDER}/*.png")

    if not all_files:
        print(f"[face] no photos found in {FACES_FOLDER}/")
        return None, {}

    for filepath in all_files:
        person_name = os.path.splitext(os.path.basename(filepath))[0]  # filename = person name
        img = cv2.imread(filepath)
        if img is None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)   # [1] dev.to line: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = detector.detectMultiScale(gray, 1.1, 5)   # [1] dev.to line: faces = faceDetect.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0:
            print(f"[face] no face found in {filepath}, skipping")
            continue

        x, y, w, h = faces[0]
        face_crop = cv2.resize(gray[y:y+h, x:x+w], (200, 200))   # [2] opencv docs: resize face region before training

        if person_name not in names.values():
            names[label_id] = person_name
            pid = label_id
            label_id += 1
        else:
            pid = [k for k, v in names.items() if v == person_name][0]

        images.append(face_crop)
        labels.append(pid)
        print(f"[face] loaded {person_name}")

    if not images:
        return None, {}

    # [1] dev.to line: recognizer.train(faces, IDs)
    # [2] opencv docs: model->train(images, labels)
    model = cv2.face.LBPHFaceRecognizer_create()   # [2] opencv docs: LBPHFaceRecognizer::create()
    model.train(images, np.array(labels))
    print(f"[face] trained on {len(names)} person(s)")
    return model, names


# ==============================
# enroll a new person via webcam
# [1] dev.to line: cam = cv2.VideoCapture(0)
# [1] dev.to line: ret, img = cam.read()
# [1] dev.to line: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# [1] dev.to line: faces = faceDetect.detectMultiScale(gray, 1.3, 5)
# [1] dev.to line: cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)
# [1] dev.to line: cv2.imshow("Face", img)
# [1] dev.to line: cv2.waitKey(1)
# [1] dev.to line: cam.release()
# [1] dev.to line: cv2.destroyAllWindows()
# ==============================
def enroll(name):
    detector = cv2.CascadeClassifier(CASCADE)   # [1] same as dev.to faceDetect line
    cap = cv2.VideoCapture(CAMERA)              # [1] dev.to line: cam = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[face] cant open camera")
        return

    print(f"enrolling {name} - press SPACE to capture, Q to quit")
    photos = []

    while len(photos) < 5:
        ok, frame = cap.read()   # [1] dev.to line: ret, img = cam.read()
        if not ok:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)          # [1] dev.to: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.1, 5)         # [1] dev.to: faces = faceDetect.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)   # [1] dev.to: cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)

        cv2.putText(frame, f"{len(photos)}/5 - SPACE to capture", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.imshow("Enroll", frame)   # [1] dev.to line: cv2.imshow("Face", img)

        key = cv2.waitKey(1) & 0xFF   # [1] dev.to line: cv2.waitKey(1) - added & 0xFF for safety
        if key == ord(" ") and len(faces) > 0:
            x, y, w, h = faces[0]
            photos.append(frame[y:y+h, x:x+w].copy())
            print(f"  captured {len(photos)}/5")
        elif key == ord("q"):
            break

    cap.release()              # [1] dev.to line: cam.release()
    cv2.destroyAllWindows()    # [1] dev.to line: cv2.destroyAllWindows()

    if photos:
        path = os.path.join(FACES_FOLDER, f"{name}.jpg")
        cv2.imwrite(path, photos[0])
        print(f"saved! restart the script to recognise {name}")
    else:
        print("no photos taken")


# ==============================
# main camera loop - runs forever, detects and alerts
# [1] dev.to line: cam = cv2.VideoCapture(0)
# [1] dev.to line: ret, img = cam.read()
# [1] dev.to line: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# [1] dev.to line: faces = faceDetect.detectMultiScale(gray, 1.3, 5)
# [1] dev.to line: for (x, y, w, h) in faces:
# [1] dev.to line: cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)
# [1] dev.to line: id, conf = rec.predict(gray[y:y+h, x:x+w])
# [1] dev.to line: cv2.imshow("Face", img)
# [1] dev.to line: if cv2.waitKey(1) == ord('q'): break
# [1] dev.to line: cam.release()
# [1] dev.to line: cv2.destroyAllWindows()
# [2] opencv docs: model->predict(face, predictedLabel, confidence) - confidence threshold explained
# ==============================
def run(show_window=False):
    save_to_db("system", "START")

    detector = cv2.CascadeClassifier(CASCADE)   # [1] same as dev.to faceDetect line
    model, names = train_model()

    cap = cv2.VideoCapture(CAMERA)   # [1] dev.to line: cam = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[face] cant open camera")
        sys.exit(1)

    print("[face] running... press Q to stop")
    last_alert = {}   # my own - tracks cooldown per person so we dont spam telegram
    frame_num = 0

    try:
        while True:
            ok, frame = cap.read()   # [1] dev.to line: ret, img = cam.read()
            if not ok:
                time.sleep(0.5)
                continue

            frame_num += 1
            if frame_num % 3 != 0:   # my own - skip 2 out of 3 frames to save CPU
                if show_window:
                    cv2.imshow("Face Recognition", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)                    # [1] dev.to: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.1, 5, minSize=(80, 80)) # [1] dev.to: faces = faceDetect.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:   # [1] dev.to line: for (x, y, w, h) in faces:
                now = time.time()
                face_crop = cv2.resize(gray[y:y+h, x:x+w], (200, 200))   # [2] opencv docs: crop and resize before predicting

                if model is not None:
                    # [1] dev.to line: id, conf = rec.predict(gray[y:y+h, x:x+w])
                    # [2] opencv docs: model->predict(face, predictedLabel, confidence)
                    label_id, confidence = model.predict(face_crop)

                    if confidence < THRESHOLD:   # [2] opencv docs explain this - lower confidence = better match
                        person = names.get(label_id, "Unknown")
                        color = (0, 255, 0)   # green box = known person
                        known = True
                    else:
                        person = "Stranger"
                        color = (0, 0, 255)   # red box = unknown person
                        known = False
                else:
                    person, confidence, color, known = "Unknown", 999, (255, 165, 0), False

                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)   # [1] dev.to: cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)
                cv2.putText(frame, f"{person} ({confidence:.0f})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                # my own - skip if we already alerted for this person recently
                if now - last_alert.get(person, 0) < COOLDOWN:
                    continue
                last_alert[person] = now

                # my own - send telegram alerts for smart home
                if known:
                    msg = f"Welcome home {person}! ({datetime.now().strftime('%H:%M:%S')})"
                    print(f"[face] {msg}")
                    save_to_db(person, "UNLOCKED", confidence)
                    send_telegram(msg)
                else:
                    msg = f"Unknown person at door! {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    print(f"[face] stranger! confidence={confidence:.0f}")
                    save_to_db("Stranger", "ALERT", confidence)
                    snap = f"stranger_{int(now)}.jpg"
                    cv2.imwrite(snap, frame)
                    send_telegram(msg, snap)   # my own - sends photo of stranger to telegram

            if show_window:
                cv2.imshow("Face Recognition", frame)   # [1] dev.to line: cv2.imshow("Face", img)
                if cv2.waitKey(1) & 0xFF == ord("q"):   # [1] dev.to: if cv2.waitKey(1) == ord('q'): break
                    break

    except KeyboardInterrupt:
        print("[face] stopped")
    finally:
        cap.release()            # [1] dev.to line: cam.release()
        cv2.destroyAllWindows()  # [1] dev.to line: cv2.destroyAllWindows()


# ==============================
# start
# ==============================
if __name__ == "__main__":
    if "--enroll" in sys.argv:
        i = sys.argv.index("--enroll")
        if i + 1 >= len(sys.argv):
            print("usage: python face_recognition_module.py --enroll YourName")
            sys.exit(1)
        enroll(sys.argv[i + 1])
    else:
        try:
            cv2.face.LBPHFaceRecognizer_create   # [2] this only exists in opencv-contrib, not base opencv
        except AttributeError:
            print("run: pip install opencv-contrib-python")
            sys.exit(1)
        run(show_window="--show" in sys.argv)
