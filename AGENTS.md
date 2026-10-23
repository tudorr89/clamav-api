# AGENTS.md — clamav-api

HTTP wrapper around ClamAV used by pdfcompressor. Infra notes:
`~/Projects/infra/docs/applications.md`.

## Deploy

| | |
|---|---|
| Host | `compressor` = **x.x.x.x**, `/home/user/clamav-api` |
| Compose project | default (`clamav-api`): `clamav_engine` + `clamav_api` |
| Engine | `clamav/clamav:1.5` (`platform: linux/amd64`), named volume `clamav_data` |
| API | local build `clamav-api-api`, port **5001 → 5000** |
| Endpoints | `POST /scan` (multipart field `file`), `GET /health` |

```bash
cd /home/user/clamav-api
docker compose up -d --build
curl -s http://127.0.0.1:5001/health
```

Remote: GitHub `git@github.com:tudorr89/clamav-api.git`.
First engine start downloads the signature DB (minutes) into `clamav_data`.

## Why the config looks like this

- **clamd defaults reject big PDFs**: `StreamMaxLength`/`MaxFileSize` default to
  100MB (INSTREAM), so a 150MB upload failed even though the app advertises
  500MB. The compose file sets via `CLAMD_CONF_*`:
  `StreamMaxLength=550M`, `MaxFileSize=550M`, `MaxScanSize=1G`,
  `MaxScanTime=300000`. Keep these >= the client upload limit.
- API runs behind **waitress** (not the Flask dev server), as a non-root user,
  with `MAX_CONTENT_LENGTH=MAX_UPLOAD_MB` (413) and `CLAMAV_TIMEOUT=300`.
- `scan_stream()` streams to clamd via INSTREAM; nothing is written to disk.
- Scanner problems (clamd down, INSTREAM limit, scan error) return **503**;
  clean/infected stay **200** so clients can distinguish "virus" from
  "scanner unavailable".

## Response contract

| Response | Meaning |
|---|---|
| `200 {"status":"clean"}` | no threat |
| `200 {"status":"infected","virus":"..."}` | threat found |
| `400` | no file part |
| `413` | larger than `MAX_UPLOAD_MB` |
| `503` | clamd unreachable / scan failed |

No authentication: keep it on the LAN/tailnet only.

## Local testing

```bash
docker compose up -d --build      # in a copy of this repo
curl -s -F "file=@some.pdf" http://127.0.0.1:5001/scan
```
