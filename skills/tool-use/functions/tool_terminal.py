import subprocess
import uuid
import threading
from ._internal.job_state import active_jobs

import logging

log = logging.getLogger(__name__)

def tool_terminal(params: dict, kernel=None) -> dict:
    command = params.get("command")
    background = params.get("background", False)
    
    if not command: 
        log.error("tool_terminal: No command provided.")
        return {"status": "error", "message": "No command provided."}
    
    log.info(f"tool_terminal: Executing command: {command}, background: {background}")

    if background:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        try:
            proc = subprocess.Popen(
                command, shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            active_jobs[job_id] = proc
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
