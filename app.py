import boto3
import base64
import json
import torch
import time
import subprocess
import os
# AWS Configuration
REGION = 'us-east-1'
ASU_ID = '1229855837'  # Replace with your ASU ID
REQUEST_QUEUE_URL = f'https://sqs.{REGION}.amazonaws.com/137068238639/{ASU_ID}-req-queue'
RESPONSE_QUEUE_URL = f'https://sqs.{REGION}.amazonaws.com/137068238639/{ASU_ID}-resp-queue'

# https://sqs.us-east-1.amazonaws.com/137068238639/1229855837-req-queue
# https://sqs.us-east-1.amazonaws.com/137068238639/1229855837-resp-queue

# https://sqs.us-east-1.amazonaws.com/137068238639
INPUT_BUCKET_NAME = f'{ASU_ID}-in-bucket'
OUTPUT_BUCKET_NAME = f'{ASU_ID}-out-bucket'

# Initialize AWS clients
sqs = boto3.client('sqs', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

# Load the model (replace with the correct model path)
# model = torch.load('path/to/model.pth')
# model.eval()

def process_image(file_path):
    # Perform the face recognition here using the loaded model
    model_script_path = os.path.join('model', 'face_recognition.py')
    command = ["python3", model_script_path, file_path]
    print(file_path)
    try:
        classification_result = subprocess.check_output(command, text=True).strip()
    except subprocess.CalledProcessError as e:
        classification_result = f"Error during classification: {e}"

    return classification_result  # Replace this with real inference logic

while True:
    # Receive messages from the Request Queue
    print(REQUEST_QUEUE_URL)
    response = sqs.receive_message(
        QueueUrl=REQUEST_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    if 'Messages' in response:
        for message in response['Messages']:
            body = json.loads(message['Body'])
            file_name = body['fileName']
            file_data_base64 = body['fileData']

            # Decode the base64 image data and save it
            image_bytes = base64.b64decode(file_data_base64)
            with open(file_name, 'wb') as image_file:
                image_file.write(image_bytes)

            # Upload the image to S3 Input Bucket
            s3.upload_file(file_name, INPUT_BUCKET_NAME, file_name)
            # Run the model inference on the saved image
            result = process_image(file_name)

            # Upload the classification result to the S3 Output Bucket (Optional)
            s3.put_object(Bucket=OUTPUT_BUCKET_NAME, Key=f'{file_name}.txt', Body=result)

            # Send the result to the Response Queue
            sqs.send_message(
                QueueUrl=RESPONSE_QUEUE_URL,
                MessageBody=json.dumps({
                    'fileName': file_name,
                    'classificationResult': result
                }),
            )

            # Delete the message from the Request Queue
            sqs.delete_message(
                QueueUrl=REQUEST_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )

    # time.sleep(2)
