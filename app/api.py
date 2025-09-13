import requests
import re
import json
import urllib.parse
import time
import random
import string
import os
import threading
import concurrent.futures
from datetime import datetime
from app.ui import print_colored
from colorama import Fore
import uuid

import sys
sys.dont_write_bytecode = True # Prevent the creation of .pyc files

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


def decodin(txt): # God bless KillinMachine for helping me
    return json.loads(f'"{txt}"')


def get_urlPost_sFTTag(sFTTag_url,session): # God bless KillinMachine for helping me
    global retries
    while True:
        try:
            text = session.get(sFTTag_url, timeout=15).text
            match = re.search(r'value=\\\"(.+?)\\\"', text, re.S) or re.search(r'value="(.+?)"', text, re.S)
            if match:
                sFTTag = match.group(1)
                match = re.search(r'"urlPost":"(.+?)"', text, re.S) or re.search(r"urlPost:'(.+?)'", text, re.S)
                if match:
                    return match.group(1), sFTTag, session
        except Exception:
            pass
        retries += 1


def login_microsoft_account(email, password, proxies=None):
    session = requests.Session()
    if proxies:
        session.proxies = proxies
    
    session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://account.microsoft.com/',
        'Origin': 'https://account.microsoft.com',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        response = session.get("https://account.microsoft.com/billing/redeem", allow_redirects=True, timeout=30)
        if 'AMC-MS-CV' in session.cookies:
            session.ms_cv = session.cookies['AMC-MS-CV']
        if response.status_code != 200:
            return None
            
        text = response.text
        rurl_match = re.search(r'urlPost":"([^"]+)"', text)
        if not rurl_match:
            return None
            
        rurl = "https://login.microsoftonline.com" + decodin(rurl_match.group(1))
        
        response = session.get(rurl, timeout=30)
        if response.status_code != 200:
            return None
            
        text = response.text
        furl_match = re.search(r'urlGoToAADError":"([^"]+)"', text)
        if not furl_match:
            return None
            
        furl = decodin(furl_match.group(1))
        furl = furl.replace('&jshs=0', f'&jshs=2&jsh=&jshp=&username={urllib.parse.quote(email)}&login_hint={urllib.parse.quote(email)}') # this can be optimised, and i have but im not fixing this old code
        
        try:
            urlPost, sFTTag, session = get_urlPost_sFTTag(furl, session)
        except Exception:
            return None
            
        try:
            login_response = session.post(
                urlPost,
                data={'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sFTTag},
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                allow_redirects=True,
                timeout=30
            )
            login_request = login_response.text
        except Exception:
            return None
        login_request = login_request.replace('\\', '')
        open(r'login_request.txt', 'w').write(login_request)

        try:  
            ppft_match = re.search(r'"sFT":"([^"]+)"', login_request).group(1)
            print(ppft_match)
            if not ppft_match:
                print("Failed to get sFTTag on second request! this is an error.")
                return None
        except Exception as e:
            print(f"{str(e)}")
            return None
        try:
            lurl_match = re.search(r'"urlPost":"([^"]+)"', login_request).group(1)
            print(lurl_match)

            if not lurl_match:
                print("Failed to get urlPost, most likely a regex error.")
                return None
        except Exception as e:
            print(f"{str(e)}")
            return None
        data = {
            'LoginOptions': '1',
            'type': '28',
            'ctx': '',
            'hpgrequestid': '',
            'PPFT': ppft_match,
            'canary': ''
        }
        
        lurl = lurl_match
        
        try:
            finish = session.post(
                lurl,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                allow_redirects=True,
                timeout=30
            ).text
        except Exception:
            return None
            
        reurl_match = re.search(r'replace\(\"([^\"]+)\"', finish)
        if not reurl_match:
            return None
            
        reurl = reurl_match.group(1)
        
        try:
            reresp = session.get(reurl, timeout=30).text
        except Exception:
            return None
            
        actch = re.search(r'<form.*?action="(.*?)".*?>', reresp)
        if not actch:
            return None
            
        acu = actch.group(1)
        input_matches = re.findall(r'<input.*?name="(.*?)".*?value="(.*?)".*?>', reresp)
        fta = {name: value for name, value in input_matches}
        
        try:
            final_response = session.post(acu, data=fta, allow_redirects=True, timeout=30)
            if final_response.status_code != 200:
                return None
        except Exception:
            return None
            
        token_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://account.microsoft.com/billing/redeem'
        }
        
        return session
        
    except Exception as e:
        return None

def get_auth_token(session, force_refresh=False): # WLID/MBISSL
    try:
        if not force_refresh and hasattr(session, 'wlid_token'):
            return session.wlid_token
                
        token_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://account.microsoft.com/billing/redeem'
        }
        
        token_response = session.get(
            'https://account.microsoft.com/auth/acquire-onbehalf-of-token',
            params={'scopes': 'MSComServiceMBISSL'},
            headers=token_headers,
            timeout=15
        )
        
        if token_response.status_code != 200:
            return None
            
        token_data = token_response.json()
        if not token_data or len(token_data) == 0:
            return None
            
        token = token_data[0]['token']
        
        session.wlid_token = token
        
        return token
        
    except Exception as e:
        return None


def get_store_cart_state(session, force_refresh=False):
    try:
        if force_refresh:
            if hasattr(session, 'store_state'):
                delattr(session, 'store_state')
                
        if not force_refresh and hasattr(session, 'store_state'):
            return session.store_state
            
        token = get_auth_token(session, force_refresh)
        if not token:
            return None

        ms_cv = getattr(session, 'ms_cv', None)
        if not ms_cv:
            return None
            
        ms_cv = f"{ms_cv}.21.7"
        
        url = 'https://www.microsoft.com/store/purchase/buynowui/redeemnow'
        params = {
            'ms-cv': ms_cv,
            'market': 'US',
            'locale': 'en-GB',
            'clientName': 'AccountMicrosoftCom'
        }
        # Redeemnow payload,, MSATicket, MS_CV
        payload = {'data': '{"usePurchaseSdk":true}', 'market': 'US', 'cV': ms_cv, 'locale': 'en-GB', 'msaTicket': token, 'pageFormat': 'full', 'urlRef': 'https://account.microsoft.com/billing/redeem', 'isRedeem': 'true', 'clientType': 'AccountMicrosoftCom', 'layout': 'Inline', 'cssOverride': 'AMC', 'scenario': 'redeem', 'timeToInvokeIframe': '4977', 'sdkVersion': 'VERSION_PLACEHOLDER'}
        
        headers = {
            'Origin': 'https://www.microsoft.com',
            'Referer': 'https://account.microsoft.com/billing/redeem',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        try:
            response = session.post(url, params=params, headers=headers, data=payload, timeout=30, allow_redirects=True)
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
        return None


def validate_code_primary(session, codes, force_refresh_ids=False):
    try:
        if isinstance(codes, str):
            codes = [codes]
            
        if not all(code and len(code) >= 5 and ' ' not in code for code in codes):
            return {"status": "INVALID", "message": "Invalid code format"}
        
        store_state = get_store_cart_state(session, force_refresh=force_refresh_ids)
        if not store_state:
            store_state = get_store_cart_state(session, force_refresh=True)
            if not store_state:
                return {"status": "ERROR", "message": "Failed to get store cart state"}
        
        token = get_auth_token(session, force_refresh=force_refresh_ids)
        if not token:
            token = get_auth_token(session, force_refresh=True)
            if not token:
                return {"status": "ERROR", "message": "Failed to get authentication token"}
        
        def check_single_code(code):
            try:
                headers = {
                    'origin': 'https://www.microsoft.com',
                    'x-ms-vector-id': store_state['vector_id'],
                    'referer': 'https://www.microsoft.com/',
                    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'accept': '*/*',
                    'x-authorization-muid': store_state['alternative_muid'],
                    'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8,en-IN;q=0.7',
                    'x-ms-client-type': 'AccountMicrosoftCom',
                    'Authorization': f"WLID1.0=t={token}",
                    'x-ms-correlation-id': store_state['correlation_id'],
                    'x-ms-market': 'US',
                    'content-type': 'application/json',
                    'x-ms-tracking-id': store_state['tracking_id'],
                    'x-ms-reference-id': generate_reference_id(),
                    'ms-cv': store_state['ms_cv'],
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

                response = session.post(
                    'https://buynow.production.store-web.dynamics.com/v1.0/Redeem/PrepareRedeem/?appId=RedeemNow&context=LookupToken',
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                return response
            except Exception as e:
                return None

        # Process codes in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_code = {executor.submit(check_single_code, code): code for code in codes}
            responses = []
            for future in concurrent.futures.as_completed(future_to_code):
                try:
                    response = future.result()
                    if response:
                        code = future_to_code[future]
                        responses.append((code, response))
                except Exception:
                    continue

        if not responses:
            return {"status": "ERROR", "message": "All requests failed"}

        # Process the first successful response
        code, response = responses[0]
        
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
        return {"status": "ERROR", "message": f"{code} | Error: {str(e)}"} 