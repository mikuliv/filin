"""Агрегированный монитор ресурсов parent + child processes."""
from __future__ import annotations
import json, shutil, subprocess, threading, time
from pathlib import Path
import psutil

class ResourceMonitor:
    def __init__(self, parent_pid: int, output: Path, interval: float = 1.0, stage: str = "unspecified", phase: str = "running", progress=None):
        self.parent_pid, self.output, self.interval = parent_pid, output, interval
        self.stage, self.phase, self.progress = stage, phase, progress
        self.samples, self._stop, self._thread, self.cpu_seconds = [], threading.Event(), None, {}

    def _gpu(self):
        executable = shutil.which("nvidia-smi")
        if not executable: return {"gpu_metrics_available": False}
        try:
            text = subprocess.check_output([executable, "--query-gpu=utilization.gpu,memory.used,power.draw", "--format=csv,noheader,nounits"], text=True, timeout=2).splitlines()[0]
            util, memory, power = [float(value.strip()) for value in text.split(",")]
            return {"gpu_metrics_available": True, "gpu_utilization_percent": util, "gpu_memory_used_mb": memory, "gpu_power_watts": power}
        except Exception: return {"gpu_metrics_available": False}

    def sample(self):
        try: parent = psutil.Process(self.parent_pid); processes = [parent] + parent.children(recursive=True)
        except psutil.Error: processes = []
        rss_parent = rss_children = read_bytes = write_bytes = process_cpu = 0.0
        for index, process in enumerate(processes):
            try:
                memory = process.memory_info().rss / 1024 / 1024
                if index == 0: rss_parent += memory
                else: rss_children += memory
                io = process.io_counters(); read_bytes += io.read_bytes; write_bytes += io.write_bytes
                cpu = process.cpu_times(); self.cpu_seconds[process.pid] = max(self.cpu_seconds.get(process.pid, 0), cpu.user + cpu.system)
                process_cpu += process.cpu_percent(None)
            except psutil.Error: pass
        vm, swap = psutil.virtual_memory(), psutil.swap_memory()
        progress = self.progress() if callable(self.progress) else {}
        item = {"timestamp": time.time(), "stage": self.stage, "phase": self.phase, "parent_pid": self.parent_pid, "child_process_count": max(len(processes)-1, 0),
                "process_cpu_percent": process_cpu, "parent_cpu_percent": process_cpu if len(processes)<=1 else 0.0,
                "children_cpu_percent": process_cpu if len(processes)>1 else 0.0, "system_cpu_percent": psutil.cpu_percent(None),
                "per_core_cpu_percent": psutil.cpu_percent(None, percpu=True), "process_rss_mb": rss_parent,
                "parent_rss_mb": rss_parent, "children_rss_mb": rss_children, "aggregate_rss_mb": rss_parent+rss_children, "system_memory_used_mb": vm.used/1024/1024,
                "system_memory_available_mb": vm.available/1024/1024, "swap_used_mb": swap.used/1024/1024,
                "disk_read_bytes": read_bytes, "disk_write_bytes": write_bytes,
                "completed_tasks": progress.get("completed_tasks"), "active_workers": progress.get("active_workers"), "queued_tasks": progress.get("queued_tasks")}
        item.update(self._gpu()); self.samples.append(item); return item

    def _run(self):
        while not self._stop.wait(self.interval): self.sample()

    def start(self):
        self.sample(); self._thread = threading.Thread(target=self._run, daemon=True); self._thread.start(); return self

    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=self.interval+2)
        self.sample(); self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text("".join(json.dumps(item, ensure_ascii=False)+"\n" for item in self.samples), encoding="utf-8")
        return self.summary()

    def summary(self):
        cpu = sorted(item["system_cpu_percent"] for item in self.samples)
        pick = lambda q: cpu[min(int((len(cpu)-1)*q), len(cpu)-1)] if cpu else 0.0
        rss=sorted(item["aggregate_rss_mb"] for item in self.samples)
        return {"sample_count": len(self.samples), "system_cpu_average": sum(cpu)/len(cpu) if cpu else 0.0,
                "system_cpu_p50": pick(.5), "system_cpu_p95": pick(.95),
                "peak_rss_mb": max((x["process_rss_mb"] for x in self.samples), default=0),
                "peak_children_rss_mb": max((x["children_rss_mb"] for x in self.samples), default=0),
                "process_cpu_seconds": sum(self.cpu_seconds.values()),
                "disk_read_bytes": max((x["disk_read_bytes"] for x in self.samples), default=0),
                "disk_write_bytes": max((x["disk_write_bytes"] for x in self.samples), default=0),
                "gpu_metrics_available": any(x.get("gpu_metrics_available") for x in self.samples)}
