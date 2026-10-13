#==============
def get_css() -> str:
	"""Scoped ORDER/MATCH controls; colors come from the shared theme variables."""
	css = """
.qpm-selftest .qpm-control-instructions {
  font-style: italic;
  font-size: 14px;
  margin: 10px 0;
}
.qpm-selftest .qpm-order-list,
.qpm-selftest .qpm-match-bank {
  list-style: none;
  padding: 0;
  margin: 0 0 12px;
}
.qpm-selftest .qpm-order-row {
  display: grid;
  grid-template-columns: 30px 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--qti-border);
  padding: 8px;
  margin: 5px 0;
}
.qpm-selftest .qpm-order-position,
.qpm-selftest .feedback {
  text-align: center;
}
.qpm-selftest .qpm-order-row[draggable="true"],
.qpm-selftest .qpm-match-choice[draggable="true"] {
  cursor: grab;
}
.qpm-selftest .qpm-dragging {
  opacity: 0.65;
  cursor: grabbing;
}
.qpm-selftest .qpm-drop-target {
  outline: 3px solid var(--qpm-btn-bg);
  outline-offset: 2px;
}
.qpm-selftest .qpm-order-row.qpm-drop-before {
  box-shadow: inset 0 4px var(--qpm-btn-bg);
}
.qpm-selftest .qpm-order-row.qpm-drop-after {
  box-shadow: inset 0 -4px var(--qpm-btn-bg);
}
.qpm-selftest .qpm-order-row .feedback {
  min-height: 30px;
  line-height: 30px;
}
.qpm-selftest .qpm-order-actions {
  display: flex;
  gap: 6px;
}
.qpm-selftest .qpm-order-move {
  background: var(--qpm-btn-reset-bg);
  color: var(--qpm-btn-reset-fg);
  border: 1px solid var(--qpm-btn-reset-border);
  border-radius: 4px;
  padding: 6px 10px;
}
.qpm-selftest .qpm-order-move {
  background: var(--qpm-input-bg);
}
.qpm-selftest .qpm-match-layout {
  container: qpm-match / inline-size;
}
.qpm-selftest .qpm-match-table {
  --qpm-match-feedback-width: 64px;
  --qpm-match-choice-width: clamp(180px, 25cqi, 220px);
  display: table;
  width: auto;
  max-width: 100%;
  table-layout: auto;
  border-collapse: collapse;
  border: 1px solid var(--qti-border);
  margin: 0;
}
.qpm-selftest .qpm-match-table > thead > tr > th,
.qpm-selftest .qpm-match-table > tbody > tr > td {
  border: 1px solid var(--qti-border);
  padding: 8px;
  vertical-align: middle;
}
.qpm-selftest .qpm-match-table > thead > tr > th:first-child {
  box-sizing: border-box;
  width: var(--qpm-match-feedback-width);
  min-width: var(--qpm-match-feedback-width);
  padding: 0;
}
.qpm-selftest .qpm-match-table td.qpm-match-feedback {
  padding: 0;
}
.qpm-selftest .qpm-match-feedback .feedback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
}
.qpm-selftest .qpm-match-table > thead > tr > th:nth-child(2),
.qpm-selftest .qpm-match-table td.qpm-match-answer {
  box-sizing: border-box;
  width: var(--qpm-match-choice-width);
  min-width: var(--qpm-match-choice-width);
}
.qpm-selftest .qpm-match-table td.qpm-match-answer {
  position: relative;
  height: 44px;
  padding: 0;
}
/* Bound rich/long prompts before native table sizing; short prompts stay short.
   Reserve the two control columns, prompt padding, and collapsed borders. */
.qpm-selftest .qpm-match-prompt-content {
  max-width: min(var(--qpm-match-prompt-limit, 36ch), calc(100cqi - var(--qpm-match-feedback-width) - var(--qpm-match-choice-width) - 20px));
  overflow-wrap: anywhere;
  overflow-x: auto;
}
/* Diagrams need the available column width, not a prose line-length limit. */
.qpm-selftest .qpm-match-prompt-rich {
  --qpm-match-prompt-limit: 100cqi;
}
.qpm-selftest .qpm-game-actions,
.qpm-selftest .qpm-game-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}
.qpm-selftest .qpm-game-actions {
  flex-wrap: wrap;
  margin: 10px 0;
}
.qpm-selftest .qpm-game-actions .qpm-feedback-result {
  margin: 0;
  font-size: 14px;
}
.qpm-selftest .qpm-match-bank {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.qpm-selftest .qpm-match-bank > li {
  max-width: 100%;
  min-width: 0;
}
.qpm-selftest .qpm-match-choice,
.qpm-selftest .qpm-match-slot {
  display: block;
  width: 100%;
  border: 1px solid var(--qti-border);
  padding: 8px;
  text-align: left;
  overflow-x: auto;
}
.qpm-selftest .qpm-match-choice .qpm-choice-content {
  display: block;
  overflow: visible;
}
.qpm-selftest .qpm-match-slot:not([data-value]) {
  background: var(--qpm-slot-bg);
  color: inherit;
  border: 2px dashed var(--qpm-slot-border);
  font-style: italic;
  text-align: center;
}
.qpm-selftest .qpm-selected {
  outline: 3px solid var(--qpm-btn-bg);
  outline-offset: 2px;
}
.qpm-selftest .qpm-order-move,
.qpm-selftest .qpm-match-choice,
.qpm-selftest .qpm-match-slot {
  box-sizing: border-box;
  min-height: 44px;
  min-width: 44px;
  font: inherit;
  cursor: pointer;
  overflow-wrap: anywhere;
}
.qpm-selftest .qpm-match-slot {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  font-size: 12px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.qpm-selftest .qpm-order-move:disabled {
  opacity: 0.55;
  cursor: default;
}
.qpm-selftest button:focus-visible {
  outline: 3px solid var(--qpm-btn-bg);
  outline-offset: 3px;
}
.qpm-selftest .qpm-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 700px) {
  .qpm-selftest .qpm-order-row { grid-template-columns: 30px 24px minmax(0, 1fr); }
  .qpm-selftest .qpm-order-actions { grid-column: 3; flex-wrap: wrap; }
}
/* Respond to the embedded question's width, including narrow desktop panels. */
@container qpm-match (max-width: 420px) {
  .qpm-selftest .qpm-match-table,
  .qpm-selftest .qpm-match-table > tbody { display: block; }
  .qpm-selftest .qpm-match-table { width: 100%; }
  .qpm-selftest .qpm-match-table > thead { display: none; }
  .qpm-selftest .qpm-match-table > tbody > tr {
    display: grid;
    grid-template-columns: var(--qpm-match-feedback-width) minmax(0, 1fr);
    border-bottom: 1px solid var(--qti-border);
  }
  .qpm-selftest .qpm-match-table > tbody > tr > td { border: 0; min-width: 0; }
  .qpm-selftest .qpm-match-prompt { grid-column: 1 / 3; grid-row: 1; }
  .qpm-selftest .qpm-match-prompt-content { max-width: 100%; }
  .qpm-selftest .qpm-match-table td.qpm-match-answer {
    grid-column: 2;
    grid-row: 2;
    width: auto;
    min-width: 0;
  }
  .qpm-selftest .qpm-match-table td.qpm-match-feedback { grid-column: 1; grid-row: 2; }
}
"""
	return css
