def adjust_scene_duration(story_text, target_seconds=120):
    """
    Minimal fallback duration control.
    Assigns target_seconds to each scene.
    """
    return [{"scene_id": scene.get("scene_id", "scene_001"), "duration_sec": target_seconds}
            for scene in [{"scene_id": "scene_001"}]]