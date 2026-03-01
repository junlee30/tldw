"""Pydantic models and prompt templates for Gemini video analysis."""

from pydantic import BaseModel, Field

from config import SCENES_PER_MINUTE, MIN_SCENES, MAX_SCENES


class VideoSegment(BaseModel):
    """A scene in the video's narrative."""
    timestamp: float = Field(description="Timestamp in seconds from the start of the video")
    timestamp_display: str = Field(description="Human-readable timestamp like '1:23' or '1:01:05'")
    headline: str = Field(description="Short punchy headline for this moment (max 8 words)")
    narration: str = Field(
        description="3-5 sentence story-style narration of what happens in this scene"
    )
    visual_description: str = Field(default="", description="Brief description of what's visually happening on screen")
    transition: str = Field(
        default="",
        description="Narrative connector to the next scene (e.g., 'But then...', 'Meanwhile...')"
    )


class VideoAnalysisResult(BaseModel):
    """Complete analysis of a video."""
    title_summary: str = Field(description="One-line summary of the entire video (max 15 words)")
    prologue: str = Field(
        description="3-4 sentence opening that sets the stage for the story"
    )
    epilogue: str = Field(
        default="",
        description="2-3 sentence takeaway or closing thought"
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 language code of the video's primary spoken language"
    )
    audio_only: bool = Field(
        default=False,
        description="Whether this analysis was produced from audio only"
    )
    segments: list[VideoSegment] = Field(
        description="List of scenes from the video, covering the full timeline"
    )
    thumbnail_timestamp: float = Field(
        description="Timestamp in seconds for the best thumbnail frame "
        "(most visually interesting moment)"
    )


ANALYSIS_PROMPT = """\
You are a visual storyteller narrating a comic book / webtoon adaptation of this video. \
Your goal is to **retell the entire video** so readers experience the full content without watching.

The video is {duration_display} long ({duration_seconds} seconds total). \
Produce {min_scenes}-{max_scenes} scenes that cover the full timeline from beginning to end.

IMPORTANT: Respond in the SAME LANGUAGE as the video. If the video is in Korean, write \
everything in Korean. If it's in English, write in English. Match the video's language exactly.

I repeat: ALL text output (prologue, headlines, narrations, epilogue, transitions) must be \
in the SAME LANGUAGE as the video.

Do NOT skip sections — cover the full timeline from beginning to end. Every major topic, \
argument, demonstration, or narrative development should have its own scene. If a section \
of the video introduces a new idea or shifts focus, give it a dedicated scene.

## CRITICAL: Timestamp accuracy

A still frame will be extracted from the video at the EXACT timestamp you provide and \
displayed as the image for that scene. If the timestamp is wrong, the image will not match \
your headline and narration — this completely breaks the experience.

For each scene, follow this process:
1. **Find the moment visually.** Scrub to where the topic is actually being discussed and \
a relevant graphic, chart, slide, or key visual is on screen.
2. **Read what is on screen** at that moment — text overlays, headlines, charts, presenter \
actions. Your visual_description must match what is literally visible at that timestamp.
3. **Set the timestamp to that exact frame.** Do NOT estimate or round to convenient numbers. \
The timestamp must point to a frame where the visual matches your description.
4. **Double-check:** If your headline says "NVIDIA earnings" but the screen shows an \
unrelated chart at that timestamp, you have the wrong timestamp. Fix it.

Skip pre-roll ads, sponsor segments, and outros — only pick timestamps from actual content.

## Scene content

For each scene:
1. Choose timestamps that are SPREAD across the entire video duration — don't cluster them
2. Pick timestamps where a relevant visual (chart, graphic, slide, demo, key action) is on \
screen — not just the presenter talking
3. Write a short, punchy headline (max 8 words) that captures the essence of this scene
4. Write a 3-5 sentence narration telling what happens — like you're narrating a story, not \
summarizing a report. Use vivid, engaging language.
5. Describe what is LITERALLY visible on screen at that exact timestamp (on-screen text, \
graphics, presenter actions). This description must match the actual frame.
6. Write a short transition phrase that connects to the next scene (e.g., "But then...", \
"What happened next changed everything...", "Meanwhile..."). Leave empty for the last scene.

Structure the scenes as a narrative arc:
- Opening scenes: SETUP — introduce the subject, setting, and stakes
- Middle scenes: DEVELOPMENT — build tension, show progression, reveal complications
- Peak scene: CLIMAX — the most dramatic or important moment
- Final scenes: RESOLUTION — outcome, aftermath, or conclusion

Also provide:
- A one-line summary of the entire video (max 15 words)
- A PROLOGUE: 3-4 sentences setting the stage before the first scene (like a book's opening paragraph)
- An EPILOGUE: 2-3 sentences wrapping up the story with a takeaway or closing thought
- The ISO 639-1 language code of the video's primary spoken language (e.g., "en", "ko", "ja")
- The single most visually interesting timestamp for the thumbnail

IMPORTANT RULES:
- Timestamps must be valid (between 0 and {duration_seconds})
- Space scenes roughly evenly across the video duration
- Each timestamp MUST point to a frame that visually matches the scene's topic
- Headlines should be engaging and specific, not generic
- Narrations should make the reader feel like they're watching the video unfold
- Produce {min_scenes}-{max_scenes} scenes total
"""


def compute_scene_count(duration_seconds: int) -> tuple[int, int]:
    """Compute (min_scenes, max_scenes) based on video duration.

    Returns a range for Gemini. max_scenes is the target count,
    min_scenes is ~80% of target (floored to MIN_SCENES).
    """
    duration_minutes = duration_seconds / 60
    target = round(duration_minutes * SCENES_PER_MINUTE)
    target = max(MIN_SCENES, min(MAX_SCENES, target))
    floor = max(MIN_SCENES, round(target * 0.8))
    return floor, target


AUDIO_ANALYSIS_PROMPT = """\
You are a storyteller narrating a summary adaptation of this audio recording. \
Your goal is to **retell the entire content** so readers experience the full discussion without listening.

The recording is {duration_display} long ({duration_seconds} seconds total). \
Produce {min_scenes}-{max_scenes} scenes that cover the full timeline from beginning to end.

IMPORTANT: Respond in the SAME LANGUAGE as the audio. If the audio is in Korean, write \
everything in Korean. If it's in English, write in English. Match the audio's language exactly.

I repeat: ALL text output (prologue, headlines, narrations, epilogue, transitions) must be \
in the SAME LANGUAGE as the audio.

Do NOT skip sections — cover the full timeline from beginning to end. Every major topic, \
argument, demonstration, or narrative development should have its own scene. If a section \
of the audio introduces a new idea or shifts focus, give it a dedicated scene.

## CRITICAL: Timestamp accuracy

For each scene, choose a timestamp that falls within the section being discussed. \
Timestamps should be spread evenly across the full recording duration.

Skip pre-roll ads, sponsor segments, and outros — only pick timestamps from actual content.

## Scene content

For each scene:
1. Choose timestamps that are SPREAD across the entire recording duration — don't cluster them
2. Pick timestamps at the start of each topic or discussion point
3. Write a short, punchy headline (max 8 words) that captures the essence of this scene
4. Write a 3-5 sentence narration telling what happens — like you're narrating a story, not \
summarizing a report. Use vivid, engaging language.
5. Write a short transition phrase that connects to the next scene (e.g., "But then...", \
"What happened next changed everything...", "Meanwhile..."). Leave empty for the last scene.

Structure the scenes as a narrative arc:
- Opening scenes: SETUP — introduce the subject, setting, and stakes
- Middle scenes: DEVELOPMENT — build tension, show progression, reveal complications
- Peak scene: CLIMAX — the most dramatic or important moment
- Final scenes: RESOLUTION — outcome, aftermath, or conclusion

Also provide:
- A one-line summary of the entire recording (max 15 words)
- A PROLOGUE: 3-4 sentences setting the stage before the first scene (like a book's opening paragraph)
- An EPILOGUE: 2-3 sentences wrapping up the story with a takeaway or closing thought
- The ISO 639-1 language code of the audio's primary spoken language (e.g., "en", "ko", "ja")
- The single most interesting timestamp for the thumbnail

IMPORTANT RULES:
- Timestamps must be valid (between 0 and {duration_seconds})
- Space scenes roughly evenly across the recording duration
- Headlines should be engaging and specific, not generic
- Narrations should make the reader feel like they're listening to the recording unfold
- Produce {min_scenes}-{max_scenes} scenes total
"""


def _format_duration(duration_seconds: int) -> str:
    """Format duration in seconds to a human-readable string."""
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def build_analysis_prompt(duration_seconds: int) -> str:
    """Build the analysis prompt with duration injected."""
    duration_display = _format_duration(duration_seconds)
    min_scenes, max_scenes = compute_scene_count(duration_seconds)

    return ANALYSIS_PROMPT.format(
        duration_seconds=duration_seconds,
        duration_display=duration_display,
        min_scenes=min_scenes,
        max_scenes=max_scenes,
    )


def build_audio_analysis_prompt(duration_seconds: int) -> str:
    """Build the audio-only analysis prompt with duration injected."""
    duration_display = _format_duration(duration_seconds)
    min_scenes, max_scenes = compute_scene_count(duration_seconds)

    return AUDIO_ANALYSIS_PROMPT.format(
        duration_seconds=duration_seconds,
        duration_display=duration_display,
        min_scenes=min_scenes,
        max_scenes=max_scenes,
    )
