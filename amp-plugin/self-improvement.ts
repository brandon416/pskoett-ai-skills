import type { PluginAPI } from '@ampcode/plugin'

export const description = 'Adds a per-turn reminder to capture useful learnings with the self-improvement skill.'

export default function (amp: PluginAPI) {
  amp.on('agent.start', () => ({
    message: {
      content: `<self-improvement-reminder>
Before finishing this turn, evaluate relevant corrections, knowledge gaps,
missing capabilities, and reusable discoveries. Load self-improvement when
available and follow its capture guidance. Use self-healing for active recovery
when available; do not duplicate HEAL entries. Skip logging when there is no
useful learning, keep secrets out, and respect approval requirements for
promotion or skill changes. Do not install missing skills automatically.
</self-improvement-reminder>`,
      display: false,
    },
  }))
}
