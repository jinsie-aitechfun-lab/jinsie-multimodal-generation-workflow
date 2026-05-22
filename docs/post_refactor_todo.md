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

**当前现象**：

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

**触发条件**：

`/v1/image-review/refresh-scene` 内部真实生图失败并抛出未捕获异常，例如缺少 API key、外部接口异常、超时等。

**当前现象**：

后端日志里有明确异常，例如：

```text
single scene image asset generation failed with provider=api_image_generator
```

但前端在浏览器里可能只拿到：

```text
Failed to fetch
```

这会让用户不知道是鉴权、网络、限流还是服务端异常。

**建议修复**：

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

**触发条件**：

直接运行：

```bash
python scripts/acceptance_image_provider.py --mode pillow
```

**当前现象**：

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

**建议修复**：

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

**触发条件**：

直接运行会先遇到项目导入路径问题：

```bash
python scripts/validate_candidates_fast.py
```

补上 `PYTHONPATH` 后继续运行：

```bash
PYTHONPATH=. python scripts/validate_candidates_fast.py
```

**当前现象**：

脚本失败：

```text
ImportError: cannot import name 'StepContext' from 'app.schemas.workflow'
```

**原因定位**：

`StepContext` 当前定义在 `app/services/runner.py`，不在 `app/schemas/workflow.py`。脚本里的导入已经和当前代码结构不一致：

```python
from app.schemas.workflow import WorkflowInput, StepContext
```

**建议修复**：

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
