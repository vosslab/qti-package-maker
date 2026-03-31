# Standard Library
import re
import copy
import html
import random

# Pip3 Library
import lxml.etree
import lxml.html
import num2words
import crcmod.predefined #pip

# QTI Package Maker
# none allowed here!!

#==========================
def _html_table_to_text(table_html: str) -> str:
	"""
	Best-effort conversion of an HTML <table> into a plain-text table.
	Falls back to a placeholder on parse/format failures.
	"""
	try:
		from tabulate import tabulate as _tabulate
	except ImportError:
		_tabulate = None

	try:
		table_el = lxml.html.fromstring(table_html)
	except Exception:
		return "[TABLE]"

	trs = table_el.xpath(".//tr")
	if not trs:
		return "[TABLE]"

	thead_trs = table_el.xpath(".//thead//tr")
	header_tr = thead_trs[0] if thead_trs else None
	if header_tr is None and trs and trs[0].xpath("./th"):
		header_tr = trs[0]

	def extract_row_cells(tr_el):
		cells = tr_el.xpath("./th|./td")
		out = []
		for cell in cells:
			text = cell.text_content()
			text = text.replace("\u00a0", " ")
			text = re.sub(r"\s+", " ", text).strip()
			out.append(text)
		return out

	headers = []
	data_rows = []
	for tr in trs:
		cells = extract_row_cells(tr)
		if not cells:
			continue
		if header_tr is not None and tr is header_tr:
			headers = cells
			continue
		data_rows.append(cells)

	if not data_rows and headers:
		return "[TABLE]"

	max_cols = 0
	for row in data_rows:
		max_cols = max(max_cols, len(row))
	max_cols = max(max_cols, len(headers))
	if max_cols == 0:
		return "[TABLE]"

	if headers and len(headers) < max_cols:
		headers = headers + [""] * (max_cols - len(headers))
	for i, row in enumerate(data_rows):
		if len(row) < max_cols:
			data_rows[i] = row + [""] * (max_cols - len(row))

	if _tabulate:
		try:
			return _tabulate(data_rows, headers=headers if headers else (), tablefmt="fancy_grid")
		except Exception:
			return "[TABLE]"

	lines = []
	if headers:
		lines.append(" | ".join(headers))
		lines.append("-+-".join("-" * len(h) for h in headers))
	for row in data_rows:
		lines.append(" | ".join(row))
	return "\n".join(lines)

#==========================
def number_to_letter(integer: int) -> str:
	"""
	Convert a number to its alphabetical representation.
	"""
	#letters = 'ABCDEFGHJKMNPQRSTUWXYZ'
	#letters = 'abcdefghijklmnopqrstuvwxyz'
	letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	if not (1 <= integer <= len(letters)):
		raise ValueError(f"Invalid input: {integer}. Must be between 1 and {len(letters)}.")
	return letters[integer-1]

#==========================
def number_to_lowercase(integer: int) -> str:
	"""
	Convert a number to its alphabetical representation.
	"""
	#letters = 'ABCDEFGHJKMNPQRSTUWXYZ'
	lowercase_letters = 'abcdefghijklmnopqrstuvwxyz'
	if not (1 <= integer <= len(lowercase_letters)):
		raise ValueError(f"Invalid input: {integer}. Must be between 1 and {len(lowercase_letters)}.")
	return lowercase_letters[integer-1]

#==========================
def number_to_ordinal(integer: int) -> str:
	"""
	Convert a number to its ordinal representation.
	Args:
		integer (int): A positive integer to be converted.
	Returns:
		str: The ordinal representation of the number in English.
	"""
	return num2words.num2words(integer, to='ordinal', lang='en_US')

#==========================
def number_to_cardinal(integer: int) -> str:
	"""
	Convert a number to its cardinal representation.
	Args:
		integer (int): A positive integer to be converted.
	Returns:
		str: The cardinal representation of the number in English.
	"""
	return num2words.num2words(integer, to='cardinal', lang='en_US')

#==============================================================
# Convert a number to its Roman numeral representation.
def number_to_roman(integer: int) -> str:
	"""Convert a number to its Roman numeral representation."""
	val_map = [
		(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
		(100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
		(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')
	]
	roman_numeral = ''
	for value, numeral in val_map:
		while integer >= value:
			roman_numeral += numeral
			integer -= value
	return roman_numeral

#============================
def strip_crc_prefix(question_text: str) -> str:
	"""
	Removes leading CRC-style identifiers (e.g., 'b5b6', '6902_b5b6', '<p>b5b6</p>', etc.)
	from question text. CRCs may be wrapped in <p> tags or prefixed by a number and dot.

	Args:
		question_text (str): The full question text (HTML or plain).

	Returns:
		str: Question text without the leading CRC prefix.
	"""
	crc_pattern = re.compile(
		r'^\s*'                # leading whitespace
		r'(\d{1,3}\.\s*)?'     # optional numeric prefix like '34. '
		r'(?:<p>)?'            # optional opening <p>
		r'([a-f0-9_]{4,16})'   # the CRC prefix
		r'(?:</p>)?'           # optional closing </p>
		r'\s*',                # trailing whitespace
	)
	return re.sub(crc_pattern, '', question_text, count=1)

#==============================================================
# Prefix: letter/digit + ) or : or dot that is not followed by a digit
PREFIX_RE = re.compile(r'^([A-Za-z0-9](?:\)|:|\.(?!\d)))\s*')
OUTER_TAG_RE = re.compile(r'^<(?P<tag>\w+)([^>]*)>(?P<inner>.*)</\1>$', re.IGNORECASE)
HTML_TAG_RE = re.compile(r'<[^>]+>')

#==============================================================
def has_prefix(choices_list: list[str]) -> bool:
	"""Determine if items in choices_list start with a common prefix using regex."""
	for choice in choices_list:
		cleaned_choice = re.sub(HTML_TAG_RE, '', choice)
		if not PREFIX_RE.match(cleaned_choice):
			return False
	return True

#==============================================================
def strip_prefix_from_string(choice: str) -> str:
	"""
	Removes a prefix like 'A. ', '1)', etc. from a string,
	while preserving surrounding HTML if present.
	"""
	match = OUTER_TAG_RE.match(choice)
	if match:
		tag = match.group('tag')
		attrs = match.group(2)
		inner = match.group('inner')
		inner_clean = re.sub(PREFIX_RE, '', inner, count=1)
		return f'<{tag}{attrs}>{inner_clean}</{tag}>'

	return re.sub(PREFIX_RE, '', choice, count=1)

#============================
# Simple text prefixes

#============================
# Decimals must be no-ops

#============================
# HTML-wrapped prefixes

#============================
# No prefix should be a no-op


#==============================================================
def remove_prefix_from_list(choices_list: list) -> list:
	"""
	Removes prefix like 'A. ', '1)', etc. from the content of HTML-wrapped choices,
	while preserving the outer HTML tags.
	"""
	if not has_prefix(choices_list):
		return choices_list
	cleaned_choice_list = []
	for choice_text in choices_list:
			cleaned_choice_text = strip_prefix_from_string(choice_text)
			cleaned_choice_list.append(cleaned_choice_text)
	return cleaned_choice_list

#==========================
def get_crc16_from_string(mystr: str) -> str:
	crc16 = crcmod.predefined.Crc('xmodem')
	try:
		crc16.update(mystr.encode('ascii', errors='strict'))
	except UnicodeEncodeError as e:
		check_ascii(mystr)
		raise ValueError(f"Cannot encode string to ASCII: {mystr}. Original error: {e}")
	return crc16.hexdigest().lower()

#==========================
def get_random_crc16() -> str:
	rand_crc16 = f"{random.randrange(16**4):04x}"
	return rand_crc16

#==========================
def check_ascii(mystr: str) -> bool:
	#destructive function
	mystr = mystr.replace('. ', '\n')
	mystr = mystr.replace(', ', '\n')
	mystr = mystr.replace('<p>', '\n')
	mystr = mystr.replace('</p>', '\n')
	mystr = mystr.replace('<br/>', '\n')
	mystr = mystr.replace('\n\n', '\n')
	for i,line in enumerate(mystr.split('\n')):
		for j,c in enumerate(list(line)):
			try:
				c.encode('ascii', errors='strict')
			except UnicodeEncodeError:
				print(line)
				print(i, j, c)
				print("^ is not ascii")
				raise ValueError
	return True



#==========================
def make_question_pretty(question: str) -> str:
	pretty_question = copy.copy(question)
	#print(len(pretty_question))
	table_map = {}
	table_count = 0
	pattern = re.compile(
		r'<table\b[^>]*>((?:(?!<table).)*?)</table>',
		flags=re.IGNORECASE | re.DOTALL
	)

	#==========================
	def repl_table(match):
		nonlocal table_count
		token = f"__QTI_TABLE_{table_count}__"
		table_count += 1

		table_text = _html_table_to_text(match.group(0)).rstrip("\n")

		anchor = "\x00"
		# Force the table onto its own lines in plain text
		table_map[token] = anchor + "\n" + table_text + "\n"

		# Also try to create a blank line before the token
		return f"\n\n{token}\n"

	# Keep replacing innermost tables until no more matches
	while True:
		new_pretty = pattern.sub(repl_table, pretty_question)
		if new_pretty == pretty_question:
			break
		pretty_question = new_pretty
	if '<table' in pretty_question or '</table' in pretty_question:
		print("MISSED A TABLE")
		print(pretty_question)
		raise ValueError("Table tag detected but not processed.")
	#print(len(pretty_question))
	# Replace non-breaking spaces with regular spaces
	pretty_question = re.sub('&nbsp;', ' ', pretty_question, flags=re.IGNORECASE)
	# Convert all <h1> to <h9> tags into <p> tags
	pretty_question = re.sub(r'<h[0-9]\>', '<p>', pretty_question, flags=re.IGNORECASE)
	# Convert <br/> line breaks into newline characters
	pretty_question = re.sub('<br/>', '\n', pretty_question, flags=re.IGNORECASE)
	# Convert <li> tags into bullet points with newlines
	pretty_question = re.sub('<li>', '\n* ', pretty_question, flags=re.IGNORECASE)
	# Remove <span> tags but keep the content
	pretty_question = re.sub('<span [^>]*>', ' ', pretty_question, flags=re.IGNORECASE)
	# Remove <strong> and </strong> tags
	pretty_question = re.sub(r'<\/?strong>', ' ', pretty_question, flags=re.IGNORECASE)
	# Remove <b>, </b>, <i>, and </i> tags
	pretty_question = re.sub(r'<\/?[bi]>', ' ', pretty_question, flags=re.IGNORECASE)
	# Remove closing </span> tags
	pretty_question = re.sub('</span>', '', pretty_question, flags=re.IGNORECASE)
	# Remove horizontal rule tags
	pretty_question = re.sub(r'\<hr\/\>', '', pretty_question, flags=re.IGNORECASE)
	# Replace adjacent </p><p> blocks with a newline
	pretty_question = re.sub(r'\<\/p\>\s*\<p\>', '\n', pretty_question, flags=re.IGNORECASE)
	# Replace empty <p></p> blocks with a newline
	pretty_question = re.sub(r'\<p\>\s*\<\/p\>', '\n', pretty_question, flags=re.IGNORECASE)
	# Remove closing </p> tags that are preceded by a newline
	pretty_question = re.sub(r'\n\<\/p\>', '', pretty_question, flags=re.IGNORECASE)
	# Remove opening <p> tags that are preceded by a newline
	pretty_question = re.sub(r'\n\<p\>', '\n', pretty_question, flags=re.IGNORECASE)
	# Remove any remaining HTML tags
	pretty_question = re.sub(r'\<\/?[^>]+\>', '', pretty_question)
	# Collapse double newlines into a single newline
	pretty_question = re.sub(r'\n{3,}', '\n\n', pretty_question)
	# Collapse multiple spaces into a single space
	pretty_question = re.sub('  *', ' ', pretty_question)
	# Define subscript and superscript mappings
	pretty_question = convert_sub_sup(pretty_question)
	pretty_question = html.unescape(pretty_question)
	for token, table_text in table_map.items():
		pretty_question = pretty_question.replace(token, table_text)
	#print(len(pretty_question))
	return pretty_question.strip()

#=====================
def convert_sub_sup(pretty_question: str) -> str:
	"""Replace <sub> and <sup> HTML tags with Unicode equivalents using regex."""

	# Define subscript and superscript mappings
	subscript_map = str.maketrans(
		"0123456789+-=()",
		"\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089\u208A\u208B\u208C\u208D\u208E",
	)
	superscript_map = str.maketrans(
		"0123456789+-=()",
		"\u2070\u00B9\u00B2\u00B3\u2074\u2075\u2076\u2077\u2078\u2079\u207A\u207B\u207C\u207D\u207E",
	)

	# Convert <sub> tags
	def subscript_replace(match):
		return match.group(1).translate(subscript_map)

	# Convert <sup> tags
	def superscript_replace(match):
		return match.group(1).translate(superscript_map)

	# Replace <sub> and <sup> content using regex
	pretty_question = re.sub(r'<sub>(.*?)</sub>', subscript_replace, pretty_question)
	pretty_question = re.sub(r'<sup>(.*?)</sup>', superscript_replace, pretty_question)

	return pretty_question

#==============
# This function formats HTML content using the lxml library.
def format_html_lxml(html_string: str) -> str:
	"""
	Format an HTML string using lxml library for cleaner output.

	Args:
		html_string (str): The HTML content to be formatted.

	Returns:
		str: The formatted HTML string.
	"""
	if '<script' in html_string or '</script>' in html_string:
		print("Warning: format_html_lxml() will cause syntax errors in JavaScript.")
		print("skipping...")
		return html_string
	# Create an HTML parser that removes blank text nodes
	parser = lxml.html.HTMLParser(remove_blank_text=True)
	# Parse the input HTML string into an HTML tree
	tree = lxml.html.fromstring(html_string, parser=parser)
	# Convert the parsed HTML tree to a formatted string with indentation and line breaks
	formatted_html = lxml.etree.tostring(tree, pretty_print=True, encoding="unicode").strip()
	# Ensure the string is formatted for HTML output
	formatted_html = lxml.etree.tostring(tree, pretty_print=True, encoding="unicode", method="html").strip()
	formatted_html = formatted_html.replace("&amp;", "&")
	# Return the formatted HTML string
	return formatted_html

#========================================
def html_monospace(txt: str, use_nbsp: bool = True) -> str:
	local_txt = copy.copy(txt)
	if use_nbsp is True:
		local_txt = local_txt.replace(' ', '&nbsp;')
	return f"<span style='font-family: monospace;'>{local_txt}</span>"

#==========================
def html_color_text(text: str, hex_code: str) -> str:
	return f'<span style="color: #{hex_code};">{text}</span>'

#=====================
def generate_gene_letters(num_genes: int, shift: int=-1, clear: bool=False) -> str:
	"""
	Generate a string of unique gene letters based on deterministic or random selection.
	"""
	# Define alphabets
	full_alphabet = "abcdefghijklmnopqrstuvwxyz"
	ambiguous_letters = "giloqsuvz"  # Ambiguous or easily confused letters
	clear_alphabet = ''.join(sorted(set(full_alphabet) - set(ambiguous_letters)))

	# Select alphabet based on the `clear` flag
	alphabet = clear_alphabet if clear else full_alphabet

	# Validate input
	if num_genes > len(alphabet):
		raise ValueError(f"num_genes ({num_genes}) cannot exceed the length of the alphabet ({len(alphabet)}).")

	if shift >= 0:
		# Generate a deterministic sequence with a valid shift
		shift = shift % (len(alphabet) - num_genes + 1)
		return alphabet[shift:shift + num_genes]
	else:
		# Generate random unique letters
		return ''.join(sorted(random.sample(alphabet, num_genes)))
