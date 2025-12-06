from curl_cffi import requests
import re
import json
import time
import random
import os
import threading
from datetime import datetime
import uuid
import sys
import queue
import ctypes
import asyncio
import urllib.parse
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.dont_write_bytecode = True # Prevent the creation of .pyc files
init(autoreset=True)

print_lock = threading.Lock()

def update_titlebar(results_count, processed_count, total_codes):
    valid_count = results_count.get('VALID', 0)
    validpi_count = results_count.get('VALID_REQUIRES_CARD', 0)
    region_locked_count = results_count.get('REGION_LOCKED', 0)
    invalid_count = sum([
        results_count.get('INVALID', 0),
        results_count.get('EXPIRED', 0),
        results_count.get('REDEEMED', 0),
        results_count.get('UNKNOWN', 0)
    ])
    
    title = f"Code checker by @Insomnicc1 | Checked: {processed_count}/{total_codes} | VALID: {valid_count} | VALIDPI: {validpi_count} | Region Locked: {region_locked_count} | Invalid: {invalid_count}"
    ctypes.windll.kernel32.SetConsoleTitleW(title)

def print_colored(message, color):
    with print_lock:
        print(f"{color}{message}{Style.RESET_ALL}")

def read_accounts():
    try:
        with open('accs.txt', 'r', encoding='utf8') as f:
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
    if proxy.count("@") >= 1:
        credentials, addr = proxy.split("@", 1)
        username, password = credentials.split(":", 1)
        proxy_url = f"http://{username}:{password}@{addr}"
    elif proxy.count(':') == 3:
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

def generate_reference_id(): # Basic working "reverse" of microsofts reference id stuff
    timestamp_val = int(time.time() // 30)
    
    n = f'{timestamp_val:08X}'
    o = (uuid.uuid4().hex + uuid.uuid4().hex).upper()
    result_chars = []
    for e in range(64):
        if e % 8 == 1:
            result_chars.append(n[(e - 1) // 8])
        else:
            result_chars.append(o[e])
            
    return "".join(result_chars) 


def decodin(txt):
    return json.loads(f'"{txt}"')

def login_microsoft_account(email, password, proxies=None) -> tuple[requests.Session, str]:
    session = requests.Session(impersonate="chrome")
    if proxies:
        session.proxies = proxies    
    try:    
        login_response = session.post(
            f"https://login.live.com/ppsecure/post.srf?username=%7bemail%7d&client_id=0000000048170EF2&contextid=072929F9A0DD49A4&opid=D34F9880C21AE341&bk=1765024327&uaid=a5b22c26bc704002ac309462e8d061bb&pid=15216&prompt=none",
            data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': "-Drzud3DzKKJtVD9IfM5xwJywwEjJp5zvvJmrSyu*RKOf!PbgSCQ7ReuKFS*sIpTV5r28epGtqBhqH3JYvND4!onwSWz2JEkvdeewUQC6HmAXRgjYBzSlf0mjEYbx3ULc7oy5fUK3LDSb*CnkAG03FLzwVPmT5WjYu4sE5Wqd93pCx0USJK4jelAWNvsMog0Rmj90tmeCd*1pDYjkINyPEgQSkv6y5GPuX!GmYwKccALUt*!SRaI02p*XUqePtNtJzw$$"},
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                "Cookie": "MSPRequ=id=N&lt=1765024327&co=1; uaid=a5b22c26bc704002ac309462e8d061bb; MSPOK=$uuid-90ce4cdb-2718-4d7e-9889-4136cfacc5b2; OParams=11O.DhmByHnT9kscyud7VyWQt5uWQuQOYWZ9O2v5E49mKxVoKsSZaB4KnwkAQCVjghW9A6M8syem4sO!g4KOfietehdD7U2eXeVo8eUsorIQv1deGf6v43egdNizv1*agwrVh2OTg7pu2SRE3SougNTvzlNUNe1BgtO4HFlLRm6UoEW3PNBIxuVPmFBiPs0wEU162jlfO8yA1!QZV7KKArG8NPChj0kf1IOfR95k0fIfa0!fDW8Md44pKHa3rkU0Um0KB03YEBdWMOAbJlX5RONIL3M31WhD4LG3GPAoBPAMCN9fMk2rHlwix8g6MOW3HKxDT4I0TlKrYHDBJejZWSmI23T3v2kr1MKaL9vEQoaTwOJf9VloMFBi7yB!kisHZn0BkjE!HGWhaliwYdluhJUCu1g$"
            },
            timeout=10,
            allow_redirects=False
        )
        if login_response.status_code != 302 or "error=interaction_required" in login_response.headers['Location']:
            return None, None

        token = urllib.parse.unquote(login_response.headers['Location'].split('access_token=')[1].split('&')[0])

        session.get(
            "https://buynowui.production.store-web.dynamics.com/akam/13/79883e11"
        )       
        return session, token
        
    except Exception as e:
        print(f"Error in login_microsoft_account: {e}")
        return None, None

def get_store_cart_state(session, force_refresh=False, token=None):
    try:
        if force_refresh:
            if hasattr(session, 'store_state'):
                delattr(session, 'store_state')
                
        if not force_refresh and hasattr(session, 'store_state'):
            return session.store_state
            
        ms_cv = f"xddT7qMNbECeJpTq.6.2"
        
        url = 'https://www.microsoft.com/store/purchase/buynowui/redeemnow'
        params = {
            'ms-cv': ms_cv,
            'market': 'US',
            'locale': 'en-GB',
            'clientName': 'AccountMicrosoftCom'
        }
        # Redeemnow payload,, MSATicket, MS_CV
        payload = {'data': '{"usePurchaseSdk":true}', 'market': 'US', 'cV': ms_cv, 'locale': 'en-GB', 'msaTicket': token, 'pageFormat': 'full', 'urlRef': 'https://account.microsoft.com/billing/redeem', 'isRedeem': 'true', 'clientType': 'AccountMicrosoftCom', 'layout': 'Inline', 'cssOverride': 'AMC', 'scenario': 'redeem', 'timeToInvokeIframe': '4977', 'sdkVersion': 'VERSION_PLACEHOLDER'}
        
        try:
            response = session.post(url, params=params, data=payload, timeout=30, allow_redirects=True)
        except Exception as e:
            return None
            
        text = response.text
        match = re.search(r'window\.__STORE_CART_STATE__=({.*?});', text, re.DOTALL)
        if not match:
            return None
            
        try:
            store_state = json.loads(match.group(1))
            extracted_values = {
                'ms_cv': store_state.get('appContext', {}).get('cv', ''),
                'correlation_id': store_state.get('appContext', {}).get('correlationId', ''),
                'tracking_id': store_state.get('appContext', {}).get('trackingId', ''),
                'vector_id': store_state.get('appContext', {}).get('vectorId', ''),
                'muid': store_state.get('appContext', {}).get('muid', ''),
                'alternative_muid': store_state.get('appContext', {}).get('alternativeMuid', '')
            }
            
            session.store_state = extracted_values
            
            return extracted_values
            
        except json.JSONDecodeError as e:
            return None
            
    except Exception as e:
        print(f"Error in get_store_cart_state: {e}")
        return None


async def prepare_redeem_api_call(session, code, headers, payload):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        response = await loop.run_in_executor(
            None,
            lambda: session.post(
                'https://buynow.production.store-web.dynamics.com/v1.0/Redeem/PrepareRedeem/?appId=RedeemNow&context=LookupToken',
                headers=headers,
                json=payload,
                timeout=30
            )
        )
        return response
    except Exception as e:
        return None

async def validate_code_primary(session, code, force_refresh_ids=False, token=None):
    try:
        if not code or len(code) < 5 or ' ' in code or any (char in ['A', 'E', 'I', 'O', 'U', 'L', 'S', '0', '1', '5'] for char in code):
            return {"status": "INVALID", "message": "Invalid code format"}
        
        store_state = get_store_cart_state(session, force_refresh=force_refresh_ids, token=token)
        if not store_state:
            store_state = get_store_cart_state(session, force_refresh=True, token=token)
            if not store_state:
                return {"status": "ERROR", "message": "Failed to get store cart state"}
        
        try:
            headers = {
                "host": "buynow.production.store-web.dynamics.com",
                "connection": "keep-alive",
                "x-ms-tracking-id": store_state['tracking_id'],
                "sec-ch-ua-platform": "\"Windows\"",
                "authorization": f"WLID1.0=t={token}",
                "x-ms-client-type": "AccountMicrosoftCom",
                "x-ms-market": "US",
                "sec-ch-ua": "\"Chromium\";v=\"142\", \"Microsoft Edge\";v=\"142\", \"Not_A Brand\";v=\"99\"",
                "ms-cv": store_state['ms_cv'],
                "sec-ch-ua-mobile": "?0",
                "x-ms-reference-id": generate_reference_id(),
                "x-ms-vector-id": store_state['vector_id'],
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                "x-ms-correlation-id": store_state['correlation_id'],
                "content-type": "application/json",
                "x-authorization-muid": store_state['alternative_muid'],
                "accept": "*/*",
                "origin": "https://www.microsoft.com",
                "sec-fetch-site": "cross-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://www.microsoft.com/",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9"
            }
            payload = {
                "market": "US",
                "language": "en-US",
                "flights": ["sc_abandonedretry","sc_addasyncpitelemetry","sc_adddatapropertyiap","sc_addgifteeduringordercreation","sc_aemparamforimage","sc_aemrdslocale","sc_allowalipayforcheckout","sc_allowbuynowrupay","sc_allowcustompifiltering","sc_allowelo","sc_allowfincastlerewardsforsubs","sc_allowmpesapi","sc_allowparallelorderload","sc_allowpaypay","sc_allowpaypayforcheckout","sc_allowpaysafecard","sc_allowpaysafeforus","sc_allowrupay","sc_allowrupayforcheckout","sc_allowsmdmarkettobeprimarypi","sc_allowupi","sc_allowupiforbuynow","sc_allowupiforcheckout","sc_allowupiqr","sc_allowupiqrforbuynow","sc_allowupiqrforcheckout","sc_allowvenmo","sc_allowvenmoforbuynow","sc_allowvenmoforcheckout","sc_allowverve","sc_analyticsforbuynow","sc_announcementtsenabled","sc_apperrorboundarytsenabled","sc_askaparentinsufficientbalance","sc_askaparentssr","sc_askaparenttsenabled","sc_asyncpiurlupdate","sc_asyncpurchasefailure","sc_asyncpurchasefailurexboxcom","sc_authactionts","sc_autorenewalconsentnarratorfix","sc_bankchallenge","sc_bankchallengecheckout","sc_blockcsvpurchasefrombuynow","sc_blocklegacyupgrade","sc_buynowfocustrapkeydown","sc_buynowglobalpiadd","sc_buynowlistpichanges","sc_buynowprodigilegalstrings","sc_buynowuipreload","sc_buynowuiprod","sc_cartcofincastle","sc_cartrailexperimentv2","sc_cawarrantytermsv2","sc_checkoutglobalpiadd","sc_checkoutitemfontweight","sc_checkoutredeem","sc_clientdebuginfo","sc_clienttelemetryforceenabled","sc_clienttorequestorid","sc_contactpreferenceactionts","sc_contactpreferenceupdate","sc_contactpreferenceupdatexboxcom","sc_conversionblockederror","sc_copycurrentcart","sc_cpdeclinedv2","sc_culturemarketinfo","sc_cvvforredeem","sc_dapsd2challenge","sc_delayretry","sc_deliverycostactionts","sc_devicerepairpifilter","sc_digitallicenseterms","sc_disableupgradetrycheckout","sc_discountfixforfreetrial","sc_documentrefenabled","sc_eligibilityapi","sc_emptyresultcheck","sc_enablecartcreationerrorparsing","sc_enablekakaopay","sc_errorpageviewfix","sc_errorstringsts","sc_euomnibusprice","sc_expandedpurchasespinner","sc_extendpagetagtooverride","sc_fetchlivepersonfromparentwindow","sc_fincastlebuynowallowlist","sc_fincastlebuynowv2strings","sc_fincastlecalculation","sc_fincastlecallerapplicationidcheck","sc_fincastleui","sc_fingerprinttagginglazyload","sc_fixforcalculatingtax","sc_fixredeemautorenew","sc_flexibleoffers","sc_flexsubs","sc_giftingtelemetryfix","sc_giftlabelsupdate","sc_giftserversiderendering","sc_globalhidecssphonenumber","sc_greenshipping","sc_handledccemptyresponse","sc_hidegcolinefees","sc_hidesubscriptionprice","sc_highresolutionimageforredeem","sc_hipercard","sc_imagelazyload","sc_inlineshippingselectormsa","sc_inlinetempfix","sc_isnegativeoptionruleenabled","sc_isremovesubardigitalattach","sc_jarvisconsumerprofile","sc_jarvisinvalidculture","sc_klarna","sc_lineitemactionts","sc_livepersonlistener","sc_loadingspinner","sc_lowbardiscountmap","sc_mapinapppostdata","sc_marketswithmigratingcssphonenumber","sc_moraycarousel","sc_moraystyle","sc_moraystylefull","sc_narratoraddress","sc_newcheckoutselectorforxboxcom","sc_newconversionurl","sc_newflexiblepaymentsmessage","sc_newrecoprod","sc_noawaitforupdateordercall","sc_norcalifornialaw","sc_norcalifornialawlog","sc_norcalifornialawstate","sc_nornewacceptterms","sc_officescds","sc_optionalcatalogclienttype","sc_ordercheckoutfix","sc_orderpisyncdisabled","sc_orderstatusoverridemstfix","sc_outofstock","sc_passthroughculture","sc_paymentchallengets","sc_paymentoptionnotfound","sc_paymentsessioninsummarypage","sc_pidlignoreesckey","sc_pitelemetryupdates","sc_preloadpidlcontainerts","sc_productforlicenseterms","sc_productimageoptimization","sc_prominenteddchange","sc_promocode","sc_promocodecheckout","sc_purchaseblock","sc_purchaseblockerrorhandling","sc_purchasedblocked","sc_purchasedblockedby","sc_quantitycap","sc_railv2","sc_reactcheckout","sc_readytopurchasefix","sc_redeemfocusforce","sc_reloadiflineitemdiscrepancy","sc_removepaddingctalegaltext","sc_removeresellerforstoreapp","sc_resellerdetail","sc_restoregiftfieldlimits","sc_returnoospsatocart","sc_routechangemessagetoxboxcom","sc_rspv2","sc_scenariotelemetryrefactor","sc_separatedigitallicenseterms","sc_setbehaviordefaultvalue","sc_shippingallowlist","sc_showcontactsupportlink","sc_showtax","sc_skippurchaseconfirm","sc_skipselectpi","sc_splipidltresourcehelper","sc_splittaxv2","sc_staticassetsimport","sc_surveyurlv2","sc_taxamountsubjecttochange","sc_testflight","sc_twomonthslegalstringforcn","sc_updateallowedpaymentmethodstoadd","sc_updatebillinginfo","sc_updatedcontactpreferencemarkets","sc_updateformatjsx","sc_updatetosubscriptionpricev2","sc_updatewarrantycompletesurfaceproinlinelegalterm","sc_updatewarrantytermslink","sc_usefullminimaluhf","sc_usehttpsurlstrings","sc_uuid","sc_xboxcomnosapi","sc_xboxrecofix","sc_xboxredirection","sc_xdlshipbuffer"],
                "tokenIdentifierValue": code,
                "supportsCsvTypeTokenOnly": False,
                "buyNowScenario": "redeem",
                "clientContext": {
                    "client": "AccountMicrosoftCom",
                    "deviceFamily": "Web"
                }
            }

            response = await prepare_redeem_api_call(session, code, headers, payload)
            
            if not response:
                return {"status": "ERROR", "message": "Request failed"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Request failed: {str(e)}"}
        
        if response.status_code == 429:
            return {"status": "RATE_LIMITED", "message": "Account rate limited (HTTP 429)"}
                
        if response.status_code != 200:
            return {"status": "ERROR", "message": f"Request failed with status {response.status_code}"}
            
        data = response.json()

        if "tokenType" in data and data["tokenType"] == "CSV":
            value = data.get("value")
            currency = data.get("currency")
            return {"status": "BALANCE_CODE", "message": f"{code} | {value} {currency}"}
        
        if "errorCode" in data and data["errorCode"] == "TooManyRequests":
            return {"status": "RATE_LIMITED", "message": "Account rate limited (TooManyRequests)"}
        
        if "error" in data and isinstance(data["error"], dict) and "code" in data["error"]:
            if data["error"]["code"] == "TooManyRequests" or "rate" in data["error"].get("message", "").lower():
                return {"status": "RATE_LIMITED", "message": "Account rate limited (error message)"}
        
        if "events" in data and "cart" in data["events"] and data["events"]["cart"]:
            cart_event = data["events"]["cart"][0]
            
            if "type" in cart_event and cart_event["type"] == "error":
                if cart_event.get("code") == "TooManyRequests" or "TooManyRequests" in str(cart_event):
                    return {"status": "RATE_LIMITED", "message": "Account rate limited (cart event)"}
            
            if "data" in cart_event and "reason" in cart_event["data"]:
                reason = cart_event["data"]["reason"]
                
                if "TooManyRequests" in reason or "RateLimit" in reason:
                    return {"status": "RATE_LIMITED", "message": f"Account rate limited ({reason})"}
                
                if reason == "RedeemTokenAlreadyRedeemed":
                    return {"status": "REDEEMED", "message": f"{code} | REDEEMED"}
                
                elif reason in ["RedeemTokenExpired", "LegacyTokenAuthenticationNotProvided", 
                               "RedeemTokenNoMatchingOrEligibleProductsFound"]:
                    return {"status": "EXPIRED", "message": f"{code} | EXPIRED"}
                
                elif reason == "RedeemTokenStateDeactivated":
                    return {"status": "DEACTIVATED", "message": f"{code} | DEACTIVATED"}
                
                elif reason == "RedeemTokenGeoFencingError":
                    return {"status": "REGION_LOCKED", "message": f"{code} | REGION_LOCKED"}
                
                elif reason in ["RedeemTokenNotFound", "InvalidProductKey", "RedeemTokenStateUnknown"]:
                    return {"status": "INVALID", "message": f"{code} | INVALID"}
                
                else:
                    return {"status": "INVALID", "message": f"{code} | INVALID"}
        
        if "products" in data and len(data["products"]) > 0:
            product_info = data.get("productInfos", [{}])[0]
            product_id = product_info.get("productId")
            
            for product in data["products"]:
                if product.get("id") == product_id and "sku" in product and product["sku"]:
                    product_title = product["sku"].get("title", "Unknown Title")
                    is_pi_required = product_info.get("isPIRequired", False)
                    
                    if is_pi_required:
                        return {
                            "status": "VALID_REQUIRES_CARD",
                            "product_title": product_title,
                            "message": f"{code} | {product_title}"
                        }
                    else:
                        return {
                            "status": "VALID",
                            "product_title": product_title,
                            "message": f"{code} | {product_title}"
                        }
                elif product.get("id") == product_id:
                    product_title = product.get("title", "Unknown Title")
                    is_pi_required = product_info.get("isPIRequired", False)
                    
                    if is_pi_required:
                        return {
                            "status": "VALID_REQUIRES_CARD",
                            "product_title": product_title,
                            "message": f"{code} | {product_title}"
                        }
                    else:
                        return {
                            "status": "VALID",
                            "product_title": product_title,
                            "message": f"{code} | {product_title}"
                        }
        
        return {"status": "UNKNOWN", "message": f"{code} | UNKNOWN"}
        
    except Exception as e:
        print(f"Error in validate_code_primary: {e}")
        return {"status": "ERROR", "message": f"{code} | Error: {str(e)}"}

async def validate_code(session, code, force_refresh_ids=False, token=None):
    try:
        result = await validate_code_primary(session, code, force_refresh_ids, token)
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
            elif result['status'] == 'RATE_LIMITED':
                return result
            else:
                print_colored(f"{code} | {result['status']}", Fore.RED)
                return result
        else:
            return {"status": "ERROR", "message": "Result is not a dictionary"}
    except Exception as e:
        print(f"Error in validate_code: {e}")
        return {"status": "ERROR", "message": str(e)}


async def process_code_check(session, code, email, result_files, results_count, processed_codes_lock, processed_codes, total_codes, rate_limited_accounts, token):
    try:
        with processed_codes_lock:
            if code in processed_codes:
                return True, False
        
        result = await validate_code(session, code, force_refresh_ids=False, token=token)
        status = result.get('status', 'ERROR')

        if status == 'ERROR':
            with print_lock:
                error_msg = result.get('message', 'Unknown error')
                print(f"{Fore.RED}Error checking code {code} with account {email}: {error_msg}{Style.RESET_ALL}")
            with open('error_log.txt', 'a') as f:
                f.write(f"[{datetime.now()}] Error: {code} | {email} | {result.get('message', 'Unknown')}\n")
            return False, False

        elif status == 'RATE_LIMITED':
            if rate_limited_accounts is not None and email not in rate_limited_accounts:
                rate_limited_accounts.append(email)
            return False, True

        else:
            file_key = None
            if status in ['VALID', 'VALID_REQUIRES_CARD']:
                file_key = status
            elif status == 'BALANCE_CODE':
                file_key = 'VALID'
            elif status in ['REDEEMED', 'EXPIRED', 'DEACTIVATED', 'INVALID']:
                file_key = 'INVALID'
            elif status in ['REGION_LOCKED', 'UNKNOWN']:
                file_key = status
            
            if not file_key:
                file_key = 'INVALID'
            
            result_line = f"{result.get('message', f'{code} | {status}')}\n"
            
            with processed_codes_lock:
                if file_key in results_count:
                    results_count[file_key] += 1
                if code not in processed_codes:
                    processed_codes.add(code)
                update_titlebar(results_count, len(processed_codes), total_codes)
                
                if file_key in result_files:
                    try:
                        with open(result_files[file_key], 'a') as f:
                            f.write(result_line)
                    except Exception as fe:
                        with open('error_log.txt', 'a') as elf:
                            elf.write(f"[{datetime.now()}] File write error: {result_files[file_key]} | {str(fe)}\n")

            return True, False

    except Exception as e:
        with print_lock:
            print(f"{Fore.RED}Exception checking code {code} with account {email}: {str(e)}{Style.RESET_ALL}")
        with open('error_log.txt', 'a') as f:
            f.write(f"[{datetime.now()}] Exception: {code} | {email} | {str(e)}\n")
        return False, False


def process_codes_for_account(account, codes_queue, result_files, results_count, processed_codes_lock, processed_codes, total_codes, proxy=None, rate_limited_accounts=None):
    email, password = account
    session, token = login_microsoft_account(email, password, proxy)

    if not session or not token:
        with print_lock:
            print(f"{Fore.RED}Invalid - {email}{Style.RESET_ALL}")
        return

    with print_lock:
        print(f"{Fore.GREEN}Logged in {email}{Style.RESET_ALL}")

    codes_checked = 0
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        while True:
            if rate_limited_accounts is not None and email in rate_limited_accounts:
                return
            
            with processed_codes_lock:
                if len(processed_codes) >= total_codes:
                    return
            
            try:
                code = codes_queue.get(timeout=5)
            except queue.Empty:
                with processed_codes_lock:
                    remaining_codes = total_codes - len(processed_codes)
                if remaining_codes <= 0:
                    return
                continue
            
            try:
                success, is_rate_limited = loop.run_until_complete(
                    process_code_check(
                        session, code, email, result_files, results_count,
                        processed_codes_lock, processed_codes, total_codes, rate_limited_accounts, token
                    )
                )
                    
                with processed_codes_lock:
                    if len(processed_codes) >= total_codes:
                        return
                
                if is_rate_limited:
                    codes_queue.put(code)
                    return
                elif success:
                    codes_checked += 1
                else:
                    codes_queue.put(code)
            except Exception as e:
                with print_lock:
                    print(f"{Fore.RED}Error processing code {code} with account {email}: {str(e)}{Style.RESET_ALL}")
                with open('error_log.txt', 'a') as f:
                    f.write(f"[{datetime.now()}] Account processing error: {code} | {email} | {str(e)}\n")
                codes_queue.put(code)
            finally:
                codes_queue.task_done()
    finally:
        loop.close()

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

    unique_codes = list(dict.fromkeys(codes))
    duplicate_count = len(codes) - len(unique_codes)
    if duplicate_count > 0:
        print(f"{Fore.YELLOW}Detected and removed {duplicate_count} duplicate codes.{Style.RESET_ALL}")
    codes = unique_codes
    
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
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_folder = f"results/check_{timestamp}"
    os.makedirs(results_folder, exist_ok=True)
    
    result_files = {
        'VALID': f'{results_folder}/valid_codes.txt',
        'VALID_REQUIRES_CARD': f'{results_folder}/valid_cardrequired_codes.txt',
        'INVALID': f'{results_folder}/invalid.txt',
        'UNKNOWN': f'{results_folder}/unknown_codes.txt',
        'REGION_LOCKED': f'{results_folder}/region_locked_codes.txt',
    }
    
    results_count = {status: 0 for status in result_files.keys()}
    
    update_titlebar(results_count, 0, len(codes))
    
    for file_path in result_files.values():
        with open(file_path, 'a'):
            pass
    
    with open(f'error_log.txt', 'w'):
        pass
    
    with open(f'{results_folder}/summary.txt', 'w') as f:
        f.write(f"Code Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total Codes: {len(codes)}\n")
        f.write(f"Total Accounts: {len(accounts)}\n")
        f.write(f"Batch Size: {batch_size}\n")
        if proxies:
            f.write(f"Proxies Used: {len(proxies)}\n")
        f.write("\nResults will be updated as checks complete...\n")
    
    codes_queue = queue.Queue()
    for code in codes:
        codes_queue.put(code)
    
    print(f"Added {len(codes)} codes to the queue")
    
    processed_codes = set()
    processed_codes_lock = threading.Lock()
    
    rate_limited_accounts = []
    
    with ThreadPoolExecutor(max_workers=batch_size) as account_executor:
        account_futures = {
            account_executor.submit(
                process_codes_for_account,
                account,
                codes_queue,
                result_files,
                results_count,
                processed_codes_lock,
                processed_codes,
                len(codes),
                get_random_proxy(proxies) if proxies else None,
                rate_limited_accounts
            ): account for account in accounts
        }
        
        for future in as_completed(account_futures):
            pass

    with print_lock:
        print(f"{Fore.GREEN}All threads have completed.{Style.RESET_ALL}")

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
        f.write(f"Valid Codes: {results_count.get('VALID', 0)}\n")
        f.write(f"Valid (Requires Card): {results_count.get('VALID_REQUIRES_CARD', 0)}\n")
        f.write(f"Region Locked: {results_count.get('REGION_LOCKED', 0)}\n")
        f.write(f"Invalid: {results_count.get('INVALID', 0)}\n")
        f.write(f"Unknown: {results_count.get('UNKNOWN', 0)}\n")
    
    with open('codes.txt', 'w') as f:
        remaining_codes = [c for c in codes if c not in processed_codes]
        f.write('\n'.join(remaining_codes))

    while True:
        response = input(f"{Fore.CYAN}Exit the program? (yes/no): {Style.RESET_ALL}").lower().strip()
        if response in ['yes', 'y']:
            print(f"{Fore.GREEN}Exiting program...{Style.RESET_ALL}")
            if rate_limited_accounts:
                print(f"{Fore.YELLOW}Found {len(rate_limited_accounts)} rate-limited accounts.{Style.RESET_ALL}")
                remove_response = input(f"{Fore.CYAN}Remove rate-limited accounts from accounts.txt? (y/n): {Style.RESET_ALL}").lower().strip()
                if remove_response in ['y']:
                    remove_rate_limited_accounts(rate_limited_accounts)
            break
        elif response in ['n']:
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


main()
