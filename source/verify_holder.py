"""Functional and exported-mesh checks, executed through FreeCAD MCP."""
import json
from pathlib import Path
import FreeCAD as App
import Part
import Mesh

ROOT = Path(r"D:\Workspace\Personal_Project\3DP-Toothbrush_shaver_holder")
doc = App.getDocument("ToothbrushShaverHolder")
shape = doc.Holder.Shape
V = App.Vector
report = json.loads((ROOT / "reports" / "geometry_v2.json").read_text())
report["drains_clear"] = all(shape.common(Part.makeCylinder(2.49, 20, V(25,y,-1))).Volume < 1e-6
                             for y in (25,))
report["side_holes_closed"] = all(abs(shape.common(Part.makeCylinder(2.5,3,V(25,y,9))).Volume
                                         - 3.141592653589793*2.5**2*3) < 1e-6
                                  for y in (18,32))
# Open semicircular space between tray and guard rail, away from bevel roots.
gap = Part.makeCylinder(15, 21.6, V(20,25,14.7)).common(
    Part.makeBox(20,40,22,V(20.7,5,14.7)))
report["gap_interference_mm3"] = shape.common(gap).Volume
report["razor_removal_interference_mm3"] = []
for x,z in [(0,0),(0,1),(0,2),(0,4),(-5,4),(-20,4),(-40,4)]:
    ref = doc.RazorReference.Shape.copy()
    ref.translate(V(x,0,z))
    report["razor_removal_interference_mm3"].append(shape.common(ref).Volume)
mesh = Mesh.Mesh(str(ROOT / "print" / "toothbrush_shaver_holder_v2.stl"))
report["stl"] = {"facets": mesh.CountFacets, "closed": mesh.isSolid(),
                 "components": mesh.countComponents(), "volume_mm3": mesh.Volume,
                 "bounds_mm": [mesh.BoundBox.XLength,mesh.BoundBox.YLength,mesh.BoundBox.ZLength]}
report["step"] = {}
roundtrip = Part.read(str(ROOT / "models" / "toothbrush_shaver_holder_v2.step"))
report["step"] = {"valid": roundtrip.isValid(), "solids": len(roundtrip.Solids),
                  "volume_mm3": roundtrip.Volume}
assert report["drains_clear"]
assert report["side_holes_closed"]
assert report["gap_interference_mm3"] < 1e-6
assert max(report["razor_removal_interference_mm3"]) < 1e-6
assert report["stl"]["closed"] and report["stl"]["components"] == 1
assert abs(mesh.Volume - shape.Volume) / shape.Volume < 0.001
assert roundtrip.isValid() and len(roundtrip.Solids) == 1
(ROOT / "reports" / "validation_v2.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
