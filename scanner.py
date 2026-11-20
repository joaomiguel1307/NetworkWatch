"""Descoberta básica de dispositivos na rede local autorizada."""
import ipaddress
import platform
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_local_network():
    """Obtém uma rede IPv4 privada da interface local."""
    candidates = []
    if platform.system().lower() == "linux":
        try:
            output = subprocess.check_output(
                ["ip", "-o", "-f", "inet", "addr", "show", "scope", "global"],
                text=True, stderr=subprocess.DEVNULL, timeout=3
            )
            for item in re.findall(r"inet\s+(\d+\.\d+\.\d+\.\d+/\d+)", output):
                interface = ipaddress.ip_interface(item)
                if interface.ip.is_private and not interface.ip.is_loopback:
                    candidates.append(interface.network)
        except (OSError, subprocess.SubprocessError):
            pass

    if candidates:
        network = candidates[0]
        if network.num_addresses > 256:
            network = ipaddress.ip_network(f"{network.network_address}/24", strict=False)
        return network

    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        local_ip = sock.getsockname()[0]
    except OSError:
        local_ip = "127.0.0.1"
    finally:
        sock.close()
    address = ipaddress.ip_address(local_ip)
    if not address.is_private:
        raise RuntimeError("Não foi possível identificar uma rede privada local.")
    return ipaddress.ip_network(f"{local_ip}/24", strict=False)


def get_mac(ip):
    if platform.system().lower() != "linux":
        return None
    try:
        output = subprocess.check_output(
            ["ip", "neigh", "show", ip], text=True,
            stderr=subprocess.DEVNULL, timeout=2
        )
        match = re.search(r"lladdr\s+([0-9a-f:]{17})", output, re.I)
        return match.group(1).upper() if match else None
    except (OSError, subprocess.SubprocessError):
        return None


def ping_host(ip):
    system = platform.system().lower()
    command = (
        ["ping", "-n", "1", "-w", "1000", str(ip)]
        if system == "windows"
        else ["ping", "-n", "-c", "1", "-W", "1", str(ip)]
    )
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=2
        )
        if result.returncode != 0:
            return None
        match = re.search(r"time[=<]([0-9.]+)\s*ms", result.stdout, re.I)
        latency = float(match.group(1)) if match else None
        return {"ip": str(ip), "latency_ms": latency, "mac": get_mac(str(ip))}
    except (OSError, subprocess.SubprocessError):
        return None


def scan_local_network():
    network = get_local_network()
    found = []
    with ThreadPoolExecutor(max_workers=64) as pool:
        futures = [pool.submit(ping_host, ip) for ip in network.hosts()]
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
    found.sort(key=lambda item: tuple(int(part) for part in item["ip"].split(".")))
    return found, str(network)
