"""
Emotion categories and lists for journal entries.
"""

EMOTIONS = {
    "Positive": [
        "Happy",
        "Joyful",
        "Excited",
        "Thrilled",
        "Cheerful",
        "Content",
        "Satisfied",
        "Peaceful",
        "Calm",
        "Relaxed",
        "Loving",
        "Grateful",
        "Optimistic",
        "Hopeful",
        "Inspired",
        "Motivated",
        "Confident",
        "Proud",
        "Amused",
        "Playful",
        "Energetic",
        "Vibrant",
        "Refreshed",
        "Blissful",
        "Upbeat",
        "Radiant",
        "Delighted",
        "Jubilant",
        "Triumphant",
        "Enthusiastic",
        "Passionate",
        "Friendly",
        "Sociable",
        "Connected",
        "Supported"
    ],
    "Negative": [
        "Sad",
        "Depressed",
        "Anxious",
        "Worried",
        "Nervous",
        "Stressed",
        "Frustrated",
        "Angry",
        "Irritated",
        "Disgusted",
        "Ashamed",
        "Guilty",
        "Lonely",
        "Isolated",
        "Rejected",
        "Hurt",
        "Confused",
        "Overwhelmed",
        "Defeated",
        "Helpless",
        "Hopeless",
        "Insecure",
        "Jealous",
        "Envious",
        "Resentful",
        "Bitter",
        "Tired",
        "Exhausted",
        "Drained",
        "Disappointed",
        "Apprehensive",
        "Dreadful",
        "Panicked",
        "Terrified"
    ],
    "Neutral": [
        "Indifferent",
        "Apathetic",
        "Curious",
        "Interested",
        "Focused",
        "Thoughtful",
        "Contemplative",
        "Reflective",
        "Aware",
        "Present",
        "Surprised",
        "Amazed",
        "Nostalgic",
        "Sentimental",
        "Awkward",
        "Embarrassed",
        "Vulnerable",
        "Determined",
        "Driven",
        "Empowered",
        "Cautious",
        "Suspicious"
    ]
}

def get_all_emotions():
    """Get all emotions as a flat list."""
    all_emotions = []
    for category, emotions in EMOTIONS.items():
        all_emotions.extend(emotions)
    return sorted(all_emotions)

def get_emotions_by_category():
    """Get emotions organized by category."""
    return EMOTIONS