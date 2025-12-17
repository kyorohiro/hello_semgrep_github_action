#!/usr/bin/env python3
import json, os

job_status = os.getenv("JOB_STATUS", "unknown")
repo = os.getenv("REPO", "unknown")
ref = os.getenv("REF", "unknown")
event = os.getenv("EVENT", "unknown")
actor = os.getenv("ACTOR", "unknown")
run_url = os.getenv("RUN_URL", "")
body = os.getenv("BODY", "")

payload = {
  "text": f"Semgrep {job_status} - {repo}",
  "blocks": [
    {"type": "section", "text": {"type": "mrkdwn", "text":
      f"*Semgrep {job_status}*\n"
      f"*Repo:* {repo}\n"
      f"*Ref:* {ref}\n"
      f"*Event:* {event}\n"
      f"*Actor:* {actor}\n"
      f"*Run:* <{run_url}|Open GitHub Actions run>"
    }},
    {"type": "section", "text": {"type": "mrkdwn", "text":
      "*Output (first 3000 chars)*\n```\n" + body + "\n```"
    }},
  ]
}

print(json.dumps(payload))
