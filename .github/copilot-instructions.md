# Repository instructions

- Use Python 3.12 or newer with type hints and concise, readable modules.
- Preserve the compact FastAPI architecture under `app/`.
- Keep AWS credentials in the ignored `.env` file; never hardcode or commit secrets.
- Reuse the process-wide Bedrock Runtime client and keep boto3 calls off the async event loop.
- Validate all generated API output with the Pydantic response model.
- Keep the external response keys `questionText`, `options`, and `correctAnswer` unchanged.
- Run Python compilation and focused smoke tests after code changes.

## Project setup status

- [x] Requirements clarified
- [x] Project scaffolded and customized
- [x] Production and development dependencies locked
- [x] Linting, compilation, API tests, and workflow validation completed
- [x] Non-root production Docker image and health check configured
- [x] AWS EC2 Docker deployment through GitHub Actions configured
- [x] Production deployment is manual and targets the configured Elastic IP
- [x] Local and deployment documentation completed
