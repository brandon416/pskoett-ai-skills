export type Audience = {
  creatorUserID: string
  meta: {
    executorType?: string
    visibility?: string
    workspaceID?: string | null
    sharedGroupIDs?: string[]
  }
}

export const threadID = /^T-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i

export function compatible(destination: Audience, source: Audience): boolean {
  if (typeof destination?.creatorUserID !== 'string' || !destination.creatorUserID || source?.creatorUserID !== destination.creatorUserID ||
      !destination.meta || !source.meta) return false
  if (destination.meta.visibility === 'private') return true
  if (destination.meta.visibility === 'unlisted') return source.meta.visibility === 'unlisted'
  if (!['workspace', 'group'].includes(destination.meta.visibility ?? '') ||
      typeof destination.meta.workspaceID !== 'string' || !destination.meta.workspaceID ||
      source.meta.workspaceID !== destination.meta.workspaceID) return false
  if (source.meta.visibility === 'workspace') return true
  const groups = destination.meta.sharedGroupIDs
  return destination.meta.visibility === 'group' && source.meta.visibility === 'group' &&
    Array.isArray(groups) && groups.length > 0 && Array.isArray(source.meta.sharedGroupIDs) &&
    groups.every(group => typeof group === 'string' && group.length > 0 && source.meta.sharedGroupIDs!.includes(group))
}
