# -*- coding: utf-8 -*-
"""一键把当前版本发布到 GitHub（约定：每次版本更新都要跑）。

流程：
  1. 从 src/app.py 读 APP_VER，确认 dist/ 与 源码交付/ 下有对应版本产物；
  2. git add -A → commit（若有改动）→ tag v<版本> → push main + tag；
  3. 创建/复用 Release v<版本>，上传/替换三个资产：
       ImageToPDF_Studio_v<版本>.exe
       ImageToPDF_Source_v<版本>.zip
       Manual_v<版本>.html
  4. 全程不把 Token 写入任何文件。

用法：
    set GITHUB_TOKEN=ghp_xxx        (Windows CMD)
    $env:GITHUB_TOKEN="ghp_xxx"     (PowerShell)
    export GITHUB_TOKEN=ghp_xxx     (Git Bash)
    python scripts/upload_to_github.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = "borisKP"
REPO = "ImageToPDF_Studio"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
UPLOADS = f"https://uploads.github.com/repos/{OWNER}/{REPO}"


def die(msg: str):
    print(f"错误: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read_version() -> str:
    with open(os.path.join(ROOT, "src", "app.py"), encoding="utf-8") as f:
        m = re.search(r'^APP_VER\s*=\s*"([^"]+)"', f.read(), re.M)
    if not m:
        die("无法从 src/app.py 读取 APP_VER")
    return m.group(1)


def git(args: list[str], *, allow_fail: bool = False) -> str:
    """执行 git，复用系统代理但避免 Git 自身 CONNECT tunnel 502。"""
    env = os.environ.copy()
    proxy = env.get("HTTPS_PROXY") or env.get("https_proxy") or ""
    for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        env.pop(k, None)
    cmd = ["git"]
    if proxy:
        cmd += ["-c", f"http.proxy={proxy}", "-c", f"https.proxy={proxy}"]
    cmd += ["-c", "credential.helper=", "-C", ROOT] + args
    p = subprocess.run(cmd, env=env, text=True, capture_output=True)
    if p.returncode and not allow_fail:
        safe = (p.stderr or "").replace(os.environ.get("GITHUB_TOKEN", ""), "***")
        die(f"git {' '.join(args)} 失败:\n{safe.strip()}")
    return (p.stdout or p.stderr or "").strip()


def api(method: str, path: str, payload: dict | None = None,
        *, upload: bool = False, data_path: str | None = None,
        content_type: str | None = None):
    base = UPLOADS if upload else API
    url = base + path
    token = os.environ["GITHUB_TOKEN"]
    body = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ImageToPDF-Release-Bot",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif data_path:
        with open(data_path, "rb") as f:
            body = f.read()
        headers["Content-Type"] = content_type or "application/octet-stream"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        die(f"GitHub API {method} {path} 失败: HTTP {e.code}\n{e.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as e:
        die(f"GitHub API {method} {path} 网络失败: {e.reason}")
    return json.loads(raw) if raw.strip().startswith(("{", "[")) else raw


def main():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        die("未设置 GITHUB_TOKEN。请设置 classic PAT（勾 repo 权限）后重试；不要把 Token 写进文件。")

    ver = read_version()
    tag = f"v{ver}"
    print(f"版本: {tag}")

    assets = [
        (f"ImageToPDF_Studio_v{ver}.exe",
         os.path.join(ROOT, "dist", "ImageToPDF_Studio.exe"), "application/octet-stream"),
        (f"ImageToPDF_Source_v{ver}.zip",
         os.path.join(ROOT, "源码交付", f"ImageToPDF_源码_v{ver}.zip"), "application/zip"),
        (f"Manual_v{ver}.html",
         os.path.join(ROOT, "dist", "使用说明.html"), "text/html"),
    ]
    for name, path, _ in assets:
        if not os.path.isfile(path):
            die(f"缺少构建产物: {path}（先跑 build.bat）")

    # 提交 + 标签 + 推送
    git(["add", "-A"])
    changed = git(["status", "--porcelain"])
    if changed:
        git(["commit", "-m", f"Release {tag}: version-synced source and docs"])
        print("已提交本地改动")
    else:
        print("无本地改动需要提交")
    if tag in git(["tag", "--list", tag]).splitlines():
        print(f"标签 {tag} 已存在，跳过")
    else:
        git(["tag", tag])
    # 一次性 URL 携带 Token 推送；不把 Token 写进 remote / .git/config / 任何文件
    remote = f"https://{OWNER}:{urllib.parse.quote(token, safe='')}@github.com/{OWNER}/{REPO}.git"
    git(["push", "-u", remote, "main"])
    git(["push", remote, tag])
    print("源码与标签已推送")

    # Release：存在则复用，否则创建
    releases = api("GET", "/releases")
    rel = next((r for r in releases if r.get("tag_name") == tag), None)
    if rel is None:
        rel = api("POST", "/releases", {
            "tag_name": tag,
            "name": f"ImageToPDF Studio {tag}",
            "body": "EXE trimmed from 75 MB to 52 MB. See CHANGELOG.md for details.",
            "draft": False,
            "prerelease": False,
        })
        print(f"已创建 Release {tag}")
    else:
        print(f"复用已有 Release {tag} (id={rel['id']})")
    rid = rel["id"]

    # 同名资产先删再传，保证版本更新后资产是最新文件
    for a in api("GET", f"/releases/{rid}/assets"):
        if a["name"] in {n for n, _, _ in assets}:
            api("DELETE", f"/releases/assets/{a['id']}")
    for name, path, ctype in assets:
        result = api("POST", f"/releases/{rid}/assets?name={urllib.parse.quote(name)}",
                     upload=True, data_path=path, content_type=ctype)
        print(f"上传 {result['name']}  {result['size'] / 1024 / 1024:.2f} MB")

    print(f"\n完成: https://github.com/{OWNER}/{REPO}/releases/tag/{tag}")


if __name__ == "__main__":
    main()
