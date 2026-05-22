#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import StepContext, WorkflowRunner

# ---------- 配置 ----------
duration_sec = 60
story_single = "小兔子去旅行"
story_multi = "兔子和乌龟赛跑"

runner_instance = WorkflowRunner()

# 输出目录
out_dir = Path("assets/mock/test_run")
out_dir.mkdir(parents=True, exist_ok=True)

# ---------- 单角色 candidate ----------
workflow_input_single = WorkflowInput(
    story=story_single,
    duration_sec=duration_sec,
    character_anchor_enabled=True,
    topic=story_single
)
ctx_single = StepContext(
    workflow_id=str(uuid4()),
    session_id=None,
    run_id=str(uuid4()),
    input=workflow_input_single
)

outputs = {}
runner_instance._run_storyboard(ctx_single, outputs)
runner_instance._run_sentence_shots(ctx_single, outputs)
runner_instance._run_image_assets(ctx_single, outputs)  # 不生成视频/音频

# 保存 JSON
out_path_single = out_dir / "single_role_outputs.json"
with out_path_single.open("w", encoding="utf-8") as f:
    json.dump(outputs, f, ensure_ascii=False, indent=2)
print(f"✅ 单角色 candidate JSON 已保存: {out_path_single}")

# 打开图片
for i, scene in enumerate(outputs.get("storyboard", {}).get("scenes", []), start=1):
    print(f"Scene {i} character_anchor:", json.dumps(scene.get("character_anchor"), ensure_ascii=False))
    for img in scene.get("reference_images", []):
        path = img.get("path")
        if path and Path(path).exists():
            subprocess.run(["open", path])

for i, shot in enumerate(outputs.get("shots", []), start=1):
    print(f"Shot {i} character_anchor:", json.dumps(shot.get("character_anchor"), ensure_ascii=False))
    for img in shot.get("reference_images", []):
        path = img.get("path")
        if path and Path(path).exists():
            subprocess.run(["open", path])

# ---------- 多角色 candidate ----------
workflow_input_multi = WorkflowInput(
    story=story_multi,
    duration_sec=duration_sec,
    character_anchor_enabled=True,
    topic=story_multi
)
ctx_multi = StepContext(
    workflow_id=str(uuid4()),
    session_id=None,
    run_id=str(uuid4()),
    input=workflow_input_multi
)

outputs.clear()
runner_instance._run_storyboard(ctx_multi, outputs)
runner_instance._run_sentence_shots(ctx_multi, outputs)
runner_instance._run_image_assets(ctx_multi, outputs)  # 不生成视频/音频

# 保存 JSON
out_path_multi = out_dir / "multi_role_outputs.json"
with out_path_multi.open("w", encoding="utf-8") as f:
    json.dump(outputs, f, ensure_ascii=False, indent=2)
print(f"✅ 多角色 candidate JSON 已保存: {out_path_multi}")

# 打开图片
for i, scene in enumerate(outputs.get("storyboard", {}).get("scenes", []), start=1):
    print(f"Scene {i} character_anchor:", json.dumps(scene.get("character_anchor"), ensure_ascii=False))
    for img in scene.get("reference_images", []):
        path = img.get("path")
        if path and Path(path).exists():
            subprocess.run(["open", path])

for i, shot in enumerate(outputs.get("shots", []), start=1):
    print(f"Shot {i} character_anchor:", json.dumps(shot.get("character_anchor"), ensure_ascii=False))
    for img in shot.get("reference_images", []):
        path = img.get("path")
        if path and Path(path).exists():
            subprocess.run(["open", path])

print("\n✅ 单角色 & 多角色 candidate 验证完成（不生成视频/音频）")
