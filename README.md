# Swedish Citizenship Question API

A production-ready FastAPI service that uses Amazon Nova Lite through the AWS
Bedrock Converse API to generate validated Swedish citizenship practice
questions.

## What is included

- FastAPI API with strict Pydantic response validation
- Non-blocking Bedrock calls, bounded SDK timeouts, and retry handling
- Health checks, request IDs, security headers, and JSON production logs
- Non-root, read-only, multi-stage Docker image
- Automated linting, tests, container smoke tests, ECR publishing, and ECS rollout
- CloudFormation for ECR, VPC, ALB, WAF rate limiting, ECS Fargate, IAM,
  CloudWatch, deployment rollback, and CPU autoscaling

The AWS design places two ECS tasks in private subnets across two Availability
Zones. An Application Load Balancer is public, and the application task role can
invoke only the configured Bedrock foundation model.

## Local development

Requirements:

- Python 3.12+
- AWS credentials from the standard SDK credential chain
- Bedrock access to `amazon.nova-lite-v1:0` in the selected region

Create the environment and install the locked development dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements-dev.txt
Copy-Item .env.example .env
```

Prefer an AWS SSO/profile session over long-lived keys:

```powershell
aws sso login --profile your-profile
```

Set `AWS_PROFILE=your-profile` in `.env`, then run:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Useful URLs:

- Health: `http://localhost:8000/health`
- OpenAPI UI: `http://localhost:8000/docs`
- Generate: `POST http://localhost:8000/generate-question`

Run the quality checks locally:

```powershell
ruff check .
ruff format --check .
pytest
```

## Docker

Build and run the same image used in production:

```powershell
docker build -t swedish-language-ai .
docker compose up --build
```

`compose.yaml` reads the ignored `.env` file. A container cannot automatically
use a profile stored on the host, so supply temporary AWS credentials to the
container when testing the Bedrock endpoint. ECS does not need credential
variables because it receives credentials from its task IAM role.

## GitHub Actions deployment setup

The deployment creates billable resources, including an Application Load
Balancer, NAT Gateways, WAF, and Fargate tasks. Review current AWS pricing before
deploying.

Add these encrypted repository secrets under **Settings → Secrets and variables →
Actions**:

| Secret | Required | Purpose |
| --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | Yes | Credentials for a dedicated AWS deployment identity |
| `AWS_SECRET_ACCESS_KEY` | Yes | Secret for that deployment identity |
| `AWS_SESSION_TOKEN` | Only for temporary credentials | Session token |

The deployment identity must be allowed to manage the CloudFormation, ECR, VPC,
ECS, load balancer, WAF, CloudWatch Logs, autoscaling, and project IAM resources
defined under `infra/`. Do not reuse a personal administrator access key.

Add these repository variables:

| Variable | Required | Value |
| --- | --- | --- |
| `AWS_REGION` | No | Defaults to `us-east-1` |
| `CORS_ORIGIN_REGEX` | Yes | Exact HTTPS frontend regex, such as `^https://app\.example\.com$` |
| `CERTIFICATE_ARN` | Production HTTPS | ACM certificate ARN in the deployment region |
| `PUBLIC_BASE_URL` | HTTPS smoke test | Public DNS URL covered by that certificate |

When `CERTIFICATE_ARN` is provided, the ALB redirects HTTP to HTTPS. Create a DNS
alias/CNAME that points the public hostname to the `LoadBalancerDnsName`
CloudFormation output, then set `PUBLIC_BASE_URL` to that hostname.

### Deploy

Push or merge to `main`. The workflow in `.github/workflows/ci-cd.yaml` will:

1. lint, format-check, and test the Python code;
2. build and health-check the container;
3. authenticate to AWS with the configured GitHub secrets;
4. provision the immutable ECR repository;
5. push a commit-tagged image with provenance and an SBOM;
6. deploy the image by digest through CloudFormation;
7. wait for the ECS rolling deployment and circuit-breaker checks;
8. verify `/health` when a directly usable endpoint is available.

Pull requests run CI but never deploy. Production deployments are serialized to
avoid overlapping CloudFormation updates. The ECS deployment circuit breaker
automatically rolls back a release whose tasks do not become healthy.

## API

Generate a question with no request body:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/generate-question
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
and repeatedly invalid generated content returns `502`. Every response includes
an `X-Request-ID` header for log correlation.

## Runtime configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Enables JSON logs when set to `production` |
| `AWS_REGION` | `us-east-1` | Bedrock client region |
| `AWS_PROFILE` | `default` | Optional local AWS profile; not used on ECS |
| `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` | Foundation model invoked by the service |
| `BEDROCK_CONNECT_TIMEOUT_SECONDS` | `5` | SDK connection timeout |
| `BEDROCK_READ_TIMEOUT_SECONDS` | `60` | SDK response timeout |
| `CORS_ORIGIN_REGEX` | localhost only | Browser origins allowed by CORS |
| `DOCS_ENABLED` | `true` | Enables `/docs` and `/openapi.json`; ECS sets `false` |
| `LOG_LEVEL` | `INFO` | Process log level |
| `PORT` | `8000` | Container listener port |

Never commit `.env`. In AWS, modify runtime settings through the CloudFormation
parameters rather than adding credentials to the task definition.
