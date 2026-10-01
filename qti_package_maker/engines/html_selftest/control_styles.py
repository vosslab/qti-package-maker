#==============
def get_css() -> str:
	"""Scoped ORDER/MATCH controls; colors come from the shared theme variables."""
	css = """
.qti-selftest .qti-control-instructions {
  font-style: italic;
  font-size: 14px;
  margin: 10px 0;
}
.qti-selftest .qti-order-list,
.qti-selftest .qti-match-bank {
  list-style: none;
  padding: 0;
  margin: 0 0 12px;
}
.qti-selftest .qti-order-row {
  display: grid;
  grid-template-columns: 30px 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--qti-border);
  padding: 8px;
  margin: 5px 0;
}
.qti-selftest .qti-order-position,
.qti-selftest .feedback {
  text-align: center;
}
.qti-selftest .qti-order-row[draggable="true"],
.qti-selftest .qti-match-choice[draggable="true"] {
  cursor: grab;
}
.qti-selftest .qti-dragging {
  opacity: 0.65;
  cursor: grabbing;
}
.qti-selftest .qti-drop-target {
  outline: 3px solid var(--qti-btn-bg);
  outline-offset: 2px;
}
.qti-selftest .qti-order-row.qti-drop-before {
  box-shadow: inset 0 4px var(--qti-btn-bg);
}
.qti-selftest .qti-order-row.qti-drop-after {
  box-shadow: inset 0 -4px var(--qti-btn-bg);
}
.qti-selftest .qti-order-row .feedback {
  min-height: 30px;
  line-height: 30px;
}
.qti-selftest .qti-order-actions {
  display: flex;
  gap: 6px;
}
.qti-selftest .qti-order-move {
  background: var(--qti-btn-reset-bg);
  color: var(--qti-btn-reset-fg);
  border: 1px solid var(--qti-btn-reset-border);
  border-radius: 4px;
  padding: 6px 10px;
}
.qti-selftest .qti-order-move {
  background: var(--qti-input-bg);
}
.qti-selftest .qti-match-layout {
  container: qti-match / inline-size;
}
.qti-selftest .qti-match-table {
  --qti-match-feedback-width: 64px;
  --qti-match-choice-width: clamp(180px, 25cqi, 220px);
  display: table;
  width: auto;
  max-width: 100%;
  table-layout: auto;
  border-collapse: collapse;
  border: 1px solid var(--qti-border);
  margin: 0;
}
.qti-selftest .qti-match-table > thead > tr > th,
.qti-selftest .qti-match-table > tbody > tr > td {
  border: 1px solid var(--qti-border);
  padding: 8px;
  vertical-align: middle;
}
.qti-selftest .qti-match-table > thead > tr > th:first-child {
  box-sizing: border-box;
  width: var(--qti-match-feedback-width);
  min-width: var(--qti-match-feedback-width);
  padding: 0;
}
.qti-selftest .qti-match-table td.qti-match-feedback {
  padding: 0;
}
.qti-selftest .qti-match-feedback .feedback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
}
.qti-selftest .qti-match-table > thead > tr > th:nth-child(2),
.qti-selftest .qti-match-table td.qti-match-answer {
  box-sizing: border-box;
  width: var(--qti-match-choice-width);
  min-width: var(--qti-match-choice-width);
}
.qti-selftest .qti-match-table td.qti-match-answer {
  position: relative;
  height: 44px;
  padding: 0;
}
/* Bound rich/long prompts before native table sizing; short prompts stay short.
   Reserve the two control columns, prompt padding, and collapsed borders. */
.qti-selftest .qti-match-prompt-content {
  max-width: min(var(--qti-match-prompt-limit, 36ch), calc(100cqi - var(--qti-match-feedback-width) - var(--qti-match-choice-width) - 20px));
  overflow-wrap: anywhere;
  overflow-x: auto;
}
/* Diagrams need the available column width, not a prose line-length limit. */
.qti-selftest .qti-match-prompt-rich {
  --qti-match-prompt-limit: 100cqi;
}
.qti-selftest .qti-game-actions,
.qti-selftest .qti-game-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}
.qti-selftest .qti-game-actions {
  flex-wrap: wrap;
  margin: 10px 0;
}
.qti-selftest .qti-game-actions .qti-feedback-result {
  margin: 0;
  font-size: 14px;
}
.qti-selftest .qti-match-bank {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.qti-selftest .qti-match-bank > li {
  max-width: 100%;
  min-width: 0;
}
.qti-selftest .qti-match-choice,
.qti-selftest .qti-match-slot {
  display: block;
  width: 100%;
  border: 1px solid var(--qti-border);
  padding: 8px;
  text-align: left;
  overflow-x: auto;
}
.qti-selftest .qti-match-choice .qti-choice-content {
  display: block;
  overflow: visible;
}
.qti-selftest .qti-match-slot:not([data-value]) {
  background: var(--qti-slot-bg);
  color: inherit;
  border: 2px dashed var(--qti-slot-border);
  font-style: italic;
  text-align: center;
}
.qti-selftest .qti-selected {
  outline: 3px solid var(--qti-btn-bg);
  outline-offset: 2px;
}
.qti-selftest .qti-order-move,
.qti-selftest .qti-match-choice,
.qti-selftest .qti-match-slot {
  box-sizing: border-box;
  min-height: 44px;
  min-width: 44px;
  font: inherit;
  cursor: pointer;
  overflow-wrap: anywhere;
}
.qti-selftest .qti-match-slot {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  font-size: 12px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.qti-selftest .qti-order-move:disabled {
  opacity: 0.55;
  cursor: default;
}
.qti-selftest button:focus-visible {
  outline: 3px solid var(--qti-btn-bg);
  outline-offset: 3px;
}
.qti-selftest .qti-sr-only {
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
  .qti-selftest .qti-order-row { grid-template-columns: 30px 24px minmax(0, 1fr); }
  .qti-selftest .qti-order-actions { grid-column: 3; flex-wrap: wrap; }
}
/* Respond to the embedded question's width, including narrow desktop panels. */
@container qti-match (max-width: 420px) {
  .qti-selftest .qti-match-table,
  .qti-selftest .qti-match-table > tbody { display: block; }
  .qti-selftest .qti-match-table { width: 100%; }
  .qti-selftest .qti-match-table > thead { display: none; }
  .qti-selftest .qti-match-table > tbody > tr {
    display: grid;
    grid-template-columns: var(--qti-match-feedback-width) minmax(0, 1fr);
    border-bottom: 1px solid var(--qti-border);
  }
  .qti-selftest .qti-match-table > tbody > tr > td { border: 0; min-width: 0; }
  .qti-selftest .qti-match-prompt { grid-column: 1 / 3; grid-row: 1; }
  .qti-selftest .qti-match-prompt-content { max-width: 100%; }
  .qti-selftest .qti-match-table td.qti-match-answer {
    grid-column: 2;
    grid-row: 2;
    width: auto;
    min-width: 0;
  }
  .qti-selftest .qti-match-table td.qti-match-feedback { grid-column: 1; grid-row: 2; }
}
"""
	return css
