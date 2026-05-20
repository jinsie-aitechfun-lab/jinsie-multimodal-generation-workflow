def build_multi_character_profile(runner, ctx, outputs):
    """
    Minimal wrapper to call the LLM character profile builder.
    Ensures compatibility with current runner and outputs structure.
    """
    from app.services.character_visual_profile_llm import build_llm_character_visual_profiles
    if ctx is None:
        ctx = {}
    if "storyboard" not in outputs:
        outputs["storyboard"] = {"scenes": []}
    return build_llm_character_visual_profiles(runner, ctx, outputs)