// Inspiration Library — curated starting points for new creators.
// 3 kinds: character (主角形象), style (画面风格), template (故事模板).
//
// Each item is a "prefill engine entry point": a single click that maps
// to 4-8 form fields the user would otherwise fill manually. The card's
// hero content is the human-readable preview of what the click will do,
// not a visual cover — this is intentional. Image-based covers were
// removed because (a) we can't currently lock character identity at the
// generation layer (Kolors is text-to-image only, no reference-image
// support at the integrated tier), so promising "this exact character"
// via a thumbnail would over-sell. The card now sells the actual value:
// "click and your form is configured."
//
// Character / style items duplicate identity into `topic` (the only
// payload field that flows in every voice mode) so the story LLM and
// downstream image prompts can pick up the character anchor even
// without structured_characters.

// `package` is the hero kind — a one-click *complete* configuration that
// fills all creation fields (topic / audience / tone / visual / character
// / voice mode + voice slots / duration / quality / structured-character
// fields). Character / style / template kinds are partial-prefill cards
// (4-8 fields each) used combinatorially. A package is *not* user-
// editable in v1 — the point is "3 秒从零到生成"; once the user starts
// editing, they're back to the normal form. They can still override
// individual fields after applying.
//
// Packages intentionally do NOT touch 4 preference fields and 5 system
// fields:
//   prefs:  renderMode, audioEnabled, voiceoverEnabled, subtitleEnabled
//   system: sessionId, language, videoProvider, outputMode
// These are user workflow habits or technical defaults — packages make
// creative decisions, not habit decisions.
export type InspirationKind = 'package' | 'character' | 'style' | 'template'

export interface InspirationItem {
  id: string
  kind: InspirationKind
  title: string
  subtitle: string
  description: string
  tags: string[]
  /** Tiny corner accent icon — emoji or short string. Decoration only. */
  icon: string
  /**
   * Human-readable preview of the click's effect. Hero content of the
   * card. Curated per item so we can translate machine keys
   * (cute_chibi_anime) into product labels (可爱绘本) and condense long
   * topic seeds into a card-friendly summary.
   */
  preview: Array<{ label: string; value: string }>
  /**
   * Shallow-merged into workflowForm when the user applies this item.
   */
  prefill: Record<string, unknown>
}

const PACKAGES: InspirationItem[] = [
  {
    id: 'pkg-bedtime-bunny',
    kind: 'package',
    title: '温馨睡前 · 小白兔的森林夜',
    subtitle: '舒缓睡前故事 · 水彩童话 · 故事妈妈旁白',
    description:
      '夜幕降临，米米回到森林家中，月光、星星与温柔的母亲声陪伴入睡。水彩童话画风、单人旁白、60 秒短篇——最经典的睡前组合。',
    tags: ['睡前', '温馨', '单人旁白', '60s'],
    icon: '🌙',
    preview: [
      { label: '故事种子', value: '小白兔米米在森林家中入睡的夜晚' },
      { label: '画面风格', value: '水彩童话 · 温暖治愈' },
      { label: '配音', value: '单人旁白 · 故事妈妈' },
      { label: '时长 / 画质', value: '60 秒 · 标准' },
    ],
    prefill: {
      topic:
        '讲一个节奏舒缓的睡前儿童故事。主角是米米，一只蓬松白色长毛、粉色耳朵内侧的温柔小白兔。夜幕降临，米米和森林里的朋友们道别回家，月亮升起，星星眨眼，妈妈唱起轻轻的歌，米米依偎着妈妈安然入睡。',
      audience: 'children',
      tone: 'bedtime',
      visualStyle: 'watercolor',
      characterStyle: 'animal',
      voiceMode: 'single',
      voiceStyle: 'warm_female',
      narratorVoiceStyle: 'warm_mother',
      motherVoiceStyle: '',
      childVoiceStyle: '',
      durationSec: 60,
      qualityTier: 'quality',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '米米',
      primaryCharacterSpecies: '小白兔',
      primaryCharacterVisualTraits:
        '蓬松的白色长毛，粉色耳朵内侧，温柔的大眼睛，圆圆的脸',
      primaryCharacterForbiddenTraits: '不要灰色、不要红眼睛、不要短毛',
      secondaryCharacterDisplayName: '',
      secondaryCharacterSpecies: '',
      secondaryCharacterVisualTraits: '',
      secondaryCharacterForbiddenTraits: '',
    },
  },
  {
    id: 'pkg-curious-seal',
    kind: 'package',
    title: '好奇探险 · 海边小海豹',
    subtitle: '可爱绘本 · 温暖单人旁白 · 60 秒',
    description:
      '波波沿着浪线发现新事物，遇到陌生海洋朋友，带回一颗小礼物。可爱绘本画风，温柔女声旁白——最易共鸣的童趣探险。',
    tags: ['探险', '童趣', '动物', '60s'],
    icon: '🦭',
    preview: [
      { label: '故事种子', value: '小海豹波波沿浪线探险，发现新朋友' },
      { label: '画面风格', value: '可爱绘本 · 温暖治愈' },
      { label: '配音', value: '单人旁白 · 温柔女声' },
      { label: '时长 / 画质', value: '60 秒 · 标准' },
    ],
    prefill: {
      topic:
        '讲一个充满童趣的儿童探险故事。主角是波波，一只圆圆胖胖、银灰色光滑皮肤、圆圆大眼睛的可爱小海豹。它好奇心强，沿着海岸线追逐浪花和阳光，途中遇到了一只从未见过的小螃蟹，两个小家伙一起度过了奇妙的一天，最后波波带着小贝壳作为纪念回到礁石间的家。',
      audience: 'children',
      tone: 'warm',
      visualStyle: 'cute_chibi_anime',
      characterStyle: 'animal',
      voiceMode: 'single',
      voiceStyle: 'warm_female',
      narratorVoiceStyle: 'warm_female',
      motherVoiceStyle: '',
      childVoiceStyle: '',
      durationSec: 60,
      qualityTier: 'quality',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '波波',
      primaryCharacterSpecies: '小海豹',
      primaryCharacterVisualTraits:
        '银灰色光滑皮肤，圆圆胖胖的身形，圆圆的大眼睛，短小可爱的鳍',
      primaryCharacterForbiddenTraits: '不要尖牙、不要瘦削、不要黑色',
      secondaryCharacterDisplayName: '',
      secondaryCharacterSpecies: '',
      secondaryCharacterVisualTraits: '',
      secondaryCharacterForbiddenTraits: '',
    },
  },
  {
    id: 'pkg-friendship-duo',
    kind: 'package',
    title: '友谊双角色 · 米米与松松',
    subtitle: '角色配音 · 双主角对话 · 120 秒',
    description:
      '温柔小白兔与活泼小松鼠在森林相遇，一起分享橡果、躲过雨天、成为挚友。角色配音模式（主角+配角+旁白三声），最能体现配音差异化的演示。',
    tags: ['友谊', '双角色', '角色配音', '120s'],
    icon: '🤝',
    preview: [
      { label: '故事种子', value: '小白兔遇上小松鼠，从害羞到挚友' },
      { label: '画面风格', value: '可爱绘本 · 温暖治愈' },
      { label: '配音', value: '角色配音 · 三种声线' },
      { label: '时长 / 画质', value: '120 秒 · 标准' },
    ],
    prefill: {
      topic:
        '讲一个关于友谊的儿童故事。一只温柔的小白兔米米和一只活泼的小松鼠松松在森林里第一次相遇。米米性格安静喜欢倾听，松松性格活泼爱蹦跳。它们从最初的害羞试探，到一起分享橡果、躲过一场小雨，最后慢慢变成了形影不离的好朋友。',
      audience: 'children',
      tone: 'warm',
      visualStyle: 'cute_chibi_anime',
      characterStyle: 'animal',
      voiceMode: 'character',
      voiceStyle: 'warm_female',
      narratorVoiceStyle: 'warm_female',
      motherVoiceStyle: 'warm_female',
      childVoiceStyle: 'gentle_child',
      durationSec: 120,
      qualityTier: 'quality',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '米米',
      primaryCharacterSpecies: '小白兔',
      primaryCharacterVisualTraits:
        '蓬松的白色长毛，粉色耳朵内侧，温柔的大眼睛，圆圆的脸',
      primaryCharacterForbiddenTraits: '不要灰色、不要红眼睛、不要短毛',
      secondaryCharacterDisplayName: '松松',
      secondaryCharacterSpecies: '小松鼠',
      secondaryCharacterVisualTraits:
        '红棕色蓬松大尾巴，圆圆的脸蛋，灵动的黑眼睛，小巧灵活',
      secondaryCharacterForbiddenTraits: '不要灰松鼠、尾巴不要细小、不要黑色',
    },
  },
  {
    id: 'pkg-family-cozy',
    kind: 'package',
    title: '亲子共读 · 森林家庭日',
    subtitle: '亲子轮流配音 · 水彩童话 · 120 秒',
    description:
      '兔妈妈与小兔米米的一日相处——清晨采花、午后野餐、傍晚回家。亲子轮流配音模式（妈妈声 + 孩子声），还原睡前故事会的语境。',
    tags: ['亲子', '日常', '亲子轮流', '120s'],
    icon: '🐰',
    preview: [
      { label: '故事种子', value: '兔妈妈与小兔米米的森林家庭日' },
      { label: '画面风格', value: '水彩童话 · 温暖治愈' },
      { label: '配音', value: '亲子轮流 · 妈妈声 + 孩子声' },
      { label: '时长 / 画质', value: '120 秒 · 标准' },
    ],
    prefill: {
      topic:
        '讲一个温馨的亲子日常故事。兔妈妈带着小兔米米在森林里度过一天——清晨一起去溪边采花，午后在大树下野餐分享胡萝卜蛋糕，傍晚牵着手走回家，途中聊起今天最开心的事。',
      audience: 'family',
      tone: 'warm',
      visualStyle: 'watercolor',
      characterStyle: 'animal',
      voiceMode: 'multi',
      voiceStyle: 'warm_female',
      narratorVoiceStyle: 'warm_female',
      motherVoiceStyle: 'warm_mother',
      childVoiceStyle: 'gentle_child',
      durationSec: 120,
      qualityTier: 'quality',
      structuredCharactersEnabled: false,
      primaryCharacterDisplayName: '',
      primaryCharacterSpecies: '',
      primaryCharacterVisualTraits: '',
      primaryCharacterForbiddenTraits: '',
      secondaryCharacterDisplayName: '',
      secondaryCharacterSpecies: '',
      secondaryCharacterVisualTraits: '',
      secondaryCharacterForbiddenTraits: '',
    },
  },
  {
    id: 'pkg-fantasy-cinematic',
    kind: 'package',
    title: '奇幻冒险 · 月夜萤火之旅',
    subtitle: '电影感画面 · 180 秒长篇 · Cinematic 画质',
    description:
      '月圆之夜，小灰鼠跟随发光的萤火虫进入森林深处，遇到夜行小伙伴，度过一晚奇遇。电影感画风、长篇时长、cinematic 画质——展示画面叙事密度的高配套餐。',
    tags: ['奇幻', '冒险', '电影感', 'cinematic', '180s'],
    icon: '✨',
    preview: [
      { label: '故事种子', value: '小灰鼠在月夜跟随萤火虫的奇遇之旅' },
      { label: '画面风格', value: '电影感 · 温暖治愈' },
      { label: '配音', value: '单人旁白 · 故事旁白声' },
      { label: '时长 / 画质', value: '180 秒 · Cinematic' },
    ],
    prefill: {
      topic:
        '讲一个充满奇幻感的儿童冒险故事。一只柔和灰白毛色、明亮好奇眼睛的小灰鼠在月圆之夜被一只发光的萤火虫领进了森林深处，沿途月光洒下，溪水反着银光。它先后遇到了戴着橡果帽的夜行小蚁、披着叶子披风的小刺猬，加入了它们的夜间漫步，最终在天亮前被萤火虫送回家门口，留下了一晚难忘的回忆。',
      audience: 'children',
      tone: 'adventure',
      visualStyle: 'cinematic',
      characterStyle: 'animal',
      voiceMode: 'single',
      voiceStyle: 'narrator_female',
      narratorVoiceStyle: 'narrator_female',
      motherVoiceStyle: '',
      childVoiceStyle: '',
      durationSec: 180,
      qualityTier: 'cinematic',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '小鼠',
      primaryCharacterSpecies: '小灰鼠',
      primaryCharacterVisualTraits:
        '柔和的灰白毛色，明亮好奇的大眼睛，小巧的身形，圆润的耳朵',
      primaryCharacterForbiddenTraits: '不要黑色、不要尖锐的牙、不要病态瘦削',
      secondaryCharacterDisplayName: '',
      secondaryCharacterSpecies: '',
      secondaryCharacterVisualTraits: '',
      secondaryCharacterForbiddenTraits: '',
    },
  },
  {
    id: 'pkg-chinese-folk',
    kind: 'package',
    title: '国风童话 · 竹林小白兔',
    subtitle: '国风插画 · 童趣启蒙 · 60 秒',
    description:
      '小白兔在竹林里遇见会说话的兰花，听它讲季节更替与花开花落的小道理。国风插画画风、科普启蒙基调——展示中式童话美学的独家套餐。',
    tags: ['国风', '科普启蒙', '童趣', '60s'],
    icon: '🎋',
    preview: [
      { label: '故事种子', value: '小白兔与竹林兰花，认识四季' },
      { label: '画面风格', value: '国风插画 · 温暖治愈' },
      { label: '配音', value: '单人旁白 · 温柔女声' },
      { label: '时长 / 画质', value: '60 秒 · 标准' },
    ],
    prefill: {
      topic:
        '讲一个充满中式童趣的儿童启蒙故事。一只蓬松白色长毛的小白兔米米在江南竹林里散步，遇到一朵会说话的兰花。兰花告诉它春天的雨、夏天的萤火、秋天的桂香、冬天的雪——四季在竹林里轮转的小道理。',
      audience: 'children',
      tone: 'educational',
      visualStyle: 'chinese_illustration',
      characterStyle: 'animal',
      voiceMode: 'single',
      voiceStyle: 'warm_female',
      narratorVoiceStyle: 'warm_female',
      motherVoiceStyle: '',
      childVoiceStyle: '',
      durationSec: 60,
      qualityTier: 'quality',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '米米',
      primaryCharacterSpecies: '小白兔',
      primaryCharacterVisualTraits:
        '蓬松的白色长毛，粉色耳朵内侧，温柔的大眼睛，圆圆的脸',
      primaryCharacterForbiddenTraits: '不要灰色、不要红眼睛、不要短毛',
      secondaryCharacterDisplayName: '',
      secondaryCharacterSpecies: '',
      secondaryCharacterVisualTraits: '',
      secondaryCharacterForbiddenTraits: '',
    },
  },
]

const CHARACTERS: InspirationItem[] = [
  {
    id: 'char-bobo-seal',
    kind: 'character',
    title: '波波 · 小海豹',
    subtitle: '好奇心强的海边探险家',
    description:
      '一只圆圆胖胖的小海豹，住在海边的礁石间，最爱沿着浪线发现新事物。适合"好奇探险""勇气成长"类故事主角。',
    tags: ['动物主角', '探险', '水生'],
    icon: '🦭',
    preview: [
      { label: '主角', value: '波波 · 小海豹' },
      { label: '外观', value: '银灰光滑皮、圆圆大眼' },
      { label: '故事方向', value: '好奇心驱动的小探险' },
    ],
    prefill: {
      topic:
        '讲一个温暖治愈的儿童故事。主角是波波，一只圆圆胖胖、银灰色光滑皮肤、圆圆大眼睛的可爱小海豹，住在海边的礁石间。它好奇心强，最爱沿着浪线去发现新事物。',
      characterStyle: 'animal',
      structuredCharactersEnabled: true,
      primaryCharacterDisplayName: '波波',
      primaryCharacterSpecies: '小海豹',
      primaryCharacterVisualTraits:
        '银灰色光滑皮肤，圆圆胖胖的身形，圆圆的大眼睛，短小可爱的鳍',
      primaryCharacterForbiddenTraits: '不要尖牙、不要瘦削、不要黑色',
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
    icon: '🐰',
    preview: [
      { label: '主角', value: '米米 · 小白兔' },
      { label: '外观', value: '蓬松白长毛、粉色耳内' },
      { label: '故事方向', value: '友谊、相遇、治愈' },
    ],
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
    icon: '🐿️',
    preview: [
      { label: '主角', value: '松松 · 小松鼠' },
      { label: '外观', value: '红棕大尾巴、灵动黑眼' },
      { label: '故事方向', value: '童趣、玩耍、冒险' },
    ],
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
    icon: '🐭',
    preview: [
      { label: '主角', value: '小鼠 · 小灰鼠' },
      { label: '外观', value: '柔灰白毛、明亮好奇眼' },
      { label: '故事方向', value: '夜晚奇遇、勇气成长' },
    ],
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
    icon: '🎨',
    preview: [
      { label: '画面风格', value: '水彩童话' },
      { label: '色调', value: '温暖治愈' },
    ],
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
    icon: '✨',
    preview: [
      { label: '画面风格', value: '可爱绘本' },
      { label: '色调', value: '温暖治愈' },
    ],
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
    icon: '🌙',
    preview: [
      { label: '画面风格', value: '可爱绘本（夜景调）' },
      { label: '色调', value: '温暖治愈' },
    ],
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
    icon: '🎬',
    preview: [
      { label: '画面风格', value: '电影感' },
      { label: '画质档位', value: 'Cinematic（更慢更精）' },
      { label: '色调', value: '温暖治愈' },
    ],
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
    icon: '🌿',
    preview: [
      { label: '故事种子', value: '小动物追着声音去探险，带着收获回家' },
      { label: '时长', value: '60 秒' },
    ],
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
    icon: '🤝',
    preview: [
      { label: '故事种子', value: '温柔小白兔遇上活泼小松鼠，从害羞到挚友' },
      { label: '时长', value: '60 秒' },
    ],
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
    icon: '🌙',
    preview: [
      { label: '故事种子', value: '夜幕降临，小动物各自回家，星星眨眼' },
      { label: '时长', value: '60 秒' },
      { label: '旁白配音', value: '故事妈妈' },
    ],
    prefill: {
      topic:
        '讲一个节奏舒缓的睡前儿童故事。夜幕降临，小动物们各自回到温暖的家。月亮升起，星星眨眼，整片森林安静下来，小白兔依偎着妈妈轻轻闭上眼睛。',
      durationSec: 60,
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
    icon: '✨',
    preview: [
      { label: '故事种子', value: '小灰鼠跟随萤火虫，月夜进入森林深处' },
      { label: '时长', value: '60 秒' },
      { label: '画面风格', value: '可爱绘本' },
    ],
    prefill: {
      topic:
        '讲一个充满奇幻感的儿童故事。一只小灰鼠在月圆之夜被一只发光的萤火虫领进了森林深处，遇到了一群从未见过的夜行小伙伴，度过了难忘的一晚。',
      durationSec: 60,
      visualStyle: 'cute_chibi_anime',
    },
  },
]

// Packages first so they render as the hero section on the page.
export const INSPIRATION_ITEMS: InspirationItem[] = [
  ...PACKAGES,
  ...CHARACTERS,
  ...STYLES,
  ...TEMPLATES,
]

export const KIND_META: Record<InspirationKind, { label: string; eyebrow: string; description: string; icon: string }> = {
  package: {
    label: '完整套餐',
    eyebrow: 'STORY PACKAGES',
    description: '一键就绪——故事种子、画面风格、角色配音、时长画质全部填好，点了就能生成。',
    icon: '◉',
  },
  character: {
    label: '角色形象',
    eyebrow: 'CHARACTERS',
    description: '挑一个主角形象，故事和外观一键就位。',
    icon: '◆',
  },
  style: {
    label: '画面风格',
    eyebrow: 'VISUAL STYLES',
    description: '一键切换整片画风，故事氛围立刻变。',
    icon: '✦',
  },
  template: {
    label: '故事模板',
    eyebrow: 'STORY TEMPLATES',
    description: '常用叙事骨架，省去"从零想"的时间。',
    icon: '❖',
  },
}
