def adjust_scene_duration(story_text, target_seconds=120):
    # 所有场景使用 target_seconds 作为占位
    return [{"scene_id": "scene_001", "duration_sec": target_seconds}]