# Scripts

Development and CI/CD scripts.

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `proto-gen.sh` | Generate proto stubs | `./scripts/proto-gen.sh` |
| `local-dev.sh` | Start local environment | `./scripts/local-dev.sh` |
| `run-tests.sh` | Run all tests | `./scripts/run-tests.sh` |
| `deploy.sh` | Deployment script | `./scripts/deploy.sh qa` |

## Makefile Commands

Most scripts are also available via Makefile:

```bash
make proto        # Generate proto stubs
make install      # Install all dependencies
make test         # Run all tests
make lint         # Run linting
make docker-build # Build Docker images
make local-up     # Start local environment
make local-down   # Stop local environment
make deploy-qa    # Deploy to QA
```

See `_bmad-output/architecture/repository-structure.md` for development workflow.
