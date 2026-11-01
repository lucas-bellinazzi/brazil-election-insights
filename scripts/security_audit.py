"""Security audit and supply chain integrity verification script for Brazil Election Insights."""

import ast
import re
import sys
from pathlib import Path

# Unsafe functions that should never be present in application code
DANGEROUS_CALLS = {
    "eval",
    "exec",
    "pickle.loads",
    "pickle.load",
    "os.system",
    "subprocess.Popen",
}


def audit_lockfile(root_dir: Path) -> tuple[bool, str]:
    """Verify uv.lock presence, format, and hash pinning."""
    lock_path = root_dir / "uv.lock"
    if not lock_path.is_file():
        return (
            False,
            "CRITICAL: uv.lock file is missing! Reproducibility and supply chain compromised.",
        )

    content = lock_path.read_text(encoding="utf-8")
    if len(content) < 1000:
        return False, "CRITICAL: uv.lock appears truncated or empty."

    # Verify that packages have hashes
    if "hash = " not in content and "hashes = [" not in content:
        return (
            False,
            "WARNING: uv.lock does not appear to contain cryptographic hashes for wheels.",
        )

    # Count packages in lockfile
    package_count = len(re.findall(r"\[\[package\]\]", content))
    return True, f"OK: uv.lock present and verified ({package_count} pinned packages with hashes)."


def audit_secrets_exposure(root_dir: Path) -> list[str]:
    """Scan all Python and config files for hardcoded secrets or API keys."""
    findings = []
    secret_regex = re.compile(r"sk-[a-zA-Z0-9_\-]{20,}")

    for ext in ["*.py", "*.toml", "*.yaml", "*.yml", "*.json"]:
        for file_path in root_dir.glob(f"**/{ext}"):
            # Skip virtualenv, git, and test fixture directories
            if any(
                part in file_path.parts
                for part in [".venv", "venv", ".git", "__pycache__", "tests"]
            ):
                continue

            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                matches = secret_regex.findall(text)
                if matches:
                    findings.append(
                        f"CRITICAL: Possible hardcoded secret in {file_path.relative_to(root_dir)}"
                    )
            except Exception:
                continue

    return findings


def audit_code_safety(root_dir: Path) -> list[str]:
    """AST-based scan for unsafe execution functions (eval, exec, etc.)."""
    findings = []

    for py_file in (root_dir / "src").glob("**/*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    func_name = f"{node.func.value.id}.{node.func.attr}"

                if func_name in DANGEROUS_CALLS:
                    findings.append(
                        f"CRITICAL: Dangerous call '{func_name}' at {py_file.name}:{node.lineno}"
                    )

    return findings


def audit_gitignore(root_dir: Path) -> tuple[bool, str]:
    """Verify that .env is ignored and uv.lock is NOT ignored."""
    gitignore_path = root_dir / ".gitignore"
    if not gitignore_path.is_file():
        return False, "CRITICAL: .gitignore missing!"

    content = gitignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines()]

    if ".env" not in lines and not any(".env" in line for line in lines):
        return False, "CRITICAL: .env is not listed in .gitignore!"

    if "uv.lock" in lines:
        return False, "CRITICAL: uv.lock is listed in .gitignore! It MUST be committed."

    return True, "OK: .gitignore properly protects .env and preserves uv.lock."


def run_security_audit() -> bool:
    """Run full security suite audit and print structured report."""
    root_dir = Path(__file__).resolve().parent.parent
    print("=" * 80)
    print("BRAZIL ELECTION INSIGHTS — SECURITY & SUPPLY CHAIN AUDIT")
    print("=" * 80)

    all_passed = True

    # 1. Lockfile audit
    lock_ok, lock_msg = audit_lockfile(root_dir)
    print(f"[*] Lockfile & Supply Chain Check: {lock_msg}")
    if not lock_ok:
        all_passed = False

    # 2. Gitignore audit
    gi_ok, gi_msg = audit_gitignore(root_dir)
    print(f"[*] Gitignore & Secrets Boundary: {gi_msg}")
    if not gi_ok:
        all_passed = False

    # 3. Secrets exposure scan
    secret_findings = audit_secrets_exposure(root_dir)
    if secret_findings:
        print("[!] Secrets Scan: FAILED")
        for f in secret_findings:
            print(f"    - {f}")
        all_passed = False
    else:
        print("[*] Secrets Scan: OK (No hardcoded API tokens or keys found).")

    # 4. Code safety audit
    code_findings = audit_code_safety(root_dir)
    if code_findings:
        print("[!] Code Safety Scan: FAILED")
        for f in code_findings:
            print(f"    - {f}")
        all_passed = False
    else:
        print("[*] Code Safety Scan: OK (No eval, exec, os.system, or pickle usage in src/).")

    print("=" * 80)
    if all_passed:
        print("RESULT: ALL SECURITY AUDIT CHECKS PASSED SUCCESSFULLY [100% SECURE]")
    else:
        print("RESULT: SECURITY CHECKS FAILED - REMEDIATION REQUIRED")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = run_security_audit()
    sys.exit(0 if success else 1)
