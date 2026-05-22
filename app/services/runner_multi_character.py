def build_multi_character_profile(runner, ctx, outputs):
    from app.services.character_visual_profile_llm import build_llm_character_visual_profiles
    if ctx is None:
        ctx = {}
    if "storyboard" not in outputs:
        outputs["storyboard"] = {"scenes": []}
    return build_llm_character_visual_profiles(runner, ctx, outputs)