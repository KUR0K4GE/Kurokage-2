"""Defines the consistent hacker avatar character used across all generated images.

The seed passed to Pollinations.ai is kept fixed per character so that the model
produces a visually coherent avatar across the 30-day carousel series.
"""

# Core visual identity — do not change between slides; consistency is the goal.
_CHARACTER_CORE = (
    "stylized 3D avatar of an anonymous hacker wearing a black balaclava, "
    "cyberpunk aesthetic, neon cyan and electric blue accent lighting, "
    "very dark near-black background, clean digital illustration, "
    "cinematic composition, high detail render, professional quality, "
    "no text, no watermark, no logo, no face visible"
)

# Tags that degrade quality or break character consistency
_NEGATIVE_TAGS = (
    "face visible, realistic photo, blurry, low quality, watermark, text overlay, "
    "logo, cartoon, anime, deformed, ugly, nsfw, extra limbs, bad anatomy"
)

# Visual context hints per slide position — help the model vary the scene
# without changing the character identity.
_SLIDE_CONTEXTS: dict[int, str] = {
    1: "dramatic hero shot, arms crossed, forward facing, dark server room backdrop",
    2: "looking at holographic data streams, side profile, glowing screens",
    3: "typing on glowing keyboard, hands visible, command terminal background",
    4: "pointing at viewer, confident pose, matrix code rain in background",
    5: "holding a smartphone with neon glow, code reflection on visor",
}

_DEFAULT_CONTEXT = "neutral pose, dark environment, subtle neon glow from below"


def build_slide_prompt(slide_text: str, slide_index: int = 1) -> str:
    """Return a Pollinations.ai prompt for a given slide.

    The slide text is condensed to extract visual intent without overloading the
    prompt length (URL limit consideration). The character core always leads.
    """
    context = _SLIDE_CONTEXTS.get(slide_index, _DEFAULT_CONTEXT)
    # Use first 80 chars of slide text as thematic context clue
    thematic = slide_text[:80].replace("\n", " ").strip()
    return f"{_CHARACTER_CORE}, {context}, theme: {thematic}"


def get_negative_prompt() -> str:
    return _NEGATIVE_TAGS
