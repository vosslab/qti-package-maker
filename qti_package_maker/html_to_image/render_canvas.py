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
	highlight_bonds = list(source.highlight_bonds)
	if source.highlight_peptide_bonds:
		peptide_pattern = Chem.MolFromSmarts("CC(=O)NC")
		for match in mol.GetSubstructMatches(peptide_pattern):
			peptide_bond = mol.GetBondBetweenAtoms(match[1], match[3])
			if peptide_bond is not None:
				highlight_bonds.append(peptide_bond.GetIdx())
	if any(index < 0 or index >= mol.GetNumAtoms()
			for index in source.highlight_atoms):
		raise ValueError("RDKit atom highlight index is outside the molecule")
	if any(index < 0 or index >= mol.GetNumBonds()
			for index in highlight_bonds):
		raise ValueError("RDKit bond highlight index is outside the molecule")
	if source.highlight_peptide_bonds and not highlight_bonds:
		raise ValueError("RDKit peptide canvas contains no matching peptide bonds")
	drawer = rdMolDraw2D.MolDraw2DCairo(source.width, source.height)
	options = drawer.drawOptions()
	options.explicitMethyl = source.explicit_methyl
	legend = source.legend if source.legend is not None else ""
	highlight_atom_colours = {}
	highlight_bond_colours = {}
	if source.highlight_colour is not None:
		highlight_atom_colours = {
			index: source.highlight_colour for index in source.highlight_atoms}
		highlight_bond_colours = {
			index: source.highlight_colour for index in highlight_bonds}
	drawer.DrawMolecule(
		mol,
		highlightAtoms=list(source.highlight_atoms),
		highlightBonds=highlight_bonds,
		highlightAtomColors=highlight_atom_colours,
		highlightBondColors=highlight_bond_colours,
		legend=legend)
	drawer.FinishDrawing()
	png_bytes = drawer.GetDrawingText()
	return png_bytes
