"""Strict checks for demonstrable inline CSS errors, without rewriting authored HTML."""

# Standard Library
import html.parser

# Pip3 Library
import cssutils
import tinycss2
import tinycss2.ast
import tinycss2.color4


# Keep this coverage contract aligned with qpm-core's inline_css module. Unsupported
# properties/functions are unclassified, not invalid. These are validation scopes,
# not a whitelist restricting what authors may use.
COMMON_PROPERTIES = frozenset("""
background background-color border border-top border-right border-bottom border-left
border-color border-top-color border-right-color border-bottom-color border-left-color
border-width border-top-width border-right-width border-bottom-width border-left-width
border-style border-top-style border-right-style border-bottom-style border-left-style
border-spacing border-radius box-shadow box-sizing
color display font font-family font-size font-style font-weight height width
min-height min-width max-height max-width left right top bottom line-height
margin margin-top margin-right margin-bottom margin-left padding padding-top
padding-right padding-bottom padding-left overflow overflow-x overflow-y position
text-align text-decoration text-transform vertical-align visibility white-space
letter-spacing word-spacing outline outline-color outline-style outline-width
""".split())
COLOR_PROPERTIES = frozenset("""
color background-color border-color border-top-color border-right-color
border-bottom-color border-left-color outline-color text-decoration-color
column-rule-color caret-color accent-color
""".split())
COLOR_CONTEXTS = COLOR_PROPERTIES | frozenset("""
background border border-top border-right border-bottom border-left outline
box-shadow text-shadow text-decoration column-rule
""".split())
COLOR_FUNCTIONS = frozenset("rgb rgba hsl hsla hwb lab lch oklab oklch color".split())
WIDE_KEYWORDS = frozenset("inherit initial unset revert revert-layer".split())
SYSTEM_COLORS = frozenset("""
accentcolor accentcolortext activetext buttonborder buttonface buttontext canvas
canvastext field fieldtext graytext highlight highlighttext linktext mark marktext
selecteditem selecteditemtext visitedtext activeborder activecaption appworkspace
background buttonhighlight buttonshadow captiontext inactiveborder inactivecaption
inactivecaptiontext infobackground infotext menu menutext scrollbar threeddarkshadow
threedface threedhighlight threedlightshadow threedshadow window windowframe windowtext
""".split())
LENGTH_UNITS = frozenset("""
px cm mm q in pt pc em ex ch rem cap ic lh rlh rex rcap rch ric
vw vh vi vb vmin vmax svw svh svi svb svmin svmax lvw lvh lvi lvb lvmin lvmax
dvw dvh dvi dvb dvmin dvmax cqw cqh cqi cqb cqmin cqmax
""".split())
# cssutils implements older grammars. These standard extensions must not become
# false errors merely because its property profile predates them.
MODERN_KEYWORDS = {
	'display': frozenset('flex inline-flex grid inline-grid contents flow-root ruby'.split()),
	'text-align': frozenset('start end match-parent justify-all'.split()),
	'white-space': frozenset('break-spaces preserve preserve-breaks preserve-spaces wrap collapse'.split()),
	'overflow': frozenset(['clip']),
	'overflow-x': frozenset(['clip']),
	'overflow-y': frozenset(['clip']),
	'position': frozenset(['sticky']),
	'font-size': frozenset(['xxx-large', 'math']),
	'width': frozenset('min-content max-content fit-content stretch contain'.split()),
	'height': frozenset('min-content max-content fit-content stretch contain'.split()),
	'min-width': frozenset('auto min-content max-content fit-content stretch contain'.split()),
	'min-height': frozenset('auto min-content max-content fit-content stretch contain'.split()),
	'max-width': frozenset('min-content max-content fit-content stretch contain'.split()),
	'max-height': frozenset('min-content max-content fit-content stretch contain'.split()),
}


class InlineCssError(ValueError):
	"""Confirmed CSS failure that readers must not downgrade to a skipped item."""


def _components(tokens: list) -> list:
	return [token for token in tokens if token.type not in ('whitespace', 'comment')]


def _token_error(tokens: list) -> str | None:
	for token in tokens:
		if token.type == 'error':
			return token.message
		children = None
		if token.type == 'function':
			children = token.arguments
		elif token.type in ('() block', '[] block', '{} block'):
			children = token.content
		if children is not None:
			error = _token_error(children)
			if error is not None:
				return error
	return None


def _deferred(token: tinycss2.ast.Node) -> bool:
	if token.type == 'function':
		if token.lower_name not in COLOR_FUNCTIONS:
			return True
		arguments = _components(token.arguments)
		if arguments and arguments[0].type == 'ident' and arguments[0].lower_value == 'from':
			return True
		if token.lower_name == 'color' and arguments and arguments[0].type == 'ident' and arguments[0].value.startswith('--'):
			return True
		return any(_deferred(child) for child in token.arguments)
	return token.type in ('() block', '[] block', '{} block', 'url')


def _color_error(token: tinycss2.ast.Node) -> str | None:
	if _deferred(token):
		return None
	if token.type == 'ident' and token.lower_value in SYSTEM_COLORS:
		return None
	if tinycss2.color4.parse_color(token) is None:
		return 'expected a CSS color (hex colors require # and 3, 4, 6, or 8 hex digits)'
	return None


def _nonnegative(name: str) -> bool:
	return (
		name in ('width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
			'font-size', 'line-height', 'border-spacing', 'outline-width')
		or name.startswith('padding') or name.startswith('border')
	)


def declaration_error(name: str, tokens: list) -> str | None:
	"""Return evidence of invalid CSS, or None for valid/unclassified declarations."""
	# ASVS 2.2.1: validate original parsed values; never repair the authored CSS.
	error = _token_error(tokens)
	if error is not None:
		return error
	if name == 'vert-align':
		return 'vert-align is not a CSS property; use vertical-align'
	if name == 'spacing':
		return 'spacing is not a CSS property; choose padding, margin, or border-spacing'
	if name.startswith('--'):
		return None
	parts = _components(tokens)
	if not parts:
		return 'a property value is required'
	if len(parts) == 1 and parts[0].type == 'ident' and parts[0].lower_value in WIDE_KEYWORDS:
		return None
	if name in COLOR_PROPERTIES:
		if name in ('caret-color', 'accent-color') and len(parts) == 1 and parts[0].type == 'ident' and parts[0].lower_value == 'auto':
			return None
		# A variable may expand to several components, so its arity is deferred.
		for token in parts:
			if token.type == 'hash' or (token.type == 'function' and token.lower_name in COLOR_FUNCTIONS):
				error = _color_error(token)
				if error is not None:
					return error
		if any(_deferred(token) for token in parts):
			return None
		if len(parts) > (4 if name == 'border-color' else 1):
			return 'unexpected extra color components'
		for token in parts:
			error = _color_error(token)
			if error is not None:
				return error
		return None
	# Check explicit colors even when another component cannot be classified.
	if name in COLOR_CONTEXTS:
		for token in parts:
			if token.type == 'hash' or (token.type == 'function' and token.lower_name in COLOR_FUNCTIONS):
				error = _color_error(token)
				if error is not None:
					return error
	if name not in COMMON_PROPERTIES:
		return None
	if any(_deferred(token) for token in parts):
		return None
	if name in MODERN_KEYWORDS and any(
		token.type == 'ident' and token.lower_value in MODERN_KEYWORDS[name] for token in parts
	):
		return None
	# These expanded grammars are not shared by both validation libraries.
	if (name in ('font-style', 'text-decoration', 'display', 'white-space') and len(parts) > 1
		or name == 'background' and any(token.type == 'literal' and token.value == '/' for token in parts)):
		return None
	if name == 'font-weight' and len(parts) == 1 and parts[0].type == 'number':
		if 1 <= parts[0].value <= 1000:
			return None
		return 'numeric font-weight must be between 1 and 1000'
	# Substitute already-validated modern colors/length units ONLY in the grammar
	# probe. Input HTML and its original attribute values are never changed.
	probe = []
	for token in parts:
		if token.type == 'dimension':
			if token.lower_unit not in LENGTH_UNITS:
				return f'unknown length unit {token.unit!r}'
			if token.value < 0 and _nonnegative(name):
				return 'this property requires a non-negative length'
			probe.append(f'{token.value}px')
		elif token.type in ('number', 'percentage') and token.value < 0 and _nonnegative(name):
			return 'this property requires a non-negative value'
		elif name in COLOR_CONTEXTS and (
			token.type in ('hash', 'function')
			or (token.type == 'ident' and token.lower_value in SYSTEM_COLORS)
			or tinycss2.color4.parse_color(token) is not None
		):
			probe.append('black')
		else:
			probe.append(token.serialize())
	if not cssutils.profile.validate(name, ' '.join(probe)):
		return 'invalid value for this CSS property; check units, keywords, and components'
	return None


def validate_style(style: str, context: str) -> None:
	for declaration in tinycss2.parse_declaration_list(style, skip_comments=True, skip_whitespace=True):
		if declaration.type != 'declaration':
			raise InlineCssError(f'{context}: invalid inline CSS declaration in {style!r}; expected property: value')
		error = declaration_error(declaration.lower_name, declaration.value)
		if error is not None:
			value = tinycss2.serialize(declaration.value).strip()
			raise InlineCssError(f'{context}: invalid inline CSS {declaration.name}: {value!r}; {error}')


class _InlineCssParser(html.parser.HTMLParser):
	"""Read original attribute values with HTML character references decoded."""

	def __init__(self, field: str) -> None:
		super().__init__(convert_charrefs=True)
		self.field = field

	def handle_starttag(self, tag: str, attrs: list) -> None:
		context = f'{self.field} <{tag}>'
		for name, value in attrs:
			if value is None:
				continue
			if name == 'style':
				validate_style(value, context)
			elif name in ('color', 'bgcolor'):
				tokens = tinycss2.parse_component_value_list(value)
				error = declaration_error('color', tokens)
				if error is not None:
					raise InlineCssError(f'{context}: invalid {name}={value!r}; {error}')


def validate_html_attributes(html_text: str, field: str) -> None:
	parser = _InlineCssParser(field)
	parser.feed(html_text)
	parser.close()
