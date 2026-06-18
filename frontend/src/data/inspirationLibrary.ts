// Inspiration Library — curated starting points for new creators.
// 3 kinds: character (主角形象), style (画面风格), template (故事模板).
// Each item carries a `prefill` payload that is shallow-merged into the
// Studio workflow form when the user clicks "用此 X 创作".
//
// Visual covers use dark jewel-tone gradients with subtle gold accents
// so they read as "native to the dark-gold theme" rather than as bright
// sticker tiles. Icons are rendered with reduced opacity for the same
// reason — they're a recognition aid, not the focal point.
//
// Topic prefills embed character name + species + key visual traits
// directly in the prompt text. This is important: the backend's
// `structured_characters` payload only flows through in character voice
// mode, while topic flows through every mode. Putting character info in
// topic guarantees the story LLM (and downstream image prompts) will
// pick up and respect the character identity regardless of voice mode.

export type InspirationKind = 'character' | 'style' | 'template'

export interface InspirationItem {
  id: string
  kind: InspirationKind
  title: string
  subtitle: string
  description: string
  tags: string[]
  // Visual placeholder until real reference assets are curated.
  // Dark jewel-tone gradients tuned to the amber/champagne dark theme.
  gradient: string
  icon: string
  // Shallow-merged into workflowForm when the user applies this item.
  // Crucially, character info is duplicated into `topic` so it flows
  // through all voice modes (not just character mode).
  prefill: Record<string, unknown>
}

const CHARACTERS: InspirationItem[] = [
  {
    id: 'char-doudou-tadpole',
    kind: 'character',
    title: '豆豆 · 小蝌蚪',
    subtitle: '好奇心强的水边探险家',
    description:
      '一只总爱问"为什么"的小蝌蚪，喜欢沿着溪流寻找新奇事物。适合"好奇探险"类故事主角。',
    tags: ['动物主角', '探险', '水生'],
    gradient: 'linear-gradient(135deg, #0a1828 0%, #1c3454 55%, #050d1a 100%)',
    icon: '🐸',
    prefill: {
      topic:
        '讲一个温暖治愈的儿童故事。主角是豆豆，一只圆圆大眼睛、深色身体、戴着小红头巾的可爱小蝌蚪，住在一条清澈的小溪里。它好奇心强，最爱追着声音去寻找新事物。',
      characterStyle: 'animal',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '豆豆',
      primaryCharacterSpecies: '小蝌蚪',
      primaryCharacterVisualTraits:
        '深色圆润身体，圆圆的大眼睛，戴一条小红头巾，尾巴细长',
      primaryCharacterForbiddenTraits: '不要画成青蛙、不要长出腿、不要灰色',
    },
  },
  {
    id: 'char-mimi-bunny',
    kind: 'character',
    title: '米米 · 小白兔',
    subtitle: '温柔安静的森林小友',
    description:
      '一只白色长毛兔，性格温柔、善于倾听。适合"友谊相遇""睡前故事"类主题。',
    tags: ['动物主角', '温柔', '森林'],
    gradient: 'linear-gradient(135deg, #1e1608 0%, #3a2c18 55%, #0e0a04 100%)',
    icon: '🐰',
    prefill: {
      topic:
        '讲一个温暖治愈的儿童故事。主角是米米，一只蓬松白色长毛、粉色耳朵内侧、温柔安静的小兔子，住在一片宁静的森林里。它善于倾听，常常成为朋友们倾诉烦恼的对象。',
      characterStyle: 'animal',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '米米',
      primaryCharacterSpecies: '小白兔',
      primaryCharacterVisualTraits:
        '蓬松的白色长毛，粉色耳朵内侧，温柔的大眼睛，圆圆的脸',
      primaryCharacterForbiddenTraits: '不要灰色、不要红眼睛、不要短毛',
    },
  },
  {
    id: 'char-songsong-squirrel',
    kind: 'character',
    title: '松松 · 小松鼠',
    subtitle: '活泼好动的森林玩伴',
    description:
      '一只红棕色的小松鼠，毛茸茸的大尾巴，喜欢蹦跳和收集橡果。常与米米结伴出现。',
    tags: ['动物主角', '活泼', '森林'],
    gradient: 'linear-gradient(135deg, #1a1e0a 0%, #2e3818 55%, #0a1004 100%)',
    icon: '🐿️',
    prefill: {
      topic:
        '讲一个充满童趣的儿童故事。主角是松松，一只红棕色蓬松大尾巴、灵动黑眼睛的活泼小松鼠。它最喜欢在森林里蹦蹦跳跳、收集橡果，常常和好朋友米米一起冒险。',
      characterStyle: 'animal',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '松松',
      primaryCharacterSpecies: '小松鼠',
      primaryCharacterVisualTraits:
        '红棕色蓬松大尾巴，圆圆的脸蛋，灵动的黑眼睛，小巧灵活',
      primaryCharacterForbiddenTraits: '不要灰松鼠、尾巴不要细小、不要黑色',
    },
  },
  {
    id: 'char-xiaoshu-mouse',
    kind: 'character',
    title: '小鼠 · 月夜旅人',
    subtitle: '勇敢追梦的夜行小客',
    description:
      '一只小灰鼠，在月光下踏上寻找答案的旅程。适合"夜晚奇遇""勇气成长"类故事。',
    tags: ['动物主角', '夜景', '梦幻'],
    gradient: 'linear-gradient(135deg, #0e0e2a 0%, #2a2858 55%, #04041e 100%)',
    icon: '🐭',
    prefill: {
      topic:
        '讲一个充满奇遇感的儿童故事。主角是小鼠，一只柔和灰白毛色、明亮好奇眼睛的小灰鼠。在一个月圆之夜，它被一只发光的萤火虫引向森林深处，开启了一段奇妙的旅程。',
      characterStyle: 'animal',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '小鼠',
      primaryCharacterSpecies: '小灰鼠',
      primaryCharacterVisualTraits:
        '柔和的灰白毛色，明亮好奇的大眼睛，小巧的身形，圆润的耳朵',
      primaryCharacterForbiddenTraits: '不要黑色、不要尖锐的牙、不要病态瘦削',
    },
  },
]

const STYLES: InspirationItem[] = [
  {
    id: 'style-watercolor',
    kind: 'style',
    title: '水彩童话',
    subtitle: '柔和透明的童书插画感',
    description:
      '水彩晕染、柔光、半透明边缘——经典童书绘本质感。适合温柔治愈类的故事。',
    tags: ['watercolor', '柔光', '童书'],
    gradient: 'linear-gradient(135deg, #2e0e2a 0%, #4e1e44 55%, #1e081e 100%)',
    icon: '🎨',
    prefill: {
      visualStyle: 'watercolor',
      tone: 'warm',
    },
  },
  {
    id: 'style-cute-chibi',
    kind: 'style',
    title: '可爱绘本',
    subtitle: '圆润 chibi 卡通主角',
    description:
      '圆润的 chibi 比例、可爱的表情、鲜亮但不刺眼的色调。最常用的儿童故事画风。',
    tags: ['cute_chibi_anime', '卡通', '主流'],
    gradient: 'linear-gradient(135deg, #2e1a08 0%, #4e3018 55%, #1e1004 100%)',
    icon: '✨',
    prefill: {
      visualStyle: 'cute_chibi_anime',
      tone: 'warm',
    },
  },
  {
    id: 'style-starry-night',
    kind: 'style',
    title: '童话星空',
    subtitle: '梦幻夜景与流光氛围',
    description:
      '深蓝夜空、星轨、暖光月亮——适合睡前故事、夜晚冒险类主题。',
    tags: ['cute_chibi_anime', '夜景', '梦幻'],
    gradient: 'linear-gradient(135deg, #08102e 0%, #1e2858 55%, #04081e 100%)',
    icon: '🌙',
    prefill: {
      visualStyle: 'cute_chibi_anime',
      tone: 'warm',
    },
  },
  {
    id: 'style-cinematic',
    kind: 'style',
    title: '电影感叙事',
    subtitle: '景深、光影、有质感的镜头',
    description:
      '更高的画面叙事密度、电影级光影和景深——适合大场面、史诗类儿童故事。',
    tags: ['cinematic', '景深', '高质感'],
    gradient: 'linear-gradient(135deg, #1e1208 0%, #3a2818 55%, #14080a 100%)',
    icon: '🎬',
    prefill: {
      visualStyle: 'cinematic',
      tone: 'warm',
      qualityTier: 'cinematic',
    },
  },
]

const TEMPLATES: InspirationItem[] = [
  {
    id: 'tpl-curiosity-adventure',
    kind: 'template',
    title: '好奇探险',
    subtitle: '小动物发现新奇事物的探索之旅',
    description:
      '主角因为好奇心踏上一段小旅程，途中遇到新事物并最终带着收获回家。是绘本里最常见、最易共鸣的叙事模板。',
    tags: ['探险', '好奇心', '成长'],
    gradient: 'linear-gradient(135deg, #0a1e0a 0%, #1e3a1e 55%, #060e06 100%)',
    icon: '🌿',
    prefill: {
      topic:
        '讲一个温暖的儿童故事。一只小动物听到远处有奇怪的声音，决定沿着溪流去看个究竟。一路上它遇到了从未见过的花草和小伙伴，最后带着一颗小小的礼物回到家。',
      durationSec: 60,
    },
  },
  {
    id: 'tpl-friendship-meet',
    kind: 'template',
    title: '友谊相遇',
    subtitle: '两个不同的小动物相遇并成为朋友',
    description:
      '通过一次偶然相遇，性格不同的两个小动物从陌生到熟悉、最后建立友谊。适合教孩子社交与共情。',
    tags: ['友谊', '相遇', '共情'],
    gradient: 'linear-gradient(135deg, #2a1a08 0%, #4a3018 55%, #1a0e04 100%)',
    icon: '🤝',
    prefill: {
      topic:
        '讲一个关于友谊的儿童故事。一只温柔的小白兔和一只活泼的小松鼠在森林里第一次相遇，从最初的害羞到一起分享橡果，慢慢变成了最好的朋友。',
      durationSec: 60,
    },
  },
  {
    id: 'tpl-bedtime-cozy',
    kind: 'template',
    title: '睡前温馨',
    subtitle: '舒缓平静的入睡治愈故事',
    description:
      '节奏舒缓、情绪平稳、画面温暖。适合 1-2 分钟的睡前故事，结尾点到"该睡觉啦"。',
    tags: ['睡前', '治愈', '安宁'],
    gradient: 'linear-gradient(135deg, #0a1428 0%, #1e2e5a 55%, #040814 100%)',
    icon: '🌙',
    prefill: {
      topic:
        '讲一个节奏舒缓的睡前儿童故事。夜幕降临，小动物们各自回到温暖的家。月亮升起，星星眨眼，整片森林安静下来，小白兔依偎着妈妈轻轻闭上眼睛。',
      durationSec: 90,
      voiceStyle: 'warm_mother',
      narratorVoiceStyle: 'warm_mother',
    },
  },
  {
    id: 'tpl-moonlit-encounter',
    kind: 'template',
    title: '月夜奇遇',
    subtitle: '月光下的奇妙旅程',
    description:
      '月光下小动物踏上一段神秘的旅程，遇到不寻常的角色与场景。适合"勇气""想象力"类主题。',
    tags: ['夜景', '奇幻', '勇气'],
    gradient: 'linear-gradient(135deg, #0e082a 0%, #2a1e5e 55%, #04021e 100%)',
    icon: '✨',
    prefill: {
      topic:
        '讲一个充满奇幻感的儿童故事。一只小灰鼠在月圆之夜被一只发光的萤火虫领进了森林深处，遇到了一群从未见过的夜行小伙伴，度过了难忘的一晚。',
      durationSec: 60,
      visualStyle: 'cute_chibi_anime',
    },
  },
]

export const INSPIRATION_ITEMS: InspirationItem[] = [
  ...CHARACTERS,
  ...STYLES,
  ...TEMPLATES,
]

export const KIND_META: Record<InspirationKind, { label: string; eyebrow: string; description: string }> = {
  character: {
    label: '角色形象',
    eyebrow: 'CHARACTERS',
    description: '挑一个主角形象，绑定外貌设定，多场景出现保持一致。',
  },
  style: {
    label: '画面风格',
    eyebrow: 'VISUAL STYLES',
    description: '一键切换整片画风，故事氛围立刻变。',
  },
  template: {
    label: '故事模板',
    eyebrow: 'STORY TEMPLATES',
    description: '常用叙事骨架，省去"从零想"的时间。',
  },
}

// Storage key for the prefill handoff between this panel and the Studio
// form. Using sessionStorage instead of URL params keeps the handoff
// payload flexible (any shape) and avoids polluting the URL.
export const INSPIRATION_PREFILL_KEY = 'jinsie.inspirationPrefill.v1'
