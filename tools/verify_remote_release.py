#!/usr/bin/env python3
"""Verify the pushed GitHub release handoff after local gates pass.

This helper is intentionally networked and post-push oriented. It fetches the
configured remote, proves the remote release branch matches local HEAD, can
verify an explicit remote release tag, verifies the remote AAB checksum from
`play_store/upload_checksums.md`, scans remote trees for signing/install
artifacts, and reuses the hosted privacy-policy URL checker.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKSUMS_PATH = ROOT / "play_store/upload_checksums.md"
POST_UPLOAD_EVIDENCE_PATH = ROOT / "play_store/play_console_post_upload_evidence_ru.md"
PRIVACY_URL_CHECK = ROOT / "tools/check_privacy_policy_url.py"
AAB_PATH = "app/build/outputs/bundle/release/app-release.aab"

MAIN_FORBIDDEN_PATTERNS = (
    re.compile(r"(^|/)(keystore\.properties|local\.properties)$"),
    re.compile(r"(^|/)private/"),
    re.compile(r"\.p12$"),
    re.compile(r"\.apk$"),
    re.compile(r"\.apks$"),
    re.compile(r"\.idsig$"),
)
PAGES_FORBIDDEN_PATTERNS = (*MAIN_FORBIDDEN_PATTERNS, re.compile(r"\.aab$"))


class RemoteReleaseError(RuntimeError):
    pass


def run_text(args: list[str], *, timeout: int = 60) -> str:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RemoteReleaseError(f"command failed ({completed.returncode}): {' '.join(args)}\n{completed.stdout}")
    return completed.stdout.strip()


def run_bytes(args: list[str], *, timeout: int = 60) -> bytes:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        output = completed.stdout.decode("utf-8", errors="ignore")
        raise RemoteReleaseError(f"command failed ({completed.returncode}): {' '.join(args)}\n{output}")
    return completed.stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RemoteReleaseError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify pushed Line 56 release state on a Git remote.")
    parser.add_argument("--remote", default="origin", help="Git remote to fetch and verify. Default: origin.")
    parser.add_argument("--branch", default="main", help="Release branch to verify. Default: main.")
    parser.add_argument("--pages-branch", default="gh-pages", help="Privacy-policy hosting branch. Default: gh-pages.")
    parser.add_argument("--tag", help="Optional release tag that must exist on the remote and peel to local HEAD.")
    parser.add_argument("--privacy-url", help="Hosted privacy-policy URL to validate. Defaults to recorded evidence URL.")
    parser.add_argument("--skip-privacy-url", action="store_true", help="Skip hosted privacy URL validation for diagnostics.")
    parser.add_argument("--allow-dirty", action="store_true", help="Do not require a clean local worktree before comparison.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned checks without contacting the remote.")
    return parser.parse_args()


def expected_aab() -> tuple[int, str]:
    text = CHECKSUMS_PATH.read_text(encoding="utf-8")
    match = re.search(
        rf"\| `{re.escape(AAB_PATH)}` \| (?P<bytes>\d+) \| `(?P<sha>[0-9a-f]{{64}})` \|",
        text,
    )
    require(match is not None, f"upload checksums missing {AAB_PATH} row")
    return int(match.group("bytes")), match.group("sha")


def recorded_privacy_url() -> str:
    text = POST_UPLOAD_EVIDENCE_PATH.read_text(encoding="utf-8")
    match = re.search(r"^- Public privacy policy URL:\s*(?P<url>\S+)", text, re.M)
    require(match is not None, "recorded Public privacy policy URL is missing")
    return match.group("url").rstrip(".,;)")


def require_clean_worktree() -> None:
    status = run_text(["git", "status", "--porcelain"], timeout=30)
    require(status == "", "local worktree is dirty; commit or stash changes before verifying pushed release state")


def fetch_remote(remote: str, branch: str, pages_branch: str, tag: str | None = None) -> None:
    refspecs = [
        f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}",
        f"+refs/heads/{pages_branch}:refs/remotes/{remote}/{pages_branch}",
    ]
    if tag:
        refspecs.append(f"+refs/tags/{tag}:refs/remotes/{remote}/tags/{tag}")
    run_text(["git", "fetch", "--quiet", remote, *refspecs], timeout=120)


def remote_ref(remote: str, branch: str) -> str:
    return f"refs/remotes/{remote}/{branch}"


def remote_tag_ref(remote: str, tag: str) -> str:
    return f"refs/remotes/{remote}/tags/{tag}"


def require_remote_head_matches(remote: str, branch: str) -> tuple[str, str]:
    local_head = run_text(["git", "rev-parse", "HEAD"], timeout=30)
    remote_head = run_text(["git", "rev-parse", remote_ref(remote, branch)], timeout=30)
    require(
        local_head == remote_head,
        f"{remote}/{branch} does not match local HEAD: remote={remote_head}, local={local_head}",
    )
    return local_head, remote_head


def require_remote_tag_matches(remote: str, tag: str, expected_commit: str) -> str:
    tag_commit = run_text(["git", "rev-parse", f"{remote_tag_ref(remote, tag)}^{{}}"], timeout=30)
    require(
        tag_commit == expected_commit,
        f"{remote} tag {tag} does not peel to local HEAD: tag={tag_commit}, local={expected_commit}",
    )
    return tag_commit


def verify_remote_aab(remote: str, branch: str) -> tuple[int, str]:
    expected_size, expected_sha = expected_aab()
    data = run_bytes(["git", "show", f"{remote_ref(remote, branch)}:{AAB_PATH}"], timeout=120)
    actual_size = len(data)
    actual_sha = hashlib.sha256(data).hexdigest()
    require(actual_size == expected_size, f"remote AAB size mismatch: {actual_size} != {expected_size}")
    require(actual_sha == expected_sha, f"remote AAB SHA-256 mismatch: {actual_sha} != {expected_sha}")
    return actual_size, actual_sha


def tree_paths(ref: str) -> list[str]:
    output = run_text(["git", "ls-tree", "-r", "--name-only", ref], timeout=60)
    return [line for line in output.splitlines() if line.strip()]


def verify_forbidden_paths(ref_label: str, paths: list[str], patterns: tuple[re.Pattern[str], ...]) -> None:
    forbidden = [path for path in paths if any(pattern.search(path) for pattern in patterns)]
    require(not forbidden, f"{ref_label} contains forbidden signing/install paths: {forbidden}")


def validate_privacy_url(url: str) -> None:
    output = run_text([str(PRIVACY_URL_CHECK), "--url", url], timeout=60)
    require("privacy_policy_url_ok" in output, "privacy policy URL check did not return privacy_policy_url_ok")


def main() -> int:
    args = parse_args()
    privacy_url = args.privacy_url or recorded_privacy_url()

    print("Remote release verification")
    print("===========================")
    print(f"Remote: {args.remote}")
    print(f"Branch: {args.branch}")
    print(f"Pages branch: {args.pages_branch}")
    if args.tag:
        print(f"Tag: {args.tag}")

    if args.dry_run:
        print(f"- fetch {args.remote} {args.branch} and {args.pages_branch}")
        print(f"- require {args.remote}/{args.branch} matches local HEAD")
        if args.tag:
            print(f"- require {args.remote} tag {args.tag} peels to local HEAD")
        print(f"- verify remote `{AAB_PATH}` bytes and SHA-256 from `play_store/upload_checksums.md`")
        print("- scan remote release branch for signing/install artifacts")
        print("- scan remote pages branch for signing/install/binary artifacts")
        if args.skip_privacy_url:
            print("- skip hosted privacy URL validation")
        else:
            print(f"- validate hosted privacy URL: {privacy_url}")
        print("remote_release_dry_run_ok")
        return 0

    try:
        if not args.allow_dirty:
            require_clean_worktree()
        fetch_remote(args.remote, args.branch, args.pages_branch, args.tag)
        local_head, _remote_head = require_remote_head_matches(args.remote, args.branch)
        tag_commit = require_remote_tag_matches(args.remote, args.tag, local_head) if args.tag else None
        aab_size, aab_sha = verify_remote_aab(args.remote, args.branch)

        release_ref = remote_ref(args.remote, args.branch)
        release_paths = tree_paths(release_ref)
        verify_forbidden_paths(f"{args.remote}/{args.branch}", release_paths, MAIN_FORBIDDEN_PATTERNS)

        pages_ref = remote_ref(args.remote, args.pages_branch)
        pages_paths = tree_paths(pages_ref)
        require("privacy_policy_ru.html" in pages_paths, f"{args.remote}/{args.pages_branch} missing privacy_policy_ru.html")
        verify_forbidden_paths(f"{args.remote}/{args.pages_branch}", pages_paths, PAGES_FORBIDDEN_PATTERNS)

        if not args.skip_privacy_url:
            validate_privacy_url(privacy_url)

        print(f"- commit: {local_head}")
        if args.tag:
            print(f"- remote tag {args.tag}: {tag_commit}")
        print(f"- remote AAB: {aab_size} bytes, sha256 {aab_sha}")
        print(f"- remote release branch forbidden-path scan: ok")
        print(f"- remote pages branch forbidden-path scan: ok")
        if args.skip_privacy_url:
            print("- hosted privacy URL check: skipped")
        else:
            print("- hosted privacy URL check: privacy_policy_url_ok")
        print("remote_release_ok")
        return 0
    except (OSError, RemoteReleaseError, subprocess.TimeoutExpired) as exc:
        print(f"remote_release_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
