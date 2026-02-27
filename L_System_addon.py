bl_info = {
    "name": "Procedural 3D Tree Full UI",
    "author": "YourName",
    "version": (1, 4),
    "blender": (5, 0, 1),
    "location": "View3D > Sidebar > Procedural Tree",
    "description": "3D tree generator with editable parameters",
    "category": "Add Mesh",
}

import bpy
from math import radians
from mathutils import Vector, Matrix
import random

# -------------------------------
# L-SYSTEM
# -------------------------------
def l_system(axiom, rules, iterations):
    current = axiom
    for _ in range(iterations):
        next_string = ""
        for char in current:
            next_string += rules.get(char, char)
        current = next_string
    return current

# -------------------------------
# TREE GENERATOR
# -------------------------------
def generate_tree(
        axiom,
        rules,
        iterations,
        angle,
        step,
        base_radius,
        radius_decay,
        taper_rate,
        leaf_size,
        leaf_depth,
        leaf_probability
    ):

    l_string = l_system(axiom, rules, iterations)
    angle_rad = radians(angle)

    leaf_collection = bpy.data.collections.get("Leaves")
    if not leaf_collection:
        leaf_collection = bpy.data.collections.new("Leaves")
        bpy.context.scene.collection.children.link(leaf_collection)

    curve_data = bpy.data.curves.new("TreeCurve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 1.0
    curve_data.bevel_resolution = 4

    curve_obj = bpy.data.objects.new("ProceduralTree", curve_data)
    bpy.context.collection.objects.link(curve_obj)

    position = Vector((0, 0, 0))
    orientation = Matrix.Identity(3)
    stack = []

    branch_depth = 0
    current_radius = base_radius

    current_spline = curve_data.splines.new('POLY')
    current_spline.points.add(0)
    current_spline.points[0].co = (*position, 1)
    current_spline.points[0].radius = current_radius

    for char in l_string:
        if char in ('F', 'f'):
            position = position + orientation @ Vector((0, 0, step))
            current_spline.points.add(1)
            p = current_spline.points[-1]
            p.co = (*position, 1)
            current_radius *= taper_rate
            p.radius = current_radius

        elif char == '+':
            orientation @= Matrix.Rotation(-angle_rad, 3, 'Z')
        elif char == '-':
            orientation @= Matrix.Rotation(angle_rad, 3, 'Z')
        elif char == '&':
            orientation @= Matrix.Rotation(angle_rad, 3, 'X')
        elif char == '^':
            orientation @= Matrix.Rotation(-angle_rad, 3, 'X')
        elif char in ('<', '\\'):
            orientation @= Matrix.Rotation(angle_rad, 3, 'Y')
        elif char in ('>', '/'):
            orientation @= Matrix.Rotation(-angle_rad, 3, 'Y')

        elif char == '[':
            stack.append((position.copy(), orientation.copy(), branch_depth, current_radius))
            branch_depth += 1
            current_radius *= radius_decay

        elif char == ']':
            if branch_depth >= leaf_depth and random.random() < leaf_probability:
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=leaf_size * random.uniform(0.8, 1.2),
                    location=position
                )
                leaf = bpy.context.object
                leaf_collection.objects.link(leaf)
                bpy.context.collection.objects.unlink(leaf)

            position, orientation, branch_depth, current_radius = stack.pop()
            current_spline = curve_data.splines.new('POLY')
            current_spline.points.add(0)
            current_spline.points[0].co = (*position, 1)
            current_spline.points[0].radius = current_radius

    return curve_obj

# -------------------------------
# PropertyGroup для UI
# -------------------------------
class ProceduralTreeProperties(bpy.types.PropertyGroup):
    iterations: bpy.props.IntProperty(name="Iterations", default=4, min=1, max=6)
    angle: bpy.props.FloatProperty(name="Angle", default=20, min=0, max=90)
    step: bpy.props.FloatProperty(name="Step Size", default=0.2, min=0.1)
    base_radius: bpy.props.FloatProperty(name="Base Radius", default=0.05, min=0.01)
    radius_decay: bpy.props.FloatProperty(name="Radius Decay", default=0.4, min=0.1, max=1.0)
    taper_rate: bpy.props.FloatProperty(name="Taper Rate", default=0.99, min=0.8, max=1.0)
    leaf_size: bpy.props.FloatProperty(name="Leaf Size", default=0.2, min=0.01)
    leaf_depth: bpy.props.IntProperty(name="Leaf Depth", default=2, min=1)
    leaf_probability: bpy.props.FloatProperty(name="Leaf Probability", default=0.05, min=0.0, max=1.0)
    axiom: bpy.props.StringProperty(name="Axiom", default="X")
    rules: bpy.props.StringProperty(name="Rules", default="X:F[+X][-X][&X][/X];F:FF")

# -------------------------------
# Оператор
# -------------------------------
class OBJECT_OT_generate_tree(bpy.types.Operator):
    bl_idname = "object.generate_procedural_tree"
    bl_label = "Generate 3D Tree"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.procedural_tree_props

        # Преобразуем правила в словарь
        try:
            rules_dict = {}
            for pair in props.rules.split(";"):
                key, value = pair.split(":")
                rules_dict[key.strip()] = value.strip()
        except Exception as e:
            self.report({'ERROR'}, f"Invalid rules format: {e}")
            return {'CANCELLED'}

        generate_tree(
            axiom=props.axiom,
            rules=rules_dict,
            iterations=props.iterations,
            angle=props.angle,
            step=props.step,
            base_radius=props.base_radius,
            radius_decay=props.radius_decay,
            taper_rate=props.taper_rate,
            leaf_size=props.leaf_size,
            leaf_depth=props.leaf_depth,
            leaf_probability=props.leaf_probability
        )
        return {'FINISHED'}

# -------------------------------
# Панель UI
# -------------------------------
class VIEW3D_PT_procedural_tree(bpy.types.Panel):
    bl_label = "Procedural 3D Tree"
    bl_idname = "VIEW3D_PT_procedural_tree"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Procedural Tree"

    def draw(self, context):
        layout = self.layout
        props = context.scene.procedural_tree_props
        layout.operator("object.generate_procedural_tree", text="Generate 3D Tree")
        
        layout.prop(props, "axiom")
        layout.prop(props, "rules")
        layout.prop(props, "iterations")
        layout.prop(props, "angle")
        layout.prop(props, "step")
        layout.prop(props, "base_radius")
        layout.prop(props, "radius_decay")
        layout.prop(props, "taper_rate")
        layout.prop(props, "leaf_size")
        layout.prop(props, "leaf_depth")
        layout.prop(props, "leaf_probability")

# -------------------------------
# Регистрация
# -------------------------------
classes = [ProceduralTreeProperties, OBJECT_OT_generate_tree, VIEW3D_PT_procedural_tree]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.procedural_tree_props = bpy.props.PointerProperty(type=ProceduralTreeProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.procedural_tree_props

if __name__ == "__main__":
    register()