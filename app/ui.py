import ctypes
from colorama import Fore, Style
import threading

import sys
sys.dont_write_bytecode = True # Prevent the creation of .pyc files

print_lock = threading.Lock()

def print_banner():
    banner = """
╔═════════════════════════════════════════╗
║        Microsoft Code Checker           ║
║        By: @insomnicc1                  ║
╚═════════════════════════════════════════╝"""
    print(banner)

def update_titlebar(results_count):
    valid_count = results_count.get('VALID', 0)
    region_locked_count = results_count.get('REGION_LOCKED', 0)
    invalid_count = sum([
        results_count.get('INVALID', 0),
        results_count.get('EXPIRED', 0),
        results_count.get('REDEEMED', 0),
        results_count.get('UNKNOWN', 0)
    ])
    
    title = f"Code checker by @Insomnicc1 | VALID: {valid_count} | Region Locked: {region_locked_count} | Invalid: {invalid_count}"
    ctypes.windll.kernel32.SetConsoleTitleW(title)

def print_colored(message, color):
    with print_lock:
        print(f"{color}{message}{Style.RESET_ALL}") 