"""Slice locally using installed Bambu profiles. Does not send to a printer."""
import json
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = Path(r"C:\Program Files\Bambu Studio\bambu-studio.exe")
PROFILES = STUDIO.parent / "resources" / "profiles" / "BBL"
OUTPUT = ROOT / "reports" / "slicing"
PRINT = ROOT / "print"


def resolve(kind, name, stack=()):
    assert name not in stack, "Profile inheritance cycle"
    source = json.loads((PROFILES / kind / (name + ".json")).read_text(encoding="utf-8"))
    parent = source.get("inherits")
    result = resolve(kind, parent, stack + (name,)) if parent else {}
    for include in source.get("include", []):
        result.update(resolve(kind, include, stack + (name,)))
    result.update(source)
    for key in ("inherits", "include"):
        result.pop(key, None)
    return result


machine = resolve("machine", "Bambu Lab A1 0.4 nozzle")
process = resolve("process", "0.20mm Standard @BBL A1")
filament = resolve("filament", "Bambu PETG Basic @BBL A1")
machine["printer_settings_id"] = machine["name"]
process.update(
    name="Holder v2 0.20mm PETG supports", print_settings_id="Holder v2 0.20mm PETG supports",
    wall_loops="4", sparse_infill_density="20%", sparse_infill_pattern="gyroid",
    top_shell_layers="5", bottom_shell_layers="5", layer_height="0.2",
    enable_support="1", support_type="tree(auto)", support_style="default",
    support_threshold_angle="45", support_on_build_plate_only="0",
    support_top_z_distance="0.2", support_bottom_z_distance="0.2",
    support_object_xy_distance="0.35", support_interface_top_layers="3",
    support_interface_spacing="0.5", brim_type="outer_only", brim_width="5",
    outer_wall_speed="80", inner_wall_speed="120", sparse_infill_speed="120",
)
filament["filament_settings_id"] = [filament["name"]]
OUTPUT.mkdir(parents=True, exist_ok=True)
PRINT.mkdir(exist_ok=True)
for name, data in [("machine", machine), ("process", process), ("filament", filament)]:
    (OUTPUT / (name + ".json")).write_text(json.dumps(data, indent=2), encoding="utf-8")
command = [str(STUDIO), "--debug", "2", "--arrange", "1",
           "--curr-bed-type", "Textured PEI Plate", "--load-settings",
           str(OUTPUT / "machine.json") + ";" + str(OUTPUT / "process.json"),
           "--load-filaments", str(OUTPUT / "filament.json"), "--slice", "0",
           "--outputdir", str(OUTPUT), "--export-3mf", "holder_v2_A1_PETG.3mf",
           str(PRINT / "toothbrush_shaver_holder_v2.stl")]
result = subprocess.run(command, cwd=OUTPUT, capture_output=True, timeout=600,
                        creationflags=subprocess.CREATE_NO_WINDOW)
if result.stdout or result.stderr or result.returncode:
    (OUTPUT / "console.log").write_bytes(result.stdout + result.stderr)
print("Bambu Studio exit:", result.returncode)
if (OUTPUT / "result.json").exists():
    print((OUTPUT / "result.json").read_text(encoding="utf-8"))
assert result.returncode == 0, "See reports/slicing/console.log"
assert (OUTPUT / "holder_v2_A1_PETG.3mf").is_file()
shutil.move(str(OUTPUT / "holder_v2_A1_PETG.3mf"), str(PRINT / "holder_v2_A1_PETG.3mf"))
# The 3MF embeds this exact G-code; keep one print artifact instead of duplicates.
(OUTPUT / "plate_1.gcode").unlink()
