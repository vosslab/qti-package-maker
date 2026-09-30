"""In-memory content cache for HTML-to-image renderer output."""

# Standard Library
from collections.abc import Callable

#============================================
class RenderCache:
	"""Store rendered PNG bytes by renderer identity, family, and content."""

	def __init__(self) -> None:
		self._png_by_key: dict[tuple[int, str, object], bytes] = {}
		# Retain identities so a collected callback's id cannot be reused by another.
		self._renderers: dict[int, object] = {}
		self.hits = 0
		self.misses = 0


	#============================================
	def get_or_render(
			self, family: str, key: object,
			render_fn: Callable[[], bytes], *, renderer: object = None) -> bytes:
		"""Return cached PNG bytes, rendering and retaining them on a miss."""
		renderer_id = id(renderer)
		self._renderers[renderer_id] = renderer
		cache_key = (renderer_id, family, key)
		if cache_key in self._png_by_key:
			self.hits += 1
			return self._png_by_key[cache_key]
		self.misses += 1
		png_bytes = render_fn()
		self._png_by_key[cache_key] = png_bytes
		return png_bytes
