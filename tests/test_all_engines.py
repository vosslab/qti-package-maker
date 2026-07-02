# Standard Library
import os
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker import package_interface


@pytest.mark.smoke
def test_all_engines_write(tmp_cwd: pathlib.Path, sample_items: dict) -> None:
	qti_packer = package_interface.QTIPackageInterface("dummy", verbose=False)
	engine_name_list = qti_packer.get_available_engines()
	available_item_types = qti_packer.get_available_item_types()

	for item_type in available_item_types:
		item_tuple = sample_items[item_type]
		qti_packer.add_item(item_type, item_tuple)
		for engine_name in engine_name_list:
			try:
				output_file = qti_packer.save_package(engine_name)
			except (NotImplementedError, ImportError):
				continue
			if output_file and isinstance(output_file, (str, os.PathLike)):
				assert os.path.exists(output_file)
				os.remove(output_file)
		qti_packer.reset_item_bank()
