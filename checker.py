import requests
import random
import time
from enum import Enum
from dataclasses import dataclass

class CheckStatus(Enum):
    AVAILABLE = "available"
    TAKEN = "taken"
    UNSURE = "unsure"
    BANNED = "banned"

@dataclass
class CheckResult:
    username: str
    status: CheckStatus

def get_random_headers() -> dict:
    # Modern browser version ranges
    chrome_ver = random.randint(118, 123)
    chrome_patch = random.randint(0, 5000)
    safari_ver = f"{random.randint(15, 17)}.{random.randint(0, 6)}"
    ios_ver = f"{random.randint(16, 17)}_{random.randint(0, 6)}"
    
    profiles = [
        # Windows Chrome
        {
            "ua": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver}.0.{chrome_patch}.0 Safari/537.36",
            "sec_ch_ua": f'"Not_A Brand";v="8", "Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}"',
            "sec_ch_ua_mobile": "?0",
            "sec_ch_ua_platform": '"Windows"'
        },
        # Windows Chrome (Win 11)
        {
            "ua": f"Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver}.0.{chrome_patch}.0 Safari/537.36",
            "sec_ch_ua": f'"Not_A Brand";v="8", "Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}"',
            "sec_ch_ua_mobile": "?0",
            "sec_ch_ua_platform": '"Windows"'
        },
        # Mac Chrome
        {
            "ua": f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver}.0.{chrome_patch}.0 Safari/537.36",
            "sec_ch_ua": f'"Google Chrome";v="{chrome_ver}", "Chromium";v="{chrome_ver}", "Not?A_Brand";v="24"',
            "sec_ch_ua_mobile": "?0",
            "sec_ch_ua_platform": '"macOS"'
        },
        # Linux Chrome
        {
            "ua": f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver}.0.{chrome_patch}.0 Safari/537.36",
            "sec_ch_ua": f'"Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}", "Not=A?Brand";v="99"',
            "sec_ch_ua_mobile": "?0",
            "sec_ch_ua_platform": '"Linux"'
        },
        # iOS Safari
        {
            "ua": f"Mozilla/5.0 (iPhone; CPU iPhone OS {ios_ver} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Mobile/15E148 Safari/604.1",
            "sec_ch_ua": None,
            "sec_ch_ua_mobile": None,
            "sec_ch_ua_platform": None
        },
        # Android Chrome
        {
            "ua": f"Mozilla/5.0 (Linux; Android {random.randint(11, 14)}; SM-S{random.randint(900, 918)}B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver}.0.{chrome_patch}.0 Mobile Safari/537.36",
            "sec_ch_ua": f'"Chromium";v="{chrome_ver}", "Google Chrome";v="{chrome_ver}", "Not:A-Brand";v="99"',
            "sec_ch_ua_mobile": "?1",
            "sec_ch_ua_platform": '"Android"'
        },
        # Windows Firefox
        {
            "ua": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{random.randint(115, 122)}.0) Gecko/20100101 Firefox/{random.randint(115, 122)}.0",
            "sec_ch_ua": None,
            "sec_ch_ua_mobile": None,
            "sec_ch_ua_platform": None
        },
        # Mac Firefox
        {
            "ua": f"Mozilla/5.0 (Macintosh; Intel Mac OS X 14.{random.randint(0, 3)}; rv:{random.randint(115, 122)}.0) Gecko/20100101 Firefox/{random.randint(115, 122)}.0",
            "sec_ch_ua": None,
            "sec_ch_ua_mobile": None,
            "sec_ch_ua_platform": None
        },
        # Windows Edge
        {
            "ua": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver}.0.{chrome_patch}.0 Safari/537.36 Edg/{chrome_ver}.0.{chrome_patch}.0",
            "sec_ch_ua": f'"Not_A Brand";v="8", "Chromium";v="{chrome_ver}", "Microsoft Edge";v="{chrome_ver}"',
            "sec_ch_ua_mobile": "?0",
            "sec_ch_ua_platform": '"Windows"'
        }
    ]
    
    prof = random.choice(profiles)
    headers = {
        "User-Agent": prof["ua"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive"
    }
    
    if prof.get("sec_ch_ua"):
        headers["sec-ch-ua"] = prof["sec_ch_ua"]
    if prof.get("sec_ch_ua_mobile"):
        headers["sec-ch-ua-mobile"] = prof["sec_ch_ua_mobile"]
    if prof.get("sec_ch_ua_platform"):
        headers["sec-ch-ua-platform"] = prof["sec_ch_ua_platform"]
        
    return headers


# Global session for connection pooling, drastically reducing socket overhead
GLOBAL_SESSION = requests.Session()

def check_username(username: str) -> CheckResult:
    """
    Advanced availability check utilizing both direct profile checks
    and specific API patterns with sophisticated headers to avoid WAF blocks.
    """
    # 1. API endpoint check (often cleaner, but requires x-ig-app-id)
    api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    # 2. Fallback HTML check
    html_url = f"https://www.instagram.com/{username}/"
    
    headers = get_random_headers()
    
    api_headers = headers.copy()
    api_headers["Accept"] = "*/*"
    api_headers["X-IG-App-ID"] = "936619743392459" # Standard hardcoded app ID for Insta Web
    api_headers["Sec-Fetch-Dest"] = "empty"
    api_headers["Sec-Fetch-Mode"] = "cors"
    api_headers["Sec-Fetch-Site"] = "same-origin"
    
    for attempt in range(3):
        try:
            # Try API approach first using connection pooling
            response = GLOBAL_SESSION.get(api_url, headers=api_headers, timeout=12, allow_redirects=False)
            
            if response.status_code == 404:
                return CheckResult(username, CheckStatus.AVAILABLE)
            elif response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("data", {}).get("user") is not None:
                        return CheckResult(username, CheckStatus.TAKEN)
                    else:
                        # User is None -> might be available or not found
                        return CheckResult(username, CheckStatus.AVAILABLE)
                except ValueError:
                    pass # Not JSON, fallback to HTML
            
            elif response.status_code in [429, 403]:
                return CheckResult(username, CheckStatus.BANNED)
                
            # If the API returned 302, 401, or anything else, fallback to HTML check
            html_resp = GLOBAL_SESSION.get(html_url, headers=headers, timeout=12, allow_redirects=True)
            
            if html_resp.status_code in [429, 403]:
                return CheckResult(username, CheckStatus.BANNED)
                
            if html_resp.status_code == 404:
                return CheckResult(username, CheckStatus.AVAILABLE)
                
            content_length = int(html_resp.headers.get("content-length", len(html_resp.text)))
            redirect_headers = html_resp.headers.get("X-Instagram-Redirect", "") or html_resp.headers.get("Location", "")
            final_url = html_resp.url.lower()
            
            # Login wall redirect usually happens when taken or restricted
            if "/accounts/login/" in final_url or "accounts/login" in str(redirect_headers).lower():
                return CheckResult(username, CheckStatus.TAKEN)
                
            if html_resp.status_code == 200:
                content = html_resp.text.lower()
                
                # Check for "standard" profile markers
                if "<title>" in content:
                    title = content.split("<title>")[1].split("</title>")[0]
                    # If title contains "Instagram photos and videos" it's definitely taken
                    if "instagram photos and videos" in title or "login • instagram" in title:
                        return CheckResult(username, CheckStatus.TAKEN)
                    # If title is just "Instagram" it might be restricted or restricted location
                    if title.strip() == "instagram":
                        return CheckResult(username, CheckStatus.TAKEN)

                # Strong profile markers
                has_profile_meta = 'og:type" content="profile"' in content
                has_follower_count = '"follower_count"' in content
                has_profile_schema = '"@type":"profilepage"' in content.replace(" ", "")
                
                if has_profile_meta or has_follower_count or has_profile_schema or f'"{username}"' in content[:5000]:
                     return CheckResult(username, CheckStatus.TAKEN)
                     
                # Strong available markers
                has_404_title = "page not found" in content
                has_unavailable_text = "sorry, this page isn't available" in content
                
                if has_404_title or has_unavailable_text or content_length < 15000:
                     return CheckResult(username, CheckStatus.AVAILABLE)
                     
            return CheckResult(username, CheckStatus.TAKEN)
            
        except requests.exceptions.RequestException as e:
            if attempt < 2:
                time.sleep(15 * (attempt + 1)) # Progressive backoff
            else:
                return CheckResult(username, CheckStatus.TAKEN)
                
    return CheckResult(username, CheckStatus.TAKEN)

def get_stealth_delay(checks_done: int) -> float:
    # Burst pause every 15 checks (less frequent but longer)
    if checks_done > 0 and checks_done % 15 == 0:
        return random.uniform(60.0, 120.0)
    else:
        # Conservative jitter delay: 10-25s
        jitter = random.uniform(10.0, 25.0)
        # Random spike delays (15% chance)
        if random.random() < 0.15:
            jitter += random.uniform(15.0, 30.0)
        return jitter
