#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==========================================
Version: 1.0.7
Date: 2026-03-30
Summary: CSS内 url(...) も画像取得・ローカル書き換え
Author: Codex
==========================================
"""
from __future__ import annotations

import argparse
import html.parser
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Set, Tuple

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _norm_url(base: str, href: str) -> Optional[str]:
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    joined = urllib.parse.urljoin(base, href)
    parsed = urllib.parse.urlparse(joined)
    if parsed.scheme not in ("http", "https"):
        return None
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
    )


def _same_host(url: str, host: str) -> bool:
    return urllib.parse.urlparse(url).netloc.lower() == host.lower()


def _local_path_for_url(site_out: str, site_host: str, url: str, flat: bool) -> str:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path or "/"
    if path.endswith("/"):
        path = path + "index.html"
    path = path.lstrip("/")
    if not path:
        path = "index.html"
    base = site_out if flat else os.path.join(site_out, site_host)
    full = os.path.join(base, path)
    return full


class LinkCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        ad = dict(attrs)
        candidates: List[str] = []
        if tag == "link" and ad.get("rel", "").lower() in (
            "stylesheet",
            "shortcut icon",
            "icon",
        ):
            if ad.get("href"):
                candidates.append(ad["href"])
        elif tag == "script" and ad.get("src"):
            candidates.append(ad["src"])
        elif tag == "img":
            # srcset/data-srcset は "URL descriptor, URL descriptor" 形式のため、
            # 先頭URLだけを個別候補として回収する。
            if ad.get("src"):
                candidates.append(ad["src"])
            if ad.get("data-src"):
                candidates.append(ad["data-src"])
            for key in ("srcset", "data-srcset"):
                v = ad.get(key)
                if not v:
                    continue
                for part in v.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    tokens = part.split()
                    if tokens:
                        candidates.append(tokens[0])
        elif tag in ("a", "area") and ad.get("href"):
            candidates.append(ad["href"])
        elif tag in ("source",):
            if ad.get("src"):
                candidates.append(ad["src"])
            v = ad.get("srcset")
            if v:
                for part in v.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    tokens = part.split()
                    if tokens:
                        candidates.append(tokens[0])
        style_val = ad.get("style")
        if style_val and "url(" in style_val:
            # style="... background-image:url(http(s)://host/path) ..." のような記法を拾う
            for m in re.finditer(
                r'url\((["\']?)(https?://[^)"\']+)\1\)',
                style_val,
                flags=re.I,
            ):
                candidates.append(m.group(2))
        for c in candidates:
            if c:
                self.urls.append(c)


def fetch(url: str, timeout: int = 30) -> Tuple[bytes, str, Dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = resp.headers.get_content_type()
        return data, ctype, dict(resp.headers)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="開始URL（例: https://example.com/top/）")
    ap.add_argument("--out", required=True, help="出力ルート")
    ap.add_argument(
        "--max-fetches",
        type=int,
        default=4000,
        help="最大取得回数（HTML/CSS/画像など合計）",
    )
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument(
        "--flat",
        action="store_true",
        help="ホスト名フォルダを付けず site_out 直下にパスだけで保存",
    )
    args = ap.parse_args()

    start = args.start.strip()
    parsed = urllib.parse.urlparse(start)
    host = parsed.netloc
    if not host:
        print("invalid start url", file=sys.stderr)
        return 1

    site_out = os.path.abspath(args.out)
    os.makedirs(site_out, exist_ok=True)

    queue: List[str] = [start]
    seen: Set[str] = set()
    html_pages = 0
    total_fetches = 0

    while queue and total_fetches < args.max_fetches:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if not _same_host(url, host):
            continue

        local_path = _local_path_for_url(site_out, host, url, args.flat)
        parent = os.path.dirname(local_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        try:
            time.sleep(args.delay)
            data, ctype, _headers = fetch(url)
            total_fetches += 1
        except urllib.error.HTTPError as e:
            print(f"HTTPError {e.code} {url}", file=sys.stderr)
            total_fetches += 1
            continue
        except Exception as e:
            print(f"fetch fail {url}: {e}", file=sys.stderr)
            total_fetches += 1
            continue

        is_html = "html" in ctype or url.endswith((".htm", ".html")) or (
            ctype.startswith("text/") and b"<html" in data[:2000].lower()
        )
        is_css = url.lower().endswith(".css") or ctype.startswith("text/css")

        if is_html:
            html_pages += 1
            text = data.decode("utf-8", errors="replace")
            collector = LinkCollector()
            try:
                collector.feed(text)
            except Exception:
                pass
            for raw in collector.urls:
                abs_u = _norm_url(url, raw)
                if abs_u and _same_host(abs_u, host) and abs_u not in seen:
                    queue.append(abs_u)

            def rel_for_target(target_url: str) -> Optional[str]:
                if not _same_host(target_url, host):
                    return None
                cur_dir = os.path.dirname(local_path)
                tgt_path = _local_path_for_url(site_out, host, target_url, args.flat)
                rel = os.path.relpath(tgt_path, cur_dir)
                return rel.replace(os.sep, "/")

            def rewrite_attr(match: re.Match) -> str:
                attr_raw = match.group(1)
                attr = attr_raw.lower()
                quote = match.group(2)
                val = match.group(3)

                if attr in ("srcset", "data-srcset"):
                    # srcset/data-srcset は「URL descriptor, URL descriptor」の形式があるため、
                    # まずカンマ区切りで分割し、各要素の先頭URLだけをローカルへ書き換える。
                    rewritten_parts: List[str] = []
                    for part in val.split(","):
                        part = part.strip()
                        if not part:
                            continue
                        tokens = part.split()
                        if not tokens:
                            continue
                        first_url = tokens[0]
                        abs_u = _norm_url(url, first_url)
                        if abs_u and _same_host(abs_u, host):
                            r = rel_for_target(abs_u)
                            if r:
                                tokens[0] = r
                                rewritten_parts.append(" ".join(tokens))
                                continue
                        rewritten_parts.append(part)

                    if rewritten_parts:
                        new_val = ", ".join(rewritten_parts)
                        return f"{attr_raw}={quote}{new_val}{quote}"
                    return match.group(0)

                abs_u = _norm_url(url, val)
                if abs_u and _same_host(abs_u, host):
                    r = rel_for_target(abs_u)
                    if r:
                        return f"{attr_raw}={quote}{r}{quote}"
                return match.group(0)

            text = re.sub(
                r'(href|src|srcset|data-src|data-srcset)=(["\'])([^"\']+)\2',
                rewrite_attr,
                text,
                flags=re.I,
            )
            def rewrite_css_url(match: re.Match) -> str:
                quote = match.group(1)
                val = match.group(2)
                abs_u = _norm_url(url, val)
                if abs_u and _same_host(abs_u, host):
                    r = rel_for_target(abs_u)
                    if r:
                        return f"url({quote}{r}{quote})"
                return match.group(0)

            # style属性やstyleタグ内の url(http(s)://...) をローカル相対パスへ書き換え
            text = re.sub(
                r'url\((["\']?)(https?://[^)"\']+)\1\)',
                rewrite_css_url,
                text,
                flags=re.I,
            )
            data = text.encode("utf-8", errors="replace")
            if not local_path.endswith((".html", ".htm")):
                if local_path.endswith("/"):
                    local_path = os.path.join(local_path, "index.html")
                elif not os.path.splitext(local_path)[1]:
                    local_path += ".html"

        if is_css:
            text = data.decode("utf-8", errors="replace")

            def rel_for_target_css(target_url: str) -> Optional[str]:
                if not _same_host(target_url, host):
                    return None
                cur_dir = os.path.dirname(local_path)
                tgt_path = _local_path_for_url(site_out, host, target_url, args.flat)
                rel = os.path.relpath(tgt_path, cur_dir)
                return rel.replace(os.sep, "/")

            # CSS内の url(...) を列挙して「同ホスト」参照の画像を取得キューへ追加
            # - 例: background-image:url(images/top_bg.jpg)
            # - 例: background-image:url(/images/foo.jpg)
            url_pat = r'url\((["\']?)([^)"\']+)\1\)'

            for m in re.finditer(url_pat, text, flags=re.I):
                raw_val = m.group(2).strip()
                if not raw_val:
                    continue
                if raw_val.startswith(("data:", "javascript:", "#")):
                    continue
                abs_u = _norm_url(url, raw_val)
                if abs_u and _same_host(abs_u, host) and abs_u not in seen:
                    queue.append(abs_u)

            # url(...) 自体もローカル相対パスへ書き換え
            def rewrite_css_url_any(match: re.Match) -> str:
                quote = match.group(1)
                val = match.group(2).strip()
                abs_u = _norm_url(url, val)
                if abs_u and _same_host(abs_u, host):
                    r = rel_for_target_css(abs_u)
                    if r:
                        return f"url({quote}{r}{quote})"
                return match.group(0)

            text = re.sub(url_pat, rewrite_css_url_any, text, flags=re.I)
            data = text.encode("utf-8", errors="replace")

        with open(local_path, "wb") as f:
            f.write(data)
        print("saved", url, "->", local_path)

    print("done. html_pages:", html_pages, "total_fetches:", total_fetches, "unique_urls:", len(seen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
