#!/usr/bin/env node
/**
 * Acceptance: Voice Mode payload isolation (static)
 *
 * Run:
 *   node scripts/acceptance_voice_mode_payload.js
 */

const fs = require('fs')
const path = require('path')

function fail(message) {
  console.error(`\n[FAIL] ${message}\n`)
  process.exit(1)
}

function ok(message) {
  console.log(`[OK] ${message}`)
}

function readFileOrFail(p) {
  if (!fs.existsSync(p)) {
    fail(`File not found: ${p}`)
  }
  return fs.readFileSync(p, 'utf8')
}

function mustInclude(text, needle, hint) {
  if (!text.includes(needle)) {
    fail(
      `Missing required pattern: ${JSON.stringify(needle)}${
        hint ? `\nHint: ${hint}` : ''
      }`,
    )
  }
}

function mustNotInclude(text, needle, hint) {
  if (text.includes(needle)) {
    fail(
      `Unexpected pattern found: ${JSON.stringify(needle)}${
        hint ? `\nHint: ${hint}` : ''
      }`,
    )
  }
}

/**
 * Extract a JS/TS block by brace counting starting from a marker.
 */
function extractBraceBlock(text, marker) {
  const markerIndex = text.indexOf(marker)
  if (markerIndex === -1) return null

  const braceStart = text.indexOf('{', markerIndex)
  if (braceStart === -1) return null

  let depth = 0
  for (let i = braceStart; i < text.length; i++) {
    const ch = text[i]
    if (ch === '{') depth++
    else if (ch === '}') depth--

    if (depth === 0) {
      return text.slice(braceStart, i + 1)
    }
  }
  return null
}

function sliceBetween(text, startMarker, endMarker) {
  const start = text.indexOf(startMarker)
  if (start === -1) return null
  const end = text.indexOf(endMarker, start + startMarker.length)
  if (end === -1) return null
  return text.slice(start, end + endMarker.length)
}

function main() {
  const repoRoot = process.cwd()

  const appVuePath = path.join(repoRoot, 'frontend', 'src', 'App.vue')
  const runPanelPath = path.join(
    repoRoot,
    'frontend',
    'src',
    'components',
    'WorkflowRunPanel.vue',
  )

  const appVue = readFileOrFail(appVuePath)
  const runPanel = readFileOrFail(runPanelPath)

  console.log('\n== Acceptance: Voice Mode payload isolation ==\n')

  // ------------------------------------------------------------
  // App.vue payload invariants
  // ------------------------------------------------------------

  mustInclude(
    appVue,
    'const inputPayload: Record<string, unknown> = {',
    'App.vue should assemble a base inputPayload and then conditionally add mode-specific fields.',
  )
  ok('App.vue: base inputPayload exists')

  mustInclude(
    appVue,
    "if (form.voiceMode === 'multi')",
    'Expected a multi-mode conditional block.',
  )
  mustInclude(
    appVue,
    'inputPayload.speaker_profiles = {',
    'Expected speaker_profiles to be assigned via inputPayload in multi-mode block.',
  )
  ok('App.vue: multi-mode speaker_profiles block exists')

  mustInclude(
    appVue,
    "if (form.voiceMode === 'character')",
    'Expected a character-mode conditional block.',
  )
  mustInclude(
    appVue,
    'inputPayload.character_speaker_profiles = {',
    'Expected character_speaker_profiles to be assigned in character-mode block.',
  )
  ok('App.vue: character-mode character_speaker_profiles block exists')

  mustNotInclude(
    appVue,
    "|| 'rabbit'",
    "Avoid hardcoding default species like 'rabbit' in base payload; it causes non-character modes to carry role bias.",
  )
  mustNotInclude(
    appVue,
    "|| 'turtle'",
    "Avoid hardcoding default species like 'turtle' in base payload; it causes non-character modes to carry role bias.",
  )
  ok('App.vue: no hardcoded default species injection found')

  // ✅ Correct mutual exclusivity check:
  // In character-mode block, we MUST NOT assign inputPayload.speaker_profiles (multi-mode only).
  // Note: 'character_speaker_profiles' contains 'speaker_profiles' as a substring, so we must match the exact assignment.
  const characterIfMarker = "if (form.voiceMode === 'character')"
  const characterBlock = extractBraceBlock(appVue, characterIfMarker)
  if (!characterBlock) {
    fail(
      "Could not extract character-mode brace block in App.vue. Marker or braces may have changed; update acceptance script.",
    )
  }

  const speakerProfilesAssignRe = /inputPayload\.speaker_profiles\s*=\s*\{/
  if (speakerProfilesAssignRe.test(characterBlock)) {
    fail(
      "App.vue: inputPayload.speaker_profiles is assigned inside character-mode block. Expected mutual exclusivity: character uses character_speaker_profiles only.",
    )
  }
  ok('App.vue: character-mode block does not assign inputPayload.speaker_profiles')

  mustInclude(
    characterBlock,
    'inputPayload.structured_characters_enabled = enableStructuredCharacters',
    'Expected structured characters toggle to be wired in character mode.',
  )
  ok('App.vue: structured_characters_enabled wired in character mode')

  // ------------------------------------------------------------
  // WorkflowRunPanel.vue mode switching invariants
  // ------------------------------------------------------------

  mustInclude(
    runPanel,
    'function updateVoiceMode(value: string)',
    'Expected a dedicated updateVoiceMode to reset stale fields when switching modes.',
  )
  ok('WorkflowRunPanel.vue: updateVoiceMode exists')

  const singleBlock = sliceBetween(runPanel, "if (value === 'single')", 'return')
  if (!singleBlock) {
    fail(
      "Could not locate single-mode updateVoiceMode slice in WorkflowRunPanel.vue. Update markers in acceptance script.",
    )
  }
  mustInclude(singleBlock, "motherVoiceStyle: ''", 'Single mode should clear motherVoiceStyle')
  mustInclude(singleBlock, "childVoiceStyle: ''", 'Single mode should clear childVoiceStyle')
  mustInclude(
    singleBlock,
    'structuredCharactersEnabled: false',
    'Single mode should disable structured characters',
  )
  ok('WorkflowRunPanel.vue: single-mode clears stale fields')

  const multiBlock = sliceBetween(runPanel, "if (value === 'multi')", 'return')
  if (!multiBlock) {
    fail(
      "Could not locate multi-mode updateVoiceMode slice in WorkflowRunPanel.vue. Update markers in acceptance script.",
    )
  }
  mustInclude(
    multiBlock,
    'structuredCharactersEnabled: false',
    'Multi mode should disable structured characters',
  )
  ok('WorkflowRunPanel.vue: multi-mode disables structured characters')

  mustInclude(
    runPanel,
    '@change="updateVoiceMode(($event.target as HTMLSelectElement).value)"',
    'Voice Mode select should route through updateVoiceMode to ensure stale fields are reset.',
  )
  ok('WorkflowRunPanel.vue: Voice Mode select uses updateVoiceMode')

  console.log('\n✅ All acceptance checks passed.\n')
}

main()