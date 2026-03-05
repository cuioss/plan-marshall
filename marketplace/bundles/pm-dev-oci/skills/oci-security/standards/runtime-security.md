# Runtime Security

Container runtime hardening covering user mapping, capabilities, filesystem isolation, resource limits, and orchestration security.

## Run as Non-Root

Never run containers as root. Create a dedicated user or use a numeric UID.

```dockerfile
# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Or use numeric UID (no user creation needed)
USER 1001
```

Verify at runtime: `docker run --user 1001:1001`

## Drop Capabilities

Remove all Linux capabilities and add back only what is needed.

```yaml
# docker-compose.yml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Only if binding to ports < 1024
```

```bash
# docker run
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE --security-opt=no-new-privileges myapp
```

## Read-Only Filesystem

Mount the container filesystem as read-only. Use tmpfs for directories that need writes.

```bash
docker run --read-only --tmpfs /tmp --tmpfs /var/cache myapp
```

```yaml
# docker-compose.yml
read_only: true
tmpfs:
  - /tmp
  - /var/cache
```

## Resource Limits

Set CPU and memory limits to prevent resource exhaustion attacks.

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

## Protect the Docker Daemon Socket

Never mount `/var/run/docker.sock` into containers. This grants root-equivalent access to the host.

## Network Segmentation

Isolate containers on separate networks. Frontend containers should not directly access database containers.

## Ephemeral Containers

Treat containers as immutable and ephemeral. Do not patch running containers - rebuild and redeploy.

## CIS Docker Benchmark

Follow the CIS Docker Benchmark for host and daemon hardening. Key areas:
- Host configuration and auditing
- Docker daemon configuration
- Container runtime restrictions
- Security operations
