import random

import sys
sys.dont_write_bytecode = True # Prevent the creation of .pyc files

def read_accounts():
    try:
        with open('accounts.txt', 'r', encoding='utf8') as f:
            accounts = []
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    email, password = line.split(':', 1)
                    accounts.append((email.strip(), password.strip()))
            print(f"Loaded {len(accounts)} accounts from accounts.txt")
            return accounts
    except FileNotFoundError:
        print("accounts.txt not found. Please create it with email:password format")
        return []
    except Exception as e:
        print(f"Error reading accounts.txt: {str(e)}")
        return []


def read_codes():
    try:
        with open('codes.txt', 'r', encoding='utf8') as f:
            codes = []
            for line in f:
                line = line.strip()
                if line:
                    # Split by | and take the first part, then strip whitespace
                    code = line.split('|')[0].strip()
                    if code:  # Only add if we got a valid code
                        codes.append(code)
            print(f"Loaded {len(codes)} codes from codes.txt")
            return codes
    except FileNotFoundError:
        print("codes.txt not found. Please create it with one code per line")
        return []
    except Exception as e:
        print(f"Error reading codes.txt: {str(e)}")
        return []


def read_proxies():
    try:
        with open('proxies.txt', 'r', encoding='utf8') as f:
            proxies = []
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    proxy = line.strip()
                    proxies.append(proxy)
            print(f"Loaded {len(proxies)} proxies from proxies.txt")
            return proxies
    except FileNotFoundError:
        print("proxies.txt not found. Running without proxies.")
        return []
    except Exception as e:
        print(f"Error reading proxies.txt: {str(e)}")
        return []


def get_random_proxy(proxies):
    if not proxies:
        return None
    proxy = random.choice(proxies)
    if proxy.count(':') == 3:
        ip, port, username, password = proxy.split(':')
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
    else:
        proxy_url = f"http://{proxy}"
    
    return {
        'http': proxy_url,
        'https': proxy_url
    }


def remove_rate_limited_accounts(rate_limited_accounts):
    if not rate_limited_accounts:
        print("No rate-limited accounts to remove.")
        return
        
    try:
        with open('accounts.txt', 'r', encoding='utf8') as f:
            accounts_lines = f.readlines()

        initial_count = len(accounts_lines)
        
        filtered_accounts = [line for line in accounts_lines if ':' in line.strip() and line.strip().split(':', 1)[0].strip() not in rate_limited_accounts]
                    
        with open('accounts.txt', 'w', encoding='utf8') as f:
            f.write(''.join(filtered_accounts))
            
        removed_count = initial_count - len(filtered_accounts)
        print(f"Successfully removed {removed_count} rate-limited accounts from accounts.txt")
        print(f"Remaining accounts: {len(filtered_accounts)}")
        
    except Exception as e:
        print(f"Error removing rate-limited accounts: {str(e)}") 