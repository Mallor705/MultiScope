import os
import signal
import subprocess
import time
from pathlib import Path
from typing import List
import psutil

class ProcessService:
    def __init__(self, logger):
        self.logger = logger
        self.pids: List[int] = []
    
    def cleanup_previous_instances(self, proton_path: Path, exe_path: Path):
        """Kill existing game instances"""
        self.logger.info(f"Terminating previous instances of '{exe_path.name}'...")
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if (str(proton_path) in cmdline and str(exe_path) in cmdline):
                    proc.terminate()
                    time.sleep(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def launch_instance(self, cmd: List[str], log_file: Path, env: dict) -> int:
        """Launch game instance and return PID"""
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd, 
                stdout=log, 
                stderr=subprocess.STDOUT,
                env=env,
                preexec_fn=os.setsid
            )
        
        self.pids.append(process.pid)
        return process.pid
    
    def terminate_all(self):
        """Terminate all managed processes"""
        if not self.pids:
            return
            
        self.logger.info(f"Terminating PIDs: {self.pids}")
        
        for pid in self.pids[:]:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(2)
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                self.pids.remove(pid)
            except (ProcessLookupError, OSError):
                pass
    
    def monitor_processes(self) -> bool:
        """Check if any processes are still running"""
        alive_pids = []
        for pid in self.pids:
            try:
                os.kill(pid, 0)  # Check if process exists
                alive_pids.append(pid)
            except OSError:
                pass
        
        self.pids = alive_pids
        return len(alive_pids) > 0