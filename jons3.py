import os
from flask import Flask, request, jsonify, send_file
import json
from faker import Faker
import random
import csv
from flasgger import Swagger
from io import StringIO
from tempfile import NamedTemporaryFile
from datetime import date

app = Flask(__name__)
swagger = Swagger(app)

fake = Faker()

ALLOWED_EXTENSIONS = {'json'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_data(data_type, key):
    if key.lower() == 'last4ofsocial':
        return str(random.randint(1000, 9999))
    elif key.lower() == 'zipcode':
        return str(random.randint(10000, 99999))
    elif key.lower() == 'vacationcarryoverhours':
        return str(random.randint(300, 500))
    elif key.lower() == 'monthofservice':
        return str(random.randint(1, 12))
    elif key.lower() == 'payeeid':
        return str(random.randint(100000000, 999999999))
    elif key.lower() == 'sicktimeaccrualrate':
        return str(random.randint(10, 99))
    elif key.lower() == 'dob' or key.lower() == 'dateofbirth':
        return fake.date_of_birth().strftime('%Y-%m-%d')
    elif key.lower() == 'userid':
        return str(random.randint(100000000, 999999999))  # 9 digit number
    elif key.lower() == 'phonenumber':
        # Generating random phone number using the provided pattern
        return fake.phone_number()
    elif data_type == 'string':
        return fake.word()
    elif data_type == 'number':
        return str(random.randint(10 ** 11, 10 ** 15))
    elif data_type == 'boolean':
        return str(random.choice([True, False]))
    elif data_type == 'date':
        return fake.date_of_birth().strftime('%Y-%m-%d')
    else:
        return None



def generate_dummy_data(schema, num_outputs):
    dummy_data_list = []

    properties = schema.get('properties', {})
    if not properties:
        # If properties are not defined, generate data based on keys in the JSON object
        keys = list(schema.keys())
        for _ in range(num_outputs):
            dummy_data = {}
            for key in keys:
                data_type = schema[key].get('type', 'string')
                dummy_data[key] = generate_data(data_type, key)
            dummy_data_list.append(dummy_data)
    else:
        for _ in range(num_outputs):
            dummy_data = {}
            for key, prop in properties.items():
                data_type = prop.get('type', 'string')
                dummy_data[key] = generate_data(data_type, key)
            dummy_data_list.append(dummy_data)

    return dummy_data_list

def generate_json_output(data):
    return json.dumps(data, indent=4)


def generate_delimited_output(data, delimiter=','):
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter=delimiter)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def generate_txt_output(data):
    output = StringIO()
    for item in data:
        output.write(json.dumps(item) + '\n')
    return output.getvalue()



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

    responses:
      200:
        description: Dummy data generated successfully.
        schema:
          type: object
    """
    uploaded_file = request.files['file']

    if not uploaded_file or not allowed_file(uploaded_file.filename):
        return jsonify({"error": "Invalid file or file extension."})

    schema_content = uploaded_file.read()
    schema = json.loads(schema_content.decode('utf-8'))

    num_outputs = int(request.form['num_outputs'])

    dummy_data = generate_dummy_data(schema, num_outputs)

    # Save generated data to files in different formats
    with open("generated_dummy_data.json", "w") as json_file:
        json.dump(dummy_data, json_file, indent=4)

    with open("generated_dummy_data.delimiter", "w") as delimiter_file:
        delimiter_char = request.form.get('delimiter_char', ',')  # Default delimiter is comma
        delimiter_file.write(generate_delimited_output(dummy_data, delimiter=delimiter_char))

    with open("generated_dummy_data.text", "w") as text_file:
        text_file.write(generate_txt_output(dummy_data))

    return jsonify(dummy_data)  # generates dummy data


@app.route('/download_dummy_data', methods=['GET'])
def download_dummy_data():
    """
    Download the generated dummy data file in specified format.

    ---
    parameters:
      - name: format
        in: query
        type: string
        enum: [json, delimiter, text]
        required: true
      - name: delimiter_char
        in: query
        type: string
        required: false

    responses:
      200:
        description: The generated dummy data file.
      404:
        description: The generated dummy data file was not found.
    """
    format = request.args.get('format')
    if format not in ['json', 'delimiter', 'text']:
        return jsonify({'error': 'Invalid format specified'}), 400

    delimiter_char = request.args.get('delimiter_char', ',')  # Default delimiter is comma
    filename = f"generated_dummy_data.{format}"
    if os.path.exists(filename):
        if format == 'json':
            return send_file(filename, as_attachment=True)
        elif format == 'delimiter':
            with open(filename, 'r') as file:
                content = file.read().replace(',', delimiter_char)
            with NamedTemporaryFile(delete=False, mode='w', suffix='.csv') as temp_file:
                temp_file.write(content)
            return send_file(temp_file.name, as_attachment=True, mimetype='text/csv', download_name="generated_dummy_data.delimiter")
        elif format == 'text':
            return send_file(filename, as_attachment=True, mimetype='text/plain')
    else:
        return jsonify({'error': 'Generated dummy data file not found'}), 404



if __name__ == '__main__':
    app.run(debug=True)
