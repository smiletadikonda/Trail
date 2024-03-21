from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import jwt
from functools import wraps

app = Flask(__name__)

# Dummy secret key for JWT encoding/decoding
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Dummy database for user information
users = []


# JWT token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.form.get('token')

        if not token:
            return jsonify({'message': 'Token is missing!'}), 403

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # If token is valid, proceed with the decorated function
            return f(*args, **kwargs)
        except:
            return jsonify({'message': 'Token is invalid!'}), 403

    return decorated


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/user_info', methods=['GET', 'POST'])
def user_info():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']

        # Check if the email is unique
        if any(user['email'] == email for user in users):
            return 'Email already exists! Please try again with a different email.'

        # Generate JWT token
        token = jwt.encode({'email': email}, app.config['SECRET_KEY'], algorithm="HS256")

        return render_template('token_verification.html', token=token)

    return render_template('user_info.html')


@app.route('/verify_token', methods=['POST'])
@token_required
def verify_token():
    # If token verification is successful, redirect to the upload file page
    return redirect(url_for('upload_file'))


@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Get the uploaded file
        uploaded_file = request.files['file']

        # Save the file to the uploads folder
        file_path = os.path.join('uploads', uploaded_file.filename)
        uploaded_file.save(file_path)

        # Process the file (dummy processing)
        # For now, let's just create an output file with a message
        output_file_path = os.path.join('uploads', 'output.txt')
        with open(output_file_path, 'w') as output_file:
            output_file.write('File uploaded successfully!')

        return redirect(url_for('download_file'))

    return render_template('upload_file.html')


@app.route('/download_file')
def download_file():
    # Provide a link to download the output file
    return f'<a href="/static/output.txt" download>Download Output File</a>'


if __name__ == '__main__':
    app.run(debug=True)
