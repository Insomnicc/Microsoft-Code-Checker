import os
import threading
from datetime import datetime
from queue import Queue
from colorama import init, Fore, Style
from app.config import read_accounts, read_codes, read_proxies, get_random_proxy, remove_rate_limited_accounts
from app.ui import print_banner, update_titlebar
from app.processor import process_account_batch

import sys
sys.dont_write_bytecode = True # Prevent the creation of .pyc files

init(autoreset=True)

def main():
    if not os.path.exists('results'):
        os.makedirs('results')
    
    accounts = read_accounts()
    if not accounts:
        print(f"{Fore.RED}No valid accounts found. Exiting.{Style.RESET_ALL}")
        return
        
    codes = read_codes()
    if not codes:
        print(f"{Fore.RED}No valid codes found. Exiting.{Style.RESET_ALL}")
        return
    
    proxies = read_proxies()
    if proxies:
        print(f"{Fore.GREEN}Using {len(proxies)} proxies{Style.RESET_ALL}")
    
    while True:
        try:
            batch_size = int(input(f"{Fore.CYAN}Thread Count? (1-{len(accounts)}): {Style.RESET_ALL}"))
            if 1 <= batch_size <= len(accounts):
                break
            else:
                print(f"{Fore.RED}Please enter a number between 1 and {len(accounts)}{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")
    
    # Create timestamp for the results folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_folder = f"results/check_{timestamp}"
    os.makedirs(results_folder, exist_ok=True)
    
    result_files = {
        'VALID': f'{results_folder}/valid_codes.txt',
        'VALID_REQUIRES_CARD': f'{results_folder}/valid_requires_card_codes.txt',
        'INVALID': f'{results_folder}/invalid_codes.txt',
        'EXPIRED': f'{results_folder}/expired_codes.txt',
        'REDEEMED': f'{results_folder}/redeemed_codes.txt',
        'UNKNOWN': f'{results_folder}/unknown_codes.txt',
        'REGION_LOCKED': f'{results_folder}/region_locked_codes.txt',
        'RATE_LIMITED': f'{results_folder}/rate_limited.txt'
    }
    
    results_count = {status: 0 for status in result_files.keys()}
    
    update_titlebar(results_count)
    
    for file_path in result_files.values():
        with open(file_path, 'a'):
            pass
    
    with open(f'error_log.txt', 'w'):
        pass
    
    # Create a summary file
    with open(f'{results_folder}/summary.txt', 'w') as f:
        f.write(f"Code Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total Codes: {len(codes)}\n")
        f.write(f"Total Accounts: {len(accounts)}\n")
        f.write(f"Batch Size: {batch_size}\n")
        if proxies:
            f.write(f"Proxies Used: {len(proxies)}\n")
        f.write("\nResults will be updated as checks complete...\n")
    
    codes_queue = Queue()
    for code in codes:
        codes_queue.put(code)
    
    print(f"Added {len(codes)} codes to the queue")
    
    processed_codes = []
    processed_codes_lock = threading.Lock()
    print_lock = threading.Lock()
    
    rate_limited_accounts = []
    
    for i in range(0, len(accounts), batch_size):
        accounts_batch = accounts[i:i + batch_size]
        all_codes_processed = False
        
        # Process each account directly without using ThreadPoolExecutor
        for account in accounts_batch:
            proxy = get_random_proxy(proxies) if proxies else None
            result = process_account_batch(
                [account],
                codes_queue,
                result_files,
                results_count,
                processed_codes_lock,
                processed_codes,
                proxy,
                rate_limited_accounts
            )
            if result:
                all_codes_processed = True
        
        if all_codes_processed:
            with print_lock:
                print(f"{Fore.YELLOW}All codes have been processed.{Style.RESET_ALL}")
            
            # Update summary file with final results
            with open(f'{results_folder}/summary.txt', 'w') as f:
                f.write(f"Code Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total Codes: {len(codes)}\n")
                f.write(f"Total Accounts: {len(accounts)}\n")
                f.write(f"Batch Size: {batch_size}\n")
                if proxies:
                    f.write(f"Proxies Used: {len(proxies)}\n")
                f.write("\nFinal Results:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Valid Codes: {results_count['VALID']}\n")
                f.write(f"Valid (Requires Card): {results_count['VALID_REQUIRES_CARD']}\n")
                f.write(f"Region Locked: {results_count['REGION_LOCKED']}\n")
                f.write(f"Invalid: {results_count['INVALID']}\n")
                f.write(f"Expired: {results_count['EXPIRED']}\n")
                f.write(f"Redeemed: {results_count['REDEEMED']}\n")
                f.write(f"Unknown: {results_count['UNKNOWN']}\n")
                f.write(f"Rate Limited Accounts: {results_count['RATE_LIMITED']}\n")
            
            while True:
                response = input(f"{Fore.CYAN}Exit the program? (yes/no): {Style.RESET_ALL}").lower().strip()
                if response in ['yes', 'y']:
                    print(f"{Fore.GREEN}Exiting program...{Style.RESET_ALL}")
                    if rate_limited_accounts:
                        print(f"{Fore.YELLOW}Found {len(rate_limited_accounts)} rate-limited accounts.{Style.RESET_ALL}")
                        remove_response = input(f"{Fore.CYAN}Remove rate-limited accounts from accounts.txt? (yes/no): {Style.RESET_ALL}").lower().strip()
                        if remove_response in ['yes', 'y']:
                            remove_rate_limited_accounts(rate_limited_accounts)
                    return
                elif response in ['no', 'n']:
                    print(f"{Fore.YELLOW}Continuing with next batch...{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED}Please enter 'yes' or 'no'{Style.RESET_ALL}")
        
        with processed_codes_lock:
            remaining_codes = [c for c in codes if c not in processed_codes]
            with open('codes.txt', 'w') as f:
                f.write('\n'.join(remaining_codes))
            
            # Update summary file with current progress
            with open(f'{results_folder}/summary.txt', 'w') as f:
                f.write(f"Code Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total Codes: {len(codes)}\n")
                f.write(f"Total Accounts: {len(accounts)}\n")
                f.write(f"Batch Size: {batch_size}\n")
                if proxies:
                    f.write(f"Proxies Used: {len(proxies)}\n")
                f.write("\nCurrent Progress:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Processed Codes: {len(processed_codes)}\n")
                f.write(f"Remaining Codes: {len(remaining_codes)}\n")
                f.write(f"Valid Codes: {results_count['VALID']}\n")
                f.write(f"Valid (Requires Card): {results_count['VALID_REQUIRES_CARD']}\n")
                f.write(f"Region Locked: {results_count['REGION_LOCKED']}\n")
                f.write(f"Invalid: {results_count['INVALID']}\n")
                f.write(f"Expired: {results_count['EXPIRED']}\n")
                f.write(f"Redeemed: {results_count['REDEEMED']}\n")
                f.write(f"Unknown: {results_count['UNKNOWN']}\n")
                f.write(f"Rate Limited Accounts: {results_count['RATE_LIMITED']}\n")
    
    with print_lock:
        print(f"{Fore.GREEN}Finished! Processed {len(processed_codes)} codes total.{Style.RESET_ALL}")
    
    # Update summary file with final results
    with open(f'{results_folder}/summary.txt', 'w') as f:
        f.write(f"Code Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total Codes: {len(codes)}\n")
        f.write(f"Total Accounts: {len(accounts)}\n")
        f.write(f"Batch Size: {batch_size}\n")
        if proxies:
            f.write(f"Proxies Used: {len(proxies)}\n")
        f.write("\nFinal Results:\n")
        f.write("-" * 20 + "\n")
        f.write(f"Valid Codes: {results_count['VALID']}\n")
        f.write(f"Valid (Requires Card): {results_count['VALID_REQUIRES_CARD']}\n")
        f.write(f"Region Locked: {results_count['REGION_LOCKED']}\n")
        f.write(f"Invalid: {results_count['INVALID']}\n")
        f.write(f"Expired: {results_count['EXPIRED']}\n")
        f.write(f"Redeemed: {results_count['REDEEMED']}\n")
        f.write(f"Unknown: {results_count['UNKNOWN']}\n")
        f.write(f"Rate Limited Accounts: {results_count['RATE_LIMITED']}\n")
    
    while True:
        response = input(f"{Fore.CYAN}Exit the program? (yes/no): {Style.RESET_ALL}").lower().strip()
        if response in ['yes', 'y']:
            print(f"{Fore.GREEN}Exiting program...{Style.RESET_ALL}")
            if rate_limited_accounts:
                print(f"{Fore.YELLOW}Found {len(rate_limited_accounts)} rate-limited accounts.{Style.RESET_ALL}")
                remove_response = input(f"{Fore.CYAN}Remove rate-limited accounts from accounts.txt? (yes/no): {Style.RESET_ALL}").lower().strip()
                if remove_response in ['yes', 'y']:
                    remove_rate_limited_accounts(rate_limited_accounts)
            break
        elif response in ['no', 'n']:
            print(f"{Fore.YELLOW}Program will remain open.{Style.RESET_ALL}")
            input(f"{Fore.CYAN}Press Enter to exit when ready...{Style.RESET_ALL}")
            if rate_limited_accounts:
                print(f"{Fore.YELLOW}Found {len(rate_limited_accounts)} rate-limited accounts.{Style.RESET_ALL}")
                remove_response = input(f"{Fore.CYAN}Remove rate-limited accounts from accounts.txt? (yes/no): {Style.RESET_ALL}").lower().strip()
                if remove_response in ['yes', 'y']:
                    remove_rate_limited_accounts(rate_limited_accounts)
            break
        else:
            print(f"{Fore.RED}Please enter 'yes' or 'no'{Style.RESET_ALL}")


if __name__ == "__main__":
    print_banner()
    main() 