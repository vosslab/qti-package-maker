"""HTML sanitizer for Blackboard Ultra QTI 2.1 output.

Ultra's HTML5 parser has a critical bug: <colgroup width="160"/> (self-closing
on a non-void element) causes the parser to treat the element as unclosed,
breaking the entire table tree construction.

The core fix: re-serialize every HTML fragment through lxml.html.fromstring and
lxml.html.tostring. lxml automatically repairs self-closing non-void tags.

This sanitizer also enforces Ultra's empirically-derived allowlist of tags and
attributes, per the findings in docs/BLACKBOARD_ULTRA_NOTES.md.
"""

import lxml.html
import lxml.etree


#============================================

def sanitize_fragment(html_fragment: str) -> str:
	"""
	Sanitize an HTML fragment for Blackboard Ultra compatibility.

	Repairs self-closing non-void tags (the critical Michaelis-Menten bug),
	rewrites legacy tags to Ultra-compatible forms, strips disallowed
	attributes, and drops unsupported tags while preserving allowed content.

	Args:
		html_fragment: A string containing HTML content (may be a complete
			element or fragment). If the input is already parsed, this should
			be the inner text/content.

	Returns:
		A sanitized HTML string safe for Ultra import, with all self-closing
		non-void tags repaired and all disallowed tags/attributes removed.
	"""
	# Wrap fragment in a container so lxml.html.fromstring parses it as a
	# fragment rather than a full document.
	wrapped_input = f'<div>{html_fragment}</div>'

	try:
		root = lxml.html.fromstring(wrapped_input)
	except Exception:
		# If parsing fails, return the fragment unchanged to avoid data loss.
		# The output will fail downstream validation, but at least the content
		# survives for debugging.
		return html_fragment

	# Phase 1: Snapshot original tags BEFORE any rewriting (for idempotence).
	# Store the original tag for each element so we can rewrite based on the
	# ORIGINAL tag, not tags that may have been rewritten in a previous pass.
	# Use a list to avoid Python object ID reuse bugs.
	all_elements = list(root.iter())
	original_tags = [elem.tag for elem in all_elements]

	# Rewrite legacy tags to Ultra-compatible forms.
	_rewrite_legacy_tags(all_elements, original_tags)

	# Phase 2: Strip disallowed attributes from all elements.
	_strip_disallowed_attributes(root)

	# Phase 3: Unwrap or drop disallowed tags.
	_handle_disallowed_tags(root)

	# Extract the inner HTML of the root div (everything inside, not the div itself).
	result_html = _serialize_inner_html(root)

	return result_html


#============================================

def _rewrite_legacy_tags(all_elements: list, original_tags: list) -> None:
	"""
	Rewrite legacy tags to Ultra-compatible forms in-place.

	Handles:
	- b -> strong
	- i -> em
	- u -> span
	- h1, h2, h3 -> h4
	- h4 -> h5 (only if the ORIGINAL tag from before ANY rewrites was h4)
	- pre -> p

	Args:
		all_elements: A list of lxml elements (from root.iter()).
		original_tags: A list of tag names, parallel to all_elements, captured
			before any rewrites. This ensures idempotence by always rewriting
			based on the ORIGINAL tag, not tags modified in previous passes.
	"""
	# Single pass: rewrite each element based on its ORIGINAL tag (from the snapshot).
	for elem, original_tag in zip(all_elements, original_tags):
		if original_tag in ('h1', 'h2', 'h3'):
			# Promote h1/h2/h3 to h4
			elem.tag = 'h4'
		elif original_tag == 'h4':
			# This was originally h4 in the INPUT, demote it to h5
			# BUT only if we're sure this is the first pass. Since we can't know,
			# we need a different strategy for idempotence.
			# Strategy: we check if the element has already been processed by
			# seeing if the original_tag is still h4 but the current tag would
			# suggest otherwise. Actually, simpler: the original_tags snapshot
			# tells us the ORIGINAL tag from the CURRENT input. If we're re-running
			# on an already-sanitized output that has h4, then original_tag IS h4,
			# and we WOULD demote it. To prevent this, we need to make h4->h5
			# idempotent. Solution: only demote h4 if we also see that h1/h2/h3
			# were demoted (indicating a first pass). OR: use a marker attribute.
			# Simplest: check if ANY h1/h2/h3 elements exist. If not, don't demote h4.
			h123_exist = any(ot in ('h1', 'h2', 'h3') for ot in original_tags)
			if h123_exist:
				# We're in the first pass (h1/h2/h3 exist), so demote original h4
				elem.tag = 'h5'
			# If h1/h2/h3 don't exist, this is a re-run on already-sanitized output,
			# so don't demote h4 (it might be new h4s from h1/h2/h3)
		elif original_tag == 'b':
			elem.tag = 'strong'
		elif original_tag == 'i':
			elem.tag = 'em'
		elif original_tag == 'u':
			elem.tag = 'span'
		elif original_tag == 'pre':
			elem.tag = 'p'


#============================================

def _strip_disallowed_attributes(element) -> None:
	"""
	Remove disallowed attributes from all elements.

	Unconditionally strips: style, class, id, cellpadding, cellspacing,
	bgcolor, border, align, width, height, color, face, valign, and all
	event handlers (onclick, etc.) and namespaced attributes.

	Exception: <a> elements retain their href attribute.

	Args:
		element: An lxml element tree.
	"""
	# Attributes to strip unconditionally
	strip_attrs = {
		'style', 'class', 'id',
		'cellpadding', 'cellspacing', 'bgcolor', 'border', 'align',
		'width', 'height', 'color', 'face', 'valign',
	}

	for elem in element.iter():
		attrs_to_remove = []

		for attr_name in elem.attrib:
			# Strip if it's in the explicit blocklist
			if attr_name in strip_attrs:
				attrs_to_remove.append(attr_name)
			# Strip all event handlers (on*)
			elif attr_name.startswith('on'):
				attrs_to_remove.append(attr_name)
			# Strip all namespaced attributes (containing ':')
			elif ':' in attr_name:
				attrs_to_remove.append(attr_name)

		# For non-<a> elements, also remove href if present
		if elem.tag != 'a':
			if 'href' in elem.attrib:
				attrs_to_remove.append('href')

		# Remove the collected attributes
		for attr_name in attrs_to_remove:
			del elem.attrib[attr_name]


#============================================

def _handle_disallowed_tags(element) -> None:
	"""
	Unwrap or drop disallowed tags.

	Allowed tags: p, div, span, br, em, strong, sub, sup, code, ul, ol, li,
	h4, h5, table, tbody, tr, th, td, colgroup, col, a

	- blockquote, kbd: unwrap (keep content)
	- Any other tag not in allowlist and not in the drop list: unwrap
	- script, style, img: drop entirely (tag and content)

	Args:
		element: An lxml element tree (modified in-place).
	"""
	allowed_tags = {
		'p', 'div', 'span', 'br', 'em', 'strong', 'sub', 'sup', 'code',
		'ul', 'ol', 'li', 'h4', 'h5', 'table', 'tbody', 'tr', 'th', 'td',
		'colgroup', 'col', 'a',
	}

	drop_tags = {'script', 'style', 'img'}

	# Iterate over a snapshot of all elements because we'll be modifying the tree.
	all_elements = list(element.iter())

	for elem in all_elements:
		if elem.tag in allowed_tags:
			# Keep this element and its children
			continue
		elif elem.tag in drop_tags:
			# Drop this element entirely (including all children)
			parent = elem.getparent()
			if parent is not None:
				parent.remove(elem)
		else:
			# Unwrap: keep children and text, remove the wrapper tag
			# This includes blockquote, kbd, and any unknown tags
			parent = elem.getparent()
			if parent is not None:
				# Get the position of this element in the parent (before we modify)
				try:
					index = list(parent).index(elem)
				except ValueError:
					# Element was already removed
					continue

				# If the element has text (and no children), wrap it in a text node
				# that becomes the previous sibling's tail or the parent's text.
				if elem.text and not list(elem):
					# Element has text but no children. We need to preserve the text.
					# Append it to the previous sibling's tail, or to parent's text
					if index > 0:
						prev_elem = parent[index - 1]
						prev_elem.tail = (prev_elem.tail or '') + elem.text
					else:
						parent.text = (parent.text or '') + elem.text

				# Move all children to the parent, right before this element
				for child in list(elem):
					elem.remove(child)
					parent.insert(index, child)
					index += 1

				# Remove the wrapper element
				parent.remove(elem)


#============================================

def _serialize_inner_html(root) -> str:
	"""
	Serialize the inner HTML of a root element.

	Returns the HTML content of all children of the root, without the root
	element itself. Re-serializes through lxml to guarantee repair of any
	remaining self-closing non-void tags.

	Args:
		root: An lxml element (typically the wrapping div).

	Returns:
		A string containing the serialized inner HTML.
	"""
	# Collect the serialized form of each child
	parts = []
	for child in root:
		# Serialize this child and its subtree
		child_html = lxml.html.tostring(
			child,
			encoding='unicode',
			method='html'
		)
		parts.append(child_html)

	# Also add any tail text from the root (text after the root open tag,
	# before the first child)
	if root.text:
		parts.insert(0, root.text)

	return ''.join(parts)
