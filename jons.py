from flask import Flask, request, jsonify, send_file
from flasgger import Swagger
import json
import jwt
import os
import uuid
from datetime import datetime, timedelta
import re
from faker import Faker
import random

app = Flask(__name__)
swagger = Swagger(app)
fake = Faker()

SECRET_KEY = "hkBxrbZ9Td4QEwgRewV6gZSVH4q78vBia4GBYuqd09SsiMsIjH"
TOKEN_EXPIRATION_SECONDS = 86400
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_value(value):
    try:
        value = json.loads(value.strip())

        if isinstance(value, (dict, list)):
            return value
        elif isinstance(value, (str, int, bool)):
            return value
        else:
            raise ValueError(f"Unsupported data type: {type(value)}")

    except (json.JSONDecodeError, ValueError):
        return value.strip()

def generate_dummy_data(schema, num_outputs):
    dummy_data_list = []

    if isinstance(schema, dict):
        for _ in range(num_outputs):
            dummy_data = {}

            for key, value in schema.items():
                value = process_value(json.dumps(value))

                if isinstance(value, dict):
                    dummy_data[key] = generate_dummy_data(value, 1)[0]
                elif isinstance(value, list):
                    dummy_data[key] = [generate_dummy_data(item, 1)[0] for item in value]
                else:
                    dummy_data[key] = generate_data(value)

            dummy_data_list.append(dummy_data)

    elif isinstance(schema, (str, int, bool)):
        for _ in range(num_outputs):
            dummy_data_list.append(generate_data(schema))

    else:
        raise ValueError(f"Unsupported schema type: {type(schema)}")

    return dummy_data_list

def generate_data(data):
    if isinstance(data, str):
        return fake.word()
    elif isinstance(data, int):
        return random.randint(10 ** 11, 10 ** 15)
    elif isinstance(data, bool):
        return random.choice([True, False])
    else:
        raise ValueError(f"Unsupported data type: {type(data)}")

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

def is_valid_email(email):
    pattern = r'^\S+@\S+\.\S+$'
    return re.match(pattern, email)

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
        "token": token  # Remove the decode('utf-8') call here
    }

    return jsonify(user_info)

@app.route('/generate_dummy_data', methods=['POST'])
def generate_dummy_data_api():
    """
    Endpoint to generate dummy data based on a JSON schema.

    ---
    parameters:
      - name: file
        in: formData
        type: file
        required: true
      - name: num_outputs
        in: formData
        type: integer
        required: true
      - name: Authorization
        in: header
        type: string
        required: true
    responses:
      200:
        description: File uploaded successfully.
        schema:
          type: object
    """
    token = request.headers.get('Authorization')
    print("Received Token:", token)  # Print out received token for debugging
    if not token or not verify_token(token):
        return jsonify({"error": "Invalid or expired token."}), 401
    uploaded_file = request.files['file']

    if not uploaded_file or not allowed_file(uploaded_file.filename):
        return jsonify({"error": "Invalid file or file extension."})

    schema_content = uploaded_file.read()
    schema = json.loads(schema_content.decode('utf-8'))

    num_outputs = int(request.form['num_outputs'])

    dummy_data = generate_dummy_data(schema, num_outputs)

    return jsonify(dummy_data)  # generates dummy data

if __name__ == '__main__':
    app.run(debug=True)
