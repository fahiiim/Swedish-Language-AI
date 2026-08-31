# Swedish Citizenship Question API

A FastAPI service that generates validated Swedish citizenship practice
questions with Amazon Nova Lite through AWS Bedrock.

## Deployment target

The production target is one AWS EC2 instance with an Elastic IP. Docker keeps
the application isolated inside the instance:

- Public address: `http://ELASTIC_IP:8005`
- EC2 host port: `8005`
- Container port: `8000`
- Health check: `http://ELASTIC_IP:8005/health`
- API endpoint: `POST http://ELASTIC_IP:8005/generate-question`

The project does not use ECS, an Application Load Balancer, ECR, CloudFormation,
OIDC, or CORS configuration.

## Local development

Requirements:

- Python 3.12+
- AWS credentials from the standard boto3 credential chain
- Bedrock permission for `amazon.nova-lite-v1:0`

Set up the project:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements-dev.txt
Copy-Item .env.example .env
```

Run it directly on port `8005`:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

Or run it with Docker Compose:

```powershell
docker compose up --build
```

Then open:

- `http://localhost:8005/health`
- `http://localhost:8005/docs`

Run checks:

```powershell
ruff check .
ruff format --check .
pytest
```

## Prepare the EC2 instance

The instance needs Docker, `curl`, and `gzip`. Its SSH user must be able to run
Docker with `sudo` without an interactive password.

The deployment workflow creates `/opt/swedish-language-ai/.env` on the instance
from the encrypted GitHub secrets and restricts it to root access.

The EC2 security group must allow:

- SSH port `22` from the intended deployment source
- Application port `8005` from the clients that should reach the API

## GitHub Actions secrets

Go to **Repository Settings → Secrets and variables → Actions → Secrets** and
create only these secrets:

| Secret | Required | Value |
| --- | --- | --- |
| `EC2_HOST` | Yes | The EC2 Elastic IP, without `http://` or a port |
| `EC2_USER` | Yes | Usually `ubuntu` or `ec2-user` |
| `EC2_SSH_PRIVATE_KEY` | Yes | Complete private SSH key, including header and footer |
| `AWS_ACCESS_KEY_ID` | Yes | Dedicated AWS key with Bedrock invocation permission |
| `AWS_SECRET_ACCESS_KEY` | Yes | Secret belonging to that AWS key |
| `AWS_REGION` | No | Defaults to `us-east-1` |
| `APP_PORT` | No | Defaults to `8005` |

The AWS identity only needs `bedrock:InvokeModel` for the selected model. It does
not need administrator, EC2, ECR, or CloudFormation permissions. No GitHub
Actions variables, AWS session token, or CORS value is required.

## Deploy

Pushes and pull requests run tests and build the Docker image but do not deploy.
To deploy intentionally:

1. Open **GitHub → Actions → CI/CD**.
2. Choose **Run workflow**.
3. Run it from `main`.

The deployment job builds the image, transfers it to the Elastic IP over SSH,
loads it into Docker, and starts it on host port `8005`. It checks `/health` on
the EC2 instance and from the GitHub runner. If the new container fails its local
health check, the workflow restores the previously running image.

## API

Generate a question with no request body:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://ELASTIC_IP:8005/generate-question
```

Example response:

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

Bedrock authentication failures return `503`, invocation failures return `502`,
and repeatedly invalid generated content returns `502`. Responses include an
`X-Request-ID` header for log correlation.

## Application environment

| Setting | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Uses JSON logging when set to `production` |
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `AWS_PROFILE` | `default` | Optional local AWS profile |
| `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` | Bedrock foundation model |
| `BEDROCK_CONNECT_TIMEOUT_SECONDS` | `5` | SDK connection timeout |
| `BEDROCK_READ_TIMEOUT_SECONDS` | `60` | SDK response timeout |
| `DOCS_ENABLED` | `true` | Enables `/docs`; production example disables it |
| `LOG_LEVEL` | `INFO` | Application log level |
| `PORT` | `8000` | Internal container port |

Never commit `.env` or SSH private keys.
