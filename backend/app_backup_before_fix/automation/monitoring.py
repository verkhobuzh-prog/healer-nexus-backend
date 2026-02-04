import psutil
from app.config import settings

async def collect_system_metrics():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    alerts = []
    if cpu > settings.CRITICAL_CPU:
        alerts.append(f"⚠️ CPU: {cpu}%")
    if ram > settings.CRITICAL_RAM:
        alerts.append(f"⚠️ RAM: {ram}%")
        
    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "alerts": alerts
    }
