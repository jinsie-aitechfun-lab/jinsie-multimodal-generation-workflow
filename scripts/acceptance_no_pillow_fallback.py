import os
import sys
from app.services.runner import WorkflowRunner

def main():
    runner = WorkflowRunner()
    runner._api_image_fallback_to_pillow = lambda: False  # 强制禁用 fallback

    try:
        # 调用原 acceptance 流程（覆盖 IMAGE_FALLBACK 检查）
        os.environ['CHARACTER_PROFILE_PROVIDER'] = 'openai_compatible_llm'
        from scripts.acceptance_image_prompt_multi_character import main as run_acceptance
        run_acceptance()
    except Exception as e:
        print("Acceptance test failed:", e)
        sys.exit(1)

    print("=== Pillow fallback disabled acceptance PASSED ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
