// Runs in the export pipeline, before bounded stdout crosses the plugin RPC.
// Never print the raw export: it includes hidden messages, tools, and environment.
import { compatible, threadID, type Audience } from './audience'

type Message = {
  messageId?: string | number
  protocolMessageID?: string
  role: string
  content: Array<{ type: string; text?: string; hidden?: boolean }>
}
try {
  const source = JSON.parse(await Bun.stdin.text()) as Audience & {
    id: string
    title?: string
    meta: Audience['meta'] & { fromExecutorThreadID?: string }
    messages: Message[]
  }
  const options = JSON.parse(process.argv[2]) as {
    id: string; initialPrompt: boolean; terms: string[]; destination?: Audience & { id: string }
  }
  if (!threadID.test(options.id) || source.id !== options.id || !source.meta || !Array.isArray(source.messages) ||
      (options.destination && (!compatible(options.destination, source) ||
        source.meta.fromExecutorThreadID === options.destination.id)) ||
      (options.terms.length > 0 && !options.destination)) throw new Error('Thread export rejected')

  const { executorType, visibility, workspaceID, sharedGroupIDs } = source.meta
  const visible = (message: Message) => message.content.filter(block => block.type === 'text' && !block.hidden)
  let messages: Message[] = []
  if (options.terms.length) {
    const blocks = source.messages.flatMap((message, order) =>
      message.role === 'user' || message.role === 'assistant'
        ? visible(message).map(block => ({ message, order, text: block.text ?? '' })) : [])
    const tokens = (text: string) => new Set(text.toLowerCase().match(/[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*/g) ?? [])
    const frequencies = new Map(options.terms.map(term => [term, 0]))
    for (const block of blocks) {
      const words = tokens(block.text)
      for (const term of options.terms) if (words.has(term)) frequencies.set(term, frequencies.get(term)! + 1)
    }
    const weights = options.terms.map(term => ({ term, weight: Math.log(1 + blocks.length / (1 + frequencies.get(term)!)) }))
    const passages: Array<{ message: Message; score: number; order: number }> = []
    for (const { message, order, text } of blocks) {
      let best = { text: '', score: -1 }
      for (let offset = 0; offset < text.length; offset += 600) {
        const passage = text.slice(offset, offset + 1200)
        const words = tokens(passage)
        // Distinctive whole words matter more than ubiquitous task vocabulary.
        const score = weights.reduce((sum, { term, weight }) => sum + (words.has(term) ? weight : 0), 0)
        if (score > best.score) best = { text: passage, score }
      }
      if (best.score <= 0) continue
      passages.push({ score: best.score, order, message: {
        messageId: message.messageId, protocolMessageID: message.protocolMessageID, role: message.role,
        content: [{ type: 'text', text: best.text }],
      } })
    }
    const seen = new Set<string>()
    messages = passages.sort((a, b) => b.score - a.score || b.order - a.order)
      .filter(({ message }) => {
        const text = message.content[0].text!
        if (seen.has(text)) return false
        seen.add(text)
        return true
      }).slice(0, 8).map(passage => passage.message)
  } else if (options.initialPrompt) {
    messages = source.messages.slice(-400).map(message => ({
      messageId: message.messageId, protocolMessageID: message.protocolMessageID, role: message.role,
      content: visible(message).map(block => ({ type: 'text', text: (block.text ?? '').slice(0, 6000) })),
    }))
  }
  // Only candidate exports with a successful audience check may expose a title.
  const title = options.terms.length && typeof source.title === 'string'
    ? source.title.replace(/[\s\u0000-\u001f\u007f-\u009f]+/g, ' ').trim().slice(0, 200) : undefined
  console.log(JSON.stringify({ id: source.id, title, creatorUserID: source.creatorUserID,
    meta: { executorType, visibility, workspaceID, sharedGroupIDs }, messages }))
} catch {
  // Parser/provider details can contain rejected text. Keep stderr content-free too.
  console.error('Thread export unavailable or incompatible')
  process.exitCode = 1
}
