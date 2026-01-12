tree
.
├── llmstxt.translate.yaml
├── scripts/
│   └── llmstxt_translate_artifacts.py
└── src/
    └── llmstxt_translate/
        ├── __init__.py
        ├── cache.py
        ├── config.py
        ├── nllb.py
        ├── runner.py
        └── segment.py

```yaml
# path: llmstxt.translate.yaml
# Additional translation run for generated artifacts (run-your-own MT)
# Example: repo-native artifact is Japanese -> produce an English sibling.

translator:
  backend: nllb
  model_id: facebook/nllb-200-distilled-600M

  # FLORES-200 language codes (examples): Japanese=jpn_Jpan, English=eng_Latn
  source_lang: jpn_Jpan
  target_langs:
    - eng_Latn

  # Device selection
  device: auto         # auto|cpu|cuda:0|mps
  dtype: auto          # auto|float16|bfloat16|float32

  # Optional quantization (kept off by default)
  # - bnb8bit uses bitsandbytes 8-bit weights (GPU-oriented)
  quantization: none   # none|bnb8bit

  # Generation defaults: deterministic, no sampling
  generate:
    max_new_tokens: 256
    num_beams: 1
    do_sample: false

io:
  # Which artifacts to translate (post-generation)
  artifacts_glob:
    - "**/llms.txt"
    - "**/llms-full.txt"

  # Output naming: create siblings next to the source file.
  # Supported template vars:
  #   {src_path} {src_stem} {src_suffix} {tgt_lang}
  output_template: "{src_stem}.{tgt_lang}{src_suffix}"

  # If true, skip translation when the target file exists.
  skip_if_exists: true

  # Optional: only translate when the source seems non-English.
  # (light heuristic; safe default is false and rely on explicit source_lang)
  only_if_non_english: false

  # Deterministic cache for translated segments
  cache_dir: ".cache/llmstxt-translate"

markdown:
  # Preserve these constructs verbatim.
  preserve_code_fences: true

  # Protect inline code and markdown links by placeholdering before translation
  preserve_inline_code: true
  preserve_markdown_links: true
  preserve_urls: true

  # Additional do-not-translate patterns (regex). Useful for paths/identifiers.
  do_not_translate_regex:
    - "(?<!\\w)(?:\\.?\\/)?[A-Za-z0-9_.-]+(?:\\/[A-Za-z0-9_.-]+)+(?<!\\W)"   # path-ish
    - "(?<!\\w)[A-Za-z0-9_.-]+\\.(?:md|txt|json|yaml|yml|toml|py|go|js|ts)(?!\\w)" # filenames
    - "`[^`]+`"  # inline code (redundant if preserve_inline_code=true)

runtime:
  batch_size: 8
  max_chars_per_segment: 1800
  log_level: info
```

```python
# path: scripts/llmstxt_translate_artifacts.py
"""CLI entrypoint for an additional, local translation run over generated artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from llmstxt_translate.config import load_config
from llmstxt_translate.runner import translate_artifacts


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="llmstxt-translate-artifacts",
        description="Translate lms-llmstxt artifacts using a local MT model (NLLB).",
    )
    p.add_argument("--config", required=True, help="Path to llmstxt.translate.yaml")
    p.add_argument(
        "--root",
        default=".",
        help="Repo/workdir root (used to resolve globs). Defaults to current dir.",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    cfg = load_config(Path(args.config))
    root = Path(args.root).resolve()

    result = translate_artifacts(root=root, cfg=cfg)

    # Minimal machine-readable summary
    print(f"translated_files={result.translated_files}")
    print(f"skipped_files={result.skipped_files}")
    print(f"segments_total={result.segments_total}")
    print(f"segments_cache_hit={result.segments_cache_hit}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

```python
# path: src/llmstxt_translate/__init__.py
__all__ = [
    "config",
    "runner",
    "nllb",
    "segment",
    "cache",
]
```

```python
# path: src/llmstxt_translate/config.py
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml


Quantization = Literal["none", "bnb8bit"]


@dataclass(frozen=True)
class GenerateConfig:
    max_new_tokens: int = 256
    num_beams: int = 1
    do_sample: bool = False


@dataclass(frozen=True)
class TranslatorConfig:
    backend: str
    model_id: str
    source_lang: str
    target_langs: list[str]
    device: str = "auto"  # auto|cpu|cuda:0|mps
    dtype: str = "auto"   # auto|float16|bfloat16|float32
    quantization: Quantization = "none"
    generate: GenerateConfig = dataclasses.field(default_factory=GenerateConfig)


@dataclass(frozen=True)
class IOConfig:
    artifacts_glob: list[str]
    output_template: str
    skip_if_exists: bool = True
    only_if_non_english: bool = False
    cache_dir: str = ".cache/llmstxt-translate"


@dataclass(frozen=True)
class MarkdownConfig:
    preserve_code_fences: bool = True
    preserve_inline_code: bool = True
    preserve_markdown_links: bool = True
    preserve_urls: bool = True
    do_not_translate_regex: list[str] = dataclasses.field(default_factory=list)


@dataclass(frozen=True)
class RuntimeConfig:
    batch_size: int = 8
    max_chars_per_segment: int = 1800
    log_level: str = "info"


@dataclass(frozen=True)
class AppConfig:
    translator: TranslatorConfig
    io: IOConfig
    markdown: MarkdownConfig
    runtime: RuntimeConfig


def _require(d: dict[str, Any], key: str) -> Any:
    if key not in d:
        raise ValueError(f"Missing required config key: {key}")
    return d[key]


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config must be a YAML mapping")

    t = _require(raw, "translator")
    i = _require(raw, "io")
    m = raw.get("markdown", {})
    r = raw.get("runtime", {})

    gen = t.get("generate", {})

    cfg = AppConfig(
        translator=TranslatorConfig(
            backend=_require(t, "backend"),
            model_id=_require(t, "model_id"),
            source_lang=_require(t, "source_lang"),
            target_langs=list(_require(t, "target_langs")),
            device=t.get("device", "auto"),
            dtype=t.get("dtype", "auto"),
            quantization=t.get("quantization", "none"),
            generate=GenerateConfig(
                max_new_tokens=int(gen.get("max_new_tokens", 256)),
                num_beams=int(gen.get("num_beams", 1)),
                do_sample=bool(gen.get("do_sample", False)),
            ),
        ),
        io=IOConfig(
            artifacts_glob=list(_require(i, "artifacts_glob")),
            output_template=_require(i, "output_template"),
            skip_if_exists=bool(i.get("skip_if_exists", True)),
            only_if_non_english=bool(i.get("only_if_non_english", False)),
            cache_dir=i.get("cache_dir", ".cache/llmstxt-translate"),
        ),
        markdown=MarkdownConfig(
            preserve_code_fences=bool(m.get("preserve_code_fences", True)),
            preserve_inline_code=bool(m.get("preserve_inline_code", True)),
            preserve_markdown_links=bool(m.get("preserve_markdown_links", True)),
            preserve_urls=bool(m.get("preserve_urls", True)),
            do_not_translate_regex=list(m.get("do_not_translate_regex", [])),
        ),
        runtime=RuntimeConfig(
            batch_size=int(r.get("batch_size", 8)),
            max_chars_per_segment=int(r.get("max_chars_per_segment", 1800)),
            log_level=str(r.get("log_level", "info")),
        ),
    )

    if cfg.translator.backend != "nllb":
        raise ValueError(f"Unsupported backend: {cfg.translator.backend}")

    return cfg
```

```python
# path: src/llmstxt_translate/cache.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CacheKey:
    model_id: str
    src_lang: str
    tgt_lang: str
    text_hash: str

    def as_str(self) -> str:
        return f"{self.model_id}|{self.src_lang}|{self.tgt_lang}|{self.text_hash}"


class TranslationCache:
    """Append-only JSONL cache: each line is {key, value}."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.cache_dir / "translations.jsonl"
        self._mem: dict[str, str] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        if not self.path.exists():
            self._loaded = True
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                self._mem[str(obj["key"])] = str(obj["value"])
            except Exception:
                # Corrupt line: ignore (keeps cache best-effort)
                continue
        self._loaded = True

    def get(self, key: CacheKey) -> Optional[str]:
        self.load()
        return self._mem.get(key.as_str())

    def put(self, key: CacheKey, value: str) -> None:
        self.load()
        k = key.as_str()
        if k in self._mem:
            return
        self._mem[k] = value
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": k, "value": value}, ensure_ascii=False) + "\n")

    @staticmethod
    def make_key(model_id: str, src_lang: str, tgt_lang: str, text: str) -> CacheKey:
        normalized = " ".join(text.split())
        return CacheKey(model_id=model_id, src_lang=src_lang, tgt_lang=tgt_lang, text_hash=_sha256(normalized))
```

```python
# path: src/llmstxt_translate/segment.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


_FENCE_RE = re.compile(r"^```")


@dataclass(frozen=True)
class Block:
    kind: str  # "code" | "text"
    text: str


def split_markdown_blocks(md: str) -> list[Block]:
    """Split into code-fence blocks vs text blocks.

    This is intentionally simple and deterministic.
    """
    lines = md.splitlines(keepends=True)
    blocks: list[Block] = []

    in_code = False
    buf: list[str] = []

    def flush(kind: str) -> None:
        nonlocal buf
        if buf:
            blocks.append(Block(kind=kind, text="".join(buf)))
            buf = []

    for ln in lines:
        if _FENCE_RE.match(ln):
            # fence line belongs to whichever state we're in, then toggles.
            if in_code:
                buf.append(ln)
                flush("code")
                in_code = False
            else:
                flush("text")
                in_code = True
                buf.append(ln)
            continue

        buf.append(ln)

    flush("code" if in_code else "text")
    return blocks


@dataclass(frozen=True)
class Protected:
    text: str
    table: dict[str, str]


def protect_spans(
    s: str,
    *,
    preserve_inline_code: bool,
    preserve_markdown_links: bool,
    preserve_urls: bool,
    extra_regex: list[str],
) -> Protected:
    """Replace spans that should not be translated with placeholders."""

    patterns: list[re.Pattern[str]] = []

    if preserve_inline_code:
        patterns.append(re.compile(r"`[^`]+`"))

    if preserve_markdown_links:
        patterns.append(re.compile(r"\[[^\]]+\]\([^\)]+\)"))

    if preserve_urls:
        patterns.append(re.compile(r"https?://\S+"))

    for rgx in extra_regex:
        patterns.append(re.compile(rgx))

    table: dict[str, str] = {}
    out = s

    # Apply patterns in order, left-to-right; deterministic placeholder naming.
    idx = 0
    for pat in patterns:
        while True:
            m = pat.search(out)
            if not m:
                break
            token = f"__NT{idx}__"
            idx += 1
            table[token] = m.group(0)
            out = out[: m.start()] + token + out[m.end() :]

    return Protected(text=out, table=table)


def unprotect_spans(s: str, table: dict[str, str]) -> str:
    out = s
    # Deterministic restoration in placeholder creation order.
    for token, original in table.items():
        out = out.replace(token, original)
    return out


_LINE_PREFIX_RE = re.compile(r"^(\s*(?:[#>*-]|\d+\.|\+|\*|\|)\s*)")


def iter_translatable_lines(block_text: str) -> Iterable[tuple[str, str]]:
    """Yield (prefix, content) for each line, preserving markdown prefixes."""
    for ln in block_text.splitlines(keepends=False):
        m = _LINE_PREFIX_RE.match(ln)
        if m:
            prefix = m.group(1)
            content = ln[len(prefix) :]
            yield prefix, content
        else:
            yield "", ln
```

```python
# path: src/llmstxt_translate/nllb.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _resolve_device(device: str) -> tuple[int | str, str]:
    """Return (pipeline_device, torch_device_str).

    - transformers pipeline uses: device=-1 for CPU, device>=0 for CUDA
    """
    if device == "auto":
        try:
            import torch

            if torch.cuda.is_available():
                return 0, "cuda:0"
        except Exception:
            pass
        return -1, "cpu"

    if device == "cpu":
        return -1, "cpu"

    if device.startswith("cuda"):
        # cuda or cuda:0
        parts = device.split(":", 1)
        idx = int(parts[1]) if len(parts) == 2 else 0
        return idx, f"cuda:{idx}"

    if device == "mps":
        # transformers pipeline doesn't accept mps index the same way; fall back to AutoModel path if needed.
        return -1, "mps"

    return -1, "cpu"


def _resolve_dtype(dtype: str, torch_device: str) -> Any:
    if dtype == "auto":
        try:
            import torch

            if torch_device.startswith("cuda"):
                return torch.float16
            return torch.float32
        except Exception:
            return None

    try:
        import torch

        return {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }[dtype]
    except Exception:
        return None


@dataclass
class NllbTranslator:
    model_id: str
    src_lang: str
    tgt_lang: str
    device: str = "auto"
    dtype: str = "auto"
    quantization: str = "none"  # none|bnb8bit
    generate_kwargs: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.generate_kwargs = dict(self.generate_kwargs or {})

        # Lazy init for faster CLI startup when listing files, etc.
        self._pipe = None

    def _init(self) -> None:
        if self._pipe is not None:
            return

        pipe_device, torch_device = _resolve_device(self.device)
        dtype = _resolve_dtype(self.dtype, torch_device)

        if self.quantization == "bnb8bit":
            # Optional path for GPU environments.
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, BitsAndBytesConfig, pipeline

            bnb_config = BitsAndBytesConfig(load_in_8bit=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id, quantization_config=bnb_config)
            tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self._pipe = pipeline(
                task="translation",
                model=model,
                tokenizer=tokenizer,
                src_lang=self.src_lang,
                tgt_lang=self.tgt_lang,
                device=pipe_device,
                dtype=dtype,
            )
            return

        from transformers import pipeline

        self._pipe = pipeline(
            task="translation",
            model=self.model_id,
            src_lang=self.src_lang,
            tgt_lang=self.tgt_lang,
            device=pipe_device,
            dtype=dtype,
        )

    def translate_batch(self, texts: list[str], *, batch_size: int) -> list[str]:
        self._init()
        assert self._pipe is not None

        out = self._pipe(
            texts,
            batch_size=batch_size,
            generate_kwargs=self.generate_kwargs,
        )

        # pipeline returns list[dict] with "translation_text"
        return [d["translation_text"] for d in out]
```

```python
# path: src/llmstxt_translate/runner.py
from __future__ import annotations

import glob
import re
from dataclasses import dataclass
from pathlib import Path

from llmstxt_translate.cache import TranslationCache
from llmstxt_translate.config import AppConfig
from llmstxt_translate.nllb import NllbTranslator
from llmstxt_translate.segment import (
    iter_translatable_lines,
    protect_spans,
    split_markdown_blocks,
    unprotect_spans,
)


@dataclass(frozen=True)
class RunResult:
    translated_files: int
    skipped_files: int
    segments_total: int
    segments_cache_hit: int


def _seems_english(text: str) -> bool:
    # Lightweight heuristic: if the text has a lot of CJK, treat as non-English.
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff")
    latin = sum(1 for ch in text if "A" <= ch <= "Z" or "a" <= ch <= "z")
    return latin >= max(50, cjk * 3)


def _render_output_path(src_path: Path, *, template: str, tgt_lang: str) -> Path:
    return src_path.with_name(
        template.format(
            src_path=str(src_path),
            src_stem=src_path.stem,
            src_suffix=src_path.suffix,
            tgt_lang=tgt_lang,
        )
    )


def translate_artifacts(*, root: Path, cfg: AppConfig) -> RunResult:
    cache = TranslationCache(root / cfg.io.cache_dir)

    translated_files = 0
    skipped_files = 0
    segments_total = 0
    segments_cache_hit = 0

    # Deterministic file ordering
    files: list[Path] = []
    for g in cfg.io.artifacts_glob:
        files.extend(Path(p) for p in glob.glob(str(root / g), recursive=True))
    files = sorted({p.resolve() for p in files})

    for src_path in files:
        src_text = src_path.read_text(encoding="utf-8", errors="replace")

        if cfg.io.only_if_non_english and _seems_english(src_text):
            skipped_files += 1
            continue

        for tgt_lang in cfg.translator.target_langs:
            out_path = _render_output_path(src_path, template=cfg.io.output_template, tgt_lang=tgt_lang)

            if cfg.io.skip_if_exists and out_path.exists():
                skipped_files += 1
                continue

            translator = NllbTranslator(
                model_id=cfg.translator.model_id,
                src_lang=cfg.translator.source_lang,
                tgt_lang=tgt_lang,
                device=cfg.translator.device,
                dtype=cfg.translator.dtype,
                quantization=cfg.translator.quantization,
                generate_kwargs={
                    "max_new_tokens": cfg.translator.generate.max_new_tokens,
                    "num_beams": cfg.translator.generate.num_beams,
                    "do_sample": cfg.translator.generate.do_sample,
                },
            )

            blocks = split_markdown_blocks(src_text)
            out_chunks: list[str] = []

            # Collect translatable segments first for batching.
            segments: list[str] = []
            meta: list[tuple[int, list[tuple[str, dict[str, str]]]]] = []
            # meta: per-block index -> list of (prefix, protect_table)

            for bi, b in enumerate(blocks):
                if b.kind == "code" and cfg.markdown.preserve_code_fences:
                    out_chunks.append(b.text)
                    continue

                # Translate text blocks line-by-line to preserve markdown structure.
                per_block_meta: list[tuple[str, dict[str, str]]] = []
                for prefix, content in iter_translatable_lines(b.text):
                    protected = protect_spans(
                        content,
                        preserve_inline_code=cfg.markdown.preserve_inline_code,
                        preserve_markdown_links=cfg.markdown.preserve_markdown_links,
                        preserve_urls=cfg.markdown.preserve_urls,
                        extra_regex=cfg.markdown.do_not_translate_regex,
                    )
                    segments.append(protected.text)
                    per_block_meta.append((prefix, protected.table))
                meta.append((bi, per_block_meta))

            # Translate with caching
            translated_segments: list[str] = []
            i = 0
            while i < len(segments):
                batch = segments[i : i + cfg.runtime.batch_size]

                batch_out: list[str] = [""] * len(batch)
                missing_texts: list[str] = []
                missing_idx: list[int] = []

                for j, s in enumerate(batch):
                    segments_total += 1
                    key = cache.make_key(cfg.translator.model_id, cfg.translator.source_lang, tgt_lang, s)
                    hit = cache.get(key)
                    if hit is not None:
                        segments_cache_hit += 1
                        batch_out[j] = hit
                    else:
                        missing_texts.append(s)
                        missing_idx.append(j)

                if missing_texts:
                    new = translator.translate_batch(missing_texts, batch_size=cfg.runtime.batch_size)
                    for k, translated in enumerate(new):
                        j = missing_idx[k]
                        batch_out[j] = translated
                        key = cache.make_key(cfg.translator.model_id, cfg.translator.source_lang, tgt_lang, batch[j])
                        cache.put(key, translated)

                translated_segments.extend(batch_out)
                i += cfg.runtime.batch_size

            # Rebuild output preserving prefixes and protected spans.
            seg_cursor = 0
            rebuilt: dict[int, str] = {}
            for bi, per_block_meta in meta:
                lines: list[str] = []
                for prefix, table in per_block_meta:
                    t = translated_segments[seg_cursor]
                    seg_cursor += 1
                    t = unprotect_spans(t, table)
                    lines.append(prefix + t)
                rebuilt[bi] = "\n".join(lines) + "\n"

            # Stitch blocks back together.
            final_parts: list[str] = []
            for bi, b in enumerate(blocks):
                if b.kind == "code" and cfg.markdown.preserve_code_fences:
                    final_parts.append(b.text)
                else:
                    final_parts.append(rebuilt.get(bi, b.text))

            out_path.write_text("".join(final_parts), encoding="utf-8")
            translated_files += 1

    return RunResult(
        translated_files=translated_files,
        skipped_files=skipped_files,
        segments_total=segments_total,
        segments_cache_hit=segments_cache_hit,
    )
```

