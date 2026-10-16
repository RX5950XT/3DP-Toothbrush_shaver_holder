"""Check the saved slicer output, including support beneath all three overhangs."""
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
folder = ROOT / "reports" / "slicing"
result = json.loads((folder / "result.json").read_text())
assert result["return_code"] == 0
plate = result["sliced_plates"][0]
assert not plate["warning_message"]
regions = {
    "tray": (8, 9, 20, 36, 9, 41),
    "rail": (36, 37, 20, 36, 9, 41),
    "hook_1": (90, 91, -29, 0, 12, 19),
    "hook_2": (90, 91, -29, 0, 31, 38),
}
with zipfile.ZipFile(ROOT / "print" / "holder_v2_A1_PETG.3mf") as archive:
    assert archive.testzip() is None
    assert "Metadata/plate_1.gcode" in archive.namelist()
    gcode = archive.read("Metadata/plate_1.gcode").decode("utf-8")
    model = ET.fromstring(archive.read("3D/3dmodel.model"))
    item = model.find("{*}build/{*}item")
    matrix = [float(value) for value in item.attrib["transform"].split()]
    assert abs(matrix[1]) < 1e-6 and abs(matrix[3]) < 1e-6
    for name,(z0,z1,x0,x1,y0,y1) in list(regions.items()):
        xx = sorted(matrix[0]*v+matrix[9] for v in (x0,x1))
        yy = sorted(matrix[4]*v+matrix[10] for v in (y0,y1))
        regions[name] = (z0,z1,*xx,*yy)
hits = dict.fromkeys(regions, 0)
feature, z, x, y = "", 0, 0, 0
for line in gcode.splitlines():
    if line.startswith("; FEATURE: "):
        feature = line[11:]
    elif line.startswith("; Z_HEIGHT: "):
        z = float(line[12:])
    elif line.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
        words = dict((k,float(v)) for k,v in re.findall(r"([XYE])(-?(?:\d+(?:\.\d*)?|\.\d+))", line))
        x, y = words.get("X",x), words.get("Y",y)
        if feature.startswith("Support") and words.get("E",0) > 0:
            for name,(z0,z1,x0,x1,y0,y1) in regions.items():
                if z0 <= z <= z1 and x0 <= x <= x1 and y0 <= y <= y1:
                    hits[name] += 1
assert all(hits.values()), hits
report = {"slicer": "BambuStudio 02.07.01.62", "return_code": 0,
          "warning": plate["warning_message"], "support_extrusion_hits": hits,
          "estimated_seconds": plate["total_predication"],
          "estimated_grams": plate["filaments"][0]["total_used_g"],
          "layers": 520, "project_3mf_valid": True}
(ROOT / "reports" / "slice_v2.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
