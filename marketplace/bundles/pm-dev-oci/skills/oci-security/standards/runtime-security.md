# Runtime Security Quick Reference

Concise runtime hardening checklist. For detailed threat descriptions, implementation examples, and verification commands, see the OWASP Container Security reference (`standards/owasp-container-security.md`, controls D01, D04, D05, D07, D09).

## Hardened Container Template

```yaml
# docker-compose.yml - hardened service
services:
  app:
    image: myapp:v1.0
    user: "1001:1001"
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if binding to ports < 1024
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
          pids: 100
        reservations:
          memory: 256M
          cpus: '0.25'
```

## Checklist

| Control | Rule | OWASP |
|---------|------|-------|
| Non-root user | `USER 1001` in Dockerfile or `user: "1001:1001"` in Compose | D01 |
| Drop capabilities | `cap_drop: [ALL]`, selectively `cap_add` | D04 |
| No privilege escalation | `no-new-privileges:true` | D04 |
| Read-only filesystem | `read_only: true` with `tmpfs` for write dirs | D09 |
| Resource limits | Memory, CPU, PID limits set | D07 |
| Security profiles | Default seccomp/AppArmor active, never `--privileged` | D05 |
| No daemon socket | Never mount `/var/run/docker.sock` | D04 |
| Network segmentation | Separate networks per tier (frontend/backend/db) | D03 |
| Immutable containers | Rebuild and redeploy, never patch running containers | D09 |
| Logging | Centralized log driver with rotation | D10 |

## Capability Reference

| Capability | When Needed |
|------------|-------------|
| `NET_BIND_SERVICE` | Binding to ports below 1024 |
| `CHOWN` | Changing file ownership at runtime |
| `SETUID`/`SETGID` | Process identity switching (avoid if possible) |
| `SYS_PTRACE` | Debugging only (never in production) |
