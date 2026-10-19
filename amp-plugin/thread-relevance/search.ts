// Discard titles before the shell RPC can log them. Search results have no
// workspace/group metadata, so they cannot authorize sharing their content.
import { threadID } from './audience'

try {
  const results: unknown = JSON.parse(await Bun.stdin.text())
  if (!Array.isArray(results)) throw new Error('Unexpected search response')
  console.log(JSON.stringify(results.slice(0, 20).flatMap(value =>
    typeof value?.id === 'string' && threadID.test(value.id) ? [{ id: value.id }] : [])))
} catch {
  console.error('Thread search unavailable')
  process.exitCode = 1
}
