# Deployment

Kubernetes manifests and Docker configurations.

## Directory Structure

```
deploy/
├── kubernetes/
│   ├── base/                    # Base Kustomize manifests
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   └── services/            # Per-service deployments
│   ├── overlays/                # Environment-specific patches
│   │   ├── qa/
│   │   ├── preprod/
│   │   └── prod/
│   └── components/
│       ├── dapr/                # DAPR component configs
│       └── secrets/             # External secrets config
│
└── docker/
    ├── Dockerfile.python        # Base Python image
    ├── docker-compose.yml       # Local development stack
    └── ...
```

## Kustomize Usage

```bash
# Deploy to QA
kubectl apply -k deploy/kubernetes/overlays/qa

# Deploy to Production
kubectl apply -k deploy/kubernetes/overlays/prod
```

## Local Development

```bash
# Start local infrastructure (MongoDB, Redis, DAPR)
docker-compose -f deploy/docker/docker-compose.yml up -d

# Or use Makefile
make local-up
```

## Environment Configuration

| Environment | Namespace | Replicas | Notes |
|-------------|-----------|----------|-------|
| QA | farmer-power-qa | 1 | Testing |
| Preprod | farmer-power-preprod | 2 | Staging |
| Prod | farmer-power-prod | 3+ | Production with HPA |

See `_bmad-output/architecture/repository-structure.md` for deployment details.
