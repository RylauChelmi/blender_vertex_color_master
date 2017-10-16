#  ***** GPL LICENSE BLOCK *****
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  All rights reserved.
#  ***** GPL LICENSE BLOCK *****


# + Transfer vertex colors to single channel 
# + paint greyscale, r, g, b or whatever
# + convert colors by luminosity, channel copy, channel mask, channel swap
# + fill channel with color
# + fill can use selection as a mask
# + fill can have fade out from selection (i.e. selected verts are 1.0, verts at fade dist are 0, and in between are lerped)
# + support alpha using technique from existing vcolor addons
# + convert vcol to weights and back
# + convert weights to channel
# + channel viewer

# where is the vcol data stored? temp vcol channel, or temp object copy?
# blender only supports r,g,b. could use two rgb channels giving 6 channels total

# first steps
# fill channel
# invert channel
# use vertex selection mask with fill and invert
#   selection using vertices must get each vertex from loop data (per face vertex)
#   selection usin faces must get just the loop for entire face

# TODO:
# active channels is weird. Just make RGBA part of the brush settings and call it brush_channels or something
# think about workflow properly
#
#

import bpy
from bpy.props import (
        StringProperty,
        BoolProperty,
        FloatProperty,
        EnumProperty,
        )


bl_info = {
  "name": "Vertex Color Master",
  "author": "Andrew Palmer",
  "version": (0, 0, 1),
  "blender": (2, 79, 0),
  "location": "",
  "description": "Tools for working with vertex colors at greater precision than using the paint brush.",
  "category": "Paint"
}

red_id = 'R'
green_id = 'G'
blue_id = 'B'
alpha_id = 'A'

##### HELPER FUNCTIONS #####
def set_channels_visible(object, active_channels):
  return None

def set_brush_params(brush_opacity, brush_mode, active_channels):
  return None

def channel_id_to_idx(id):
  if id is red_id:
    return 0
  if id is green_id:
    return 1
  if id is blue_id:
    return 2
  if id is alpha_id:
    return 3
  # default to red
  return 0 

def rgb_to_luminosity(color):
  # Y = 0.299 R + 0.587 G + 0.114 B
  return color[0]*0.299 + color[1]*0.587 + color[2]*0.114


def convert_rgb_to_luminosity(mesh, src_vcol_id, dst_vcol_id, dst_channel_idx, dst_all_channels=False):
  # validate input
  if mesh.vertex_colors is None:
    print("mesh has no vertex colors")
    return
  src_vcol = None if src_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[src_vcol_id]
  dst_vcol = None if dst_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[dst_vcol_id]

  if src_vcol is None or dst_vcol is None:
    print("source or destination are invalid")
    return

  # convert color to luminosity
  if dst_all_channels:
    for loop_index, loop in enumerate(mesh.loops):
      luminosity = rgb_to_luminosity(src_vcol.data[loop_index].color)
      dst_vcol.data[loop_index].color = [luminosity]*3
  else:
    for loop_index, loop in enumerate(mesh.loops):
      luminosity = rgb_to_luminosity(src_vcol.data[loop_index].color)
      dst_vcol.data[loop_index].color[dst_channel_idx] = luminosity


def copy_rgb_channel(mesh, src_vcol_id, dst_vcol_id, src_channel_idx, dst_channel_idx, swap=False, dst_all_channels=False):
  # validate input
  if mesh.vertex_colors is None:
    print("mesh has no vertex colors")
    return
  src_vcol = None if src_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[src_vcol_id]
  dst_vcol = None if dst_vcol_id not in mesh.vertex_colors else mesh.vertex_colors[dst_vcol_id]

  if src_vcol is None or dst_vcol is None:
    print("source or destination are invalid")
    return

  if dst_all_channels:
    for loop_index, loop in enumerate(mesh.loops):
      src_val = src_vcol.data[loop_index].color[src_channel_idx]
      dst_vcol.data[loop_index].color = [src_val]*3
  else:
    if src_vcol == dst_vcol and src_channel_idx == dst_channel_idx:
      print("source and destination are the same")
      return

    # perfrom channel copy/swap
    if swap:
      for loop_index, loop in enumerate(mesh.loops):
        src_val = src_vcol.data[loop_index].color[src_channel_idx]
        dst_val = dst_vcol.data[loop_index].color[dst_channel_idx]
        dst_vcol.data[loop_index].color[dst_channel_idx] = src_val
        src_vcol.data[loop_index].color[src_channel_idx] = dst_val
    else:
      for loop_index, loop in enumerate(mesh.loops):
        dst_vcol.data[loop_index].color[dst_channel_idx] = src_vcol.data[loop_index].color[src_channel_idx]  

  mesh.update()


##### MAIN OPERATOR CLASSES #####
class VertexColorMaster_RgbToGrayscale(bpy.types.Operator):
  """Convert the RGB color of a vertex color layer to a grayscale value"""
  bl_idname = 'vertexcolormaster.rgb_to_grayscale'
  bl_label = 'VCM RGB to grayscale'
  bl_options = {'REGISTER', 'UNDO'}

  all_channels = bpy.props.BoolProperty(
    name = "all channels",
    default = True,
    description = "Put the grayscale value in all channels of the destination"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    src_id = context.scene.src_vcol_id
    dst_id = context.scene.dst_vcol_id
    dst_channel_idx = channel_id_to_idx(context.scene.dst_channel_id)
    mesh = context.active_object.data

    convert_rgb_to_luminosity(mesh, src_id, dst_id, dst_channel_idx, self.all_channels)

    return {'FINISHED'}


class VertexColorMaster_CopyChannel(bpy.types.Operator):
  """Copy or swap channel data from one channel to another"""
  bl_idname = 'vertexcolormaster.copy_channel'
  bl_label = 'VCM Copy channel data'
  bl_options = {'REGISTER', 'UNDO'}

  swap_channels = bpy.props.BoolProperty(
    name = "swap channels",
    default = False,
    description = "Swap source and destination channels instead of copy"
    )

  all_channels = bpy.props.BoolProperty(
    name = "all channels",
    default = False,
    description = "Put the copied value in all channels of the destination"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    src_id = context.scene.src_vcol_id
    dst_id = context.scene.dst_vcol_id
    src_channel_idx = channel_id_to_idx(context.scene.src_channel_id)
    dst_channel_idx = channel_id_to_idx(context.scene.dst_channel_id)
    mesh = context.active_object.data

    copy_rgb_channel(mesh, src_id, dst_id, src_channel_idx, dst_channel_idx, self.swap_channels, self.all_channels)

    return {'FINISHED'}


class VertexColorMaster_Fill(bpy.types.Operator):
  """Fill the active vertex color channel(s)"""
  bl_idname = 'vertexcolormaster.fill'
  bl_label = 'VCM Fill'
  bl_options = {'REGISTER', 'UNDO'}

  value = bpy.props.FloatProperty(
    name = "value",
    default = 1.0,
    min = 0.0,
    max = 1.0,
    description = "Value to fill channel(s) with"
    )

  clear_inactive = bpy.props.BoolProperty(
    name = "clear inactive",
    default = False,
    description = "Clear inactive channel(s)"
    )

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    active_channels = context.scene.active_channels
    mesh = context.active_object.data

    if mesh.vertex_colors:
      vcol_layer = mesh.vertex_colors.active
    else:
      vcol_layer = mesh.vertex_colors.new()

    value = self.value
    rmul = 1.0 if not self.clear_inactive or red_id in active_channels else 0.0
    gmul = 1.0 if not self.clear_inactive or green_id in active_channels else 0.0
    bmul = 1.0 if not self.clear_inactive or blue_id in active_channels else 0.0

    for loop_index, loop in enumerate(mesh.loops):
      color = vcol_layer.data[loop_index].color
      vcol_layer.data[loop_index].color = [
        value if red_id in active_channels else color[0] * rmul,
        value if green_id in active_channels else color[1] * gmul,
        value if blue_id in active_channels else color[2] * bmul
        ]

    mesh.vertex_colors.active = vcol_layer
    mesh.update()

    return {'FINISHED'}

class VertexColorMaster_Invert(bpy.types.Operator):
  """Invert active vertex color channel(s)"""
  bl_idname = 'vertexcolormaster.invert'
  bl_label = 'VCM Invert'
  bl_options = {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    active_obj = context.active_object
    return active_obj != None and active_obj.type == 'MESH'

  def execute(self, context):
    active_channels = context.scene.active_channels
    mesh = context.active_object.data

    if mesh.vertex_colors:
      vcol_layer = mesh.vertex_colors.active
    else:
      vcol_layer = mesh.vertex_colors.new()

    for loop_index, loop in enumerate(mesh.loops):
      color = vcol_layer.data[loop_index].color
      if red_id in active_channels:
        color[0] = 1 - color[0]
      if green_id in active_channels:
        color[1] = 1 - color[1]
      if blue_id in active_channels:
        color[2] = 1 - color[2]
      vcol_layer.data[loop_index].color = color

    mesh.vertex_colors.active = vcol_layer
    mesh.update()

    return {'FINISHED'}


##### MAIN CLASS, UI AND REGISTRATION #####
class VertexColorMaster(bpy.types.Panel):
  """COMMENT"""
  bl_space_type = 'VIEW_3D'
  bl_region_type = 'TOOLS'
  bl_label = 'Vertex Color Master'
  bl_category = 'Tools'
  bl_context = 'vertexpaint'

  def update_rgba(self, context):
    active_channels = context.scene.active_channels
    brush_value = context.scene.brush_value

    # set draw color based on mask
    draw_color = [0.0, 0.0, 0.0]
    if red_id in active_channels:
      draw_color[0] = brush_value
    if green_id in active_channels:
      draw_color[1] = brush_value
    if blue_id in active_channels:
      draw_color[2] = brush_value

    bpy.data.brushes['Draw'].color = draw_color

    # update rgba of vertex colors shown in viewport to match mask
    return None

  channel_items = ((red_id, "R", ""), (green_id, "G", ""), (blue_id, "B", ""))#, (alpha_id, "A", ""))

  bpy.types.Scene.active_channels = EnumProperty(
    name="Active Channels",
    options={'ENUM_FLAG'},
    items=channel_items,
    description="Which channels to enable",
    default={'R', 'G', 'B'},
    update=update_rgba,
    )

  bpy.types.Scene.brush_value = FloatProperty(
    name="Brush Value",
    description="Value of the brush color",
    default=1.0,
    min=0.0,
    max=1.0,
    update=update_rgba,
    )

  def vcol_layer_items(self, context):
    mesh = context.active_object.data
    if mesh.vertex_colors == None:
      return [('', '', '')]
    return [(vcol.name, vcol.name, '') for vcol in mesh.vertex_colors]

  bpy.types.Scene.src_vcol_id = EnumProperty(
    name="Source Layer",
    items=vcol_layer_items,
    description="Source vertex color layer",
    )

  bpy.types.Scene.src_channel_id = EnumProperty(
    name="Source Channel",
    items=channel_items,
    description="Source color channel"
    )

  bpy.types.Scene.dst_vcol_id = EnumProperty(
    name="Destination Layer",
    items=vcol_layer_items,
    description="Destination vertex color layer",
    )

  bpy.types.Scene.dst_channel_id = EnumProperty(
    name="Destination Channel",
    items=channel_items,
    description="Destination color channel"
    )


  # @classmethod
  # def poll(cls, context):
  #   active_obj = context.active_object
  #   return active_obj != None and active_obj.type == 'MESH'

  def draw(self, context):
    layout = self.layout

    brush = bpy.data.brushes['Draw']
    col = layout.column(align=True)
    row = col.row()
    row.label('Brush Color')
    row = col.row()
    row.prop(brush, 'color', text = "")
    row.prop(context.scene, 'brush_value', 'Val')

    col = layout.column(align=True)
    row = col.row()
    row.label('Active Channels')
    row = col.row()
    row.prop(context.scene, 'active_channels', expand=True)

    layout.separator()
    row = layout.row(align = True)
    row.operator('vertexcolormaster.fill', 'Fill').value = 1.0
    row.operator('vertexcolormaster.fill', 'Clear').value = 0.0
    row = layout.row()
    row.operator('vertexcolormaster.invert', 'Invert channel(s)')

    lcol_percentage = 0.8
    row = layout.row()
    split = row.split(lcol_percentage, align=True)
    col = split.column(align=True)
    col.prop(context.scene, 'src_vcol_id', 'Src')
    split = split.split(align=True)
    col = split.column(align=True)
    col.prop(context.scene, 'src_channel_id', '')

    row = layout.row()
    split = row.split(lcol_percentage, align=True)
    col = split.column(align=True)
    col.prop(context.scene, 'dst_vcol_id', 'Dst')
    split = split.split(align=True)
    col = split.column(align=True)
    col.prop(context.scene, 'dst_channel_id', '')

    row = layout.row(align=True)
    row.operator('vertexcolormaster.copy_channel', 'Copy').swap_channels = False
    row.operator('vertexcolormaster.copy_channel', 'Swap').swap_channels = True
    row = layout.row()
    row.operator('vertexcolormaster.rgb_to_grayscale', 'Convert to Grayscale')


##### OPERATOR REGISTRATION #####
def register():
  bpy.utils.register_class(VertexColorMaster)
  bpy.utils.register_class(VertexColorMaster_Fill)
  bpy.utils.register_class(VertexColorMaster_Invert)
  bpy.utils.register_class(VertexColorMaster_CopyChannel)
  bpy.utils.register_class(VertexColorMaster_RgbToGrayscale)


def unregister():
  bpy.utils.unregister_class(VertexColorMaster)
  bpy.utils.unregister_class(VertexColorMaster_Fill)
  bpy.utils.unregister_class(VertexColorMaster_Invert)
  bpy.utils.unregister_class(VertexColorMaster_CopyChannel)
  bpy.utils.unregister_class(VertexColorMaster_RgbToGrayscale)


# allows running addon from text editor
if __name__ == '__main__':
  register()