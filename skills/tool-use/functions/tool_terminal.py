import subprocess
import uuid
import time
import threading
from ._internal.job_state import active_jobs
from ._internal.path_guard import is_command_dangerous

import logging

log = logging.getLogger(__name__)

MAX_BACKGROUND_JOBS = 3
JOB_TIMEOUT_SECONDS = 300  # 5 minutes

def _cleanup_expired_jobs():
    """Kill background jobs that exceeded their timeout (FIX-20)."""
    now = time.time()
    expired = [jid for jid, info in active_jobs.items()
               if isinstance(info, dict) and now - info.get("started_at", 0) > JOB_TIMEOUT_SECONDS]
    for jid in expired:
        try:
            active_jobs[jid]["process"].kill()
        except Exception:
            pass
        del active_jobs[jid]
    # Also clean up legacy entries that are just Popen objects (pre-FIX-20)
    legacy_expired = []
    for jid, val in active_jobs.items():
        if not isinstance(val, dict):
            try:
                if val.poll() is not None:
                    legacy_expired.append(jid)
            except Exception:
                legacy_expired.append(jid)
    for jid in legacy_expired:
        del active_jobs[jid]


def tool_terminal(params: dict, kernel=None) -> dict:
    command = params.get("command")
    background = params.get("background", False)
    
    if not command: 
        log.error("tool_terminal: No command provided.")
        return {"status": "error", "message": "No command provided."}
    
    # FIX-01: Block dangerous commands
    dangerous, reason = is_command_dangerous(command)
    if dangerous:
        log.warning(f"tool_terminal: BLOCKED dangerous command: {command}")
        return {"status": "error", "message": f"BLOCKED: {reason}"}

    log.info(f"tool_terminal: Executing command: {command}, background: {background}")

    if background:
        # FIX-20: Job lifecycle management
        _cleanup_expired_jobs()
        if len(active_jobs) >= MAX_BACKGROUND_JOBS:
            return {"status": "error", "message": f"Max {MAX_BACKGROUND_JOBS} background jobs reached. Kill one first."}

        job_id = f"job-{uuid.uuid4().hex[:8]}"
        try:
            proc = subprocess.Popen(
                command, shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            active_jobs[job_id] = {"process": proc, "started_at": time.time(), "command": command}
            log.info(f"tool_terminal: Background job {job_id} started for command: {command}")
            return {"status": "ok", "job_id": job_id, "message": "Started in background."}
        except Exception as e:
            log.exception(f"tool_terminal: Error starting background job for command: {command}")
            return {"status": "error", "message": f"Failed to start background job: {e}"}
    else:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                log.warning(f"tool_terminal: Command failed with return code {result.returncode}: {command}, Stderr: {result.stderr[:500]}")
            else:
                log.info(f"tool_terminal: Command successful: {command}")
            return {
                "status": "ok", 
                "stdout": (result.stdout or "")[:4000],
                "stderr": (result.stderr or "")[:4000], 
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            log.error(f"tool_terminal: Command timed out after 120 seconds: {command}")
            return {"status": "error", "message": "Timeout expired after 120 seconds."}
        except Exception as e:
            log.exception(f"tool_terminal: Error executing command: {command}")
            return {"status": "error", "message": f"Error executing command: {e}"}

