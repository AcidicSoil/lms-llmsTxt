
how can I have this program also collect the links on pages for its final artifacts?

---

Add link harvesting in `full_builder.build_llms_full_from_repo` and emit them per block.

### What to change

1. Parse links from each fetched page body. Support Markdown `[text](url)` and HTML `<a href="...">text</a>`.

2. Resolve relative links against the source GitHub path and ref.

3. Append a “Links discovered” list under each `--- path ---` block in `llms-full`.
    This is the narrowest change. No CLI or schema edits needed. It fits where you already parse curated links and fetch bodies. codebase

### Patch

    *** a/full_builder.py
    --- b/full_builder.py
    @@
    -_PAGE_LINK = re.compile(r"^\s*-\s*\[(?P<title>.+?)\]\((?P<url>https?://[^\s)]+)\)", re.M)
    +_PAGE_LINK = re.compile(r"^\s*-\s*\[(?P<title>.+?)\]\((?P<url>https?://[^\s)]+)\)", re.M)
    +# within-page link patterns
    +_MD_LINK = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<href>[^)\s]+)\)")
    +_HTML_LINK = re.compile(r"<a\s+[^>]*href=[\"'](?P<href>[^\"'#]+)[\"'][^>]*>(?P<text>.*?)</a>", re.I | re.S)
    @@
     def iter_llms_links(curated_text: str) -> Iterable[Tuple[str, str]]:
         for match in _PAGE_LINK.finditer(curated_text):
             yield match.group("title").strip(), match.group("url").strip()


     def sanitize_path_for_block(title: str, url: str, gh: Optional[GhRef]) -> str:
    @@
         return path.lstrip("/")

    +def _resolve_repo_url(gh: GhRef, ref: str, href: str) -> Optional[str]:
    +    """
    +    Turn a relative repo doc link into a raw.githubusercontent URL when possible.
    +    Returns None for non-resolvable schemes like mailto:, javascript:, or fragments.
    +    """
    +    href = href.strip()
    +    if not href or href.startswith(("#", "mailto:", "javascript:")):
    +        return None
    +    if href.startswith(("http://", "https://")):
    +        return href
    +    # Resolve against the current file's directory
    +    base_dir = gh.path.rsplit("/", 1)[0] if "/" in gh.path else ""
    +    if href.startswith("/"):
    +        # repo-root relative
    +        resolved_path = href.lstrip("/")
    +    else:
    +        resolved_path = f"{base_dir}/{href}".replace("//", "/")
    +    return f"https://raw.githubusercontent.com/{gh.owner}/{gh.repo}/{ref}/{resolved_path}"
    +
    +def _extract_links(body_text: str, gh: Optional[GhRef], ref: str) -> list[tuple[str, str]]:
    +    """
    +    Extract outbound links from page content and resolve to absolute URLs.
    +    """
    +    seen: set[tuple[str, str]] = set()
    +    found: list[tuple[str, str]] = []
    +    # Markdown links
    +    for m in _MD_LINK.finditer(body_text):
    +        text = m.group("text").strip()
    +        href = m.group("href").strip()
    +        if gh:
    +            resolved = _resolve_repo_url(gh, ref, href)
    +        else:
    +            resolved = href if href.startswith(("http://", "https://")) else None
    +        if not resolved:
    +            continue
    +        key = (text, resolved)
    +        if key not in seen:
    +            seen.add(key)
    +            found.append((text, resolved))
    +    # HTML links
    +    for m in _HTML_LINK.finditer(body_text):
    +        text = re.sub(r"\s+", " ", m.group("text")).strip() or "link"
    +        href = m.group("href").strip()
    +        if gh:
    +            resolved = _resolve_repo_url(gh, ref, href)
    +        else:
    +            resolved = href if href.startswith(("http://", "https://")) else None
    +        if not resolved:
    +            continue
    +        key = (text, resolved)
    +        if key not in seen:
    +            seen.add(key)
    +            found.append((text, resolved))
    +    return found
    @@
     def build_llms_full_from_repo(
    @@
         for title, url in iter_llms_links(curated_llms_text):
    @@
    -        if len(body) > max_bytes_per_file:
    -            body = body[:max_bytes_per_file] + b"\n[truncated]\n"
    +        truncated = False
    +        if len(body) > max_bytes_per_file:
    +            body = body[:max_bytes_per_file] + b"\n[truncated]\n"
    +            truncated = True
    @@
    -        block_path = sanitize_path_for_block(title, url, gh)
    -        blocks.append(f"--- {block_path} ---\n{body.decode('utf-8', 'replace')}\n")
    +        block_path = sanitize_path_for_block(title, url, gh)
    +        text_body = body.decode("utf-8", "replace")
    +        # collect outbound links from the fetched page
    +        links = _extract_links(text_body, gh, resolved_ref)
    +        # cap to avoid runaway output if page is a link farm
    +        links = links[:100]
    +        link_section = ""
    +        if links:
    +            bullet_lines = "\n".join(f"- [{t}]({h})" for t, h in links)
    +            link_section = f"\n## Links discovered\n{bullet_lines}\n"
    +        blocks.append(f"--- {block_path} ---\n{text_body}\n{link_section}")
             count += 1


### Why here

* You already iterate curated links and fetch raw content in `build_llms_full_from_repo`, so link discovery belongs there. codebase

* Keeps CLI and artifact paths stable. `-llms-full.txt` gains a deterministic “Links discovered” section per source page. codebase

### Notes

* Relative links are resolved to the same repo and `resolved_ref` so downstream tools can fetch them. codebase

* The cap of 100 avoids bloat. Adjust as needed.

* If you prefer a separate artifact, emit `links.json` or `links.txt` in `pipeline.run_generation` after `llms_full_text` is built; the extraction function above is reusable in that step. codebase

Run your pipeline as usual. The generated `*-llms-full.txt` will now include per-page outbound links under “Links discovered.”

---
