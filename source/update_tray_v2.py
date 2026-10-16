"""Local v1 -> v2 tray edit, executed inside FreeCAD through AgentCAD MCP."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part

ROOT = Path(r"D:\Workspace\Personal_Project\3DP-Toothbrush_shaver_holder")
RIM_HEIGHT, RIM_WALL, RIM_CHAMFER = 2.0, 3.0, 0.4
V = App.Vector
doc = App.getDocument("ToothbrushShaverHolder")
holder = doc.getObject("Holder")
assert holder and "v1" in holder.Label, "Expected the verified v1 Holder"
original = holder.Shape.copy()
print("Baseline:", original.BoundBox, original.Volume, len(original.Solids))

# Plugs cover the existing 0.6 mm hole-mouth chamfers, staying within the tray.
plugs = [Part.makeCylinder(3.11, 3, V(25,y,9)) for y in (18,32)]
rim = Part.makeCylinder(12.5 + RIM_WALL, RIM_HEIGHT + 0.8, V(20,25,11.2))
rim = rim.cut(Part.makeCylinder(12.5, 4, V(20,25,11)))
top_edges = [e for e in rim.Edges if abs(e.BoundBox.ZMin - 14) < 1e-6]
rim = rim.makeChamfer(RIM_CHAMFER, top_edges)
updated = original.multiFuse(plugs + [rim]).removeSplitter()
assert updated.isValid() and updated.isClosed() and len(updated.Solids) == 1

# Prove all additions stay local to the bottom tray and nothing was removed.
region = Part.makeBox(32,32,5.02,V(4,9,8.99))
added_outside = updated.cut(original).cut(region).Volume
removed = original.cut(updated).Volume
assert added_outside < 1e-6 and removed < 1e-6
razor_overlap = updated.common(doc.RazorReference.Shape).Volume
brush_overlap = updated.common(doc.ToothbrushSpaceReference.Shape).Volume
assert razor_overlap < 1e-6 and brush_overlap < 1e-6

previous = doc.addObject("Part::Feature", "HolderV1")
previous.Label = "v1 修改前備份（不列印）"
previous.Shape = original
previous.ViewObject.Visibility = False
holder.Shape = updated
holder.Label = "牙刷刮鬍刀架 v2（可列印）"
holder.addProperty("App::PropertyLength", "TrayRimHeight", "Design dimensions")
holder.TrayRimHeight = RIM_HEIGHT
holder.setEditorMode("TrayRimHeight", 1)
doc.recompute()
Gui.Selection.clearSelection()
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
bb = updated.BoundBox
report = {"valid": updated.isValid(), "closed": updated.isClosed(),
          "solids": len(updated.Solids), "volume_mm3": updated.Volume,
          "bounds_mm": [bb.XLength,bb.YLength,bb.ZLength],
          "faces": len(updated.Faces), "edges": len(updated.Edges),
          "razor_interference_mm3": razor_overlap,
          "toothbrush_space_interference_mm3": brush_overlap,
          "added_outside_tray_mm3": added_outside, "removed_mm3": removed,
          "rim_height_mm": RIM_HEIGHT, "drain_diameter_mm": 5}
assert all(abs(a-b) < 1e-6 for a,b in zip(report["bounds_mm"],[70,50,104]))
(ROOT / "reports" / "geometry_v2.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
