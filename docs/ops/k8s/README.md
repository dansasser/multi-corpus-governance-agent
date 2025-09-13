# Kubernetes Deployment (Scaffold)

## Manifests
- `namespace.yaml`: creates `mcg-agent` namespace
- `configmap.yaml`: non-secret configuration
- `secret.example.yaml`: example secrets; copy and replace with real values
- `deployment.yaml`: app deployment with probes and security context
- `service.yaml`: ClusterIP service (80 -> 8000)
- `ingress.yaml`: nginx Ingress with TLS and basic rate limiting

## Quick Start
1. Create namespace:
```
kubectl apply -f namespace.yaml
```
2. Apply config and secrets (replace values):
```
kubectl apply -f configmap.yaml
kubectl apply -f secret.example.yaml  # use a real secret in production
```
3. Deploy app and service:
```
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```
4. Ingress:
```
# Update host and TLS secret, then:
kubectl apply -f ingress.yaml
```

## Notes
- Replace `your-registry/mcg-agent:latest` with your image.
- Consider adding HPA, PodDisruptionBudget, and securing `/metrics` at the Ingress.
- Use a managed Postgres and Redis and set `DATABASE_URL`/`REDIS_*` via Secret.

