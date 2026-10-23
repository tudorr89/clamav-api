# AGENTS.md — clamav-api

Small HTTP wrapper around ClamAV used by the PDF compressor
(`POST /scan` with a multipart `file`, `GET /health`).

Deployment hosts, IPs, paths and the private registry are not kept in this
public repository; they live in the private infra docs and the local-only
`AGENTS.local.md` (gitignored).

## Contract

| Response | Meaning |
|---|---|
| `200 {"status":"clean"}` | no threat |
| `200 {"status":"infected","virus":"..."}` | threat found |
| `400` | no file part |
| `413` | larger than `MAX_UPLOAD_MB` |
| `503` | clamd unreachable / scan failed |

Scanner problems return **503** so clients can tell "virus" apart from
"scanner unavailable". There is no authentication — bind it to a private
network only.

## Runtime

- Runs behind **waitress** (not the Flask dev server) as a non-root user.
- `MAX_CONTENT_LENGTH = MAX_UPLOAD_MB` (413 instead of buffering unbounded
  uploads) and `CLAMAV_TIMEOUT` on the clamd socket.
- `scan_stream()` sends the upload to clamd via INSTREAM, nothing is written to
  disk by the API.

## clamd limits (important)

`clamav/clamav` defaults to `StreamMaxLength`/`MaxFileSize` of **100MB**, so
larger PDFs are rejected by INSTREAM even when the client advertises 500MB.
The compose file raises them via `CLAMD_CONF_*`:

```yaml
CLAMD_CONF_StreamMaxLength: "550M"
CLAMD_CONF_MaxFileSize: "550M"
CLAMD_CONF_MaxScanSize: "1G"
CLAMD_CONF_MaxScanTime: "300000"
```

Keep these >= the largest file the clients accept. The engine keeps its
signature database in the `clamav_data` volume (first start downloads it).

## Local testing

```bash
docker compose up -d --build
curl -s -F "file=@some.pdf" http://127.0.0.1:5001/scan
```
