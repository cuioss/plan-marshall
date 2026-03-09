# Certificate Management for Containers

PEM is the standard certificate format for containerized applications. It eliminates password management, simplifies rotation, and integrates naturally with container orchestration.

## Why PEM Over PKCS12

| Aspect | PEM | PKCS12 |
|--------|-----|--------|
| Password management | None required | Password must be stored/injected |
| File permissions | OS-level (600/644) | Password-protected bundle |
| Certificate rotation | Replace files, restart | Replace + update password references |
| Cloud native integration | Native support | Requires conversion |
| Separation of concerns | Key and cert in separate files | Single bundle |

## Certificate Generation

```bash
#!/bin/bash
CERT_DIR="./certificates"
VALIDITY_DAYS=${1:-1}  # 1 day for testing, 365+ for production

mkdir -p "$CERT_DIR"

# Generate private key (no password)
openssl genrsa -out "$CERT_DIR/tls.key" 2048

# Generate self-signed certificate
openssl req -new -x509 -key "$CERT_DIR/tls.key" \
    -out "$CERT_DIR/tls.crt" \
    -days "$VALIDITY_DAYS" \
    -subj "/CN=localhost/O=Development/C=US" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# Set secure file permissions
chmod 600 "$CERT_DIR/tls.key"   # Private key - restricted
chmod 644 "$CERT_DIR/tls.crt"   # Certificate - public

echo "Certificates generated in $CERT_DIR with $VALIDITY_DAYS day validity"
```

## PKCS12 to PEM Conversion

For environments migrating from PKCS12:

```bash
# Extract private key
openssl pkcs12 -in keystore.p12 -nocerts -out tls.key -nodes

# Extract certificate
openssl pkcs12 -in keystore.p12 -clcerts -nokeys -out tls.crt

# Set proper permissions
chmod 600 tls.key
chmod 644 tls.crt
```

## Container Integration

### Dockerfile

```dockerfile
# PEM certificate files with root ownership for security
COPY --chmod=0644 --chown=root:root certificates/tls.crt /app/certificates/tls.crt
COPY --chmod=0600 --chown=root:root certificates/tls.key /app/certificates/tls.key
```

### Docker Compose

```yaml
volumes:
  - ./src/main/docker/certificates:/app/certificates:ro
```

Always mount certificates as **read-only** (`:ro`). Never embed certificates in the image — use volume mounts or secrets management.

## Security Requirements

- **Algorithm**: RSA 2048-bit minimum
- **File permissions**: 600 for private keys, 644 for certificates
- **Storage**: External volume mounts only, no embedded certificates
- **Rotation**: Automate via orchestrator secrets or cert-manager
- **Validation**: Include certificate presence check in health probes
- **Non-root**: Application runs as non-root but reads root-owned cert files
