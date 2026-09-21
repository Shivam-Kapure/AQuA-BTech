import os
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Any
from datetime import datetime

from loguru import logger

from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.security_test_repo import SecurityTestCaseRepository
from app.models.security_test import SecurityTestCaseCreate, SecurityTestType

async def run_zap_scan(
    project_name: str, *, owner_id: str | None = None
) -> list[dict[str, Any]]:
    """
    Runs OWASP ZAP Baseline Scan via Docker against the project's configured URL.
    Parses the JSON report and saves findings to the database in the existing format.
    """
    project_repo = ProjectRepository()
    project = await project_repo.get_by_name(project_name, owner_id=owner_id)
    
    if not project or not project.id:
        raise ValueError(f"Project '{project_name}' not found.")
        
    target_url = project.url
    if not target_url:
        raise ValueError(f"Project '{project_name}' has no configured target URL.")
        
    logger.info(f"Starting ZAP baseline scan for project '{project_name}' against target '{target_url}'")
    
    # We will use a temporary directory to mount into the docker container to retrieve the JSON report.
    # Docker on macOS/Linux needs an absolute path for volume mounts.
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir).resolve()
        report_filename = "zap_report.json"
        
        # Run ZAP docker container
        # zap-baseline.py options:
        # -t target
        # -J json report filename (saved in /zap/wrk/)
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{temp_path}:/zap/wrk/:rw",
            "-t", "zaproxy/zap2docker-stable",
            "zap-baseline.py",
            "-t", target_url,
            "-J", report_filename
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Add a timeout for the entire scan process (e.g. 5 minutes)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError("ZAP scan timed out after 5 minutes.")
            
        # ZAP baseline script returns exit codes:
        # 0 = Pass, 1 = Fail (issues found), 2 = Error
        if process.returncode == 2:
            error_msg = stderr.decode() if stderr else stdout.decode()
            raise RuntimeError(f"ZAP scan encountered an error: {error_msg}")
            
        report_path = temp_path / report_filename
        if not report_path.exists():
            raise FileNotFoundError("ZAP did not produce a report file.")
            
        with open(report_path, "r", encoding="utf-8") as f:
            zap_data = json.load(f)
            
    # Process ZAP findings into our existing security-result format
    findings = []
    test_cases_to_create = []
    
    site_list = zap_data.get("site", [])
    if not site_list:
        logger.warning("No site data found in ZAP report.")
        return []
        
    alerts = site_list[0].get("alerts", [])
    
    for idx, alert in enumerate(alerts, start=1):
        # Map ZAP risk to our severity
        zap_risk = alert.get("riskdesc", "").lower()
        severity = "medium"
        if "high" in zap_risk:
            severity = "high"
        elif "low" in zap_risk:
            severity = "low"
            
        alert_name = alert.get("name", "Unknown Alert")
        description = alert.get("desc", "").replace("<p>", "").replace("</p>", "").strip()
        recommendation = alert.get("solution", "").replace("<p>", "").replace("</p>", "").strip()
        instances = alert.get("instances", [])
        
        # Create a single summary evidence string from instances
        evidence_list = []
        for inst in instances[:3]: # Limit to first 3 instances for brevity
            uri = inst.get("uri", "")
            method = inst.get("method", "")
            evidence_list.append(f"{method} {uri}")
        evidence = "Instances: " + ", ".join(evidence_list)
        
        # We need to map this to our predefined SecurityTestType if possible, otherwise use a fallback.
        # Since the prompt limits strictly to a few types, we will default to 'information_disclosure' 
        # or 'security_headers' based on keywords.
        alert_name_lower = alert_name.lower()
        if "header" in alert_name_lower or "csp" in alert_name_lower:
            test_type = SecurityTestType.security_headers
        elif "cookie" in alert_name_lower:
            test_type = SecurityTestType.cookie_security
        elif "disclosure" in alert_name_lower or "information" in alert_name_lower:
            test_type = SecurityTestType.information_disclosure
        else:
            test_type = SecurityTestType.input_validation # generic fallback

        test_id = f"ZAP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{idx}"
        
        tc = SecurityTestCaseCreate(
            test_id=test_id,
            title=alert_name,
            category="ZAP Baseline Scan",
            target=target_url,
            method="Various",
            parameter="",
            test_type=test_type,
            expected_secure_behavior="No vulnerabilities detected by ZAP.",
            severity=severity,
            url=target_url,
        )
        
        # We store the execution result directly since it's already "executed"
        test_cases_to_create.append({
            "create_model": tc,
            "status": "FAIL" if severity in ["high", "medium"] else "WARNING",
            "finding": description[:500] + ("..." if len(description) > 500 else ""),
            "evidence": evidence,
            "recommendation": recommendation[:500] + ("..." if len(recommendation) > 500 else ""),
        })

    if not test_cases_to_create:
        return []
        
    # Save to database
    repo = SecurityTestCaseRepository(project_name=project.name)
    created_records = await repo.create_many([tc["create_model"] for tc in test_cases_to_create], project_id=project.id)
    
    # Update the status with findings
    for record, tc_data in zip(created_records, test_cases_to_create, strict=False):
        await repo.update_status(
            record.id,
            status=tc_data["status"],
            failure_reason=tc_data["finding"],
            finding=tc_data["finding"],
            evidence=tc_data["evidence"],
            recommendation=tc_data["recommendation"]
        )
        
        result_dict = record.model_dump()
        result_dict.update({
            "status": tc_data["status"],
            "finding": tc_data["finding"],
            "evidence": tc_data["evidence"],
            "recommendation": tc_data["recommendation"]
        })
        findings.append(result_dict)
        
    return findings
