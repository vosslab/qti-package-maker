"""Draw an RDKit canvas from extracted SMILES using RDKit's Python API."""

# PIP3 modules
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

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
		ValueError: RDKit cannot parse the SMILES.
	"""
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
