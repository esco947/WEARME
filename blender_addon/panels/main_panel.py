"""Main side-panel UI for the WEARME Blender addon.

Defines the following classes, all registered by :mod:`blender_addon`:

- :class:`WEARME_PT_MainPanel` — sidebar panel in the 3D Viewport (N-panel)
- :class:`WEARME_OT_LoadGLB` — import a WEARME body GLB into the scene
- :class:`WEARME_OT_ClearBody` — remove all WEARME mesh objects
- :class:`WEARME_OT_ExportGLB` — export WEARME objects to GLB
- :class:`WEARME_OT_ExportOBJ` — export WEARME objects to OBJ

This module must only be imported inside Blender (bpy available).
"""

from __future__ import annotations

from bpy.props import StringProperty  # type: ignore[import-not-found]
from bpy.types import Context, Event, Operator, Panel  # type: ignore[import-not-found]

from wearme.sim import blender_bridge

# ── Panel ───────────────────────────────────────────────────────────────────────


class WEARME_PT_MainPanel(Panel):  # noqa: N801
    """WEARME main side panel (3D Viewport → N-panel → WEARME tab)."""

    bl_label = "WEARME Body"
    bl_idname = "WEARME_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "WEARME"

    def draw(self, context: Context) -> None:  # noqa: ARG002
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Load body", icon="IMPORT")
        col.operator(WEARME_OT_LoadGLB.bl_idname, text="Import GLB…")
        col.operator(WEARME_OT_ClearBody.bl_idname, text="Clear body", icon="TRASH")

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Export", icon="EXPORT")
        col.operator(WEARME_OT_ExportGLB.bl_idname, text="Export GLB…")
        col.operator(WEARME_OT_ExportOBJ.bl_idname, text="Export OBJ…")


# ── Operators ───────────────────────────────────────────────────────────────────


class WEARME_OT_LoadGLB(Operator):  # noqa: N801
    """Import a WEARME body mesh from a GLB file."""

    bl_idname = "wearme.load_glb"
    bl_label = "Import WEARME GLB"
    bl_description = "Import a WEARME body mesh from a GLB file into the scene"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(  # type: ignore[valid-type]
        name="File Path",
        description="Path to the GLB file",
        subtype="FILE_PATH",
    )
    filter_glob: StringProperty(  # type: ignore[valid-type]
        default="*.glb",
        options={"HIDDEN"},
    )

    def invoke(self, context: Context, event: Event) -> set[str]:  # noqa: ARG002
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: Context) -> set[str]:  # noqa: ARG002
        try:
            names = blender_bridge.import_body_from_glb(self.filepath)
            self.report({"INFO"}, f"Imported {len(names)} object(s): {', '.join(names)}")
        except FileNotFoundError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Import failed: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}


class WEARME_OT_ClearBody(Operator):  # noqa: N801
    """Remove all WEARME-managed mesh objects from the scene."""

    bl_idname = "wearme.clear_body"
    bl_label = "Clear WEARME Body"
    bl_description = "Remove all WEARME body objects from the scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: Context) -> set[str]:  # noqa: ARG002
        count = blender_bridge.clear_body_objects()
        self.report({"INFO"}, f"Removed {count} WEARME object(s)")
        return {"FINISHED"}


class WEARME_OT_ExportGLB(Operator):  # noqa: N801
    """Export the WEARME body mesh to a GLB file."""

    bl_idname = "wearme.export_glb"
    bl_label = "Export WEARME GLB"
    bl_description = "Export the WEARME body mesh to a GLB file"
    bl_options = {"REGISTER"}

    filepath: StringProperty(  # type: ignore[valid-type]
        name="File Path",
        description="Destination GLB file path",
        subtype="FILE_PATH",
        default="body.glb",
    )
    filter_glob: StringProperty(  # type: ignore[valid-type]
        default="*.glb",
        options={"HIDDEN"},
    )

    def invoke(self, context: Context, event: Event) -> set[str]:  # noqa: ARG002
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: Context) -> set[str]:  # noqa: ARG002
        try:
            out = blender_bridge.export_scene_glb(self.filepath)
            self.report({"INFO"}, f"GLB saved to {out}")
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Export failed: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}


class WEARME_OT_ExportOBJ(Operator):  # noqa: N801
    """Export the WEARME body mesh to an OBJ file."""

    bl_idname = "wearme.export_obj"
    bl_label = "Export WEARME OBJ"
    bl_description = "Export the WEARME body mesh to an OBJ file"
    bl_options = {"REGISTER"}

    filepath: StringProperty(  # type: ignore[valid-type]
        name="File Path",
        description="Destination OBJ file path",
        subtype="FILE_PATH",
        default="body.obj",
    )
    filter_glob: StringProperty(  # type: ignore[valid-type]
        default="*.obj",
        options={"HIDDEN"},
    )

    def invoke(self, context: Context, event: Event) -> set[str]:  # noqa: ARG002
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: Context) -> set[str]:  # noqa: ARG002
        try:
            out = blender_bridge.export_scene_obj(self.filepath)
            self.report({"INFO"}, f"OBJ saved to {out}")
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Export failed: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}
