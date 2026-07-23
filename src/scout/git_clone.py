"""
Secure Git Clone + Cleanup (ADR-032)
=====================================
Clones a GitHub repo into /tmp/lex-scan-{run_id}/ for local scanning.
Always deletes the clone after scanning — code never persists (ADR-001).
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

CLONE_BASE = Path("/tmp")


def clone_repo(
    repo_url: str,
    run_id: str,
    github_token: str | None = None,
) -> Path | None:
    """
    Clone a GitHub repo into /tmp/lex-scan-{run_id[:8]}/.
    Returns the local path or None on failure.
    Injects token into URL for private repos.
    """
    short_id = run_id[:8]
    clone_path = CLONE_BASE / f"lex-scan-{short_id}"

    if clone_path.exists():
        shutil.rmtree(clone_path, ignore_errors=True)

    # Inject token for private repos
    clone_url = repo_url
    if github_token and "github.com" in repo_url:
        clone_url = repo_url.replace(
            "https://github.com",
            f"https://{github_token}@github.com",
        )

    logger.info("Cloning repo: %s → %s", repo_url, clone_path)
    try:
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", clone_url, str(clone_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("git clone failed: %s", result.stderr[:200])
            return None
        logger.info("Clone successful: %s", clone_path)
        try:
            from src.utils.scan_logger import log_git_clone
            log_git_clone(run_id, repo_url, str(clone_path))
        except Exception as e:
            logger.warning("scan_logger log_git_clone failed (non-fatal): %s", e)
        return clone_path
    except subprocess.TimeoutExpired:
        logger.error("git clone timed out after 120s")
        return None
    except Exception as e:
        logger.error("git clone error: %s", e)
        return None


def cleanup_clone(clone_path: Path | None, run_id: str | None = None) -> None:
    """
    Securely delete the cloned repo (ADR-001 — code never persists).
    Called in try/finally — always runs even on scan errors.
    """
    if clone_path is None:
        return
    if clone_path.exists():
        shutil.rmtree(clone_path, ignore_errors=True)
        logger.info("Clone deleted: %s", clone_path)
        if run_id:
            try:
                from src.utils.scan_logger import log_git_delete
                log_git_delete(run_id, str(clone_path))
            except Exception as e:
                logger.warning("scan_logger log_git_delete failed (non-fatal): %s", e)
    else:
        logger.debug("Clone path already gone: %s", clone_path)
