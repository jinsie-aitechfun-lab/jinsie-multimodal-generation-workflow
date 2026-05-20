def select_image_candidates(storyboard_scenes):
    from app.services.image_candidate_selector import select_best_candidate
    results = []
    for scene in storyboard_scenes:
        candidate_asset_refs = [{"file_name": "placeholder.png", "path": "assets/mock/image/placeholder.png"}]
        scene_images = select_best_candidate(
            candidate_asset_refs=candidate_asset_refs,
            prompt=scene.get("narration", "placeholder prompt"),
            characters=[]
        )
        results.append(scene_images)
    return results