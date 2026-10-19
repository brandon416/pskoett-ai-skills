# Thread relevance

Automatically suggests up to three prior threads when you start a new Amp orb.
The agent receives clickable thread names and decides whether to investigate.
No summaries, transcript previews, mandatory reads or extra agent turns.

## Install

Requires Amp CLI, Bash, Bun and Git.

Copy this whole directory into the root of your writable Amp User Plugins
repository, then commit and push that repository. Find it with
`amp plugins repositories`. For project-only use, copy the directory into
`.amp/plugins/` instead. Review existing copies before replacing them and choose
only one installation location. See the [Amp installation guide](https://github.com/pskoett/pskoett-ai-skills#amp).

New threads load published changes automatically. Existing threads need a plugin
reload, which does not rerun startup suggestions in established threads. This
repository stores source only; pushing here does not update an installed plugin.

## How it works

Jev chooses keywords from your visible request, searches with native Amp thread
search, and classifies candidates using bounded transcript passages. It uses
`typesafe/jev` with no fallback model. This adds automatic discovery, not a new
search index or a replacement for agent-led investigation.

| Limit | Behavior |
| --- | --- |
| Search scope | Your own threads updated within 90 days, including archived threads. Same repository when `origin` is available; account-wide otherwise. Current thread and its children excluded. |
| Search budget | Up to three queries, 20 results each, at most 60 distinct candidates. |
| Transcript reads | Up to three for private threads; the first five candidates for shared threads, without ranking unchecked snippets. Rejected reads consume slots. |
| Suggestions | At most three. Useful must win Jev's final classification with probability ≥0.8. Scores are not accuracy guarantees. |
| Waiting | At most 15 seconds overall, up to seven per candidate read. Slow reads are skipped; in-flight operations may finish afterward. |

Runs once on the first prompt of an owned orb. Replies, resumed threads and
Ship/Push workflows are skipped. Failures or no strong matches leave the prompt
unchanged. An empty marker in `$XDG_CACHE_HOME/amp/thread-relevance/` (default
`~/.cache/amp/thread-relevance/`) prevents repeat attempts, including after failure.

Suggestions are unverified leads, not historical instructions. The agent should
read full history before relying on old decisions, and current instructions take
precedence. The plugin asks `session-context` to reuse the search; it does not
install or modify that skill.

## Privacy and sharing

Only threads you own are candidates, with these additional restrictions:

| New thread | Eligible history |
| --- | --- |
| Private | Your own history |
| Workspace | Workspace-visible threads in the same workspace |
| Group | Group-visible threads in the same workspace covering every destination group |
| Unlisted | Your own unlisted threads |

Shared searches expose IDs only until audience checks pass. Candidate exports
check identity, ownership and audience before emitting titles or passages, and
the destination's sharing is rechecked before returning links. Titles are bounded
and escaped. Hidden text, tool results, thinking and environment data are excluded.

The plugin does not save transcripts. Its logs contain counts and failure status,
but Amp runtime logs may contain permitted projected passages. Sharing changes
do not erase previously delivered context or logs. Review a private conversation
before sharing it.

## Known limits

Relevant history can be missed, and suggestions can be irrelevant or outdated.
No suggestions does not mean no useful history exists.

[Plugin API reference](https://ampcode.com/docs/plugin-api)
