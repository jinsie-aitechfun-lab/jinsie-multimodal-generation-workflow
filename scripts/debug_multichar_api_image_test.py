import os
import json
import time
import base64
import urllib.request
import urllib.error
from pathlib import Path

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


def post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def download_file(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as resp:
        data = resp.read()
    out_path.write_bytes(data)


def main() -> None:
    ts = int(time.time() * 1000)
    workflow_id = f"debug-multichar-api-{ts}"
    out_dir = Path("assets/mock") / workflow_id
    out_dir.mkdir(parents=True, exist_ok=True)

    req = WorkflowRunRequest(
        workflow_id=workflow_id,
        session_id=workflow_id,
        input={
            "topic": "小兔子和小乌龟赛跑",
            "duration_sec": 60,
            "audio_enabled": False,
            "voiceover_enabled": False,
            "render_mode": "manual",
        },
        steps=[
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "sentence_shots"},
            {"name": "image_prompts"},
        ],
    )

    runner = WorkflowRunner()
    result = runner.run(req)
    outputs = result.outputs or {}

    story = outputs.get("story") or {}
    style = story.get("style_profile") or {}
    manifest = outputs.get("character_manifest") or {}
    storyboard = outputs.get("storyboard") or {}
    prompts = (outputs.get("image_prompts") or {}).get("prompts") or []

    if not prompts:
        raise RuntimeError("image_prompts.prompts is empty")

    first_scene = (storyboard.get("scenes") or [])[0]
    first_prompt_item = prompts[0]
    base_prompt = str(first_prompt_item.get("prompt") or "").strip()

    prompt_debug = {
        "workflow_id": workflow_id,
        "main_character_display": style.get("main_character_display"),
        "secondary_character_display": style.get("secondary_character_display"),
        "manifest": manifest,
        "first_scene": first_scene,
        "first_prompt_item": first_prompt_item,
        "checks": {
            "has_rabbit": "小兔子" in base_prompt,
            "has_turtle": "小乌龟" in base_prompt,
            "has_required_scene_characters": "required scene characters" in base_prompt,
            "prompt_len": len(base_prompt),
        },
    }

    (out_dir / "prompt_debug.json").write_text(
        json.dumps(prompt_debug, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("workflow_id =", workflow_id)
    print("out_dir =", out_dir)
    print("main_character_display =", style.get("main_character_display"))
    print("secondary_character_display =", style.get("secondary_character_display"))
    print("manifest_count =", manifest.get("count"))
    print("has_rabbit =", prompt_debug["checks"]["has_rabbit"])
    print("has_turtle =", prompt_debug["checks"]["has_turtle"])
    print("has_required_scene_characters =", prompt_debug["checks"]["has_required_scene_characters"])
    print("prompt_len =", prompt_debug["checks"]["prompt_len"])

    idx = base_prompt.find("required scene characters")
    print("\n===== first prompt excerpt =====")
    if idx >= 0:
        print(base_prompt[idx:idx + 1200])
    else:
        print(base_prompt[:2000])

    base_url = (os.getenv("IMAGE_API_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").strip()
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    model = (os.getenv("SILICONFLOW_IMAGE_MODEL") or "").strip()
    size = (os.getenv("SILICONFLOW_IMAGE_SIZE") or "720x1280").strip()
    negative_prompt = (os.getenv("SILICONFLOW_IMAGE_NEGATIVE_PROMPT") or "").strip()

    if not base_url:
        raise RuntimeError("IMAGE_API_BASE_URL / OPENAI_BASE_URL is empty")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty")
    if not model:
        raise RuntimeError("SILICONFLOW_IMAGE_MODEL is empty")

    image_url = base_url.rstrip("/") + "/images/generations"

    payload = {
        "model": model,
        "prompt": base_prompt,
        "size": size,
        "n": 1,
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt

    headers = {"Authorization": f"Bearer {api_key}"}

    print("\n===== direct image api request =====")
    print("image_url =", image_url)
    print("model =", model)
    print("size =", size)

    response = post_json(image_url, payload, headers=headers)
    (out_dir / "direct_api_response.json").write_text(
        json.dumps(response, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    data = response.get("data") or []
    if not data:
        print("direct_api_response has no data")
        return

    first = data[0]

    if first.get("url"):
        img_path = out_dir / "direct_api_image_01.png"
        download_file(first["url"], img_path)
        print("saved_image =", img_path)
    elif first.get("b64_json"):
        img_bytes = base64.b64decode(first["b64_json"])
        img_path = out_dir / "direct_api_image_01.png"
        img_path.write_bytes(img_bytes)
        print("saved_image =", img_path)
    else:
        print("no url / no b64_json in direct_api_response.data[0]")

    print("saved_prompt_debug =", out_dir / "prompt_debug.json")
    print("saved_direct_api_response =", out_dir / "direct_api_response.json")


if __name__ == "__main__":
    main()
