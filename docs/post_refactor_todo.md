# Runner 重构完成后待办事项

> 本文件记录在 runner.py 重构期间发现、但**不属于本次重构范围**的问题。
> 这些问题应该在重构稳定后，作为独立的 PR / commit 修复。

---

## BUG-001: 角色名提取错误，把动宾短语当作角色名

**发现日期**：2026-05-21（Step 1 重构完成后的前端 UI 验证时）

**触发条件**：主题里"小X"角色后面紧跟一个动词短语，例如：
- `小狗看家` → 提取出 `"小狗看家"`（应为 `"小狗"`）
- `小猫钓鱼` → 提取出 `"小猫钓鱼"`（应为 `"小猫"`）
- `小狐狸跑步` → 提取出 `"小狐狸跑"`（应为 `"小狐狸"`）

**用户可见症状**：生成的故事里主角名变成动宾短语，例如 "小狗看家来到院子里"、"小狗看家叫了一声"，多次出现且不自然。

**根因定位**：

文件 `app/services/story_subject_extractor.py` 函数 `_cut_at_generic_syntax_boundary`：

```python
boundaries = ("去", "在", "被", "把", "给", "为", "从", "到", "向", "对", "用")
```

这个边界字符列表只覆盖了介词和少量动词，**没有 "看 / 钓 / 跑 / 种 / 吃 / 玩 / 学 / 唱 / 跳 / 做" 等常见动词**。导致主题里 "小狗看家" 这种"小X + 动词短语"切不开，整段被当作角色名。

另外 `_extract_open_xiao_subject` 的长度截断逻辑：

```python
if len(candidate) > 4:
    candidate = candidate[:3]
```

对 4 字以下的短语不截断，所以 "小狗看家"（恰好 4 字）也逃过截断。

**修复方案候选**：

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. 扩充 `boundaries` 动词列表 | 改动最小、零依赖 | 永远补不全；命中率有限 |
| B. 引入 `jieba` 分词，取第一个名词 | 准确率高、零运行时成本 | 增加一个依赖 |
| C. 用 LLM 提取（已有 OpenAI 配置） | 最准；可处理任意复杂主题 | 有延迟和 API 成本；增加失败路径 |

**建议**：B（jieba）作为默认，C（LLM）作为兜底。

**回归测试**：修复时建议补一组单元测试到 `tests/test_story_subject_extractor.py`（或 `scripts/verify_xxx.py`），至少覆盖：

```
小狗看家      → 小狗
小猫钓鱼      → 小猫
小白兔种萝卜  → 小白兔（不是"小白兔种"）
小狐狸跑步    → 小狐狸
小汽车旅行    → 小汽车
小明上学      → 小明（注意"明"不是"小X"格式）
```

**为什么不在重构期间修**：
- 重构 commit 必须保持"零行为变化"纪律
- 修这个 bug 会改变 story 生成的输出，属于行为变更
- 修复方案还需要讨论（A/B/C 选哪个）
- 等重构稳定后单独开 PR 更利于代码审查

---

## TEST-001: `scripts/acceptance.py` 仍按同步 workflow 响应断言

**发现日期**：2026-05-21（Step 4 video prompts 重构验收时）

**触发条件**：

运行：

```bash
make api
python scripts/acceptance.py
```

**修复前现象**：

脚本前几个 samples API 检查通过，但在 `/v1/workflow/run` 后失败：

```text
[FAIL] session_id mismatch: None
```

**原因定位**：

当前 `app/main.py` 的 `/v1/workflow/run` 是异步接口，立即返回：

```json
{"workflow_id": "...", "status": "processing"}
```

但 `scripts/acceptance.py` 仍按旧的同步 `WorkflowRunResponse` 契约断言，期望响应里直接包含：

- `session_id`
- `run_id`
- `status == "COMPLETED"`
- `steps`
- `outputs`
- `render_package`

**建议修复**：

把 `scripts/acceptance.py` 改成异步验收流程：

1. POST `/v1/workflow/run` 后只断言 `status == "processing"` 和 `workflow_id`。
2. 轮询 `assets/mock/<workflow_id>/outputs.json`。
3. 从落盘 outputs 中断言 step outputs、session memory、render package 等契约。

**为什么不在 Step 4 重构期间修**：

- Step 4 目标是零行为变化地抽取 video prompt 组装逻辑。
- 修改 acceptance 脚本属于测试契约更新，和 runner 代码抽取可以分开审查。

---

## TEST-002: `acceptance_character_visual_profiles_multi.py` 断言旧 prompt 文案块

**发现日期**：2026-05-21（Step 5 character manifest 重构验收时）

**触发条件**：

直接运行脚本需要显式设置项目导入路径：

```bash
PYTHONPATH=. python scripts/acceptance_character_visual_profiles_multi.py
```

**当前现象**：

脚本能生成 2 个角色视觉 profile，payload 数量也正确，但失败在首个图片 prompt 的字面文案断言：

```text
profile_count = 2
payload_count = 2
has_multi_profile_block = False
SUMMARY = FAIL
- first prompt missing multi-character visual profiles block
```

同一轮验证中，以下相关脚本通过：

```bash
PYTHONPATH=. python scripts/acceptance_image_prompt_multi_character.py
PYTHONPATH=. python scripts/acceptance_scene_character_presence.py
```

**原因定位**：

`scripts/acceptance_character_visual_profiles_multi.py` 仍断言首个 prompt 包含固定英文短语：

```text
multi-character visual profiles
```

但当前 prompt 中已经包含多角色身份锁、角色定义、must_keep / must_avoid 等约束信息，只是没有保留这个旧字面标题。该失败更像测试脚本对 prompt 文案标签的期望漂移，而不是 Step 5 抽取造成的功能缺失。

**建议修复**：

把该脚本从“固定标题字符串断言”改成更稳定的结构/语义断言，例如：

- `image_prompts.character_visual_profiles.count == 2`
- 首个 prompt 包含每个角色名
- 首个 prompt 包含多角色身份隔离关键词，如 `multi-character identity lock`
- 首个 prompt 包含每个角色的 `must_keep` / `must_avoid` 核心 traits

**为什么不在 Step 5 重构期间修**：

- Step 5 目标是零行为变化地抽取 character manifest 组装逻辑。
- 修改验收脚本断言属于测试维护，最好和重构主体拆开提交。
- 如果该脚本不阻塞 CI，可等 runner 重构稳定后统一清理；如果阻塞 CI，应单独开一个 test-only commit 修复。

---

## PERF-001: 真实生图接口耗时长时，前端需要更明确的长任务体验

**发现日期**：2026-05-21（Step 6 前端真实生图可见验证时）

**状态**：部分修复（2026-05-25）。已完成第一段：新增 `GET /v1/workflow/status/{workflow_id}`，后端在异步 workflow 开始、完成、失败时写入 `status.json`；前端先轮询状态接口，只有 `completed` 后才请求一次 `outputs.json`，避免 Network 面板刷出大量 404。已补 `scripts/verify_perf001_workflow_status_contract.py` 覆盖 `processing / completed / failed` 状态契约。第二段已给 image review 分场景刷新增加当前 scene 进度文案和进度条。第三段已增加前端“停止生成”按钮，可中断当前 refresh-scene 请求并停止剩余 scene 刷新。第四段已修正 workflow 主流程等待态：未拿到 storyboard 前不再显示 0% 假进度，也不再提示用户先执行 Run。第五段已增加主 workflow 已等待时长提示，并把状态轮询窗口从约 3 分钟延长到约 30 分钟，避免真实慢接口运行中页面过早回到空状态。第六段已增加后端 step 级进度状态，前端可显示当前步骤和已完成步骤数，避免长任务阶段只能看到泛泛的“运行中”。

**触发条件**：

使用真实 `api_image_generator` 生成多 scene 候选图，尤其是 60 秒或 120 秒 workflow 触发 6 到 12 个 scene 逐个刷新时。

**当前现象**：

- 外部真实生图接口响应很慢，用户会长时间看到等待状态。
- workflow 刚提交后，前端会直接轮询 `assets/mock/<workflow_id>/outputs.json`；在后端尚未写出文件前，Network 面板会出现大量 404 `outputs.json` 请求。功能上可用，但对用户和调试者非常不友好，看起来像系统持续失败。
- 如果某个 scene 失败，前端现在已经可以继续后续 scene 请求并展示失败状态，但长耗时阶段仍缺少足够明确的“还在工作 / 第几张 / 可取消 / 可重试”反馈。
- 真实 API 全量成功出图已在后续验证中跑通：`run_09e8fe7b57d3` 生成了 6 个 scene、每个 scene 2 张候选图，均为 `api_image_generator` 产物；但整体耗时较长，仍需要更明确的长任务体验。

**建议修复**：

- 不要让前端直接用静态 `outputs.json` 404 作为“还没生成好”的状态信号。
- 增加 workflow 状态查询接口，例如 `GET /v1/workflow/status/{workflow_id}`，返回 `processing / completed / failed` 和可选进度。
- 前端先轮询状态接口；只有状态为 `completed` 后再请求 `outputs.json`，这样 Network 面板不会刷出大量失败请求。
- 如果短期不加状态接口，前端至少应对 `outputs.json` 轮询做退避和静默处理，例如首轮 1.5s、后续 3s/5s，并在 UI 上显示“生成中”而不是把 404 当错误。
- 给 image review 刷新增加更清晰的 scene 级进度，例如 `scene_03 / 6`、候选图 A/B 状态、耗时。
- 增加取消按钮，允许用户停止剩余 scene 刷新。
- 增加单 scene 重试按钮，避免整条 workflow 重新跑。
- 为真实生图接口设置合理超时和错误分类，例如超时、429、5xx、鉴权失败、网络失败。
- 如果后端支持队列任务，前端改为轮询任务状态，而不是长时间等待单个请求。

**为什么不在 runner 重构期间修**：

- 这属于真实外部服务交互体验和任务编排改造，不是 runner 模块抽取。
- 需要和后端队列、错误契约、前端交互一起设计，适合独立提交。

---

## DEV-001: 本地真实生图验证依赖 `.env` 加载方式，直接 shell source 会失败

**发现日期**：2026-05-21（Step 6 前端真实生图可见验证时）

**触发条件**：

尝试用 shell 直接加载 `.env` 后启动后端：

```bash
set -a; source .env; set +a
```

**当前现象**：

`.env` 中存在带空格的赋值写法，例如：

```text
SILICONFLOW_API_KEY = "..."
```

这不是标准 shell env 语法，直接 `source .env` 会失败，导致后端启动时没有拿到真实生图 key，随后 `refresh-scene` 报：

```text
image api key is missing
```

**建议修复**：

- 明确本地启动入口统一加载 `.env`，例如在 `make api` 或应用启动处使用 `python-dotenv`。
- 或者规范 `.env` 写法，去掉 key/value 两侧空格，确保 shell source 也可用。
- 增加一个只打印布尔状态的诊断命令，例如检查 `IMAGE_PROVIDER`、`API_IMAGE_ENABLED`、`SILICONFLOW_API_KEY exists`，但不要输出密钥内容。

**为什么不在 runner 重构期间修**：

- 属于本地开发环境启动契约，不是 runner 行为抽取。
- 修改启动方式可能影响每个人本地环境，应单独确认后提交。

---

## BUG-002: `refresh-scene` 后端异常会让前端只看到 `Failed to fetch`

**发现日期**：2026-05-21（Step 6 前端真实生图可见验证时）

**状态**：已修复（2026-05-22）。修复内容：`/v1/image-review/refresh-scene` 运行时异常会返回 `502` 和结构化 `detail`（`code` / `scene_id` / `provider` / `message`）；前端会优先展示结构化错误，网络中断时也会显示更明确的后端连接失败文案；已补 `scripts/verify_bug002_refresh_scene_error_detail.py` 覆盖接口错误契约。

**触发条件**：

`/v1/image-review/refresh-scene` 内部真实生图失败并抛出未捕获异常，例如缺少 API key、外部接口异常、超时等。

**修复前现象**：

后端日志里有明确异常，例如：

```text
single scene image asset generation failed with provider=api_image_generator
```

但前端在浏览器里可能只拿到：

```text
Failed to fetch
```

这会让用户不知道是鉴权、网络、限流还是服务端异常。

**已采用修复**：

- 在 `app/main.py` 的 `refresh_image_review_scene` 接口层捕获可预期异常，返回结构化 JSON 错误，例如：

```json
{
  "detail": {
    "code": "IMAGE_GENERATION_FAILED",
    "scene_id": "scene_02",
    "provider": "api_image_generator",
    "message": "..."
  }
}
```

- 确保错误响应仍带 CORS 头，让前端能读取 `detail`。
- 前端按错误 code 展示更友好的文案，并保留 scene 级失败状态。

**为什么不在 runner 重构期间修**：

- 这是 API 错误契约变更，可能影响前端和验收脚本。
- 适合和真实生图长任务体验一起做独立修复。

---

## TEST-003: `acceptance_image_provider.py` 依赖后端服务运行，缺少本地前置检查

**发现日期**：2026-05-22（Step 14 scene render fallback 重构验收时）

**状态**：已修复（2026-05-22）。修复内容：`scripts/acceptance_image_provider.py` 已在发起 workflow 请求前检查 `GET /health`；后端未启动、健康检查非 200、响应非 JSON 或 `status != ok` 时，会给出明确失败提示和 `Please run: make api` 前置条件。

**触发条件**：

直接运行：

```bash
python scripts/acceptance_image_provider.py --mode pillow
```

**修复前现象**：

如果本地 `make api` 没有在 `127.0.0.1:8004` 启动，脚本会直接请求 `/v1/workflow/run` 并失败：

```text
ConnectionRefusedError: [Errno 61] Connection refused
```

如果在沙箱环境里直接运行，还可能先遇到本机网络访问限制：

```text
PermissionError: [Errno 1] Operation not permitted
```

**原因定位**：

`scripts/acceptance_image_provider.py` 是接口级验收脚本，默认假设后端服务已经启动，但脚本没有在发请求前做 health check / readiness check，也没有给出“请先启动 make api”的友好提示。

**已采用修复**：

- 在脚本开头请求一个轻量健康检查接口，或至少探测 `base_url` 是否可连接。
- 如果服务未启动，输出明确提示，例如：

```text
Backend is not running at http://127.0.0.1:8004.
Please run: make api
```

- 如无健康检查接口，可考虑补一个 `GET /health` 或 `GET /v1/health`。
- 在文档或脚本 help 中说明接口级 acceptance 的前置条件。

**为什么不在 Step 14 重构期间修**：

- Step 14 目标是零行为变化地抽取 scene render fallback。
- 修改 acceptance 脚本的运行契约属于测试体验改进，适合单独提交。
- 本轮已用进程内脚本验证了 `_build_scene_png` 正常路径和 `_build_scene_ppm` fallback 路径。

---

## TEST-004: `validate_candidates_fast.py` 引用不存在的 `StepContext`

**发现日期**：2026-05-22（Step 14 scene render fallback 重构验收时）

**状态**：已修复（2026-05-22）。修复内容：`scripts/validate_candidates_fast.py` 已在脚本内补项目根目录到 `sys.path`，并改为从 `app.services.runner` 导入 `StepContext`；已用 `python scripts/validate_candidates_fast.py` 验证单角色和多角色 candidate JSON 可生成。

**触发条件**：

直接运行会先遇到项目导入路径问题：

```bash
python scripts/validate_candidates_fast.py
```

补上 `PYTHONPATH` 后继续运行：

```bash
PYTHONPATH=. python scripts/validate_candidates_fast.py
```

**修复前现象**：

脚本失败：

```text
ImportError: cannot import name 'StepContext' from 'app.schemas.workflow'
```

**原因定位**：

`StepContext` 当前定义在 `app/services/runner.py`，不在 `app/schemas/workflow.py`。脚本里的导入已经和当前代码结构不一致：

```python
from app.schemas.workflow import WorkflowInput, StepContext
```

**已采用修复**：

- 把脚本导入改为当前结构，例如：

```python
from app.schemas.workflow import WorkflowInput
from app.services.runner import StepContext, WorkflowRunner
```

- 同时在脚本开头统一补项目根目录到 `sys.path`，避免必须手动设置 `PYTHONPATH=.`
- 修复后用它补充验证 mock image candidates 是否仍能稳定生成。

**为什么不在 Step 14 重构期间修**：

- 这是历史验证脚本维护问题，不是 scene render fallback 抽取引入。
- 为了保持本次 refactor commit 只包含 runner 拆分，不混入旧脚本修复。

---

## BUG-003: `/v1/image-review/refresh` endpoint 传参和 runner 方法签名不一致

**发现日期**：2026-05-22（Step 19 image review refresh-scene 重构时）

**状态**：已修复（2026-05-22）。修复内容：`WorkflowRunner.refresh_image_review(...)` 已接收 `character_manifest` / `image_prompts`，并把 list 形态的 `image_prompts` 归一化为内部使用的 `{"prompts": [...]}`；已补 `scripts/verify_bug003_image_review_refresh_contract.py` 覆盖显式 payload 和 stored context fallback。

**触发条件**：

调用 `app/main.py` 中的 `/v1/image-review/refresh` endpoint。

**当前现象**：

`app/main.py` 调用：

```python
_runner.refresh_image_review(
    workflow_id=req.workflow_id,
    session_id=req.session_id,
    run_id=req.run_id,
    storyboard=req.storyboard,
    workflow_input=req.workflow_input,
    image_review=req.image_review,
    character_manifest=getattr(req, "character_manifest", None),
    image_prompts=getattr(req, "image_prompts", None),
    video_provider=req.video_provider,
)
```

但修复前 `WorkflowRunner.refresh_image_review(...)` 方法签名里没有：

```python
character_manifest
image_prompts
```

这会导致 endpoint 在运行时抛：

```text
TypeError: WorkflowRunner.refresh_image_review() got an unexpected keyword argument 'character_manifest'
```

**原因定位**：

`ImageReviewRefreshRequest` schema 已经增加了 `character_manifest` / `image_prompts` 字段，`refresh-scene` 路径也使用这两个字段做多角色刷新闭环；但整批 `/v1/image-review/refresh` 的 runner 方法签名和内部 outputs 合并逻辑还没同步。

另外 schema 中：

```python
image_prompts: Optional[List[Dict]] = None
```

而其他路径通常按：

```python
{"prompts": [...]}
```

使用 image prompts，修复时也需要确认前后端实际传输结构，避免只修签名不修数据形状。

**已采用修复**：

- 给 `WorkflowRunner.refresh_image_review(...)` 增加可选参数：

```python
character_manifest: Optional[Dict[str, Any]] = None
image_prompts: Optional[Any] = None
```

- 在 refresh outputs 构建时，优先使用显式传入值，其次使用 session stored context：

```python
resolved_character_manifest = explicit_character_manifest or stored_character_manifest
resolved_image_prompts = explicit_image_prompts or stored_image_prompts
```

- 如果前端传的是 list 形态 image prompts，需要在 API 层或 runner 层统一归一化为 `{"prompts": [...]}`。
- 补一个接口或进程内验证，覆盖 `/v1/image-review/refresh` 带 `character_manifest` / `image_prompts` 的情况。

**为什么不在 Step 19 重构期间修**：

- Step 19 只做 `refresh_image_review_scene` 的等价搬移。
- 这个问题属于现有 API 调用契约不一致，修复会改变 `/v1/image-review/refresh` 行为，适合单独提交。

---

## BUG-004: 多角色主题生成图缺少关键角色

**发现日期**：2026-05-25（真实生图前端验证时）

**触发条件**：

主题包含多个核心角色，例如：

```text
写一个关于兔子和乌龟赛跑的故事
```

**当前现象**：

生成出的图片里经常只有兔子，没有乌龟；即使故事和分镜中包含乌龟，候选图也可能没有把乌龟画出来。

**用户可见影响**：

- 故事主题和画面内容不一致。
- 多角色故事无法成立，后续视频画面也会缺失关键角色。
- 用户会认为系统没有理解主题。

**可能原因**：

- scene 的 `characters` / `character_ids` 没有稳定传入真实生图 prompt。
- image prompt 对“每个 scene 必须出现哪些角色”的约束不够强。
- prompt 对 supporting / secondary 角色的权重不足，模型倾向只画主角。
- 自动选图器没有把“缺少角色”作为硬性失败条件。

**建议修复**：

- 在 image prompt 中增加 scene-level required character list，例如 `required_characters`。
- 对每个 scene 明确写入“必须同时出现：兔子、乌龟”，而不是只在全局角色 profile 里描述。
- 自动筛选器需要检测/评估候选图是否包含所有 required characters；缺失关键角色时不能选中。
- 补进程内验证：`兔子和乌龟赛跑` 的 storyboard / image_prompts / image_assets contract 中，每个相关 scene 都保留两个角色约束。

**已采用修复（prompt contract 层）**：

- `image_prompts` 每条 prompt 增加 `required_character_ids` / `required_character_names` metadata。
- 多角色 scene prompt 保留 `scene cast lock` / `required scene characters` 强约束，明确要求所有角色同框且不可省略。
- 补充 `verify_bug004_005_multi_character_prompt_contract.py`，覆盖非结构化主题“兔子和乌龟赛跑”的角色 manifest、storyboard、prompt 必需角色约束。
- 真实出图复测发现模型仍被“主角兔子”前置提示带偏后，已把多角色 required characters 约束前置到 prompt 开头，并增加 `not a solo portrait` 防单角色肖像约束。

**仍需后续跟进**：

- 真实图片候选是否真的包含全部角色，需要 BUG-007 的自动筛选器接入 required character metadata 后继续验证。

**优先级**：P0。建议下一步优先修。

---

## BUG-005: 多角色身份串扰，角色特征互相污染

**发现日期**：2026-05-25（真实生图前端验证时）

**触发条件**：

主题或结构化角色中同时包含外形差异大的角色，例如兔子和乌龟。

**当前现象**：

- 乌龟会长兔耳朵。
- 兔子会出现乌龟壳。
- 不同角色的物种、服装、身体特征互相串。
- 2026-05-25 真实复测：即使 prompt / negative prompt 已强化，仍出现“蓝色兔耳乌龟”“兔子背乌龟壳”“画面中出现额外小乌龟壳”等明显串扰。

**用户可见影响**：

画面中角色身份混乱，用户无法判断哪个角色是谁；多角色故事的视频连续性被破坏。

**可能原因**：

- 角色 identity lock 只描述了角色本身，但没有足够强的 negative constraints。
- prompt 没有明确写“兔子不能有壳 / 乌龟不能有兔耳朵”等跨角色 forbidden traits。
- 候选筛选器没有识别 identity leakage。

**建议修复**：

- 从 `character_manifest` 生成 cross-character negative constraints：
  - 兔子：must_avoid turtle shell。
  - 乌龟：must_avoid rabbit ears。
- 每个 scene prompt 同时包含 `must_keep` 与 `must_avoid`。
- 筛选器把“角色特征串扰”作为强扣分或失败条件。
- 补验证脚本覆盖兔子/乌龟互斥特征写入 prompt。

**已采用修复（prompt contract 层）**：

- 多角色 scene 自动生成跨角色 negative constraints，例如：
  - 兔子不能有 turtle shell / turtle body / short turtle legs。
  - 乌龟不能有 rabbit ears / fluffy rabbit tail / rabbit body。
- `scene_character_prompt_block` 写入 `cross-character must avoid`。
- `scene_character_negative_block` 写入带角色名的串扰负面约束，避免不同角色身体特征互相污染。
- 为兔子 / 乌龟 deterministic visual profile 增加固定外观、固定配饰和互斥特征，避免 LLM profile 失败时回落到过于泛化的“same color palette”描述。
- 真实复测仍出现兔子有壳、乌龟有耳朵后，已把 `hybrid rabbit turtle creature`、`rabbit with turtle shell`、`turtle with rabbit ears` 等约束写入 API 生图请求的 `negative_prompt` 字段。
- 真实复测仍出现乌龟长耳朵后，继续强化正向结构约束：乌龟必须是 `earless rounded turtle head / no external ears`，只有兔子有长耳，只有乌龟有壳；同时避免在全局 `negative_prompt` 中写入裸的 `rabbit ears` / `turtle shell`，只禁止 `turtle with rabbit ears`、`rabbit with turtle shell` 这类串扰组合，避免把合法特征也负向掉。

**仍需后续跟进**：

- 仅靠继续叠加 prompt / negative prompt 已经接近收益上限，真实 provider 仍可能把兔子和乌龟的身体特征混合。
- 下一步应转为“视觉级失败检测 + 自动重试”：检测到乌龟长兔耳、兔子背龟壳、缺少必需角色、额外混合物种角色时，候选图直接判失败并重新生成。
- 如果 provider 支持 reference image / seed / character consistency，应引入每个角色的参考图或稳定 seed；纯文本 prompt 很难保证多图、多角色一致。
- BUG-007 的候选评分/筛选逻辑必须把这些 forbidden traits 作为硬扣分或失败条件，不能继续默认选择第一张。

**优先级**：P0。prompt contract 已做基础修复，但真实画面仍未达产品可用标准；下一步优先做视觉检测/自动重试或参考图一致性方案。

---

## BUG-006: 角色跨图不一致，装饰、服装、外貌和颜色漂移

**发现日期**：2026-05-25（真实生图前端验证时）

**触发条件**：

同一个 workflow 生成多个 scene / candidate 图。

**当前现象**：

同一角色在不同图片里的装饰、衣服、外貌甚至颜色不一致；例如同一只兔子在不同场景中颜色、服装、配饰变化明显。2026-05-25 真实复测中，同一组兔子/乌龟仍会出现颜色、体型和物种特征漂移。

**用户可见影响**：

多张图无法构成连续故事，最终视频像是多个不同角色拼接。

**可能原因**：

- 角色视觉 profile 不够具体，缺少稳定的 color palette / outfit / accessory 锁定字段。
- 每张图 prompt 没有重复引用完整角色视觉锚点。
- 真实生图 provider 没有参考图或 seed 锁定，纯文本 prompt 难以保持跨图一致。

**建议修复**：

- 为每个角色生成稳定视觉签名：
  - 主色、辅色、衣服、配饰、体型、面部特征。
- 每个 image prompt 都注入同一份角色视觉签名。
- 如果 provider 支持参考图/seed，后续增加 reference image 或 seed 策略。
- 在 `image_review` 中展示角色一致性风险，便于人工选择。
- 仅靠当前文本 prompt 不能稳定保证跨图一致性，建议把 reference image / seed / 视觉评审重试作为后续主方案。

**优先级**：P0。现在已影响最终视频观感，建议和 BUG-005 的视觉检测/自动重试一起做。

---

## BUG-007: 图片自动筛选器没有生效，总是默认选择第一张

**发现日期**：2026-05-25（真实生图前端验证时）

**触发条件**：

每个 scene 生成多张候选图后进入自动筛选流程。

**当前现象**：

自动筛选器看起来没有真正按质量/角色匹配评分，总是默认选择第一张候选图。

**用户可见影响**：

- 如果第一张缺角色或角色串扰，系统仍会自动选中。
- “候选图筛选”功能名存实亡，用户需要手动检查每一张。

**可能原因**：

- 当前筛选器可能只做占位逻辑或 fallback 到第一张。
- 没有从候选图本身提取可评分信号。
- 没有把 prompt contract（required characters / forbidden traits）接入评分。

**建议修复**：

- 先明确当前 selector 的真实逻辑，补一个验证证明它不是固定选第一张。
- 如果当前只能基于 metadata，至少按以下规则排序：
  - provider 成功状态。
  - required characters 是否完整。
  - 是否包含 identity leakage 风险。
  - prompt/candidate metadata 是否完整。
- 如果需要视觉级判断，后续接入视觉模型评审候选图。

**已采用修复（metadata quality gate 层）**：

- `select_best_candidate` 增加通用多角色 metadata quality gate，输出 `quality_gates`，记录 required character labels、是否多角色、当前是否有视觉 verifier。
- auto 模式保持产品语义：继续自动筛选候选图并自动合成视频，不因为 metadata-only gate 强制人工确认。
- 手动模式仍允许用户进入 Review 手动改选候选图；手动选择后 `review_status` 标记为 `manually_selected`。
- 移除 selector 对 `candidate_a` 的轻微加分，避免同分或接近同分时主动偏向第一张。
- 补充 `verify_bug007_image_quality_gates.py` 覆盖多角色场景会写入 advisory-only quality gate，且不会把 auto 模式变成强制人工审核；同时覆盖当 `candidate_b` 评分更高时会选中第二张。

**仍需后续跟进**：

- 当前 selector 确实在运行，会写入 `selection_source=auto_filter`、`candidate_scores` 和 `selection_reason`，但它仍不是视觉语义筛选器。
- 它无法识别“兔子背壳”“缺少乌龟”“乌龟长兔耳朵”等真实画面语义错误；这类能力必须接视觉模型评审、对象检测、参考图一致性或 provider 原生 character consistency。
- 如果候选图在颜色/对比度等基础分数上差别不明显，selector 仍可能看起来像默认选择第一张；这不是合格的产品级图片筛选。

**优先级**：P1。建议在 BUG-004 / BUG-005 后修，否则筛选器缺少可靠评分目标。

---

## BUG-008: 60s 主题最终音频/视频只有约 40s

**发现日期**：2026-05-25（真实前端验证时）

**触发条件**：

选择 `duration_sec=60`，开启旁白/音频并生成最终视频。

**当前现象**：

最终视频跟随真实 TTS 音频时长，曾只有约 40s；不是 final video 合成层被硬截断，而是故事/分镜旁白文本总量偏短，真实音频读完后视频自然结束。后续一次修复把 60s 文本目标调到 `420-520` 字，真实验证又生成约 1:25；再调到 `300-380` 字后真实验证仍约 1:14；最终调到 `250-310` 字后真实复测约 0:58，基本符合 60s 预期。

**原因定位**：

60s story plan 的目标中文字符数原本只有 `190-260`，对真实 TTS 来说偏短，容易生成约 40s 左右的旁白；但 `420-520` 会把真实音频拉到约 80s+，`300-380` 仍会拉到 70s+，需要按真实 TTS 结果做中间校准。

**已采用修复**：

- 将 60s story plan 调整为 `250-310` 中文字符，目标约 `280` 字，按真实 TTS 验证结果从过长配置继续回调到更接近 60s 的范围。
- 补充 Step 8 验证，确保 60s template fallback story 达到新的最低文本长度。

**仍需后续跟进**：

- 真实 TTS 语速会随 provider/voice 波动，后续可以增加“音频总时长低于目标阈值时提示或重试扩写旁白”的闭环。

**优先级**：P1。当前 60s 真实复测已基本可接受，后续做音频时长闭环即可。

---

## BUG-009: 故事旁白泄漏时长控制文本

**发现日期**：2026-05-25（真实前端验证时）

**触发条件**：

选择 60s 生成兔子和乌龟故事，LLM 生成故事文本后进入 TTS / 字幕 / 视频合成。

**当前现象**：

旁白/字幕中出现“有6秒”这类不属于故事内容的文本，例如“在一个美丽的森林里，有6秒有一只活泼的兔子……”。

**原因定位**：

故事生成 prompt 中包含 `Selected duration: 60 seconds` 等时长控制信息，LLM 偶发把控制信息误写进中文故事；原 sanitizer / quality check 没有识别 `数字 + 秒` 的污染片段。

**已采用修复**：

- 将故事生成和 retry prompt 改为“时长只用于旁白节奏控制，不要写进故事”。
- 增加硬约束：不要输出 selected duration、seconds、target length、`60秒` / `有6秒` 等文本。
- `sanitize_llm_story_text` 自动清理 `有6秒有一只...` 这类污染片段。
- `story_text_has_quality_issues` 将 `数字 + 秒` 判为质量问题，触发 retry。
- 补充 Step 8 验证覆盖 `有6秒` 清理和质量检测。

**优先级**：P0。已修，后续真实 workflow 复测确认。
