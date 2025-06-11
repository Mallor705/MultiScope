import os
import signal
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Set
from functools import lru_cache
import psutil
from ..core.logger import Logger

class ProcessService:
    """Serviço responsável por gerenciar processos das instâncias do jogo."""
    def __init__(self, logger: Logger):
        """Inicializa o serviço de processos com logger e lista de PIDs."""
        self.logger = logger
        self.pids: List[int] = []
        self._terminated_pids: Set[int] = set()
    
    def cleanup_previous_instances(self, proton_path: Optional[Path], exe_path: Path) -> None:
        """Finaliza instâncias anteriores do jogo que estejam em execução."""
        self.logger.info(f"Terminating previous instances of '{exe_path.name}'...")
        
        # Otimização: buscar apenas processos relevantes
        exe_name = exe_path.name.lower()
        proton_name = proton_path.name.lower() if proton_path else None
        
        terminated_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skip already terminated processes
                if proc.info['pid'] in self._terminated_pids:
                    continue
                    
                proc_name = (proc.info['name'] or '').lower()
                cmdline = proc.info['cmdline'] or []
                
                # Quick filter by process name first
                if proton_path is None:
                    # Native game - check if process name matches or exe in cmdline
                    if exe_name not in proc_name:
                        cmdline_str = ' '.join(cmdline).lower()
                        if str(exe_path).lower() not in cmdline_str:
                            continue
                else:
                    # Proton game - quick filter by proton or exe
                    if (proton_name and proton_name not in proc_name) and exe_name not in proc_name:
                        cmdline_str = ' '.join(cmdline).lower()
                        if not (str(proton_path).lower() in cmdline_str and str(exe_path).lower() in cmdline_str):
                            continue
                
                # If we get here, terminate the process
                proc.terminate()
                self._terminated_pids.add(proc.info['pid'])
                terminated_count += 1
                
                # Small delay only for first few processes
                if terminated_count <= 3:
                    time.sleep(0.5)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if terminated_count > 0:
            self.logger.info(f"Terminated {terminated_count} previous instances")
            time.sleep(1)  # Final cleanup delay
    
    def launch_instance(self, cmd: List[str], log_file: Path, env: dict, cwd: Optional[Path] = None, nice_value: Optional[int] = None) -> int:
        """Lança uma instância do jogo e retorna o PID do processo."""
        self.logger.info(f"Launching process with command: {' '.join(cmd)}")
        self.logger.info(f"Environment variables: {env}")
        if cwd:
            self.logger.info(f"Working directory (cwd): {cwd}")
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd, 
                stdout=log, 
                stderr=subprocess.STDOUT,
                env=env,
                cwd=cwd,
                preexec_fn=os.setsid
            )
        
        if nice_value is not None:
            try:
                psutil.Process(process.pid).nice(nice_value)
                self.logger.info(f"Set nice value of PID {process.pid} to {nice_value}")
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                self.logger.warning(f"Failed to set nice value for PID {process.pid}: {e}")

        self.pids.append(process.pid)
        return process.pid
    
    def terminate_all(self) -> None:
        """Finaliza todos os processos gerenciados."""
        if not self.pids:
            return
            
        self.logger.info(f"Terminating PIDs: {self.pids}")
        
        # Terminate all processes first
        for pid in self.pids[:]:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                self._terminated_pids.add(pid)
            except (ProcessLookupError, OSError):
                self.pids.remove(pid)
        
        # Wait a bit for graceful termination
        if self.pids:
            time.sleep(2)
            
        # Force kill remaining processes
        for pid in self.pids[:]:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                self.pids.remove(pid)
            except (ProcessLookupError, OSError):
                pass
    
    @lru_cache(maxsize=32)
    def _check_pid_exists(self, pid: int) -> bool:
        """Cache para verificação de existência de PID."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def monitor_processes(self) -> bool:
        """Verifica se ainda existem processos em execução."""
        if not self.pids:
            return False
            
        alive_pids = []
        for pid in self.pids:
            if self._check_pid_exists(pid):
                alive_pids.append(pid)
            else:
                # Clear from cache when process dies
                self._check_pid_exists.cache_clear()
        
        self.pids = alive_pids
        return len(alive_pids) > 0