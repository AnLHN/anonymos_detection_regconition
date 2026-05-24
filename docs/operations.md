# Operations Guide

## Start services

```bash
./start.sh
```

## Stop services

```bash
./stop.sh
```

## Run backend

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Run camera worker manually

```powershell
python scripts/cameras/run_camera_from_env.py door_67b
```

## Run direct RTSP

```powershell
python ai_worker/run_webcam.py --camera-id door_67b --source "rtsp://user:password@ip:554/Streaming/Channels/101"
```

## Verify DB

```powershell
python scripts/db/verify_databases.py
```

## Check unknown events

```powershell
python -c "import psycopg; c=psycopg.connect('host=localhost port=7001 dbname=face_db user=face_user password=face_password'); cur=c.cursor(); cur.execute('select count(*) from unknown_events'); print(cur.fetchone()[0]); c.close()"
```

## Runtime outputs

```text
storage/snapshots/
storage/logs/events.jsonl
storage/debug_faces/
```

## Common issues

### `insightface` install fails on Windows

Install Visual C++ Build Tools with workload:

```text
Desktop development with C++
```

### RTSP fails

Check:

- IP reachable.
- Port 554 open.
- Username/password correct.
- RTSP path correct.
- Password URL-encoded if it contains special characters.

### Video lag

Try:

- Increase `DEFAULT_AI_INTERVAL` in `.env`.
- Use substream RTSP.
- Use GPU/CUDA runtime if available.
