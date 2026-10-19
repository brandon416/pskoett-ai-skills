import { afterAll, expect, test } from 'bun:test'
import { spawnSync } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { AgentStartEvent, AgentStartResult, PluginAPI, PluginEventContext } from '@ampcode/plugin'
import plugin from './index'

const cache = await mkdtemp(join(tmpdir(), 'thread-relevance-test-'))
const previousCache = process.env.XDG_CACHE_HOME
process.env.XDG_CACHE_HOME = cache
afterAll(async () => {
  if (previousCache === undefined) delete process.env.XDG_CACHE_HOME
  else process.env.XDG_CACHE_HOME = previousCache
  await rm(cache, { recursive: true, force: true })
})
let sequence = 0
const id = (n: number) => `T-00000000-0000-0000-0000-${String(n).padStart(12, '0')}` as const
type Handler = (event: AgentStartEvent, ctx: PluginEventContext<'agent.start'>) => Promise<AgentStartResult | void>

function fixture(options: {
  audience?: string; candidateAudience?: string; messageCount?: number; messageId?: number;
  executor?: string; probability?: number; shortlistProbability?: number; category?: string; fail?: string;
  changeAudience?: boolean; protocolID?: boolean; remote?: string; foreign?: boolean;
  sourceWorkspace?: string; groups?: string[]; sourceGroups?: string[]; failedCandidate?: 'large' | 'unavailable' | 'slow';
  hiddenContext?: boolean; oldEvidence?: boolean; task?: string; manyCandidates?: boolean; childCandidate?: boolean;
  privateCandidates?: number; candidateTitle?: string | null;
} = {}) {
  const currentID = id(++sequence)
  const candidates = (options.manyCandidates ? Array.from({ length: 25 }, (_, i) => 101 + i) : [101, 102, 103, 104]).map((n, i) => ({
    id: id(n), title: `JWT expiry finding ${i}`, matchedSearchText: `Evidence ${i}. Never inject this excerpt.`, creatorUserID: 'owner',
  }))
  const queries: string[] = []
  const reads: string[] = []
  const modelStates: unknown[] = []
  const logs: unknown[] = []
  const shellOutput: string[] = []
  let statusReads = 0
  const current = () => ({
    metadata: { threadID: currentID, visibility: options.audience ?? 'private', viewerOwnsThread: true },
    preview: { messageCount: options.messageCount ?? 2 },
  })
  const tools = {
    async call(name: string, input: Record<string, unknown>) {
      if (options.fail === 'tools') throw new Error('private provider detail')
      if (name === 'amp.get_thread_status') {
        if (input.thread === currentID) return current()
        throw new Error('Use the exported transcript for candidate evidence')
      }
      if (name !== 'amp.find_thread') throw new Error(`Unexpected tool ${name}`)
      const query = String(input.query)
      queries.push(query)
      if (options.fail === 'schema') return { nonsense: true }
      if (options.oldEvidence && !query.endsWith('"ownership"')) return { threads: [] }
      // Repeated candidates, the current thread, a child, and an unrelated owner exercise filtering.
      return { threads: [...candidates, { ...candidates[0], id: currentID },
        { ...candidates[0], id: id(105), origin: { sourceThreadID: currentID } },
        { ...candidates[0], id: id(106), creatorUserID: 'someone-else' }] }
    },
  }
  const ai = {
    async decide(request: { model: string; state: unknown; questions: Record<string, unknown> }) {
      if (options.fail === 'jev') throw new Error('private provider detail')
      expect(request.model).toBe('typesafe/jev')
      expect(Object.keys(request.questions).length).toBeLessThanOrEqual(20)
      if (request.questions.search) {
        const { searches } = request.state as { searches: string[][] }
        expect(searches.length).toBeGreaterThanOrEqual(2)
        expect(searches.length).toBeLessThanOrEqual(20)
        const preferred = options.oldEvidence ? ['ownership'] : ['login.ts', 'auth.ts', 'jwt']
        const probabilities = Object.fromEntries(searches.map((terms, i) => {
          const index = preferred.indexOf(terms.join(' '))
          return [`q${i}`, index < 0 ? 0 : 0.9 - index * 0.1]
        }))
        return { model: 'jev-test', answers: Object.fromEntries(['search', 'focus'].map(key =>
          [key, { type: 'choice', choice: 'q0', probabilities, confidence: 1 }])) }
      }
      modelStates.push(request.state)
      const excerpts = JSON.stringify(request.state)
      const choice = options.oldEvidence && modelStates.length > 1 && !excerpts.includes('Transfer requires tenant consent.')
        ? 'unrelated' : options.category ?? 'useful'
      const probability = (modelStates.length === 1 ? options.shortlistProbability : undefined) ?? options.probability ?? 0.9
      return { model: 'jev-test', answers: Object.fromEntries(Object.keys(request.questions).map((key, i) => [key, {
        type: 'choice', choice, probabilities: { useful: 0, unrelated: 0, [choice]: probability - i * 0.01 }, confidence: 1,
      }])) }
    },
  }
  let handler: Handler
  const amp = {
    on: (_name: string, callback: Handler) => { handler = callback },
    system: { user: { id: 'owner' }, ampURL: new URL('https://amp.example'), workspaceRoot: options.remote ? 'file:///repo' : null },
    helpers: { filePathFromURI: () => '/repo' },
  } as unknown as PluginAPI
  plugin(amp)
  const task = options.task ?? (options.oldEvidence ? 'Fix ledger ownership checks after billing workspace transfers.' : 'Fix JWT authentication expiry in auth.ts')
  const hidden = 'hidden-routing-instructions self-improvement-reminder T-11111111-2222-3333-4444-555555555555'
  const event = { thread: { id: currentID }, id: options.protocolID ? 'M-first' : 1,
    message: options.hiddenContext ? `${task}\n${hidden}\nCheck login.ts too.` : task }
  const ctx = { tools, ai, logger: { log: (...args: unknown[]) => logs.push(args) },
    $: async (strings: TemplateStringsArray, ...values: unknown[]) => {
      if (strings[0].startsWith('git')) return { exitCode: 0, stdout: options.remote, stderr: '' }
      if (options.fail === 'export') return { exitCode: 1, stdout: '', stderr: 'private provider detail' }
      if (String(values[0]).includes('threads search')) {
        queries.push(String(values[1]))
        const input = options.fail === 'schema' ? 'not JSON: private provider detail' : JSON.stringify([
          ...candidates, { ...candidates[0], id: currentID },
        ])
        const result = spawnSync('bun', [String(values[2])], { input, encoding: 'utf8' })
        shellOutput.push(result.stdout, result.stderr)
        return { exitCode: result.status ?? 1, stdout: result.stdout, stderr: result.stderr }
      }
      const thread = values[1]
      const isCurrent = thread === currentID
      if (!isCurrent) reads.push(String(thread))
      if (thread === id(101) && options.failedCandidate) {
        if (options.failedCandidate === 'slow') return new Promise<never>(() => {})
        return options.failedCandidate === 'large'
          ? { exitCode: 0, stdout: 'x'.repeat(8_000_001), stderr: '' }
          : { exitCode: 1, stdout: '', stderr: 'private provider detail' }
      }
      const value = {
        id: thread, creatorUserID: !isCurrent && options.foreign ? 'someone-else' : 'owner',
        title: options.candidateTitle === null ? undefined : options.candidateTitle ?? 'Verified JWT expiry title',
        meta: {
          executorType: options.executor ?? 'sandbox',
          visibility: isCurrent
            ? options.changeAudience && ++statusReads > 1 ? 'workspace' : options.audience ?? 'private'
            : candidates.slice(0, options.privateCandidates ?? 0).some(candidate => candidate.id === thread)
              ? 'private' : options.candidateAudience ?? 'private',
          workspaceID: isCurrent ? 'workspace-one' : options.sourceWorkspace ?? 'workspace-one',
          sharedGroupIDs: isCurrent ? options.groups ?? [] : options.sourceGroups ?? [],
          fromExecutorThreadID: !isCurrent && options.childCandidate ? currentID : undefined,
        },
        messages: [{ role: 'user', messageId: options.messageId ?? 1, protocolMessageID: 'M-first',
          content: [{ type: 'text', text: isCurrent ? task : 'JWT expiry boundary correction' },
            ...(options.hiddenContext ? [{ type: 'text', hidden: true, text: hidden },
              ...(isCurrent ? [{ type: 'text', text: 'Check login.ts too.' }] : [])] : [])] }],
      }
      if (options.oldEvidence && !isCurrent) {
        value.messages[0].content[0].text = 'old unrelated text '.repeat(350) +
          'Ledger ownership checks for billing workspace transfers: Transfer requires tenant consent.\n' + 'later unrelated text '.repeat(350)
        value.messages.push(...Array.from({ length: 500 }, (_, i) => ({
          role: 'assistant', messageId: i + 2, protocolMessageID: `M-${i + 2}`,
          content: [{ type: 'text', text: `Routine status update ${i}` }],
        })))
      }
      // Exercise the real projection process, including its stdout boundary.
      const result = spawnSync('bun', [String(values[2]), String(values[3])], { input: JSON.stringify(value), encoding: 'utf8' })
      shellOutput.push(result.stdout, result.stderr)
      return { exitCode: result.status ?? 1, stdout: result.stdout, stderr: result.stderr }
    } } as unknown as PluginEventContext<'agent.start'>
  return {
    run: () => handler(event, ctx), reload: () => plugin(amp),
    currentID, candidates, queries, reads, modelStates, logs, shellOutput,
  }
}

test('injects at most three deduplicated links, never excerpts, and survives reload without rerunning', async () => {
  const f = fixture()
  const result = await f.run()
  expect(result?.message?.content.match(/https:\/\/amp\.example\/threads\//g)).toHaveLength(3)
  expect(result?.message?.content).toContain(`[Verified JWT expiry title](https://amp.example/threads/${id(101)})`)
  expect(result?.message?.content).not.toContain('Never inject this excerpt')
  expect(result?.message?.content).not.toContain('JWT expiry boundary correction')
  expect(result?.message?.content).toContain('Investigating these suggestions is optional.')
  expect(result?.message?.content).not.toContain(id(104))
  expect(result?.message?.display).toBe(false)
  expect(f.queries).toHaveLength(3)
  expect(f.reads).toHaveLength(3)
  expect(f.modelStates).toHaveLength(2)
  f.reload()
  expect(await f.run()).toEqual({})
  expect(f.modelStates).toHaveLength(2)
})

test('thread labels are bounded, escaped and fall back to the ID when unnamed', async () => {
  const named = await fixture({ candidateTitle: '  JWT\n[link](x) <tag> & *text* \\ ' + 'z'.repeat(250) }).run()
  const label = 'JWT \\[link\\](x) &lt;tag&gt; &amp; \\*text\\* \\\\ ' + 'z'.repeat(169)
  expect(named?.message?.content).toContain(`[${label}](https://amp.example/threads/${id(101)})`)
  expect(named?.message?.content).not.toContain('<tag>')
  for (const candidateTitle of [null, ' \n\t ']) {
    const result = await fixture({ candidateTitle }).run()
    expect(result?.message?.content).toContain(`[${id(101)}](https://amp.example/threads/${id(101)})`)
  }
})

test('workspace threads accept shared history but never private history', async () => {
  const shared = fixture({ audience: 'workspace', candidateAudience: 'workspace' })
  expect((await shared.run())?.message?.content).toContain(`[Verified JWT expiry title](https://amp.example/threads/${id(101)})`)
  expect(shared.queries.every(query => query.includes('visibility:workspace'))).toBe(true)
  expect(await fixture({ audience: 'workspace', candidateAudience: 'private' }).run()).toEqual({})
  expect(await fixture({ audience: 'workspace', candidateAudience: 'workspace', sourceWorkspace: 'other-workspace' }).run()).toEqual({})
  expect(await fixture({ foreign: true }).run()).toEqual({})
  expect(await fixture({ changeAudience: true }).run()).toEqual({})
})

test('shared retrieval reaches candidates four and five after rejections, but returns at most three links', async () => {
  for (const privateCandidates of [0, 3]) {
    const f = fixture({ audience: 'workspace', candidateAudience: 'workspace', manyCandidates: true, privateCandidates })
    const result = await f.run()
    expect(f.reads).toHaveLength(5)
    expect(result?.message?.content.match(/https:\/\/amp\.example\/threads\//g)).toHaveLength(privateCandidates ? 2 : 3)
    for (const expected of privateCandidates ? [104, 105] : [101, 102, 103]) {
      expect(result?.message?.content).toContain(id(expected))
    }
    expect(result?.message?.content).not.toContain(id(106))
    expect(result?.message?.content).toContain('5 candidate transcripts')
  }
})

test('incompatible shared history never reaches classification or subprocess output', async () => {
  for (const options of [
    { audience: 'workspace', candidateAudience: 'private' },
    { audience: 'workspace', candidateAudience: 'workspace', sourceWorkspace: 'other-workspace' },
    { audience: 'group', candidateAudience: 'group', groups: ['a', 'b'], sourceGroups: ['a'] },
    { audience: 'unlisted', candidateAudience: 'private' },
    { audience: 'workspace', candidateAudience: 'workspace', foreign: true },
    { audience: 'workspace', candidateAudience: 'workspace', childCandidate: true },
    { audience: 'group', candidateAudience: 'group', groups: [], sourceGroups: ['a'] },
  ]) {
    const f = fixture(options)
    expect(await f.run()).toEqual({})
    const exposed = JSON.stringify([f.modelStates, f.shellOutput, f.logs])
    expect(exposed).not.toContain('JWT expiry finding')
    expect(exposed).not.toContain('Verified JWT expiry title')
    expect(exposed).not.toContain('Never inject this excerpt')
    expect(exposed).not.toContain('JWT expiry boundary correction')
  }
})

test('export rejects malformed or mismatched data without echoing content on either stream', () => {
  const source = { id: id(101), creatorUserID: 'owner', meta: { visibility: 'workspace', workspaceID: 'one' },
    title: 'Title confidential-boundary-sentinel',
    messages: [{ role: 'user', content: [{ type: 'text', text: 'JWT confidential-boundary-sentinel' }] }] }
  const options = { id: source.id, initialPrompt: false, terms: ['jwt'],
    destination: { id: id(999), creatorUserID: 'owner', meta: source.meta } }
  const projector = fileURLToPath(new URL('./export.ts', import.meta.url))
  const run = (input: string, config: unknown = options) => spawnSync('bun', [projector, JSON.stringify(config)], { input, encoding: 'utf8' })
  const allowed = run(JSON.stringify(source))
  expect(allowed.status).toBe(0)
  expect(allowed.stdout).toContain('confidential-boundary-sentinel')
  for (const input of [
    '{"confidential-boundary-sentinel":',
    JSON.stringify({ ...source, id: id(102) }),
    JSON.stringify({ ...source, creatorUserID: undefined }),
    JSON.stringify({ ...source, meta: undefined }),
    JSON.stringify({ ...source, meta: { ...source.meta, visibility: 'private' } }),
    JSON.stringify({ ...source, messages: [{ role: 'user', content: 'confidential-boundary-sentinel' }] }),
  ]) {
    const rejected = run(input)
    expect(rejected.status).not.toBe(0)
    expect(rejected.stdout).toBe('')
    expect(rejected.stderr).not.toContain('confidential-boundary-sentinel')
  }
  const unguarded = run(JSON.stringify(source), { ...options, destination: undefined })
  expect(unguarded.status).not.toBe(0)
  expect(unguarded.stdout).toBe('')
  const metadataOnly = run(JSON.stringify(source), { ...options, terms: [], destination: undefined })
  expect(metadataOnly.status).toBe(0)
  expect(metadataOnly.stdout).not.toContain('confidential-boundary-sentinel')
})

test('retrieval uses all visible user text, not hidden routing or reminder blocks', async () => {
  const f = fixture({ hiddenContext: true })
  expect((await f.run())?.message?.content).toContain(id(101))
  expect(f.queries).toContain('author:me after:90d "login.ts"')
  expect(f.queries).toContain('author:me after:90d "auth.ts"')
  expect(f.queries.join(' ')).not.toContain('hidden-routing-instructions')
  for (const state of f.modelStates as Array<{ task: string }>) {
    expect(state.task).toBe('Fix JWT authentication expiry in auth.ts\nCheck login.ts too.')
  }
  expect(JSON.stringify(f.modelStates)).not.toContain('hidden-routing-instructions')
  expect(JSON.stringify(f.modelStates)).not.toContain('self-improvement-reminder')
})

test('discovers behavioral context and admits evidence outside both the recent-message and text-tail windows', async () => {
  const f = fixture({ oldEvidence: true })
  const result = await f.run()
  expect(result?.message?.content).toContain(id(101))
  expect(result?.message?.content).not.toContain('Transfer requires tenant consent.')
  expect(JSON.stringify(f.modelStates)).toContain('Transfer requires tenant consent.')
  expect(JSON.stringify(f.modelStates).length).toBeLessThan(35_000)
})

test('group sharing requires every destination group to have source access; unlisted never imports private history', async () => {
  const group = { audience: 'group', candidateAudience: 'group', groups: ['a', 'b'] }
  expect((await fixture({ ...group, sourceGroups: ['a', 'b', 'c'] }).run())?.message).toBeDefined()
  expect(await fixture({ ...group, sourceGroups: ['a'] }).run()).toEqual({})
  expect(await fixture({ ...group, groups: [] }).run()).toEqual({})
  expect(await fixture({ ...group, sourceGroups: ['a', 'b'], sourceWorkspace: 'other-workspace' }).run()).toEqual({})
  expect((await fixture({ audience: 'unlisted', candidateAudience: 'unlisted' }).run())?.message).toBeDefined()
  expect(await fixture({ audience: 'unlisted', candidateAudience: 'private' }).run()).toEqual({})
})

test('does not run on replies, old compacted threads, non-orbs, or unknown audiences', async () => {
  for (const options of [{ messageCount: 3 }, { messageCount: 500 }, { messageId: 2 },
    { executor: 'local-client' }, { audience: 'unknown' }]) {
    const f = fixture(options)
    expect(await f.run()).toEqual({})
    expect(f.queries).toHaveLength(0)
    expect(f.modelStates).toHaveLength(0)
  }
  expect((await fixture({ protocolID: true }).run())?.message?.content).toContain(id(101))
})

test('requires useful probability at the threshold, never an unrelated winning score', async () => {
  expect((await fixture({ shortlistProbability: 0.45 }).run())?.message?.content).toContain(id(101))
  expect(await fixture({ shortlistProbability: 0.349 }).run()).toEqual({})
  expect((await fixture({ probability: 0.8 }).run())?.message?.content).toContain(id(101))
  expect(await fixture({ probability: 0.799 }).run()).toEqual({})
  expect(await fixture({ category: 'unrelated', probability: 0.99 }).run()).toEqual({})
})

test('scopes to the repository without leaking remote credentials or changing DSL filters', async () => {
  for (const remote of ['git@github.com:owner/repo.git', 'https://github.com/owner/repo.git', 'ssh://git@github.com/owner/repo.git']) {
    const f = fixture({ remote })
    expect((await f.run())?.message).toBeDefined()
    expect(f.queries.every(query => query.includes('repo:github.com/owner/repo ') && query.includes('author:me'))).toBe(true)
  }
  const hosted = fixture({ remote: 'https://ampcode.com/@owner/repo' })
  expect((await hosted.run())?.message).toBeDefined()
  expect(hosted.queries.every(query => query.includes('repo:ampcode.com/@owner/repo '))).toBe(true)
  const unknown = fixture({ remote: 'https://credential@github.com/owner/repo.git' })
  expect(await unknown.run()).toEqual({})
  expect(unknown.queries).toHaveLength(0)
})

test('search and Jev failures do not block work or expose provider details', async () => {
  for (const audience of ['private', 'workspace']) {
    for (const fail of ['tools', 'schema', 'jev', 'export']) {
      const f = fixture({ fail, audience })
      expect(await f.run()).toEqual({})
      expect(JSON.stringify(f.logs)).toContain('continuing without suggestions')
      expect(JSON.stringify([f.logs, f.shellOutput])).not.toContain('private provider detail')
    }
  }
})

test('one oversized or unreadable candidate does not discard the other relevant links', async () => {
  for (const failedCandidate of ['large', 'unavailable'] as const) {
    const f = fixture({ failedCandidate })
    const result = await f.run()
    expect(result?.message?.content).toContain(id(102))
    expect(result?.message?.content).toContain(id(103))
    expect(result?.message?.content).not.toContain(id(101))
    expect(JSON.stringify(f.logs)).not.toContain('private provider detail')
  }
})

test('a candidate that never responds does not discard completed relevant candidates', async () => {
  const f = fixture({ failedCandidate: 'slow', audience: 'workspace', candidateAudience: 'workspace', manyCandidates: true })
  const result = await f.run()
  expect(result?.message?.content).toContain(id(102))
  expect(result?.message?.content).toContain(id(103))
  expect(result?.message?.content).toContain(id(104))
  expect(result?.message?.content).not.toContain(id(101))
  expect(JSON.stringify(f.logs)).not.toContain('retrieval timed out')
}, 12_000)

test('long tasks and more than twenty candidates remain within provider limits', async () => {
  const task = 'Fix auth.ts JWT expiry. ' + Array.from({ length: 40 }, (_, i) => `component${i}`).join(' ')
  const f = fixture({ task, manyCandidates: true })
  expect((await f.run())?.message?.content).toContain(id(101))
  expect(f.reads).toHaveLength(3)
  expect((await fixture({ task: 'JWT' }).run())?.message?.content).toContain(id(101))
})
