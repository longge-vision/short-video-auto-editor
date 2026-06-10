---
name: short-video-auto-editor
description: Automatically edit vertical short videos for 视频号, Douyin, TikTok-style clips from narration audio/video, WeChat article images, subtitles, title card text, optional background music, and short-video scripts. Use when the user asks to 自动剪辑视频, make a short video from口播, generate a 视频号/抖音成片, add subtitles, convert to 9:16, combine voiceover with paper/article figures, or create an MP4 from a short-video script.
---

# Short Video Auto Editor

Use this skill to create a vertical short video from prepared assets.

## Inputs

Accept any practical combination:

- Narration audio: `.mp3`, `.wav`, `.m4a`, `.aac`.
- Talking-head video: `.mp4`, `.mov`, `.mkv`.
- Short-video script markdown from `wechat-article-short-video`.
- Subtitle text or SRT.
- Images from a paper/article folder.
- Optional background music.

## Main Script

Run:

```powershell
python C:\Users\User\.codex\skills\short-video-auto-editor\scripts\make_short_video.py `
  --voice "path\to\voice.wav" `
  --script "path\to\article.short-video.md" `
  --images-dir "path\to\images" `
  --output "path\to\out.mp4"
```

For a recorded talking-head video:

```powershell
python C:\Users\User\.codex\skills\short-video-auto-editor\scripts\make_short_video.py `
  --video "path\to\recording.mp4" `
  --script "path\to\article.short-video.md" `
  --images-dir "path\to\images" `
  --output "path\to\out.mp4"
```

For paper/article images as the main slideshow with the talking head in a circular
bottom-right picture-in-picture:

```powershell
python C:\Users\User\.codex\skills\short-video-auto-editor\scripts\make_short_video.py `
  --video "path\to\recording.mp4" `
  --script "path\to\article.short-video.md" `
  --images-dir "path\to\paper-images" `
  --output "path\to\out.mp4" `
  --pip-video `
  --pip-size 292
```

When only one large paper figure is available, the script creates overview and
cropped focus frames automatically so the video does not stay visually static.

## Output

- 9:16 MP4, default `1080x1920`.
- Burned Chinese subtitles.
- Title card at the beginning.
- Image slideshow / B-roll from article figures.
- Optional circular talking-head PiP over the paper/article slideshow.
- Optional background music mixed under narration.
- `.srt` subtitle file beside the output.

## Editing Rules

- Keep opening hook within first 3 seconds.
- Use large high-contrast subtitles, two lines max.
- Use paper figures or article images as B-roll; avoid static black screens.
- Keep output under 90 seconds unless the user asks otherwise.
- For technical videos, show method figure / heatmap / table while explaining method and result.
- Do not invent claims beyond the script/article.

## Dependencies

The script uses FFmpeg. It first tries:

1. `--ffmpeg` argument.
2. `FFMPEG_EXE` environment variable.
3. `ffmpeg` on PATH.
4. Python package `imageio-ffmpeg`.

If missing:

```powershell
python -m pip install imageio-ffmpeg
```

## Quality Gate

After generation:

- Verify output file exists and has nonzero duration.
- Verify resolution is vertical 9:16.
- Verify subtitles are visible and not clipped.
- Verify audio is present.
- If using article images, verify at least one image appears.
