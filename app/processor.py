import threading
import queue
from app.api import validate_code_primary, login_microsoft_account
from app.ui import print_colored, update_titlebar, print_lock
from colorama import Fore, Style

import sys
sys.dont_write_bytecode = True # Prevent the creation of .pyc files

def validate_code(session, code, force_refresh_ids=False):
    try:
        result = validate_code_primary(session, code, force_refresh_ids)
        status = result.get('status', 'ERROR')
        message = result.get('message', 'Unknown error')
        
        if isinstance(result, dict):
            if result['status'] == 'VALID':
                title = result['product_title'] if 'product_title' in result else message.split(' | ')[-1] if ' | ' in message else "Unknown Title"
                print_colored(f"{code} | {title}", Fore.GREEN)
                return result
            elif result['status'] == 'VALID_REQUIRES_CARD':
                title = result['product_title'] if 'product_title' in result else message.split(' | ')[-1] if ' | ' in message else "Unknown Title"
                print_colored(f"{code} | {title}", Fore.YELLOW)
                return result
            elif result['status'] == 'REDEEMED':
                print_colored(f"{code} | REDEEMED", Fore.RED)
                return result
            elif result['status'] == 'EXPIRED':
                print_colored(f"{code} | EXPIRED", Fore.RED)
                return result
            elif result['status'] == 'REGION_LOCKED':
                print_colored(f"{code} | REGION_LOCKED", Fore.MAGENTA)
                return result
            elif result['status'] == 'UNKNOWN':
                print_colored(f"{code} | UNKNOWN", Fore.YELLOW)
                return result
            elif result['status'] == 'BALANCE_CODE':
                print_colored(f"{code} | {message.split(' | ', 1)[1] if ' | ' in message else message}", Fore.GREEN)
                return result
            else:
                print_colored(f"{code} | {result['status']}", Fore.RED)
                return result
        else:
            return {"status": "ERROR", "message": "Result is not a dictionary"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


def process_account_batch(accounts_batch, codes_queue, result_files, results_count, processed_codes_lock, processed_codes, proxies=None, rate_limited_accounts=None):
    active_sessions = []
    
    for email, password in accounts_batch:
        session = login_microsoft_account(email, password, proxies)
        
        if not session:
            with print_lock:
                print(f"{Fore.RED}Invalid - {email}{Style.RESET_ALL}")
            continue
            
        with print_lock:
            print(f"{Fore.GREEN}Logged in {email}{Style.RESET_ALL}")
        
        active_sessions.append((email, session, 0))
    
    if not active_sessions:
        return False

    def process_code_with_session(args):
        email, session, code = args
        try:
            result = validate_code(session, code, force_refresh_ids=False)
            return code, result
        except Exception as e:
            print(f"Error in process_code_with_session: {str(e)}")
            return code, {"status": "ERROR", "message": str(e)}

    if codes_queue.empty():
        print("Code queue is empty, nothing to process")
        return True

    batch_codes = []
    try:
        for _ in range(min(15, codes_queue.qsize())):
            code = codes_queue.get_nowait()
            batch_codes.append(code)
    except queue.Empty:
        if not batch_codes:
            print("No codes left to process")
            return True
    
    for email, session, codes_checked in active_sessions[:]:
        
        for code in batch_codes:
            try:
                code_result = process_code_with_session((email, session, code))
                code, result = code_result
                
                status = result['status']
                original_status = result.get('original_status', status)
                
                if status == 'ERROR':
                    with print_lock:
                        print(f"{Fore.RED}Error checking code {code} with account {email}, will retry...{Style.RESET_ALL}")
                    codes_queue.put(code)
                    continue

                elif status == 'RATE_LIMITED':
                    with print_lock:
                        print(f"{Fore.YELLOW}Account {email} got rate-limited after {codes_checked} codes.{Style.RESET_ALL}")   
                        for i, (sess_email, sess_session, sess_codes) in enumerate(active_sessions):
                            if sess_email == email and sess_session == session:
                                active_sessions.pop(i)
                                break

                    result_line = f"{email} - Rate limited after {codes_checked} codes\n"
                    with processed_codes_lock:
                        with open(result_files['RATE_LIMITED'], 'a') as f:
                            f.write(result_line)
                        results_count['RATE_LIMITED'] += 1
                        
                        if rate_limited_accounts is not None:
                            rate_limited_accounts.append(email)
                    # Put rate-limited code at the front of the queue for priority retry
                    temp_codes = []
                    while not codes_queue.empty():
                        try:
                            temp_codes.append(codes_queue.get_nowait())
                        except queue.Empty:
                            break
                    
                    # Put rate-limited code first
                    codes_queue.put(code)
                    # Put back all other codes
                    for temp_code in temp_codes:
                        codes_queue.put(temp_code)
                    
                    return False

                else:
                    if status in ['VALID', 'VALID_REQUIRES_CARD']:
                        result_line = f"{result['message']}\n"
                        file_key = status
                        with processed_codes_lock:
                            results_count[file_key] += 1
                            update_titlebar(results_count)
                            with open(result_files[file_key], 'a') as f:
                                f.write(result_line)
                    elif status == 'BALANCE_CODE':
                        result_line = f"{result['message']}\n"
                        file_key = 'VALID'
                        with processed_codes_lock:
                            results_count[file_key] += 1
                            update_titlebar(results_count)
                            with open(result_files[file_key], 'a') as f:
                                f.write(result_line)
                    elif status == 'REGION_LOCKED':
                        result_line = f"{code} | REGION_LOCKED\n"
                        file_key = 'REGION_LOCKED'
                        with processed_codes_lock:
                            results_count[file_key] += 1
                            update_titlebar(results_count)
                            with open(result_files[file_key], 'a') as f:
                                f.write(result_line)
                    elif original_status in ['EXPIRED', 'REDEEMED'] and original_status in result_files:
                        result_line = f"{result['message']}\n"
                        file_key = original_status
                        with processed_codes_lock:
                            results_count[file_key] += 1
                            with open(result_files[file_key], 'a') as f:
                                f.write(result_line)
                            with open(result_files['INVALID'], 'a') as f:
                                f.write(result_line)
                            results_count['INVALID'] += 1
                            update_titlebar(results_count)
                    elif status == 'UNKNOWN':
                        result_line = f"{code} | UNKNOWN\n"
                        file_key = 'UNKNOWN'
                        with processed_codes_lock:
                            results_count[file_key] += 1
                            update_titlebar(results_count)
                            with open(result_files[file_key], 'a') as f:
                                f.write(result_line)
                    else:
                        issue = result['message']
                        result_line = f"{code} | {issue}\n"
                        file_key = 'INVALID'
                        with processed_codes_lock:
                            results_count[file_key] += 1
                            update_titlebar(results_count)
                            with open(result_files[file_key], 'a') as f:
                                f.write(result_line)

                    with processed_codes_lock:
                        processed_codes.append(code)

                    codes_checked += 1
                    codes_queue.task_done()
                
            except Exception as e:
                with print_lock:
                    print(f"{Fore.RED}Exception checking code {code} with account {email}: {str(e)}{Style.RESET_ALL}")
                codes_queue.put(code)
                continue

    if codes_queue.empty():
        return True
    else:
        return False 