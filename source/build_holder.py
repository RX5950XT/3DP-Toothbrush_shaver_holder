"""Run inside FreeCAD through AgentCAD MCP run_code."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part

ROOT = Path(r"D:\Workspace\Personal_Project\3DP-Toothbrush_shaver_holder")
VERSION = "v1"
BASE_WIDTH, DEPTH, BASE_THICKNESS = 70.0, 50.0, 4.0
WALL_THICKNESS, WALL_HEIGHT, FOOT_WIDTH = 20.0, 100.0, 10.0
BORE_DIAMETER, RAIL_THICKNESS = 25.0, 3.0
TRAY_BOTTOM, TRAY_THICKNESS = 9.0, 3.0
RAIL_BOTTOM, RAIL_HEIGHT = 37.0, 10.0
HOOK_REACH, HOOK_GAP, HOOK_WIDTH = 29.0, 13.0, 6.0
HOOK_TOP, HOOK_THICKNESS, LIP_HEIGHT = 96.0, 5.0, 3.0
CHAMFER = 0.6
V = App.Vector
doc = App.getDocument("ToothbrushShaverHolder")
assert not doc.Objects, "Existing model must be edited deliberately; no destructive rebuild."


def box(x, y, z, at):
    return Part.makeBox(x, y, z, V(*at))


def feature(name, shape, visible=False):
    obj = doc.getObject(name) or doc.addObject("Part::Feature", name)
    obj.Shape = shape
    obj.ViewObject.Visibility = visible
    return obj


def audit(shape):
    assert shape.isValid() and shape.isClosed() and len(shape.Solids) == 1
    bounds = shape.BoundBox
    return {"valid": shape.isValid(), "closed": shape.isClosed(),
            "solids": len(shape.Solids), "volume_mm3": shape.Volume,
            "bounds_mm": [bounds.XLength, bounds.YLength, bounds.ZLength],
            "faces": len(shape.Faces), "edges": len(shape.Edges)}


feet = [box(BASE_WIDTH, FOOT_WIDTH, BASE_THICKNESS, (-30, y, 0))
        for y in (0, DEPTH - FOOT_WIDTH)]
spine = box(WALL_THICKNESS, DEPTH, BASE_THICKNESS + WALL_HEIGHT, (0, 0, 0))
structure = spine.multiFuse(feet).removeSplitter()
feature("HBaseAndSpine", structure)
print("Structure:", json.dumps(audit(structure)))

radius = BORE_DIAMETER / 2
outer = radius + RAIL_THICKNESS
tray = Part.makeCylinder(outer, TRAY_THICKNESS, V(20, 25, TRAY_BOTTOM))
rail = Part.makeCylinder(outer, RAIL_HEIGHT, V(20, 25, RAIL_BOTTOM))
hooks = []
for y in (25 - HOOK_GAP / 2 - HOOK_WIDTH, 25 + HOOK_GAP / 2):
    arm = box(HOOK_REACH + 2, HOOK_WIDTH, HOOK_THICKNESS,
              (-HOOK_REACH, y, HOOK_TOP - HOOK_THICKNESS))
    lip = box(3, HOOK_WIDTH, LIP_HEIGHT + 1, (-HOOK_REACH, y, HOOK_TOP - 1))
    hooks.append(arm.fuse(lip).removeSplitter())
solid = structure.multiFuse([tray, rail] + hooks).removeSplitter()
audit(solid)
bore = Part.makeCylinder(radius, 110, V(20, 25, TRAY_BOTTOM + TRAY_THICKNESS))
solid = solid.cut(bore).removeSplitter()
for y in (18, 25, 32):
    drain = Part.makeCylinder(2.5, 16, V(25, y, -1))
    solid = solid.cut(drain).removeSplitter()
feature("BeforeChamfer", solid)
print("Before chamfer:", json.dumps(audit(solid)))

# Keep mating spaces clear after chamfering: concave chamfers add material.
finished = solid.makeChamfer(CHAMFER, solid.Edges)
finished = finished.cut(bore).removeSplitter()
head_clearance = box(25.6, 50, 12, (-25.8, 0, HOOK_TOP))
finished = finished.cut(head_clearance).removeSplitter()
audit(finished)
holder = feature("Holder", finished, True)
holder.Label = "牙刷刮鬍刀架 v1（可列印）"
holder.ViewObject.ShapeColor = (0.70, 0.82, 0.83)
holder.ViewObject.LineColor = (0.17, 0.25, 0.28)
for key, value in {"BoreDiameter": BORE_DIAMETER, "RailHeight": RAIL_HEIGHT,
                   "RailWall": RAIL_THICKNESS, "DrainGap": 25.0,
                   "HookGap": HOOK_GAP, "EdgeChamfer": CHAMFER}.items():
    if key not in holder.PropertiesList:
        holder.addProperty("App::PropertyLength", key, "Design dimensions")
    setattr(holder, key, value)
    holder.setEditorMode(key, 1)

head = box(25.3, 42.8, 7.3, (-25.65, 3.6, HOOK_TOP))
handle = Part.makeCylinder(5.5, 83.1, V(-13, 25, HOOK_TOP - 83.1))
razor = feature("RazorReference", head.fuse(handle))
razor.Label = "刮鬍刀尺寸參考（不列印）"
razor.ViewObject.ShapeColor = (0.35, 0.37, 0.40)
brush = feature("ToothbrushSpaceReference", Part.makeCylinder(radius, 145, V(20, 25, 12)))
brush.Label = "Ø25 牙刷空間（不列印）"
brush.ViewObject.ShapeColor = (0.30, 0.65, 0.80)
brush.ViewObject.Transparency = 60
doc.recompute()
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
report = audit(finished)
report["razor_interference_mm3"] = finished.common(razor.Shape).Volume
report["toothbrush_space_interference_mm3"] = finished.common(brush.Shape).Volume
assert report["razor_interference_mm3"] < 1e-6
assert report["toothbrush_space_interference_mm3"] < 1e-6
assert all(abs(a-b) < 1e-6 for a,b in zip(report["bounds_mm"], [70,50,104]))
(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports" / "geometry_v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
