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
- [x] Dependencies installed
- [x] Project compiled and diagnostics checked
- [x] Runtime task intentionally skipped; README commands are sufficient
- [x] Server launch intentionally skipped; live AWS credentials are not retained
- [x] Documentation completed