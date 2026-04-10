from ._internal.job_state import active_jobs

def tool_terminal_kill(params: dict, kernel=None) -> dict:
    job_id = params.get("job_id")
    if not job_id: return {"status": "error", "message": "job_id required"}
    
    if job_id in active_jobs:
        proc = active_jobs[job_id]["process"]
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
            if proc.poll() is None:
                proc.kill()
        del active_jobs[job_id]
        return {"status": "ok", "killed": True}
    return {"status": "error", "message": "job_id not found."}
