
# Standard Library
import os
import random
import pathlib
import collections.abc

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.assessment_items.item_bank import ItemBank


class BaseEngine:
	# Declared media-handling contract for every engine. Each engine routes its
	# images through exactly one of media_assets.VALID_MEDIA_POLICIES. The default
	# keeps image references verbatim and warns; packaging engines override this.
	media_policy = media_assets.POLICY_REFERENCE_WARN

	#==============
	def __init__(self, package_name: str, verbose: bool = False) -> None:
		self.package_name = package_name
		self.verbose = verbose
		self.name = self._get_name()
		# Must be overridden by child classes
		self.write_item = None

	#==============
	def _get_name(self) -> str:
		"""
		Return the engine's directory name from the module path.
		Assumes the engine class lives under qti_package_maker/engines/<engine_name>/.
		"""
		# Extract module path as a string
		module_string = self.__class__.__module__
		# Get the second-to-last element, which should be the engine folder name
		return module_string.split(".")[-2]

	#==============
	def validate_write_item_module(self) -> None:
		"""
		Validate that the engine is wired to the correct write_item module.
		Call this after assigning self.write_item in the engine subclass.
		"""
		if not self.write_item:
			raise ImportError(f"No write_item module assigned for {self.name} engine.")
		write_item_path = pathlib.Path(self.write_item.__file__).resolve()
		if self.name not in write_item_path.parts:
			raise ImportError(f"Incorrect write_item module imported for {self.name} engine. "
					f"Expected to find {self.name} in {write_item_path}.")

	#==============
	def read_package(self, infile: str) -> ItemBank:
		raise NotImplementedError("Subclasses must implement read_package().")

	#==============
	def save_package(self, item_bank: ItemBank, outfile: str | None = None) -> str:
		raise NotImplementedError("Subclasses must implement save_package().")

	#==============
	def process_random_item_from_item_bank(self, item_bank: ItemBank) -> object:
		"""
		Return the first renderable item after randomizing the item order.
		This is intentionally non-deterministic and should only be used when randomness
		is desired (for example the html_selftest engine).
		"""
		if len(item_bank) == 0:
			print("No items to write out skipping")
			return
		items = list(item_bank)
		random.shuffle(items)
		for item_cls in items:
			write_item_function = getattr(self.write_item, item_cls.item_type, None)
			if not write_item_function:
				print(f"Warning: No write function found for item type '{item_cls.item_type}'.")
				continue
			item_engine_data = write_item_function(item_cls)
			if item_engine_data is not None:
				return item_engine_data
		return None

	#=============
	def process_item_bank(
				self,
				item_bank: ItemBank,
				item_transform_fn: collections.abc.Callable | None = None,
				post_render_fn: collections.abc.Callable | None = None) -> list:
		"""
		Render each item in the ItemBank using the engine's write_item functions.

		This is the single render loop for every engine. The two optional hooks
		let an engine inject its media handling without re-implementing the loop:

		- item_transform_fn(item_cls) -> item_cls: a PRE-render transform that
		  returns the item to render (typically a rewritten deep copy). Runs
		  after the write function is resolved, so items with no write function
		  are skipped before the transform is called.
		- post_render_fn(item_cls, item_engine_data) -> item_engine_data: a
		  POST-render transform on the rendered output, keyed by the ORIGINAL
		  item. Runs only for items that rendered to non-None output.

		With both hooks left as None this is the plain render loop.

		Args:
			item_bank: the items to render, in bank order.
			item_transform_fn: optional pre-render per-item transform.
			post_render_fn: optional post-render per-item transform.

		Returns:
			The list of rendered items, in bank order, dropping None renders.
		"""
		if len(item_bank) == 0:
			print("No items to write, skipping processing.")
			return []
		assessment_items_tree = []
		for item_cls in item_bank:
			write_item_function = getattr(self.write_item, item_cls.item_type, None)
			if not write_item_function:
				print(f"Warning: No write function found for item type '{item_cls.item_type}'.")
				continue
			# Optional pre-render transform (media src rewrite or clone) decides
			# which item object the write function actually renders.
			render_item_cls = item_cls
			if item_transform_fn is not None:
				render_item_cls = item_transform_fn(item_cls)
			item_engine_data = write_item_function(render_item_cls)
			if item_engine_data is None:
				continue
			# Optional post-render transform (rendered-text substitution) is keyed
			# on the ORIGINAL item, matching the hand-rolled loops it replaces.
			if post_render_fn is not None:
				item_engine_data = post_render_fn(item_cls, item_engine_data)
			assessment_items_tree.append(item_engine_data)
		return assessment_items_tree

	#==============
	def raise_on_unpackagable_media(self, item_bank: ItemBank) -> None:
		"""
		Raise before any side effects when the bank references unpackagable media.

		File-packaging engines need a real file to bundle, so a data-URI `<img src>`
		cannot be packaged and must fail. This mirrors the per-item
		media_assets.raise_on_data_uri_assets() check the write path already
		performs, but runs it up front so save_package() can validate the whole
		bank BEFORE it creates any staging directory. Validation first, side
		effects second keeps a rejected bank from leaking an empty timestamped
		staging directory in the current working directory.

		Args:
			item_bank: the bank about to be packaged.

		Raises:
			media_assets.MediaPolicyError: an item references a data URI image.
		"""
		if len(item_bank) == 0:
			return
		# Scan the bank's HTML once; item_dependencies only carries entries for
		# items that actually reference images, so the .get default is intentional.
		collected = item_bank.collect_assets()
		for item_cls in item_bank:
			item_assets = collected.item_dependencies.get(item_cls.item_crc16, [])
			if not item_assets:
				continue
			media_assets.raise_on_data_uri_assets(item_assets, self.name, item_cls.item_crc16)

	#==============
	def get_available_question_types(self) -> list:
		"""Return a list of available question types based on write_item callables."""
		if not self.write_item:
			print(f"No write_item module assigned for engine {self.name}.")
			return []
		# Extract function names dynamically
		functions = [
			name for name in dir(self.write_item)
			if callable(getattr(self.write_item, name)) and not name.startswith("__")
		]
		return functions

	#==============
	def show_available_question_types(self) -> None:
		"""Print the available question types for this engine."""
		available_types = self.get_available_question_types()
		if available_types:
			print(f"Available question types: {', '.join(available_types)}")
		else:
			print(f"No available question types found for engine {self.name}.")

	#==============
	def get_outfile_name(self, prefix: str, extension: str, outfile: str = None) -> str:
		"""Generate an output filename from prefix/extension unless the user provides one."""
		# If the user provides an outfile, return it unchanged
		if outfile:
			return outfile
		# Default to self.package_name if no outfile is provided
		outfile = self.package_name
		# Ensure the prefix is added if it's missing
		if not outfile.startswith(f"{prefix}-"):
			outfile = f"{prefix}-{outfile}"
		# Extract the root filename (remove existing extension)
		outfile_root, _ = os.path.splitext(outfile)
		# Construct the final filename with the correct extension
		return f"{outfile_root}.{extension}"
