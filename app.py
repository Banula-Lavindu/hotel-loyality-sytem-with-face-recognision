from flask import Flask, render_template, request, redirect, url_for, session, Response
import cv2
import dlib
import face_recognition
import database
import numpy as np
import base64
import pickle

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load pre-trained face detection models
detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# Initialize the database
database.create_tables()

# Function to generate video frames for detection and recognition
def generate_frames(mode='recognition'):
    camera = cv2.VideoCapture(2)
    
    while True:
        success, frame = camera.read()
        if not success:
            break

        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)

        if mode == 'recognition':
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Draw bounding box around the face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

                # Compare face encodings with known encodings
                user_id = database.get_user_by_face(face_encoding)
                if user_id:
                    user = database.get_user_by_id(user_id)
                    name = user[1]
                    visits = user[4]
                    rewards = user[5]
                    cv2.putText(frame, f"{name}", (left + 6, top - 36), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(frame, f"Visits: {visits}", (left + 6, top - 6), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(frame, f"Rewards: {rewards}", (left + 6, top + 24), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    database.increment_visits(user_id)
                else:
                    cv2.putText(frame, "Unknown", (left + 6, top - 6), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            # Draw bounding boxes for registration mode without recognition
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # Yield the frame in byte format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    users = database.get_users()
    return render_template('dashboard.html', users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        face_encodings = []

        for i in range(10):  # Capture 10 images from different angles
            image_data = request.form.get(f'image_{i}')
            if image_data:
                image_data = image_data.split(',')[1]
                image = np.frombuffer(base64.b64decode(image_data), np.uint8)
                frame = cv2.imdecode(image, cv2.IMREAD_COLOR)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                if face_locations:
                    face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
                    face_encodings.append(face_encoding)
        
        if face_encodings:
            avg_face_encoding = np.mean(face_encodings, axis=0)  # Average the encodings
            database.add_user(name, email, avg_face_encoding)
            return redirect(url_for('dashboard'))
        else:
            return "No face detected, please try again"

    return render_template('register.html')

@app.route('/live_recognition')
def live_recognition():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('live_recognition.html')

@app.route('/video_feed')
def video_feed():
    mode = request.args.get('mode', 'recognition')
    try:
        return Response(generate_frames(mode=mode), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        return str(e)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if database.verify_credential(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials, please try again"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        database.add_credential(username, password)
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/delete_user/<name>')
def delete_user(name):
    database.delete_user_by_name(name)
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
