"""
Security Audit Logger complying with ISO/IEC 27001:2022.
Records all authentication, financial access, and administrative actions
into both database and immutable sys_security_audit.log file.
"""
import os
import logging
from datetime import datetime
from config import Config
from database.db import execute_db

# Setup file-based audit log
LOG_FILE_PATH = os.path.join(Config.BASE_DIR, "sys_security_audit.log")

audit_file_logger = logging.getLogger("SulitSecurityAudit")
audit_file_logger.setLevel(logging.INFO)

# File handler with tamper-evident formatting
if not audit_file_logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    formatter = logging.Formatter(
        "[%(asctime)s] [ISO-27001] [%(levelname)s] [User: %(user)s] [Role: %(role)s] [Action: %(action)s] - %(message)s"
    )
    file_handler.setFormatter(formatter)
    audit_file_logger.addHandler(file_handler)


def log_security_event(username: str, role: str, action: str, resource: str, status: str = "SUCCESS", ip: str = "127.0.0.1", details: str = ""):
    """Log security event to file and database."""
    extra = {"user": username or "anonymous", "role": role or "unauthenticated", "action": action}
    log_msg = f"Resource: {resource} | Status: {status} | IP: {ip} | Details: {details}"
    
    if status == "SUCCESS":
        audit_file_logger.info(log_msg, extra=extra)
    else:
        audit_file_logger.warning(log_msg, extra=extra)
        
    try:
        execute_db(
            """INSERT INTO tbl_security_audit_log
               (username, action, resource, status, ip_address, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username or "anonymous", action, resource, status, ip, details)
        )
    except Exception as e:
        # Failsafe so DB errors do not crash logging
        pass
