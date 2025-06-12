import bpy
import bpy_extras.object_utils
import math
import random
from mathutils import Vector

#This blender script generates a 3D chessboard from a FEN string and renders it.
SQUARE_SIZE = 1.5
CAMERA_HEIGHT = 15
CIRCLE_RADIUS = 20
LIGHT_ENERGY = 10000
LIGHT_SIZE = 10
LIGHT_OFFSET = Vector((2, -2, 4))
X_RES = 1440
Y_RES = 1280
RENDER = True

##################################
CAMERA_ANGLE = 1.25 * math.pi + 0.2

RANDOMIZE_ANGLES = True
angles = [0.25 * math.pi, 0.75 * math.pi, 1.25 * math.pi, 1.75 * math.pi]

if RANDOMIZE_ANGLES:
    CAMERA_ANGLE = random.choice(angles) + 0.3
####################################
RED_CORNER = "a1"
BLUE_CORNER = "h1"

RANDOMIZE_CORNERS = True
ALLOWED_CORNERS = ["a1", "a8", "h1", "h8"]

if RANDOMIZE_CORNERS:
    # Randomly pick two different corners.
    RED_CORNER, BLUE_CORNER = random.sample(ALLOWED_CORNERS, 2)

if RED_CORNER not in ALLOWED_CORNERS or BLUE_CORNER not in ALLOWED_CORNERS:
    raise ValueError("RED_CORNER and BLUE_CORNER must be one of 'a1', 'a8', 'h1', or 'h8'")
if RED_CORNER == BLUE_CORNER:
    raise ValueError("RED_CORNER and BLUE_CORNER must be two different squares.")

######################################
# Mapping from FEN letter to Blender object name.
FEN_TO_OBJECT = {
    'P': "WhitePawn",  # uppercase => White
    'R': "WhiteRook",
    'N': "WhiteKnight",
    'B': "WhiteBishop",
    'Q': "WhiteQueen",
    'K': "WhiteKing",
    'p': "BlackPawn",  # lowercase => Black
    'r': "BlackRook",
    'n': "BlackKnight",
    'b': "BlackBishop",
    'q': "BlackQueen",
    'k': "BlackKing",
}

OBJECT_TO_Z = {
    'WhitePawn': 0.31,
    'WhiteRook': 0.34,
    'WhiteKnight': 0.005,
    'WhiteBishop': 1,
    'WhiteQueen': 0.5,
    'WhiteKing': 0.5,
    'BlackPawn': 0.31,
    'BlackRook': 0.34,
    'BlackKnight': 0.005,
    'BlackBishop': 1,
    'BlackQueen': 0.5,
    'BlackKing': 0.5,
}

def clear_chess_collection(collection_name="ChessSet"):
    """
    If a collection named collection_name exists, delete all its objects and remove the collection.
    """
    if collection_name in bpy.data.collections:
        chess_coll = bpy.data.collections[collection_name]
        # Delete all objects in the collection
        for obj in list(chess_coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        # Remove the collection itself
        bpy.data.collections.remove(chess_coll)
        print(f"Cleared collection '{collection_name}'.")
        
    # Delete the chess set material if it exists
    if "ChessboardMaterial" in bpy.data.materials:
        chess_material = bpy.data.materials["ChessboardMaterial"]
        bpy.data.materials.remove(chess_material, do_unlink=True)


def get_or_create_chess_collection(collection_name="ChessSet"):
    """
    Retrieves the chess collection if it exists, otherwise creates a new one and links it to the scene.
    """
    if collection_name in bpy.data.collections:
        return bpy.data.collections[collection_name]
    else:
        new_coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(new_coll)
        return new_coll
    
def create_or_update_camera(angle=None, camera_height=15.0, circle_radius=20.0):
    """
    Deletes any existing camera named "ChessCamera" and creates a new one.
    
    The camera is placed at a constant height above the chessboard and
    on a circle of radius circle_radius around the board's center.
    
    If angle is None, a random angle (in radians) is chosen; otherwise,
    the given angle is used (0 is along the positive X axis).
    """
    camera_name = "ChessCamera"
    
    # Delete the previous camera if it exists
    if camera_name in bpy.data.objects:
        old_camera = bpy.data.objects[camera_name]
        bpy.data.objects.remove(old_camera, do_unlink=True)
    
    # Use a random angle if none is provided.
    if angle is None:
        angle = random.uniform(0, 2 * math.pi)
    
    # Compute the chessboard's center.
    board_size = 8 * SQUARE_SIZE
    board_center = Vector((board_size/2 - SQUARE_SIZE/2,
                           board_size/2 - SQUARE_SIZE/2,
                           0))
    
    # Calculate the camera's position on the circle.
    cam_x = board_center.x + circle_radius * math.cos(angle)
    cam_y = board_center.y + circle_radius * math.sin(angle)
    cam_z = camera_height  # constant height
    cam_location = Vector((cam_x, cam_y, cam_z))
    
    # Create a new camera data-block and object.
    cam_data = bpy.data.cameras.new(camera_name)
    cam_obj = bpy.data.objects.new(camera_name, cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = cam_location

    # Orient the camera to look at the chessboard center.
    direction = board_center - cam_location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    return cam_obj

def create_or_update_light_relative_to_camera(camera, light_energy = 1000, light_size = 4, light_offset=Vector((2, -2, 4))):
    """
    Creates or updates an area light named "KeyLight", parents it to the camera,
    and positions it with the given offset in the camera's local space.
    """
    light_name = "KeyLight"
    
    # Delete the previous light if it exists
    if light_name in bpy.data.objects:
        old_light = bpy.data.objects[light_name]
        bpy.data.objects.remove(old_light, do_unlink=True)
    
    # Create new light data and object
    light_data = bpy.data.lights.new(name=light_name, type='AREA')
    light_data.energy = light_energy
    light_data.size = light_size

    light_obj = bpy.data.objects.new(name=light_name, object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    
    # Parent the light to the camera so that it follows the camera's movement
    light_obj.parent = camera
    light_obj.location = light_offset  # in camera's local coordinates
    
    return light_obj

def parse_fen(fen_string):
    """
    Parse the piece placement part of a FEN string into a list of 
    (file, rank, piece_letter).
    """
    piece_placement = fen_string.split(' ')[0]
    ranks = piece_placement.split('/')
    
    piece_positions = []
    for rank_index, rank_substring in enumerate(ranks):
        file_index = 0
        for char in rank_substring:
            if char.isdigit():
                file_index += int(char)
            else:
                actual_rank = 7 - rank_index
                piece_positions.append((file_index, actual_rank, char))
                file_index += 1

    return piece_positions

def place_piece(object_name, file_idx, rank_idx, chess_coll):
    """
    Duplicates the piece with the given object_name and places it at (file_idx, rank_idx).
    """
    source_obj = bpy.data.objects.get(object_name)
    if not source_obj:
        print(f"Object '{object_name}' not found in the blend file.")
        return

    new_piece = source_obj.copy()
    new_piece.data = source_obj.data.copy()  # full copy of mesh data
    chess_coll.objects.link(new_piece)
    
    x_pos = file_idx * SQUARE_SIZE
    y_pos = rank_idx * SQUARE_SIZE
    z_pos = OBJECT_TO_Z.get(object_name, 0)
    new_piece.location = (x_pos, y_pos, z_pos)

def create_chessboard(chess_coll):
    """
    Creates an 8x8 chessboard plane with a green-tan checker pattern.
    Two corner squares are overridden with solid red and blue.
    Their positions are determined by the global variables RED_CORNER and BLUE_CORNER.
    
    The node setup works as follows:
      - It uses the board’s UVs (from 0 to 1) and then, for each override,
        conditionally “flips” the X and/or Y so that the target square becomes
        the region where (local X < 1/8 and local Y < 1/8).
    """
    board_size = 8 * SQUARE_SIZE

    # 1) Create a plane for the board.
    bpy.ops.mesh.primitive_plane_add(
        size=board_size,
        location=(board_size/2 - SQUARE_SIZE/2,
                  board_size/2 - SQUARE_SIZE/2,
                  0)
    )
    board = bpy.context.active_object
    board.name = "Chessboard"

    # 2) UV unwrap the board.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 3) Create a new checkerboard material with nodes.
    mat = bpy.data.materials.new("ChessboardMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Remove default nodes.
    for node in nodes:
        nodes.remove(node)

    # --- Create necessary nodes ---
    tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
    tex_coord_node.location = (-1000, 0)

    checker_node = nodes.new(type='ShaderNodeTexChecker')
    checker_node.location = (-600, 0)
    checker_node.inputs['Scale'].default_value = 8.0
    checker_node.inputs['Color1'].default_value = (0.0, 0.5, 0.0, 1.0)  # Green
    checker_node.inputs['Color2'].default_value = (0.71, 0.58, 0.41, 1.0)  # Tan

    # Separate the UV into X and Y.
    separate_xyz = nodes.new(type='ShaderNodeSeparateXYZ')
    separate_xyz.location = (-800, -200)
    links.new(tex_coord_node.outputs['UV'], separate_xyz.inputs[0])

    # --- Determine flip settings based on the chosen corner squares ---
    # For our node math, we want to remap the chosen square to the region (0, 1/8) in both axes.
    # The following dictionary maps each corner to a tuple (flip_x, flip_y):
    # For example, for red:
    #   - if RED_CORNER is "a1", we use (True, False) meaning: new_x = 1 - X, new_y = Y.
    #   - if "a8", use (False, False) meaning: no flip.
    #   - if "h1", use (True, True)
    #   - if "h8", use (False, True)
    corner_transform = {
        "a1": (True,  False),
        "h1": (True,  True),
        "a8": (False, False),
        "h8": (False, True)
    }
    red_flip_x, red_flip_y = corner_transform[RED_CORNER]
    blue_flip_x, blue_flip_y = corner_transform[BLUE_CORNER]

    # --- Create Red Mask Nodes ---
    # For X:
    if red_flip_x:
        red_flip_x_node = nodes.new(type='ShaderNodeMath')
        red_flip_x_node.operation = 'SUBTRACT'
        red_flip_x_node.inputs[0].default_value = 1.0
        red_flip_x_node.label = f"Red: Flip X ({RED_CORNER})"
        red_flip_x_node.location = (-600, -250)
        links.new(separate_xyz.outputs['X'], red_flip_x_node.inputs[1])
        red_x_output = red_flip_x_node.outputs[0]
    else:
        red_x_output = separate_xyz.outputs['X']
    # For Y:
    if red_flip_y:
        red_flip_y_node = nodes.new(type='ShaderNodeMath')
        red_flip_y_node.operation = 'SUBTRACT'
        red_flip_y_node.inputs[0].default_value = 1.0
        red_flip_y_node.label = f"Red: Flip Y ({RED_CORNER})"
        red_flip_y_node.location = (-600, -350)
        links.new(separate_xyz.outputs['Y'], red_flip_y_node.inputs[1])
        red_y_output = red_flip_y_node.outputs[0]
    else:
        red_y_output = separate_xyz.outputs['Y']

    # Compare remapped X and Y to 1/8.
    red_less_x = nodes.new(type='ShaderNodeMath')
    red_less_x.operation = 'LESS_THAN'
    red_less_x.inputs[1].default_value = 1/8
    red_less_x.location = (-400, -250)
    links.new(red_x_output, red_less_x.inputs[0])

    red_less_y = nodes.new(type='ShaderNodeMath')
    red_less_y.operation = 'LESS_THAN'
    red_less_y.inputs[1].default_value = 1/8
    red_less_y.location = (-400, -350)
    links.new(red_y_output, red_less_y.inputs[0])

    red_mask = nodes.new(type='ShaderNodeMath')
    red_mask.operation = 'MULTIPLY'
    red_mask.location = (-200, -300)
    links.new(red_less_x.outputs[0], red_mask.inputs[0])
    links.new(red_less_y.outputs[0], red_mask.inputs[1])

    # --- Create Blue Mask Nodes ---
    if blue_flip_x:
        blue_flip_x_node = nodes.new(type='ShaderNodeMath')
        blue_flip_x_node.operation = 'SUBTRACT'
        blue_flip_x_node.inputs[0].default_value = 1.0
        blue_flip_x_node.label = f"Blue: Flip X ({BLUE_CORNER})"
        blue_flip_x_node.location = (-600, -500)
        links.new(separate_xyz.outputs['X'], blue_flip_x_node.inputs[1])
        blue_x_output = blue_flip_x_node.outputs[0]
    else:
        blue_x_output = separate_xyz.outputs['X']

    if blue_flip_y:
        blue_flip_y_node = nodes.new(type='ShaderNodeMath')
        blue_flip_y_node.operation = 'SUBTRACT'
        blue_flip_y_node.inputs[0].default_value = 1.0
        blue_flip_y_node.label = f"Blue: Flip Y ({BLUE_CORNER})"
        blue_flip_y_node.location = (-600, -600)
        links.new(separate_xyz.outputs['Y'], blue_flip_y_node.inputs[1])
        blue_y_output = blue_flip_y_node.outputs[0]
    else:
        blue_y_output = separate_xyz.outputs['Y']

    blue_less_x = nodes.new(type='ShaderNodeMath')
    blue_less_x.operation = 'LESS_THAN'
    blue_less_x.inputs[1].default_value = 1/8
    blue_less_x.location = (-400, -500)
    links.new(blue_x_output, blue_less_x.inputs[0])

    blue_less_y = nodes.new(type='ShaderNodeMath')
    blue_less_y.operation = 'LESS_THAN'
    blue_less_y.inputs[1].default_value = 1/8
    blue_less_y.location = (-400, -600)
    links.new(blue_y_output, blue_less_y.inputs[0])

    blue_mask = nodes.new(type='ShaderNodeMath')
    blue_mask.operation = 'MULTIPLY'
    blue_mask.location = (-200, -550)
    links.new(blue_less_x.outputs[0], blue_mask.inputs[0])
    links.new(blue_less_y.outputs[0], blue_mask.inputs[1])

    # --- Mix Nodes for Overriding Colors ---
    # First mix: override with red where red_mask is active.
    mix_red = nodes.new(type='ShaderNodeMixRGB')
    mix_red.blend_type = 'MIX'
    mix_red.location = (0, 0)
    links.new(red_mask.outputs[0], mix_red.inputs['Fac'])
    links.new(checker_node.outputs['Color'], mix_red.inputs['Color1'])
    mix_red.inputs['Color2'].default_value = (1.0, 0.0, 0.0, 1.0)  # red

    # Second mix: override with blue where blue_mask is active.
    mix_blue = nodes.new(type='ShaderNodeMixRGB')
    mix_blue.blend_type = 'MIX'
    mix_blue.location = (200, 0)
    links.new(blue_mask.outputs[0], mix_blue.inputs['Fac'])
    links.new(mix_red.outputs['Color'], mix_blue.inputs['Color1'])
    mix_blue.inputs['Color2'].default_value = (0.0, 0.0, 1.0, 1.0)  # blue

    # Principled BSDF and Material Output.
    principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled_node.location = (400, 0)
    links.new(mix_blue.outputs['Color'], principled_node.inputs['Base Color'])

    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (600, 0)
    links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])

    # Assign the material to the board.
    board.data.materials.append(mat)

    # Link the board to the chess collection and remove from default.
    if board.name not in chess_coll.objects:
        chess_coll.objects.link(board)
        bpy.context.scene.collection.objects.unlink(board)

def create_chess_position(fen_string):
    """
    Clears any existing chess objects, creates a new chess collection,
    then creates the chessboard and places pieces based on the FEN string.
    """
    clear_chess_collection("ChessSet")
    chess_coll = get_or_create_chess_collection("ChessSet")
    
    create_chessboard(chess_coll)
    piece_positions = parse_fen(fen_string)
    for (file_idx, rank_idx, fen_char) in piece_positions:
        if fen_char in FEN_TO_OBJECT:
            object_name = FEN_TO_OBJECT[fen_char]
            place_piece(object_name, file_idx, rank_idx, chess_coll)
        else:
            print(f"Unrecognized FEN piece char: {fen_char}")

# ---------------------------------------------------------
# Example usage:
# ---------------------------------------------------------
fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

create_chess_position(fen)
camera = create_or_update_camera(CAMERA_ANGLE, CAMERA_HEIGHT, CIRCLE_RADIUS)
if camera:
    bpy.context.scene.camera = camera  # Set active camera
    create_or_update_light_relative_to_camera(camera, LIGHT_ENERGY, LIGHT_SIZE, LIGHT_OFFSET)
else:
    print("Camera 'ChessCamera' was not created successfully.")

# Set render resolution.
scene = bpy.context.scene
scene.render.resolution_x = X_RES
scene.render.resolution_y = Y_RES
scene.render.pixel_aspect_x = 1.0
scene.render.pixel_aspect_y = 1.0

# Set output filepath and file format.
scene.render.filepath = "chess_render.png"
scene.render.image_settings.file_format = 'PNG'

if RENDER:
    bpy.ops.render.render(write_still=True)