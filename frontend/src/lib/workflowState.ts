export type SceneGenerationState =
  | 'pending'
  | 'queued'
  | 'generating'
  | 'confirming'
  | 'ready'
  | 'failed'

export type ImageGenerationSummary = {
  totalCount: number
  readyCount: number
  queuedCount: number
  generatingCount: number
  confirmingCount: number
  failedCount: number
  pendingCount: number
  currentScene: string
  overallState: 'idle' | 'generating' | 'confirming' | 'ready' | 'partial_failure' | 'failed'
}

export function summarizeImageGeneration(
  scenes: Array<{ scene_id: string; state: SceneGenerationState }>,
): ImageGenerationSummary {
  const count = (state: SceneGenerationState) =>
    scenes.filter((scene) => scene.state === state).length
  const summary: ImageGenerationSummary = {
    totalCount: scenes.length,
    readyCount: count('ready'),
    queuedCount: count('queued'),
    generatingCount: count('generating'),
    confirmingCount: count('confirming'),
    failedCount: count('failed'),
    pendingCount: count('pending'),
    currentScene:
      scenes.find((scene) =>
        ['generating', 'queued', 'confirming'].includes(scene.state),
      )?.scene_id || '',
    overallState: 'idle',
  }

  if (summary.queuedCount + summary.generatingCount > 0) {
    summary.overallState = 'generating'
  } else if (summary.confirmingCount > 0) {
    summary.overallState = 'confirming'
  } else if (summary.totalCount > 0 && summary.readyCount === summary.totalCount) {
    summary.overallState = 'ready'
  } else if (summary.failedCount > 0) {
    summary.overallState = summary.readyCount > 0 ? 'partial_failure' : 'failed'
  }
  return summary
}

export type WorkflowProgressSummary = {
  overallPercent: number | null
  currentStage: string
  stageLabel: string
  stagePercent: number | null
  indeterminate: boolean
  completed: boolean
}

export function summarizeWorkflowProgress(input: {
  completed: boolean
  rendering: boolean
  awaitingRender: boolean
  workflowPercent: number | null
  images: ImageGenerationSummary
}): WorkflowProgressSummary {
  if (input.completed) {
    return {
      overallPercent: 100,
      currentStage: 'completed',
      stageLabel: '已生成',
      stagePercent: 100,
      indeterminate: false,
      completed: true,
    }
  }
  if (input.rendering) {
    return {
      overallPercent: null,
      currentStage: 'video_render',
      stageLabel: '正在合成视频（音频、字幕、画面拼接中）',
      stagePercent: null,
      indeterminate: true,
      completed: false,
    }
  }
  if (input.awaitingRender) {
    return {
      overallPercent: 85,
      currentStage: 'awaiting_render',
      stageLabel: '候选图已就绪，等待你点击「生成视频」',
      stagePercent: null,
      indeterminate: false,
      completed: false,
    }
  }
  if (input.images.totalCount > 0 && input.images.overallState !== 'idle') {
    const hasRunning = input.images.generatingCount > 0
    const hasQueued = input.images.queuedCount > 0
    const indeterminate = input.images.readyCount === 0 && hasRunning
    const percent = indeterminate
      ? null
      : Math.floor(
          (input.images.readyCount / input.images.totalCount) * 100,
        )
    const completedLabel = `已完成 ${input.images.readyCount} / ${input.images.totalCount}`
    const label =
      input.images.overallState === 'confirming'
        ? `正在确认生成结果 · ${completedLabel}`
        : input.images.overallState === 'ready'
          ? `候选图生成完成 · ${completedLabel}`
          : input.images.failedCount > 0 &&
              !hasQueued &&
              !hasRunning
            ? `候选图生成完成，${input.images.failedCount} 个场景待处理`
            : hasRunning
              ? `正在生成场景 ${Math.min(
                  input.images.readyCount + 1,
                  input.images.totalCount,
                )} / ${input.images.totalCount} · ${completedLabel}`
              : hasQueued
                ? `任务已提交，等待开始 · ${completedLabel}`
                : completedLabel
    return {
      overallPercent: percent,
      currentStage: 'image_generation',
      stageLabel: label,
      stagePercent: percent,
      indeterminate,
      completed: false,
    }
  }
  return {
    overallPercent: input.workflowPercent,
    currentStage: 'workflow',
    stageLabel: '',
    stagePercent: input.workflowPercent,
    indeterminate: input.workflowPercent == null,
    completed: false,
  }
}
