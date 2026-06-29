from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.services.story_retry_policy import (
    repair_retry_story_text,
    retry_story_with_llm,
    validate_story_text,
)


class RunnerStorySupport:
    """Story generation orchestration extracted from WorkflowRunner.

    Extracted as Step 7 of the runner refactor. This module owns the story
    step orchestration while delegating the still-shared text, character, and
    provider helpers back to WorkflowRunner to keep this refactor behavior-only.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def run_story(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        runner = self._runner
        provider = runner._story_provider_name()

        topic = ctx.input.topic.strip() or "一个温暖的童话故事"
        tone_label = runner._tone_label(ctx.input.tone)
        audience_label = runner._audience_label(ctx.input.audience)
        main_character_display = runner._main_character_display_label(ctx, outputs)
        secondary_character_display = runner._secondary_character_display_label(
            ctx, outputs
        )
        has_secondary_character = runner._has_secondary_character(ctx, outputs)

        llm_story: Dict[str, str] | None = None
        generation_source = "template_fallback"
        fallback_reason: Optional[str] = None

        if provider == "openai_compatible_llm":
            try:
                llm_story = runner._generate_story_with_llm(ctx, outputs)
            except Exception as error:
                fallback_reason = f"llm_error:{type(error).__name__}"
                llm_story = None
        else:
            fallback_reason = "story_provider_template"
        story_text = ""
        title = ""
        summary = ""

        if llm_story:
            title = llm_story.get("title", "") or ""
            summary = llm_story.get("summary", "") or ""
            story_text = llm_story.get("text", "") or ""

        raw_text = story_text or ""
        cleaned_text = raw_text.strip()

        if cleaned_text.startswith("{") or cleaned_text.startswith("["):
            extracted = None
            try:
                obj = json.loads(cleaned_text)
                if isinstance(obj, dict):
                    value = obj.get("text")
                    if isinstance(value, str) and value.strip():
                        extracted = value.strip()
            except Exception:
                extracted = None

            if extracted is None and "{" in cleaned_text and "}" in cleaned_text:
                start = cleaned_text.find("{")
                end = cleaned_text.rfind("}")
                if 0 <= start < end:
                    snippet = cleaned_text[start : end + 1]
                    try:
                        obj2 = json.loads(snippet)
                        if isinstance(obj2, dict):
                            value2 = obj2.get("text")
                            if isinstance(value2, str) and value2.strip():
                                extracted = value2.strip()
                    except Exception:
                        extracted = None

            if extracted is not None:
                cleaned_text = extracted

        cleaned_text = runner._sanitize_llm_story_text(cleaned_text, topic)

        story_plan = runner._duration_story_plan(ctx.input.duration_sec)
        cleaned_text, invalid_reasons = validate_story_text(
            runner,
            cleaned_text,
            topic,
            story_plan,
        )

        if invalid_reasons and provider == "openai_compatible_llm" and cleaned_text:
            retry_story: Dict[str, str] | None = None
            retry_error: Optional[str] = None

            try:
                retry_story = retry_story_with_llm(
                    runner,
                    ctx,
                    outputs,
                    cleaned_text,
                    invalid_reasons,
                )
            except Exception as error:
                retry_error = f"retry_error:{type(error).__name__}"

            if retry_story:
                retry_cleaned_text, retry_invalid_reasons = validate_story_text(
                    runner,
                    retry_story.get("text", "") or "",
                    topic,
                    story_plan,
                )

                if not retry_invalid_reasons:
                    llm_story = retry_story
                    title = retry_story.get("title", "") or title
                    summary = retry_story.get("summary", "") or summary
                    story_text = retry_cleaned_text
                    generation_source = (
                        "llm_compressed"
                        if "too_long" in invalid_reasons
                        else "llm_retried"
                    )
                    fallback_reason = None
                    invalid_reasons = []
                else:
                    repaired_text = repair_retry_story_text(
                        runner,
                        retry_cleaned_text,
                        topic,
                        story_plan,
                    )
                    repaired_cleaned_text, repaired_invalid_reasons = (
                        validate_story_text(
                            runner,
                            repaired_text,
                            topic,
                            story_plan,
                        )
                    )

                    if not repaired_invalid_reasons:
                        llm_story = retry_story
                        title = retry_story.get("title", "") or title
                        summary = retry_story.get("summary", "") or summary
                        story_text = repaired_cleaned_text
                        generation_source = "llm_repaired"
                        fallback_reason = None
                        invalid_reasons = []
                    else:
                        # Repair still left some issues. Decide whether the text is
                        # salvageable (minor length/topic drift) or truly broken
                        # (empty, garbled, or structured output). Salvageable text
                        # goes out as llm_degraded — audio speed-adjustment handles
                        # minor duration drift. Truly broken text falls to template.
                        hard_failure_reasons = {
                            "empty_text",
                            "quality_issues",
                            "structured_output",
                            "blocked_tokens",
                        }
                        is_salvageable = (
                            bool(repaired_cleaned_text)
                            and not hard_failure_reasons.intersection(
                                set(repaired_invalid_reasons)
                            )
                        )
                        if is_salvageable:
                            llm_story = retry_story
                            title = retry_story.get("title", "") or title
                            summary = retry_story.get("summary", "") or summary
                            story_text = repaired_cleaned_text
                            generation_source = "llm_degraded"
                            fallback_reason = "degraded:" + ",".join(
                                repaired_invalid_reasons
                            )
                            invalid_reasons = []
                        else:
                            fallback_reason = "retry_failed:" + ",".join(
                                repaired_invalid_reasons
                            )
                            llm_story = None
            elif retry_error:
                fallback_reason = retry_error
                llm_story = None

        if invalid_reasons:
            if not fallback_reason:
                fallback_reason = ",".join(invalid_reasons)
            llm_story = None
        else:
            if generation_source == "template_fallback":
                generation_source = (
                    "llm_sanitized" if cleaned_text != raw_text.strip() else "llm"
                )
                story_text = cleaned_text
            fallback_reason = None

        if llm_story:
            title = title or f"{topic}的故事"
            summary = summary or (
                f"一个围绕“{topic}”展开的短篇故事，整体气质{tone_label}，适合做成{audience_label}向内容。"
            )
        elif provider == "openai_compatible_llm":
            # LLM was the configured story provider and all retries +
            # repairs failed. Refuse to silently substitute a hard-coded
            # template paragraph — that content is poor quality and
            # users mistake it for real AI output, eroding trust in the
            # product. Surface the failure so the workflow run errors
            # cleanly and the FE can offer an explicit retry.
            #
            # Template-mode (STORY_PROVIDER=template) still uses the
            # paragraph builder below — that path is an intentional
            # opt-in test mode, not a fallback.
            reason = fallback_reason or "llm_unavailable"
            raise RuntimeError(f"故事生成失败：{reason}")
        else:
            generation_source = "template_fallback"
            if not fallback_reason:
                fallback_reason = "llm_unavailable_or_disabled"

            paragraphs = runner._build_story_paragraphs(ctx, outputs)
            story_plan = runner._duration_story_plan(ctx.input.duration_sec)

            safety_extensions = [
                f"这一次，{main_character_display}没有急着往前冲，而是先停下来认真观察周围的变化。它发现，真正重要的线索常常藏在很小的声音、很轻的脚步和朋友一句温柔的提醒里。",
                f"它慢慢明白，解决问题不一定要一下子变得很厉害，而是要愿意一次又一次尝试。每当它有些害怕时，都会想起出发时的愿望，于是重新鼓起勇气继续往前走。",
                f"后来，{main_character_display}也遇见了需要帮助的小伙伴。它把自己刚刚学会的方法分享出来，陪着对方一起观察、一起思考，也一起找到更安心的办法。",
                f"当旅程快要结束时，阳光把周围照得柔和明亮。{main_character_display}回头看见自己走过的路，发现那些小小的困难并没有把它吓退，反而让它更懂得勇敢和善良。",
                f"回到熟悉的地方后，{main_character_display}把这段经历认真记在心里。它知道，以后还会遇到新的问题，但只要愿意倾听、合作和坚持，就一定能找到属于自己的答案。",
            ]

            extension_index = 0
            while runner._story_text_char_count("\n".join(paragraphs)) < int(
                story_plan.get("target_min_chars") or 0
            ) and extension_index < len(safety_extensions):
                paragraphs.append(safety_extensions[extension_index])
                extension_index += 1

            story_text = "\n".join(paragraphs)

            if has_secondary_character:
                summary = (
                    f"一个围绕“{topic}”展开的短篇故事，主角是{main_character_display}，"
                    f"配角是{secondary_character_display}，整体气质{tone_label}，适合做成{audience_label}向内容。"
                )
            else:
                summary = (
                    f"一个围绕“{topic}”展开的短篇故事，主角是{main_character_display}，"
                    f"整体气质{tone_label}，适合做成{audience_label}向内容。"
                )
            title = f"{topic}的故事"

        manifest_items = runner._character_manifest_support.character_manifest_items(
            outputs
        )

        return {
            "title": title,
            "summary": summary,
            "text": story_text,
            "generation_source": generation_source,
            "fallback_reason": fallback_reason,
            "style_profile": {
                "audience": ctx.input.audience,
                "tone": ctx.input.tone,
                "visual_style": ctx.input.visual_style,
                "character_style": ctx.input.character_style,
                "main_character": ctx.input.main_character,
                "main_character_display": main_character_display,
                "secondary_character": ctx.input.secondary_character,
                "secondary_character_display": secondary_character_display,
                "character_consistency_anchor": ctx.input.character_consistency_anchor,
                "language": ctx.input.language,
                "structured_characters_enabled": bool(
                    ctx.input.structured_characters_enabled
                ),
                "character_ids": [
                    item.get("character_id")
                    for item in manifest_items
                    if item.get("character_id")
                ],
            },
        }
