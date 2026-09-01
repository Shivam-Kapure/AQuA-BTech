import httpx
from typing import Any

async def check_security_headers(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            
        headers = resp.headers
        missing = []
        if "Strict-Transport-Security" not in headers:
            missing.append("Strict-Transport-Security (HSTS)")
        if "X-Content-Type-Options" not in headers:
            missing.append("X-Content-Type-Options")
        if "X-Frame-Options" not in headers and "Content-Security-Policy" not in headers:
            missing.append("X-Frame-Options or CSP frame-ancestors")
            
        if not missing:
            return {
                "status": "PASS",
                "finding": "Essential security headers are present.",
                "evidence": f"Headers checked on {url}",
                "recommendation": "Maintain current header configuration."
            }
        else:
            return {
                "status": "FAIL",
                "finding": f"Missing critical security headers: {', '.join(missing)}",
                "evidence": f"Received headers: {dict(headers)}",
                "recommendation": "Configure the web server to emit modern security headers."
            }
    except Exception as e:
        return {
            "status": "WARNING",
            "finding": f"Could not complete header check: {str(e)}",
            "evidence": "",
            "recommendation": "Check target reachability."
        }

async def check_cookie_security(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            
        set_cookie_headers = resp.headers.get_list("set-cookie")
        if not set_cookie_headers:
            return {
                "status": "PASS",
                "finding": "No cookies set on this endpoint.",
                "evidence": "No Set-Cookie header found.",
                "recommendation": "N/A"
            }
            
        insecure_cookies = []
        for cookie in set_cookie_headers:
            cookie_lower = cookie.lower()
            issues = []
            if "secure" not in cookie_lower:
                issues.append("missing Secure flag")
            if "httponly" not in cookie_lower:
                issues.append("missing HttpOnly flag")
            if issues:
                insecure_cookies.append(f"{cookie.split('=')[0]} ({', '.join(issues)})")
                
        if insecure_cookies:
            return {
                "status": "FAIL",
                "finding": f"Insecure cookies found: {'; '.join(insecure_cookies)}",
                "evidence": f"Set-Cookie headers: {set_cookie_headers}",
                "recommendation": "Ensure all session cookies have Secure and HttpOnly flags enabled."
            }
            
        return {
            "status": "PASS",
            "finding": "All cookies have appropriate security flags.",
            "evidence": f"Set-Cookie headers: {set_cookie_headers}",
            "recommendation": "Maintain current cookie configuration."
        }
    except Exception as e:
        return {
            "status": "WARNING",
            "finding": f"Could not complete cookie check: {str(e)}",
            "evidence": "",
            "recommendation": "Check target reachability."
        }

async def check_input_validation(url: str, method: str, parameter: str) -> dict[str, Any]:
    # A generic, non-intrusive probe to see if basic payload is reflected unescaped or causes 500
    probe = "<aqua_probe>"
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            if method.upper() == "POST":
                data = {parameter: probe} if parameter else {}
                resp = await client.post(url, data=data, follow_redirects=True)
            else:
                params = {parameter: probe} if parameter else {}
                resp = await client.get(url, params=params, follow_redirects=True)
                
        if resp.status_code >= 500:
            return {
                "status": "FAIL",
                "finding": f"Endpoint returned {resp.status_code} when receiving unexpected input.",
                "evidence": f"Status Code: {resp.status_code}",
                "recommendation": "Implement robust input validation and error handling (avoid 500s on bad input)."
            }
            
        if probe in resp.text:
            return {
                "status": "FAIL",
                "finding": "Input reflection detected without output encoding.",
                "evidence": f"The payload '{probe}' was found unmodified in the response body.",
                "recommendation": "Ensure context-aware output encoding is applied before rendering user input."
            }
            
        return {
            "status": "PASS",
            "finding": "Basic input probe was handled securely (no unescaped reflection or server crash).",
            "evidence": f"Response code {resp.status_code}",
            "recommendation": "Continue applying defense-in-depth input validation."
        }
    except Exception as e:
        return {
            "status": "WARNING",
            "finding": f"Could not complete input validation check: {str(e)}",
            "evidence": "",
            "recommendation": "Check target reachability."
        }

async def check_information_disclosure(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            
        headers = resp.headers
        disclosures = []
        if "Server" in headers and len(headers["Server"]) > 5:
            # Overly descriptive server header
            disclosures.append(f"Server header exposes version: {headers['Server']}")
        if "X-Powered-By" in headers:
            disclosures.append(f"X-Powered-By header present: {headers['X-Powered-By']}")
            
        if disclosures:
            return {
                "status": "WARNING",
                "finding": "Potential information disclosure in HTTP headers.",
                "evidence": "; ".join(disclosures),
                "recommendation": "Remove or obfuscate Server and X-Powered-By headers."
            }
            
        return {
            "status": "PASS",
            "finding": "No obvious server footprinting headers found.",
            "evidence": f"Headers: {dict(headers)}",
            "recommendation": "Maintain current configuration."
        }
    except Exception as e:
        return {
            "status": "WARNING",
            "finding": f"Could not complete information disclosure check: {str(e)}",
            "evidence": "",
            "recommendation": "Check target reachability."
        }
