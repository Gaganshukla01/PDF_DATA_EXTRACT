from google import genai
from pydantic import BaseModel, Field
from twilio.rest import Client as TwilioClient
from flask import Flask, request, jsonify
import os

# Initialize Google API client
api_key = "AIzaSyCZxtVghyPARk687GNTloNrQQT4ixTPFBQ"
client = genai.Client(api_key=api_key)
model_id = "gemini-2.5-pro-exp-03-25"

# Twilio credentials
TWILIO_ACCOUNT_SID = 'AC3125531d993e19fa15df0a07cb888519'
TWILIO_AUTH_TOKEN = '960b72081c989dccbe6ac5855f46021e'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+19163142883'

# Initialize Twilio client
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Define data models
class Item(BaseModel):
    description: str = Field(description="The description of the item")
    quantity: float = Field(description="The Qty of the item")
    gross_worth: float = Field(description="The gross worth of the item")

class Invoice(BaseModel):
    invoice_number: str = Field(description="The invoice number e.g. 1234567890")
    date: str = Field(description="The date of the invoice e.g. 2024-01-01")
    items: list[Item] = Field(description="The list of items with description, quantity and gross worth")
    total_gross_worth: float = Field(description="The total gross worth of the invoice")

# Function to extract structured data from PDF
def extract_structured_data(file_path: str, model: BaseModel):
    file = client.files.upload(file=file_path, config={'display_name': file_path.split('/')[-1].split('.')[0]})
    prompt = f"Extract the structured data from the following PDF file"
    response = client.models.generate_content(model=model_id, contents=[prompt, file], config={'response_mime_type': 'application/json', 'response_schema': model})
    return response.parsed

# Flask app to handle incoming WhatsApp messages
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From')

    # Check if the incoming message contains a PDF
    if 'application/pdf' in request.headers.get('Content-Type', ''):
        # Save the PDF file
        pdf_file = request.files['file']
        pdf_file_path = f"/tmp/{pdf_file.filename}"
        pdf_file.save(pdf_file_path)

        # Extract data from the PDF
        result = extract_structured_data(pdf_file_path, Invoice)

        # Create a response message
        response_message = f"Extracted Invoice: {result.invoice_number} on {result.date} with total gross worth {result.total_gross_worth}\n"
        for item in result.items:
            response_message += f"Item: {item.description} with quantity {item.quantity} and gross worth {item.gross_worth}\n"

        # Send the response back to the user
        twilio_client.messages.create(
            body=response_message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=from_number
        )
    else:
        # Handle non-PDF messages
        twilio_client.messages.create(
            body="Please send a PDF file for data extraction.",
            from_=TWILIO_WHATSAPP_NUMBER,
            to=from_number
        )

    return jsonify({'status': 'success'}), 200

# Run the Flask app
if __name__ == '__main__':
    app.run(port=5000)
