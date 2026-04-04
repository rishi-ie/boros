from ._internal.job_state import active_jobs

def tool_terminal_input(params: dict, kernel=None) -> dict:
    job_id = params.get("job_id")
    text = params.get("text")
    
    if not job_id or not text:
        return {"status": "error", "message": "Requires job_id and text."}
        
    if job_id not in active_jobs:
        return {"status": "error", "message": f"Job {job_id} not found or terminated."}
        
    proc = active_jobs[job_id]
    if proc.poll() is not None:
        del active_jobs[job_id]
        return {"status": "error", "message": f"Job {job_id} is already dead. Returned: {proc.returncode}"}
        
    try:
        if not text.endswith("\n"): text += "\n"
        proc.stdin.write(text)
        proc.stdin.flush()
        return {"status": "ok", "message": "Input sent."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
