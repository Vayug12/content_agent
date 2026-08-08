import os
import numpy as np
from moviepy import (
    VideoFileClip, AudioFileClip, ColorClip, TextClip,
    CompositeVideoClip, concatenate_videoclips
)
from moviepy.video.fx import CrossFadeIn
from utils.logger import log


def _resolve_font() -> str:
    """Find a usable bold TTF across platforms (Linux container, Windows, macOS).
    Returns the first path that exists, or "" to let Pillow fall back to default."""
    candidates = [
        # Linux (installed via Dockerfile: fonts-dejavu-core)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        # Windows
        r"C:\Windows\Fonts\arialbd.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


FONT_PATH = _resolve_font()


# ==================== KEN BURNS EFFECT ====================

def ken_burns_effect(clip, zoom_start=1.0, zoom_end=1.03):
    """Slow zoom in/out effect - professional documentary feel
    Uses moviepy's built-in resize for each frame"""
    w, h = clip.size
    duration = clip.duration

    def apply_zoom(get_frame, t):
        frame = get_frame(t)
        progress = t / duration if duration > 0 else 0
        zoom = zoom_start + (zoom_end - zoom_start) * progress

        # Use PIL for resize
        from PIL import Image
        img = Image.fromarray(frame.astype(np.uint8))
        new_w = int(w * zoom)
        new_h = int(h * zoom)
        img = img.resize((new_w, new_h), Image.BILINEAR)

        # Center crop back to original size
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        img = img.crop((left, top, left + w, top + h))

        return np.array(img, dtype=np.uint8)

    return clip.transform(apply_zoom)


# ==================== TEXT OVERLAY ====================

def extract_keywords(text: str, max_words: int = 3) -> str:
    """Extract 2-3 keywords from narration - subtle text overlay"""
    # Remove common words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                  'would', 'could', 'should', 'may', 'might', 'can', 'shall',
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                  'as', 'into', 'through', 'during', 'before', 'after', 'and',
                  'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
                  'neither', 'each', 'every', 'all', 'any', 'few', 'more',
                  'most', 'other', 'some', 'such', 'no', 'only', 'own', 'same',
                  'than', 'too', 'very', 'just', 'because', 'if', 'when', 'this',
                  'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
                  'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his',
                  'its', 'our', 'their', 'what', 'which', 'who', 'whom'}

    words = text.lower().split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    # Take first few meaningful words
    if len(keywords) > max_words:
        keywords = keywords[:max_words]

    return ' '.join(keywords) if keywords else text[:20]


def add_text_overlay(clip, text: str) -> CompositeVideoClip:
    """Add subtle text overlay at bottom - keywords only"""
    if not text:
        return clip

    # Extract keywords (2-3 words max)
    keywords = extract_keywords(text, max_words=3)

    # Text overlay is cosmetic — if it fails (e.g. missing font), return the
    # clip WITHOUT the overlay instead of dropping the whole scene.
    try:
        txt_kwargs = dict(
            text=keywords.upper(),
            font_size=28,
            color='white',
            stroke_color='black',
            stroke_width=2,
            method='caption',
            text_align='center',
            size=(clip.w - 100, None)  # Margin from edges
        )
        if FONT_PATH:
            txt_kwargs['font'] = FONT_PATH

        txt_clip = TextClip(**txt_kwargs)

        # Position at bottom with padding
        txt_clip = txt_clip.with_duration(clip.duration * 0.7)  # Show for 70% of clip
        txt_clip = txt_clip.with_start(clip.duration * 0.15)    # Start at 15%
        txt_clip = txt_clip.with_position(('center', clip.h - 150))

        # Composite over video
        return CompositeVideoClip([clip, txt_clip])
    except Exception as e:
        log("EDIT", f"Text overlay skipped ({str(e)}) - using clip without text")
        return clip


# ==================== PREPARE CLIP ====================

def prepare_clip(input_path: str, target_duration: float, apply_zoom: bool = True) -> VideoFileClip:
    """Prepare clip with resize, crop, and optional Ken Burns effect"""
    clip = VideoFileClip(input_path)
    clip = clip.subclipped(0, min(target_duration, clip.duration))
    clip = clip.without_audio()

    w, h = clip.size
    target_w, target_h = 1080, 1920

    if w / h < target_w / target_h:
        clip = clip.resized(height=target_h)
    else:
        clip = clip.resized(width=target_w)

    x_center = clip.w / 2
    y_center = clip.h / 2
    clip = clip.cropped(x_center=x_center, y_center=y_center,
                        width=target_w, height=target_h)

    # Apply Ken Burns effect (alternating zoom in/out)
    if apply_zoom:
        # Alternate between zoom in and zoom out for variety
        zoom_in = (clip.duration % 2 == 0)
        if zoom_in:
            clip = ken_burns_effect(clip, zoom_start=1.0, zoom_end=1.03)
        else:
            clip = ken_burns_effect(clip, zoom_start=1.03, zoom_end=1.0)

    return clip


def create_text_clip(duration: float) -> ColorClip:
    """Create black screen fallback"""
    return ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_duration(duration)


# ==================== PROCESS SCENE ====================

def process_scene(scene: dict, clip_data: dict, voice_path: str, out_dir: str) -> str:
    """Process single scene with Ken Burns + subtle text overlay"""
    num = scene["scene_number"]
    clip_path = clip_data.get("path", "")
    target_duration = scene["duration"]
    narration = scene.get("narration", "")
    temp_output = os.path.join(out_dir, f"scene_{num}.mp4")

    try:
        if clip_path and os.path.exists(clip_path):
            log("EDIT", f"Scene {num}: preparing clip with Ken Burns...")
            video_clip = prepare_clip(clip_path, target_duration, apply_zoom=True)
        else:
            log("EDIT", f"Scene {num}: black screen (no video)")
            video_clip = create_text_clip(target_duration)

        if voice_path and os.path.exists(voice_path):
            audio_clip = AudioFileClip(voice_path)
            if audio_clip.duration < target_duration:
                target_duration = audio_clip.duration
            video_clip = video_clip.subclipped(0, target_duration)
            video_clip = video_clip.with_audio(audio_clip)
            log("EDIT", f"Scene {num}: audio attached ({audio_clip.duration:.1f}s)")
        else:
            log("EDIT", f"Scene {num}: no audio file found")

        # Add subtle text overlay (keywords only)
        if narration and clip_path:
            video_clip = add_text_overlay(video_clip, narration)
            log("EDIT", f"Scene {num}: text overlay added")

        video_clip.write_videofile(
            temp_output,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None
        )
        video_clip.close()

        log("EDIT", f"Scene {num}: saved to temp file")
        return temp_output

    except Exception as e:
        log("EDIT", f"Scene {num}: error - {str(e)}")
        return ""


# ==================== EDIT VIDEO ====================

def edit_video(scenes: list, clips: list, voices: list, out_dir: str) -> str:
    """Main video editing with Ken Burns, crossfade, and text overlays"""
    log("EDIT", "Starting professional video assembly...")

    voice_map = {v["scene_number"]: v["path"] for v in voices}
    clip_map = {c["scene_number"]: c for c in clips}
    temp_files = []

    for scene in scenes:
        num = scene["scene_number"]
        clip_data = clip_map.get(num, {})
        voice_path = voice_map.get(num, "")

        temp_path = process_scene(scene, clip_data, voice_path, out_dir)
        if temp_path:
            temp_files.append(temp_path)

    if not temp_files:
        log("EDIT", "No clips to merge!")
        return ""

    final_output = os.path.join(out_dir, "final_video.mp4")
    log("EDIT", f"Concatenating {len(temp_files)} scenes with crossfade...")

    clips_to_merge = []
    for f in temp_files:
        clip = VideoFileClip(f)
        clips_to_merge.append(clip)

    # Crossfade transitions (0.5s overlap)
    CROSSFADE_DURATION = 0.5

    # Apply crossfade effect
    for i in range(len(clips_to_merge)):
        if i > 0:
            clips_to_merge[i] = clips_to_merge[i].with_effects([
                CrossFadeIn(CROSSFADE_DURATION)
            ])

    final = concatenate_videoclips(clips_to_merge, method="compose",
                                   padding=-CROSSFADE_DURATION)

    final.write_videofile(
        final_output,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )

    for clip in clips_to_merge:
        clip.close()

    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass

    log("EDIT", f"Video saved: {final_output}")
    return final_output
