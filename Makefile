api:
	uvicorn app.main:app --reload --port 8004

check:
	python -m py_compile \
		app/services/runner.py \
		app/services/runner_audio_render_support.py \
		app/services/runner_character_labels.py \
		app/services/runner_character_manifest.py \
		app/services/runner_image_asset_refs.py \
		app/services/runner_image_prompts_support.py \
		app/services/runner_image_review.py \
		app/services/runner_render_plan.py \
		app/services/runner_scene_blueprints.py \
		app/services/runner_scene_characters.py \
		app/services/runner_scene_render_fallback.py \
		app/services/runner_scene_render_storybook.py \
		app/services/runner_session.py \
		app/services/runner_story_support.py \
		app/services/runner_story_text.py \
		app/services/runner_storyboard.py \
		app/services/runner_video_prompts.py

story-provider:
	@echo "STORY_PROVIDER=$$STORY_PROVIDER"
	@echo "OPENAI_MODEL=$$OPENAI_MODEL"
	@echo "OPENAI_BASE_URL=$$OPENAI_BASE_URL"
	@python -c 'import os; print("OPENAI_API_KEY exists:", bool(os.getenv("OPENAI_API_KEY")))'
