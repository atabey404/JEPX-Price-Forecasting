"""Restore the bundled source snapshots for local verification."""
from pathlib import Path
import zipfile
R=Path(__file__).resolve().parents[1];dest=R.parent/'stability_work';dest.mkdir(exist_ok=True)
for p in (R/'inputs').glob('*.zip'):
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():assert not Path(n).is_absolute() and '..' not in Path(n).parts
  z.extractall(dest)
p=dest/'JEPX_Model_Experiment_03/inputs/JEPX_Model_Experiment02_20261109.zip'
with zipfile.ZipFile(p) as z:z.extractall(dest)
print(dest)
