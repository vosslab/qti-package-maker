
def _plain_tabulate(rows: list, headers: tuple = ()) -> str:
	rows = rows or []
	headers = list(headers) if headers else []

	string_rows = []
	if headers:
		string_rows.append([str(x) for x in headers])
	for row in rows:
		string_rows.append([str(x) for x in row])

	if not string_rows:
		return ""

	col_count = max(len(r) for r in string_rows)
	for r in string_rows:
		while len(r) < col_count:
			r.append("")

	col_widths = [0] * col_count
	for r in string_rows:
		for i, cell in enumerate(r):
			col_widths[i] = max(col_widths[i], len(cell))

	def fmt_row(r: list) -> str:
		return " | ".join(r[i].ljust(col_widths[i]) for i in range(col_count)).rstrip()

	lines = []
	start_idx = 0
	if headers:
		lines.append(fmt_row(string_rows[0]))
		lines.append("-+-".join("-" * w for w in col_widths).rstrip())
		start_idx = 1

	for r in string_rows[start_idx:]:
		lines.append(fmt_row(r))
	return "\n".join(lines) + "\n"


try:
	from tabulate import tabulate as tabulate  # type: ignore
except ImportError:
	def tabulate(rows: list, headers: tuple = (), tablefmt: str | None = None) -> str:  # noqa: ARG001
		return _plain_tabulate(rows, headers=headers)

