# OWASP Container Security

Detailed mapping of OWASP Docker Top 10 controls with threat descriptions, mitigation strategies, and implementation examples. Use this reference when aligning container security practices with OWASP recommendations.

## OWASP Docker Top 10

### D01 - Secure User Mapping

**Threat**: Containers running as root inside the container are root on the host when container breakout occurs. Default Docker behavior maps container root (UID 0) to host root.

**Mitigation**:
- Set `USER` in Dockerfile to a non-root UID
- Use user namespaces (`--userns-remap`) to remap container UIDs to unprivileged host UIDs
- Run rootless Docker or Podman to eliminate host root entirely (Podman runs rootless by default)
- Verify with: `docker exec <container> id` (should show non-zero UID)

**Implementation**:

```dockerfile
# Dockerfile - create and use non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser
WORKDIR /app
COPY --chown=appuser:appgroup . .
USER appuser
```

```bash
# Enable user namespace remapping in daemon.json
{
  "userns-remap": "default"
}
```

**Verification**: `docker inspect --format '{{.Config.User}}' <image>` must return non-empty, non-root value.

---

### D02 - Patch Management Strategy

**Threat**: Unpatched base images and application dependencies contain known vulnerabilities (CVEs) that attackers actively exploit.

**Mitigation**:
- Pin base image versions and rebuild on a regular schedule (weekly minimum)
- Integrate vulnerability scanning in CI/CD (fail on CRITICAL/HIGH)
- Subscribe to security advisories for base images and key dependencies
- Maintain an image rebuild pipeline triggered by upstream security patches

**Implementation**:

```yaml
# GitHub Actions - scheduled rebuild and scan
name: Weekly Security Rebuild
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday at 06:00
jobs:
  rebuild:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:latest .
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:latest
          severity: CRITICAL,HIGH
          exit-code: 1
```

**Tools**: Trivy, Grype, Snyk Container, Docker Scout, Renovate/Dependabot for base image updates.

---

### D03 - Network Segmentation and Firewalling

**Threat**: Flat container networks allow lateral movement. A compromised frontend container can directly access the database.

**Mitigation**:
- Create separate Docker networks per tier (frontend, backend, database)
- Only connect containers to the networks they need
- Use network policies in Kubernetes to restrict pod-to-pod traffic
- Never expose management ports (Docker API, debug ports) to untrusted networks

**Implementation**:

```yaml
# docker-compose.yml - network segmentation
networks:
  frontend:
  backend:
  database:

services:
  web:
    networks: [frontend, backend]
  api:
    networks: [backend, database]
  db:
    networks: [database]
```

```yaml
# Kubernetes NetworkPolicy - restrict database access
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-access
spec:
  podSelector:
    matchLabels:
      app: database
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api
      ports:
        - port: 5432
```

---

### D04 - Secure Defaults and Hardening

**Threat**: Default Docker configurations are permissive. Containers inherit broad Linux capabilities, writable filesystems, and unlimited resources.

**Mitigation**:
- Drop all capabilities, add back selectively
- Enable `no-new-privileges` to prevent privilege escalation via setuid binaries
- Mount filesystem read-only with explicit tmpfs for writable paths
- Set resource limits (memory, CPU, PIDs)
- Disable inter-container communication when not needed (`--icc=false`)

**Implementation**:

```yaml
# docker-compose.yml - hardened service
services:
  app:
    image: myapp:v1.0
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
          pids: 100
```

**Key capabilities to review**:

| Capability | When Needed |
|------------|-------------|
| `NET_BIND_SERVICE` | Binding to ports below 1024 |
| `CHOWN` | Changing file ownership at runtime |
| `SETUID`/`SETGID` | Process identity switching (avoid if possible) |
| `SYS_PTRACE` | Debugging only (never in production) |

---

### D05 - Maintain Security Contexts

**Threat**: Security contexts (SELinux, AppArmor, seccomp) provide mandatory access control. Disabling them removes a critical defense layer.

**Mitigation**:
- Use the default Docker seccomp profile (blocks ~44 dangerous syscalls)
- Apply AppArmor or SELinux profiles for additional confinement
- Never run with `--privileged` (disables all security mechanisms)
- Create custom seccomp profiles for applications with known syscall requirements

**Implementation**:

```bash
# Apply custom seccomp profile
docker run --security-opt seccomp=custom-profile.json myapp

# Verify AppArmor is active
docker inspect --format '{{.AppArmorProfile}}' <container>
```

```json
// Minimal seccomp profile example (deny by default)
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    {
      "names": ["read", "write", "open", "close", "stat", "fstat",
                "mmap", "mprotect", "munmap", "brk", "exit_group"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

**Anti-pattern**: `docker run --privileged` grants ALL capabilities, mounts all devices, and disables seccomp/AppArmor. Never use in production.

---

### D06 - Protect Secrets

**Threat**: Secrets embedded in images, environment variables visible in `docker inspect`, or unencrypted secret stores expose credentials to attackers.

**Mitigation**:
- Never store secrets in Dockerfile instructions (ENV, ARG, COPY)
- Use BuildKit `--mount=type=secret` for build-time secrets
- Use orchestrator secret management (Kubernetes Secrets, Docker Swarm secrets)
- Integrate with external secret managers (HashiCorp Vault, AWS Secrets Manager)
- Encrypt secrets at rest and in transit

**Implementation**:

```dockerfile
# BuildKit secret mount - secret never persists in layer
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=db_password \
    cat /run/secrets/db_password | setup-db.sh
```

```yaml
# Kubernetes Secret with volume mount
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  password: <base64-encoded>
---
# Pod spec
volumes:
  - name: db-secret
    secret:
      secretName: db-credentials
containers:
  - volumeMounts:
      - name: db-secret
        mountPath: /run/secrets
        readOnly: true
```

**Verification**: `docker history <image>` must not contain any secret values.

---

### D07 - Resource Protection

**Threat**: Without resource limits, a single container can exhaust host resources (CPU, memory, disk, PIDs), causing denial of service for all containers on the host.

**Mitigation**:
- Set memory limits (`--memory`) and CPU limits (`--cpus`)
- Set PID limits (`--pids-limit`) to prevent fork bombs
- Set storage limits via storage drivers
- Monitor resource usage and alert on threshold violations
- Use `--oom-kill-disable` with caution (only with strict memory limits)

**Implementation**:

```bash
docker run \
  --memory=512m \
  --memory-swap=512m \
  --cpus=0.5 \
  --pids-limit=100 \
  --storage-opt size=10G \
  myapp
```

```yaml
# Kubernetes resource quotas
resources:
  requests:
    memory: 256Mi
    cpu: 250m
  limits:
    memory: 512Mi
    cpu: 500m
```

---

### D08 - Container Image Integrity

**Threat**: Unsigned or tampered images can introduce malicious code. Man-in-the-middle attacks on image pulls can substitute compromised images.

**Mitigation**:
- Sign images with Cosign (Sigstore) or Docker Content Trust (DCT)
- Verify signatures before deployment (admission controllers in Kubernetes)
- Use private registries with access control
- Enable Docker Content Trust (`export DOCKER_CONTENT_TRUST=1`)
- Generate and attach SBOMs and SLSA provenance attestations

**Implementation**:

```bash
# Sign with Cosign (keyless via Fulcio/Rekor)
cosign sign registry.example.com/myapp:v1.0

# Verify signature
cosign verify registry.example.com/myapp:v1.0

# Generate SBOM
syft registry.example.com/myapp:v1.0 -o spdx-json > sbom.json

# Attach SBOM to image
cosign attach sbom --sbom sbom.json registry.example.com/myapp:v1.0
```

```yaml
# Kubernetes - Kyverno policy requiring signed images
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-signed-images
spec:
  rules:
    - name: verify-signature
      match:
        resources:
          kinds: [Pod]
      verifyImages:
        - imageReferences: ["registry.example.com/*"]
          attestors:
            - entries:
                - keyless:
                    issuer: https://accounts.google.com
```

---

### D09 - Implement Immutable Paradigm

**Threat**: Mutable containers (patched or modified at runtime) drift from their defined state, making security auditing impossible and introducing untracked changes.

**Mitigation**:
- Mount container filesystems as read-only
- Never exec into production containers to apply patches
- Use immutable infrastructure: rebuild and redeploy instead of patching
- Store all state in external volumes or databases
- Use tmpfs for ephemeral write needs (caches, temp files)

**Implementation**:

```yaml
# docker-compose.yml - immutable container
services:
  app:
    image: myapp:v1.0
    read_only: true
    tmpfs:
      - /tmp:size=100M
    volumes:
      - app-data:/data  # External state only
```

**Workflow**: Code change -> Build new image -> Scan -> Sign -> Deploy -> Drain old containers

---

### D10 - Logging and Monitoring

**Threat**: Without centralized logging and monitoring, security incidents go undetected. Container logs disappear when containers are destroyed.

**Mitigation**:
- Configure centralized log aggregation (ELK, Loki, CloudWatch)
- Log to stdout/stderr (Docker captures automatically)
- Enable Docker daemon audit logging
- Monitor for anomalous behavior (unexpected processes, network connections)
- Set log rotation to prevent disk exhaustion
- Include container metadata in logs (image, container ID, labels)

**Implementation**:

```json
// Docker daemon.json - log configuration
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3",
    "labels": "app,environment"
  }
}
```

```yaml
# docker-compose.yml - logging configuration
services:
  app:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**Key events to monitor**:
- Container start/stop/restart patterns
- Exec operations (possible intrusion)
- Privilege escalation attempts
- Network connections to unexpected destinations
- File system modifications (in non-tmpfs mounts)

## Container Security Verification

### Pre-Deployment Rules

| Control | Check | OWASP Ref |
|---------|-------|-----------|
| Non-root user | `docker inspect --format '{{.Config.User}}'` returns non-root | D01 |
| Base image patched | Vulnerability scan shows no CRITICAL/HIGH | D02 |
| Network isolated | Container on scoped network, no `--network=host` | D03 |
| Capabilities dropped | `--cap-drop=ALL` with selective adds | D04 |
| Security profiles active | seccomp/AppArmor not disabled | D05 |
| No embedded secrets | `docker history` clean, no ENV secrets | D06 |
| Resource limits set | Memory, CPU, PID limits configured | D07 |
| Image signed | `cosign verify` succeeds | D08 |
| Filesystem read-only | `--read-only` flag set | D09 |
| Logging configured | Centralized log driver, rotation set | D10 |

### References

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [OWASP Docker Top 10](https://owasp.org/www-project-docker-top-10/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST SP 800-190 Application Container Security Guide](https://csrc.nist.gov/pubs/sp/800/190/final)
