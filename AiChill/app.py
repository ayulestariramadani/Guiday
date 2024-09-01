from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from http import HTTPStatus
from dashscope import Application
import dashscope
from PIL import Image
from landingai.predict import Predictor
from werkzeug.utils import secure_filename
import os


app = Flask(__name__)

# Define a directory to save uploaded images temporarily
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure the SQLAlchemy connection to AnalyticDB
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://your-username:your-password@your-analyticdb-host:3306/your-database-name'
db = SQLAlchemy(app)

dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
history = []

def call_agent_app(text_to_explain):
    response = Application.call(app_id='46f00f843f7d4dabac7c05dd16569e1f',
                                prompt=f'Explain this information in simple and easy-to-understand sundanese language only one paragraph, suitable for people in rural areas. Use everyday words and avoid terms that are too technical or difficult to understand. \n \n \n {text_to_explain}',
                                api_key='sk-67c3e1bdb84d4971a997a6776ffb04c8',)
    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        print('request_id=%s\n output=%s\n usage=%s\n' % (response.request_id, response.output, response.usage))
    return response.output.text

def call_prediction_app(disease_name):
    response = Application.call(app_id='46f00f843f7d4dabac7c05dd16569e1f',
                                prompt=f'This plant shows signs of being affected by {disease_name}. Is this plant infected? If so, what disease might be attacking this plant? What steps should be taken to address this issue? Answer using sundanese language',
                                api_key='sk-67c3e1bdb84d4971a997a6776ffb04c8',)
    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        print('request_id=%s\n output=%s\n usage=%s\n' % (response.request_id, response.output, response.usage))
    return response.output.text

def chatbot_agent_app(question_text):
    # Build the conversation history as a single string to provide context
    conversation_history = ""
    
    # Iterate through the history and append user and bot messages to the conversation history
    for message in history:
        conversation_history += f"User: {message['user']}\n"
        conversation_history += f"Bot: {message['bot']}\n"

    # Add the current user question to the conversation
    conversation_history += f"User: {question_text}\n"

    # Debug: Print the history
    print(conversation_history)

    # Call the model API with the conversation history included
    response = Application.call(app_id='46f00f843f7d4dabac7c05dd16569e1f',
                                prompt=f'{conversation_history} Answer using sundanese language',
                                api_key='sk-67c3e1bdb84d4971a997a6776ffb04c8')
    
    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
        return "Error in response"
    else:
        print('request_id=%s\n output=%s\n usage=%s\n' % (response.request_id, response.output, response.usage))
        bot_response = response.output.text

        # Add the new question and response to history
        # history.append({'user': question_text, 'bot': bot_response})

        return bot_response

def predict_image(image_url): # Enter your API Key
    endpoint_id="f3b680fd-7e5a-46a7-abb8-22ef757f9882"
    # endpoint_id = "6b826cfb-943f-4519-831f-506ea949c0f0"
    api_key = "land_sk_J5fOOOC83kCw1RSwXVpGGMUSQdw0Yy7z8z4ixm9EzMPsaXXM4A"
    # Load your image
    image = Image.open(image_url)
    # Run inference
    predictor = Predictor(endpoint_id, api_key=api_key)
    predictions = predictor.predict(image)
    return predictions

class PlantModel(db.Model):
    __tablename__ = 'your_table'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

def read_csv():
    csv_url = 'https://docs.google.com/spreadsheets/d/16qIHNp8L4RMHRC9Y8JzgvVA8KlDtmT81Yk7jRcZ09EU/export?format=csv'
    df = pd.read_csv(csv_url)
    return df

@app.route('/', methods=['GET', 'POST'])
def index():
    data = read_csv().to_dict(orient='records')
    if request.method == 'POST':
        selected_option = request.form.get('selected_option')

        return redirect(url_for('detail', selected_option=selected_option))
    return render_template('index.html', data_list = data)

@app.route('/detail')
def detail():
    # Retrieve selected option from query parameters
    selected_option = request.args.get('selected_option', '')

    # Get data from CSV
    data = read_csv().to_dict(orient='records')

    # Find the selected plant details
    plant_details = next((item for item in data if item["nama"] == selected_option), None)

    plant_details['persiapan'] = call_agent_app(plant_details['persiapan'])
    plant_details['penanaman'] = call_agent_app(plant_details['penanaman'])
    plant_details['perawatan'] = call_agent_app(plant_details['perawatan'])
    plant_details['pengendalian'] = call_agent_app(plant_details['pengendalian'])

    return render_template('detail.html', plant_details=plant_details)

@app.route('/submit_question', methods=['POST'])
def submit_question():
    # Retrieve the submitted question from the form
    question = request.form.get('question')
    # Generate bot response
    bot_response = chatbot_agent_app(question)
    # Append the question and response to the history
    history.append({'user': question, 'bot': bot_response})
    # Redirect to the chat page to display the conversation
    return redirect(url_for('chat'))

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Predict the uploaded image
        predictions = predict_image(file_path)

        prediction_summary = call_prediction_app(predictions)  # This function should return a string now
        print(predictions)
        print(prediction_summary)

        # Clean up the uploaded file after processing
        os.remove(file_path)

        return jsonify({'predictions': prediction_summary})  # Return the string prediction

    return jsonify({'error': 'File upload failed'}), 500

@app.route('/chat', methods=['GET'])
def chat():
    return render_template('chat.html', history=history)

@app.route('/data', methods=['GET'])
def get_data():
    data = PlantModel.query.limit(10).all()
    result = [{"id": d.id, "name": d.name} for d in data]
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
