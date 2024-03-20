from pydub import AudioSegment
import os
from datetime import datetime, timedelta
import jwt
import re
import uuid
import speech_recognition as sr
from flask import Flask, request, jsonify, send_file
from flasgger import Swagger
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
swagger = Swagger(app)

SECRET_KEY = "hkBxrbZ9Td4QEwgRewV6gZSVH4q78vBia4GBYuqd09SsiMsIjH"
TOKEN_EXPIRATION_SECONDS = 86400
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'aac', 'aiff', 'alac', 'amr', 'flac', 'm4a', 'mp3', 'ogg', 'wav', 'wma', '3gp', 'avi', 'flv', 'mkv', 'mov', 'mp4', 'ogv', 'webm', 'wmv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_email(email):
    pattern = r'^\S+@\S+\.\S+$'
    return re.match(pattern, email)
def generate_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.utcnow() + timedelta(seconds=TOKEN_EXPIRATION_SECONDS)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    print("Generated Token:", token)
    return token

def verify_token(token):
    try:
        print("Verifying token:", token)
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        print("Decoded Payload:", payload)
        return payload
    except jwt.ExpiredSignatureError as e:
        print("Token has expired. Error:", e)
        return None
    except jwt.InvalidTokenError as e:
        print("Invalid token. Error:", e)
        return None

def transcribe_audio(audio_chunk):
    r = sr.Recognizer()
    with sr.AudioFile(audio_chunk) as source:
        audio_listened = r.listen(source)
    try:
        rec = r.recognize_google(audio_listened)
        return rec
    except sr.UnknownValueError:
        return " "
    except sr.RequestError as e:
        return "Could not get the result; check your internet"

def process_and_save_chunk(chunk, output_format):
    transcription = transcribe_audio(chunk)
    with open("the_audio.txt", "a") as text_file:
        text_file.write(transcription + '\n')
    os.remove(chunk)  # Delete the temporary chunk file

def process_audio(filename, output_format):
    myaudio = AudioSegment.from_file(filename)
    duration_ms = len(myaudio)
    chunk_duration_ms = 30 * 1000  # 30 seconds in milliseconds
    subchunk_duration_ms = 10 * 1000  # 10 seconds in milliseconds

    try:
        os.makedirs("chunked")
    except:
        pass

    chunks = []
    for start in range(0, duration_ms, chunk_duration_ms):
        end = min(start + chunk_duration_ms, duration_ms)
        chunk = myaudio[start:end]

        # Split each chunk into sub-chunks
        subchunks = []
        for substart in range(0, len(chunk), subchunk_duration_ms):
            subend = min(substart + subchunk_duration_ms, len(chunk))
            subchunk = chunk[substart:subend]
            subchunk_name = f'./chunked/{os.path.basename(filename)}_{start}-{end}_sub_{substart}-{subend}.{output_format}'
            subchunk.export(subchunk_name, format=output_format)
            subchunks.append(subchunk_name)

        chunks.extend(subchunks)

    with ThreadPoolExecutor() as executor:
        executor.map(process_and_save_chunk, chunks, [output_format] * len(chunks))

    return jsonify({'message': 'Transcription completed and saved to the_audio.txt'}), 200

@app.route('/collect_user_info', methods=['POST'])
def collect_user_info():
    """
    Endpoint to collect user information and generate a token.
    ---
    parameters:
      - name: first_name
        in: formData
        type: string
        required: true
      - name: last_name
        in: formData
        type: string
        required: true
      - name: email
        in: formData
        type: string
        required: true
    responses:
      200:
        description: User information collected successfully.
        schema:
          type: object
    """
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format."})

    # Generate a random user ID
    user_id = str(uuid.uuid4())  # Generate a UUID4 user ID

    token = generate_token(user_id)

    user_info = {
        "user_id": user_id,  # Include user ID in the response
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "token": token
    }

    return jsonify(user_info)

@app.route('/upload', methods=['POST'])
def upload_audio():
    """
    Upload an audio file and save transcriptions to "the_audio.txt".

    ---
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: The audio file to transcribe (must be one of the supported formats).
      - name: output_format
        in: formData
        type: string
        required: false
        default: "wav"
        description: "The desired output format for audio chunks."
      - name: Authorization
        in: header
        type: string
        required: true
        description: JWT token for user authorization.
    responses:
      200:
        description: The audio file transcribed successfully.
        examples:
          message: "Transcription completed and saved to the_audio.txt"
      400:
        description: Error message if the request is invalid.
      401:
        description: Unauthorized access if the JWT token is missing or invalid.
    """
    token = request.headers.get('Authorization')
    print("Received Token:", token)  # Print out received token for debugging
    if not token or not verify_token(token):
        return jsonify({"error": "Invalid or expired token."}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'Upload failed'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    output_format = request.form.get('output_format', 'wav')

    if file and allowed_file(file.filename):
        file.save(file.filename)
        audio_file_path = file.filename
        return process_audio(audio_file_path, output_format)
    else:
        return jsonify({'message': 'Invalid File or File Extension. Kindly upload a valid file'}), 400


if __name__ == '__main__':
    app.run(debug=True)

