#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)


def find_ffmpeg(explicit: str | None = None) -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("FFMPEG_EXE"):
        candidates.append(os.environ["FFMPEG_EXE"])
    on_path = shutil.which("ffmpeg")
    if on_path:
        candidates.append(on_path)
    try:
        import imageio_ffmpeg

        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
        if candidate and shutil.which(candidate):
            return candidate
    raise RuntimeError("ffmpeg not found. Install with: python -m pip install imageio-ffmpeg")


def ffprobe_path(ffmpeg: str) -> str | None:
    path = Path(ffmpeg)
    sibling = path.with_name(path.name.replace("ffmpeg", "ffprobe"))
    if sibling.exists():
        return str(sibling)
    found = shutil.which("ffprobe")
    return found


def media_duration(ffmpeg: str, path: Path) -> float:
    ffprobe = ffprobe_path(ffmpeg)
    if ffprobe:
        result = run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            timeout=60,
        )
        if result.returncode == 0:
            try:
                return float(result.stdout.strip())
            except ValueError:
                pass
    result = run([ffmpeg, "-i", str(path), "-f", "null", "-"], timeout=120)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"could not read duration: {path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_script(path: Path | None) -> dict[str, object]:
    if not path:
        return {"title": "短视频", "subtitles": [], "tts": ""}
    text = path.read_text(encoding="utf-8")
    title = ""
    subtitles: list[str] = []
    title_options: list[str] = []
    tts = ""
    cover = ""

    title_match = re.search(r"^1\.\s*(.+)$", text, flags=re.M)
    if title_match:
        title = clean(title_match.group(1))
    title_block = re.search(r"^##\s*标题备选\s*\n(?P<body>.*?)(?=^##\s+|\Z)", text, flags=re.M | re.S)
    if title_block:
        for line in title_block.group("body").splitlines():
            match = re.match(r"\s*\d+[.、]\s*(.+)$", line)
            if match:
                title_options.append(clean(match.group(1)))
    cover_match = re.search(r"^##\s*封面字\s*\n(?P<body>.*?)(?=^##\s+|\Z)", text, flags=re.M | re.S)
    if cover_match:
        cover = clean(cover_match.group("body"))
    tts_match = re.search(r"^##\s*TTS 文本\s*\n(?P<body>.*?)(?=^##\s+|\Z)", text, flags=re.M | re.S)
    if tts_match:
        tts = clean(tts_match.group("body"))
    sub_match = re.search(r"^##\s*字幕稿\s*\n(?P<body>.*?)(?=^##\s+|\Z)", text, flags=re.M | re.S)
    if sub_match:
        for line in sub_match.group("body").splitlines():
            match = re.match(r"\s*\d+[.、]\s*(.+)$", line)
            if match:
                subtitles.append(clean(match.group(1)))
    return {"title": title or cover or "短视频", "cover": cover or title, "subtitles": subtitles, "tts": tts, "title_options": title_options}


def collect_images(images_dir: Path | None, explicit: list[str]) -> list[Path]:
    images: list[Path] = []
    for item in explicit:
        p = Path(item)
        if p.exists() and p.suffix.lower() in IMAGE_EXTS:
            images.append(p)
    if images_dir and images_dir.exists():
        for p in sorted(images_dir.iterdir()):
            if p.suffix.lower() in IMAGE_EXTS and p not in images:
                images.append(p)
    return images[:12]


def wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    words = list(text)
    lines: list[str] = []
    current = ""
    for ch in words:
        candidate = current + ch
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def render_text_card(path: Path, title: str, subtitle: str, tag: str, accent: tuple[int, int, int]) -> None:
    from PIL import Image, ImageDraw, ImageFont

    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), (14, 18, 24))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        ratio = y / h
        color = (
            int(14 + accent[0] * 0.18 * ratio),
            int(18 + accent[1] * 0.18 * ratio),
            int(24 + accent[2] * 0.18 * ratio),
        )
        draw.line((0, y, w, y), fill=color)
    font_path = "C:/Windows/Fonts/msyh.ttc"
    title_font = ImageFont.truetype(font_path, 78)
    sub_font = ImageFont.truetype(font_path, 45)
    tag_font = ImageFont.truetype(font_path, 34)
    small_font = ImageFont.truetype(font_path, 30)

    draw.rounded_rectangle((72, 120, 380, 190), radius=18, fill=accent)
    draw.text((96, 136), tag, font=tag_font, fill=(255, 255, 255))
    draw.rectangle((72, 300, 92, 900), fill=accent)

    y = 310
    for line in wrap_text(draw, title, title_font, 820)[:5]:
        draw.text((124, y), line, font=title_font, fill=(255, 255, 255))
        y += 100
    y += 34
    for line in wrap_text(draw, subtitle, sub_font, 850)[:7]:
        draw.text((124, y), line, font=sub_font, fill=(220, 232, 242))
        y += 66

    draw.rounded_rectangle((72, 1550, 1008, 1690), radius=28, outline=(95, 110, 130), width=2)
    draw.text((112, 1586), "工业视觉 / 异常检测 / 可落地论文", font=small_font, fill=(190, 205, 220))
    draw.text((112, 1632), "视频号 · 抖音短视频版", font=small_font, fill=(190, 205, 220))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=95)


def build_auto_cards(tmp: Path, script_data: dict[str, object]) -> list[Path]:
    title = clean(str(script_data.get("cover") or script_data.get("title") or "短视频"))
    subtitles = [clean(str(s)) for s in script_data.get("subtitles", []) if clean(str(s))]
    cards = [
        ("开场", title, subtitles[0] if subtitles else "先把问题讲清楚，再看方法值不值得复现。", (40, 120, 255)),
        ("痛点", "为什么工业缺陷检测难？", "缺陷样本少、换光照不稳、误报漏报都会影响产线复核。", (235, 90, 70)),
        ("方法", "这篇论文看什么？", "重点看正常外观怎么建模、异常响应怎么生成、热力图是否可用。", (48, 170, 120)),
        ("实验", "不要只看平均分", "还要看 MVTec、VAND 等数据集上的跨工况表现和失败案例。", (160, 110, 240)),
        ("结论", "适合放进方案池对比", "真正落地前，要复核误报、漏报、热力图和部署成本。", (238, 160, 54)),
    ]
    out: list[Path] = []
    for idx, (tag, card_title, subtitle, accent) in enumerate(cards, 1):
        path = tmp / f"auto_card_{idx:02d}.jpg"
        render_text_card(path, card_title, subtitle, tag, accent)
        out.append(path)
    return out


def escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def ass_time(seconds: float) -> str:
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def write_ass(path: Path, subtitles: list[str], duration: float, title: str) -> None:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Subtitle,Microsoft YaHei,58,&H00FFFFFF,&H000000FF,&H00111111,&HAA000000,-1,0,0,0,100,100,0,0,1,5,2,2,80,80,210,1",
        "Style: Title,Microsoft YaHei,72,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,6,2,5,80,80,80,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 1,{ass_time(0)},{ass_time(min(3.0, duration))},Title,,0,0,0,,{escape_ass(title)}",
    ]
    if subtitles:
        slot = max(1.6, duration / len(subtitles))
        for idx, sub in enumerate(subtitles):
            start = idx * slot
            end = min(duration, start + slot + 0.15)
            if start >= duration:
                break
            lines.append(f"Dialogue: 2,{ass_time(start)},{ass_time(end)},Subtitle,,0,0,0,,{escape_ass(sub)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_srt(path: Path, subtitles: list[str], duration: float) -> None:
    def ts(seconds: float) -> str:
        ms = int(round((seconds - int(seconds)) * 1000))
        whole = int(seconds)
        h = whole // 3600
        m = (whole % 3600) // 60
        s = whole % 60
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    slot = max(1.6, duration / max(len(subtitles), 1))
    chunks = []
    for idx, sub in enumerate(subtitles, 1):
        start = (idx - 1) * slot
        if start >= duration:
            break
        end = min(duration, start + slot + 0.15)
        if end <= start:
            break
        chunks.append(f"{idx}\n{ts(start)} --> {ts(end)}\n{sub}\n")
    path.write_text("\n".join(chunks), encoding="utf-8")


def create_slideshow(ffmpeg: str, images: list[Path], output: Path, duration: float, size: str, fps: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not images:
        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x101418:s={size}:d={duration}",
            "-vf",
            f"fps={fps}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
        result = run(cmd, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        return

    per_image = max(3.0, duration / len(images))
    segment_paths: list[Path] = []
    for idx, image in enumerate(images):
        segment = output.with_name(f"{output.stem}_segment_{idx:03d}.mp4")
        segment_paths.append(segment)
        vf = (
            f"scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},setsar=1,fps={fps},format=yuv420p"
        )
        result = run(
            [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-t",
                f"{per_image:.3f}",
                "-i",
                str(image),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "veryfast",
                str(segment),
            ],
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
    concat = output.with_suffix(".concat.txt")
    concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in segment_paths) + "\n", encoding="utf-8")
    result = run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-t",
            f"{duration:.3f}",
            "-c",
            "copy",
            str(output),
        ],
        timeout=900,
    )
    for path in [concat, *segment_paths]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def ass_filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value


def compose_video(
    ffmpeg: str,
    base_video: Path,
    voice: Path | None,
    source_video: Path | None,
    music: Path | None,
    ass: Path,
    output: Path,
    duration: float,
    size: str,
    fps: int,
) -> None:
    inputs = ["-i", str(source_video or base_video)]
    audio_index = None
    music_index = None
    idx = 1
    if source_video is None and voice:
        inputs += ["-i", str(voice)]
        audio_index = idx
        idx += 1
    elif source_video is not None:
        audio_index = 0
    if music:
        inputs += ["-i", str(music)]
        music_index = idx

    vf = (
        f"scale={size}:force_original_aspect_ratio=increase,"
        f"crop={size},setsar=1,fps={fps},"
        f"ass='{ass_filter_path(ass)}'"
    )
    cmd = [ffmpeg, "-y", *inputs, "-t", f"{duration:.3f}", "-vf", vf]
    if audio_index is not None and music_index is not None:
        cmd += [
            "-filter_complex",
            f"[{audio_index}:a]volume=1.0[a0];[{music_index}:a]volume=0.12,aloop=loop=-1:size=2e+09[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
        ]
    elif audio_index is not None:
        cmd += ["-map", "0:v", "-map", f"{audio_index}:a"]
    else:
        cmd += ["-an"]
    cmd += [
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output),
    ]
    result = run(cmd, timeout=1200)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice")
    parser.add_argument("--video")
    parser.add_argument("--script")
    parser.add_argument("--subtitles", nargs="*")
    parser.add_argument("--images-dir")
    parser.add_argument("--image", action="append", default=[])
    parser.add_argument("--music")
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--size", default="1080:1920")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--no-auto-cards", action="store_true")
    args = parser.parse_args()

    ffmpeg = find_ffmpeg(args.ffmpeg)
    voice = Path(args.voice) if args.voice else None
    video = Path(args.video) if args.video else None
    script = Path(args.script) if args.script else None
    music = Path(args.music) if args.music else None
    output = Path(args.output)
    if not voice and not video:
        raise RuntimeError("provide --voice or --video")
    if voice and not voice.exists():
        raise RuntimeError(f"voice not found: {voice}")
    if video and not video.exists():
        raise RuntimeError(f"video not found: {video}")

    script_data = parse_script(script)
    title = clean(str(script_data.get("cover") or script_data.get("title") or "短视频"))
    subtitles = [clean(s) for s in (args.subtitles or []) if clean(s)]
    if not subtitles:
        subtitles = [str(s) for s in script_data.get("subtitles", []) if clean(str(s))]
    duration_source = video or voice
    assert duration_source is not None
    duration = args.duration or media_duration(ffmpeg, duration_source)
    duration = min(duration, 90.0)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="short_video_") as tmpdir:
        tmp = Path(tmpdir)
        images = collect_images(Path(args.images_dir) if args.images_dir else None, args.image)
        if not args.no_auto_cards:
            cards = build_auto_cards(tmp, script_data)
            if images:
                mixed: list[Path] = []
                for idx, card in enumerate(cards):
                    mixed.append(card)
                    if idx < len(images):
                        mixed.append(images[idx])
                images = mixed + images[len(cards):]
            else:
                images = cards
        ass = tmp / "subtitles.ass"
        write_ass(ass, subtitles, duration, title)
        write_srt(output.with_suffix(".srt"), subtitles, duration)
        base = tmp / "base.mp4"
        if video is None:
            create_slideshow(ffmpeg, images, base, duration, args.size, args.fps)
            source_video = None
        else:
            source_video = video
        compose_video(ffmpeg, base, voice, source_video, music, ass, output, duration, args.size, args.fps)
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
