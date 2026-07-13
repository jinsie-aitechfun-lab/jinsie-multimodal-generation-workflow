from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional


ImageProviderName = Literal[
    "pillow_storybook_renderer",
    "api_image_generator",
]

ImageAssetStatus = Literal[
    "generated",
    "pending",
    "retrying",
    "failed",
]


PROVIDER_PILLOW: ImageProviderName = "pillow_storybook_renderer"
PROVIDER_API: ImageProviderName = "api_image_generator"


@dataclass
class ImageCandidateResult:
    provider: str
    file_name: str
    relative_path: str
    public_url: str
    mime_type: str = "image/png"
    bytes_data: bytes = b""


@dataclass
class ImageGenerationTask:
    run_id: str
    item_id: str
    scene_id: str
    prompt: str
    candidate_suffix: str
    output_path: Any
    relative_path: str
    public_url: str
    reference_images: List[Dict[str, Any]] = field(default_factory=list)
    prompt_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 1.5
    backoff_multiplier: float = 1.5
    retry_on_rate_limit: bool = True
    retry_on_network_error: bool = True


@dataclass
class RetryResult:
    ok: bool
    value: Any = None
    error: Optional[Exception] = None
    attempts: int = 0
    last_delay_seconds: float = 0.0


@dataclass
class QueueExecutionResult:
    status: ImageAssetStatus
    provider: str
    assets: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    retry_after_sec: Optional[int] = None
    fallback: Dict[str, Any] = field(default_factory=dict)
    character_anchor: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueuePolicy:
    primary_provider: str
    fallback_provider: str
    fallback_enabled: bool
    rate_limit_strategy: str = "pending"


AdapterGenerateFunc = Callable[[ImageGenerationTask], bytes]