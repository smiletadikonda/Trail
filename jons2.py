import os
from flask import Flask, request, jsonify, send_file
from flasgger import Swagger
import json
from faker import Faker
import random
import csv
from io import StringIO

app = Flask(__name__)
swagger = Swagger(app)

fake = Faker()

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


def generate_data(data):
    try:
        if isinstance(data, str):
            return fake.word()
        elif isinstance(data, int):
            return random.randint(10 ** 11, 10 ** 15)
        elif isinstance(data, bool):
            return random.choice([True, False])
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    except Exception as e:
        return None


def generate_dummy_data(schema, num_outputs):
    dummy_data_list = []

    if isinstance(schema, dict):
        for _ in range(num_outputs):
            dummy_data = {}

            for key, value in schema.items():
                if key != 'required':  # Ignore 'required' field
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
        delimiter_file.write(generate_delimited_output(dummy_data))

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

    responses:
      200:
        description: The generated dummy data file.
      404:
        description: The generated dummy data file was not found.
    """
    format = request.args.get('format')
    if format not in ['json', 'delimiter', 'text']:
        return jsonify({'error': 'Invalid format specified'}), 400

    filename = f"generated_dummy_data.{format}"
    if os.path.exists(filename):
        if format == 'json':
            return send_file(filename, as_attachment=True)
        elif format == 'delimiter':
            return send_file(filename, as_attachment=True, mimetype='text/csv')
        elif format == 'text':
            return send_file(filename, as_attachment=True, mimetype='text/plain')
    else:
        return jsonify({'error': 'Generated dummy data file not found'}), 404


if __name__ == '__main__':
    app.run(debug=True)
