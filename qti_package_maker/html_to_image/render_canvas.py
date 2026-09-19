"""Draw an RDKit canvas from extracted SMILES using RDKit's Python API.

RDKit is an extra (`pip_extras.txt`). Import it only when a canvas is drawn so
table-only --html-to-image runs do not require the package. A missing install
raises ImportError at draw time.
"""

# local repo modules
from qti_package_maker.html_to_image.selectors import CanvasSource


#============================================
def render_canvas_png(source: CanvasSource) -> bytes:
	"""
	Draw a molecule PNG from a CanvasSource.

	Args:
		source: SMILES plus legend / explicitMethyl / size from the HTML.

	Returns:
		PNG bytes from MolDraw2DCairo.

	Raises:
		ImportError: rdkit is not installed.
		ValueError: RDKit cannot parse the SMILES.
	"""
	from rdkit import Chem
	from rdkit.Chem.Draw import rdMolDraw2D
	mol = Chem.MolFromSmiles(source.smiles)
	if mol is None:
		raise ValueError(f"RDKit could not parse SMILES: {source.smiles}")
	drawer = rdMolDraw2D.MolDraw2DCairo(source.width, source.height)
	options = drawer.drawOptions()
	options.explicitMethyl = source.explicit_methyl
	legend = source.legend if source.legend is not None else ""
	drawer.DrawMolecule(mol, legend=legend)
	drawer.FinishDrawing()
	png_bytes = drawer.GetDrawingText()
	return png_bytes
