# Swedish Citizenship Question API

A compact FastAPI microservice that generates and validates one Swedish-language citizenship test question per request using Amazon Nova Lite through the AWS Bedrock Converse API.

## Requirements

- Python 3.12 or newer
- AWS credentials with `bedrock:InvokeModel` permission
- Amazon Nova Lite model access in `us-east-1`

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Set the credentials in `.env`:

```dotenv
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-1
```

Never commit a populated `.env` file. In deployed AWS environments, the standard boto3 credential chain can use an IAM role instead.

## Run

```powershell
uvicorn app.main:app --host 10.10.28.89 --port 8005 --reload
```

The interactive API documentation is available at `http://10.10.28.89:8005/docs`.

## Generate a question

The endpoint requires no request body:

```powershell
Invoke-RestMethod -Method Post -Uri http://10.10.28.89:8005/generate-question
```

Sample response:

```json
{
  "questionText": "Vilken stad är Sveriges huvudstad?",
  "options": {
    "A": "Stockholm",
    "B": "Göteborg",
    "C": "Malmö",
    "D": "Uppsala"
  },
  "correctAnswer": "A"
}
```

The service safely extracts JSON from model output, validates the complete response with Pydantic, and retries once when parsing or validation fails. Authentication failures return HTTP 503, Bedrock invocation failures return HTTP 502, and repeated invalid model output returns HTTP 500.

## Configuration

The Bedrock client is created lazily once per application process and reused. To change the model, edit only `BEDROCK_MODEL_ID` in `app/config.py`.