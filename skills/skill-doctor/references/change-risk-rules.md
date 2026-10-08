# Change Review Rules

The highest matching risk wins. The report includes every matching rule; these are deterministic heuristics, not a security verdict.

| Risk | Conditions |
|---|---|
| High | New wildcard or expanded explicit tool set; removal of all explicit tool restrictions; new error finding; removed Skill; newly broad or missing trigger context. |
| Medium | Added/modified script; removed resource; material trigger-term change; quality score drop of at least 10; instruction lines or words grow by more than 25% and at least 10. |
| Low | Smaller instruction/metadata edits; added/modified references or assets; resolved findings; restricted tool set; directory move; clean new Skill without higher conditions. |
| None | No snapshot-relevant changes. |

Trigger terms are lowercase words excluding common English stopwords. A material change adds or removes at least two terms, or its symmetric difference is at least 30% of the smaller term set (denominator at least one). A replaced word counts as one removal and one addition. Counts are not semantic understanding.

Tools are normalized as a set, preserving arguments inside parentheses. Tools introduced by a new Skill also require review. Resources use SHA-256 hashes; a rename is an addition plus a removal. Skills pair by non-empty frontmatter name; changing a name is a removal plus an addition. Duplicate names fail comparison instead of silently overwriting a Skill.

The baseline comes from a Git commit, and the current side includes staged, unstaged, and untracked files. Missing baseline collections are empty. A missing current target is an error; compare the enclosing collection when reviewing deletion of a Skill. Symlink resources are rejected. No scanned script is executed, no model is called, and no API key is needed.

Markdown is for human review, JSON for tools, and `github` for workflow annotations. SARIF is available only for static scans. The Action emits annotations and a job summary without posting comments or requiring write permissions.
