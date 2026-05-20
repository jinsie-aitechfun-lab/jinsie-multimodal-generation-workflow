def build_multi_character_profile(runner, ctx, outputs):
    from app.services.character_visual_profile_llm import build_llm_character_visual_profiles
    # 调用最新函数签名
    return build_llm_character_visual_profiles(runner, ctx, outputs)