"""Per-item-type dispatch functions for the Blackboard pool export engine.

Each module-level function is named exactly by its item_type so
base_engine.process_item_bank can dispatch via
  getattr(self.write_item, item_cls.item_type)(item_cls)

Supported types: MC, MA, MATCH, FIB, NUM, MULTI_FIB.
ORDER is intentionally omitted -- base_engine.process_item_bank emits a
warning for any type without a matching function and continues.

Each type's `<item>` subtree is built by its own per-type module (`MC.py`,
`MA.py`, etc.); shared XML primitives live in `common_xml.py`. The per-type
modules are imported by full dotted path because the dispatch functions below
must keep the bare type names (MC, MA, ...) and would otherwise shadow a
short module binding of the same name.
"""

# Standard Library
import lxml.etree

ENGINE_NAME = "blackboard_export_zip"

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
import qti_package_maker.engines.blackboard_export_zip.MC
import qti_package_maker.engines.blackboard_export_zip.MA
import qti_package_maker.engines.blackboard_export_zip.FIB
import qti_package_maker.engines.blackboard_export_zip.NUM
import qti_package_maker.engines.blackboard_export_zip.MATCH
import qti_package_maker.engines.blackboard_export_zip.MULTI_FIB

#============================================
def MC(item_cls: item_types.MC) -> lxml.etree.Element:
	"""Render an MC item as a Blackboard pool <item> element."""
	return qti_package_maker.engines.blackboard_export_zip.MC.build_MC(item_cls)

#============================================
def MA(item_cls: item_types.MA) -> lxml.etree.Element:
	"""Render an MA item as a Blackboard pool <item> element."""
	return qti_package_maker.engines.blackboard_export_zip.MA.build_MA(item_cls)

#============================================
def MATCH(item_cls: item_types.MATCH) -> lxml.etree.Element:
	"""Render a MATCH item as a Blackboard pool <item> element."""
	return qti_package_maker.engines.blackboard_export_zip.MATCH.build_MATCH(item_cls)

#============================================
def FIB(item_cls: item_types.FIB) -> lxml.etree.Element:
	"""Render a FIB item as a Blackboard pool <item> element."""
	return qti_package_maker.engines.blackboard_export_zip.FIB.build_FIB(item_cls)

#============================================
def NUM(item_cls: item_types.NUM) -> lxml.etree.Element:
	"""Render a NUM item as a Blackboard pool <item> element."""
	return qti_package_maker.engines.blackboard_export_zip.NUM.build_NUM(item_cls)

#============================================
def MULTI_FIB(item_cls: item_types.MULTI_FIB) -> lxml.etree.Element:
	"""Render a MULTI_FIB item as a Blackboard pool <item> element."""
	return qti_package_maker.engines.blackboard_export_zip.MULTI_FIB.build_MULTI_FIB(item_cls)
