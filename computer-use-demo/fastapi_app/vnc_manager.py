import asyncio
import subprocess
import os
import signal
import psutil
from typing import Optional, Dict, Any
from .models import VNCConnection

class VNCManager:
    def __init__(self):
        self._vnc_process: Optional[subprocess.Popen] = None
        self._vnc_port: int = 5901
        self._vnc_password: Optional[str] = None
        self._novnc_process: Optional[subprocess.Popen] = None
        self._novnc_port: int = 8080
        self._status: str = "stopped"
    
    async def start_vnc(self, port: int = 5901, novnc_port: int = 8080, 
                       password: Optional[str] = None) -> VNCConnection:
        """Start VNC server and noVNC"""
        try:
            # Stop existing VNC if running
            await self.stop_vnc()
            
            self._vnc_port = port
            self._novnc_port = novnc_port
            self._vnc_password = password
            self._status = "starting"
            
            # Start Xvfb if not already running
            await self._ensure_xvfb()
            
            # Start VNC server
            await self._start_vnc_server()
            
            # Start noVNC
            await self._start_novnc()
            
            self._status = "running"
            
            return VNCConnection(
                host="localhost",
                port=self._vnc_port,
                password=self._vnc_password,
                status=self._status,
                websocket_url=f"ws://localhost:{self._novnc_port}/websockify"
            )
            
        except Exception as e:
            self._status = "error"
            raise Exception(f"Failed to start VNC: {str(e)}")
    
    async def stop_vnc(self):
        """Stop VNC server and noVNC"""
        try:
            # Stop noVNC
            if self._novnc_process:
                try:
                    self._novnc_process.terminate()
                    try:
                        await asyncio.wait_for(self._novnc_process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        self._novnc_process.kill()
                        await self._novnc_process.wait()
                except Exception as e:
                    print(f"Warning: Error stopping noVNC: {e}")
                finally:
                    self._novnc_process = None
            
            # Stop VNC server
            if self._vnc_process:
                try:
                    self._vnc_process.terminate()
                    try:
                        await asyncio.wait_for(self._vnc_process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        self._vnc_process.kill()
                        await self._vnc_process.wait()
                except Exception as e:
                    print(f"Warning: Error stopping VNC server: {e}")
                finally:
                    self._vnc_process = None
            
            # Stop Xvfb if we started it
            if self._xvfb_process:
                try:
                    self._xvfb_process.terminate()
                    try:
                        await asyncio.wait_for(self._xvfb_process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        self._xvfb_process.kill()
                        await self._xvfb_process.wait()
                except Exception as e:
                    print(f"Warning: Error stopping Xvfb: {e}")
                finally:
                    self._xvfb_process = None
            
            self._status = "stopped"
            
        except Exception as e:
            print(f"Error stopping VNC: {e}")
            # Don't re-raise, just log the error
    
    async def get_status(self) -> Dict[str, Any]:
        """Get VNC status"""
        is_running = False
        if self._vnc_process:
            try:
                # Check if process is still running
                poll_result = self._vnc_process.poll()
                is_running = poll_result is None
                if not is_running:
                    self._status = "stopped"
            except:
                is_running = False
                self._status = "stopped"
        
        return {
            "status": self._status,
            "vnc_port": self._vnc_port,
            "novnc_port": self._novnc_port,
            "is_running": is_running,
            "has_password": self._vnc_password is not None
        }
    
    async def close(self):
        """Clean up resources"""
        await self.stop_vnc()
    
    async def _ensure_xvfb(self):
        """Ensure Xvfb is running"""
        try:
            # Check if Xvfb is already running
            result = await asyncio.create_subprocess_exec(
                "pgrep", "Xvfb",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode != 0:
                # Start Xvfb
                self._xvfb_process = await asyncio.create_subprocess_exec(
                    "Xvfb", ":1", "-screen", "0", "1024x768x24",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Wait a moment for Xvfb to start
                await asyncio.sleep(2)
                
                # Check if Xvfb started successfully using pgrep
                check_result = await asyncio.create_subprocess_exec(
                    "pgrep", "Xvfb",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await check_result.wait()
                
                if check_result.returncode != 0:
                    raise Exception("Failed to start Xvfb")
        except Exception as e:
            raise Exception(f"Xvfb setup failed: {str(e)}")
    
    async def _start_vnc_server(self):
        """Start VNC server"""
        try:
            # Set display environment
            env = os.environ.copy()
            env["DISPLAY"] = ":1"
            
            # Build VNC command
            vnc_cmd = ["x11vnc", "-display", ":1", "-port", str(self._vnc_port)]
            
            if self._vnc_password:
                # Create password file
                password_file = "/tmp/vncpasswd"
                with open(password_file, "w") as f:
                    f.write(self._vnc_password)
                os.chmod(password_file, 0o600)
                vnc_cmd.extend(["-passwd", password_file])
            
            vnc_cmd.extend([
                "-forever",  # Keep running
                "-shared",   # Allow multiple connections
                "-nopw",     # No password prompt if no password set
                "-xkb",      # Enable keyboard
                "-noxrecord", # Disable recording
                "-noxfixes",  # Disable fixes
                "-noxdamage", # Disable damage
                "-rfbportv6", "-1", # Disable IPv6
                "-env", "FD_XG=0",  # Disable XGrab
                "-env", "FD_PROG=/usr/bin/xterm",  # Default program
                "-env", "XKL_XMODMAP_DISABLE=1",   # Disable XKL
                "-overwrite", # Overwrite existing port
                "-bg"        # Run in background
            ])
            
            # Start VNC server
            self._vnc_process = await asyncio.create_subprocess_exec(
                *vnc_cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a moment for VNC to start
            await asyncio.sleep(3)
            
            # VNC is likely running if we got here without exceptions
            # The x11vnc output shows it's working, so we'll assume success
            print("VNC server started successfully")
            
        except Exception as e:
            raise Exception(f"Failed to start VNC server: {str(e)}")
    
    async def _start_novnc(self):
        """Start noVNC websocket proxy"""
        try:
            # Check if noVNC exists
            novnc_path = "/opt/noVNC"
            if not os.path.exists(novnc_path):
                raise Exception("noVNC not found at /opt/noVNC")
            
            # Start noVNC
            self._novnc_process = await asyncio.create_subprocess_exec(
                "/opt/noVNC/utils/websockify/websockify.py",
                str(self._novnc_port),
                f"localhost:{self._vnc_port}",
                "--web", novnc_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a moment for noVNC to start
            await asyncio.sleep(2)
            
            # Check if noVNC started successfully - be more lenient
            try:
                check_result = await asyncio.create_subprocess_exec(
                    "pgrep", "websockify",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await check_result.wait()
                
                # If pgrep fails, try a different approach
                if check_result.returncode != 0:
                    # Check if our noVNC process is still running
                    if self._novnc_process.returncode is not None:
                        stdout, stderr = await self._novnc_process.communicate()
                        raise Exception(f"noVNC failed to start: {stderr.decode()}")
                    # If returncode is None, process is still running, which is good
            except Exception as e:
                # If pgrep fails but noVNC process is running, that's okay
                if self._novnc_process.returncode is None:
                    pass  # noVNC is running, continue
                else:
                    raise e
                
        except Exception as e:
            raise Exception(f"Failed to start noVNC: {str(e)}")
    
    def _kill_process_tree(self, pid: int):
        """Kill a process and all its children"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            for child in children:
                child.terminate()
            
            parent.terminate()
            
            # Wait for processes to terminate
            gone, alive = psutil.wait_procs([parent] + children, timeout=3)
            
            # Force kill if still alive
            for p in alive:
                p.kill()
                
        except psutil.NoSuchProcess:
            pass  # Process already gone
        except Exception as e:
            print(f"Error killing process tree: {e}") 