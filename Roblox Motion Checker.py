bl_info = {
    "name": "Roblox Motion Checker",
    "author": "Nultron",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "3D Viewport > N Panel > Roblox Tools",
    "description": "Checks motion speed of animations for Roblox emotions",
    "category": "Animation",
}

import bpy
import bmesh
from mathutils import Vector
import math
import time
from bpy.props import FloatProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import Panel, Operator, PropertyGroup

# Global variables for storing results
motion_problems = []
check_progress = 0.0
check_status = "Ready"
check_timer = None
check_data = None

# List of important bones for Roblox animations
ROBLOX_IMPORTANT_BONES = {
    'Root',
    'HumanoidRootPart', 
    'LowerTorso',
    'RightUpperLeg',
    'RightLowerLeg', 
    'RightFoot',
    'LeftUpperLeg',
    'LeftLowerLeg',
    'LeftFoot',
    'UpperTorso',
    'RightUpperArm',
    'RightLowerArm',
    'RightHand',
    'LeftUpperArm',
    'LeftLowerArm',
    'LeftHand',
    'Head'
}

class RobloxMotionProperties(PropertyGroup):
    max_speed: FloatProperty(
        name="Max Speed",
        description="Maximum speed in studs per frame",
        default=1.0,
        min=0.1,
        max=10.0,
        step=0.1,
        precision=2
    )
    
    check_roblox_bones_only: BoolProperty(
        name="Roblox Bones Only",
        description="Check only bones important for Roblox animations",
        default=True
    )
    
    frame_step: IntProperty(
        name="Frame Step",
        description="Check every Nth frame (1 = all frames)",
        default=1,
        min=1,
        max=10
    )
    
    selected_only: BoolProperty(
        name="Selected Only",
        description="Check only selected objects",
        default=False
    )
    
    selected_rig: bpy.props.PointerProperty(
        name="Selected Rig",
        description="Select a specific armature to check",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )

class RobloxUIProperties(PropertyGroup):
    """Properties for storing UI state"""
    pass

def get_world_position_fast(obj, frame):
    """Fast world coordinates retrieval with caching"""
    scene = bpy.context.scene
    if scene.frame_current != frame:
        scene.frame_set(frame)
    return obj.matrix_world.translation.copy()

def process_chunk():
    """Processes a small portion of the check"""
    global check_data, motion_problems, check_progress, check_status, check_timer
    
    if not check_data or check_data['finished']:
        return None
    
    start_time = time.time()
    chunk_operations = 0
    max_chunk_time = 0.05  # 50ms maximum per chunk
    
    while chunk_operations < 20 and (time.time() - start_time) < max_chunk_time:
        data = check_data
        
        if data['current_obj_idx'] >= len(data['objects_to_check']):
            # Finish check
            data['finished'] = True
            end_time = time.time()
            check_time = end_time - data['start_time']
            
            # FIXED: When rechecking bone, count only new problems
            if 'target_bone' in data:
                # This is a bone recheck - count only found problems
                new_problems_count = data.get('problems_found_during_check', 0)
                if new_problems_count > 0:
                    check_status = f"Recheck completed: found {new_problems_count} problems in {check_time:.1f}s"
                else:
                    check_status = f"Recheck completed: no problems in {check_time:.1f}s"
            else:
                # Regular full check
                if motion_problems:
                    check_status = f"Found {len(motion_problems)} problems in {check_time:.1f}s"
                else:
                    check_status = f"No problems! ({check_time:.1f}s)"
            
            check_progress = 1.0
            return None
        
        obj = data['objects_to_check'][data['current_obj_idx']]
        
        # Process only armatures (bones)
        if obj.type == 'ARMATURE':
            if not data['bone_setup']:
                # Setup bone check once
                try:
                    bpy.context.view_layer.objects.active = obj
                    if bpy.context.mode != 'POSE':
                        bpy.ops.object.mode_set(mode='POSE')
                    
                    # Get list of bones to check
                    if 'target_bone' in data:
                        # Recheck specific bone
                        target_bone_name = data['target_bone']
                        if target_bone_name in ROBLOX_IMPORTANT_BONES or not data['props'].check_roblox_bones_only:
                            data['bones_to_check'] = [target_bone_name]
                            data['current_bone_idx'] = 0
                        else:
                            # Bone not in important list, finish check
                            data['finished'] = True
                            return None
                    else:
                        # Regular check - get list of important bones
                        data['bones_to_check'] = get_important_bones(obj, data['props'].check_roblox_bones_only)
                        data['current_bone_idx'] = 0
                    
                    data['bone_setup'] = True
                except:
                    # Skip armature if we can't switch
                    data['current_obj_idx'] += 1
                    data['current_frame'] = data['start_frame']
                    data['prev_pos'] = None
                    data['bone_setup'] = False
                    continue
            
            # Check if we need to move to next bone
            if data['current_bone_idx'] >= len(data['bones_to_check']):
                # Move to next object
                data['current_obj_idx'] += 1
                data['current_frame'] = data['start_frame']
                data['prev_pos'] = None
                data['bone_setup'] = False
                data['current_bone_idx'] = 0
                continue
            
            bone_name = data['bones_to_check'][data['current_bone_idx']]
            bone = obj.data.bones.get(bone_name)
            if not bone:
                # Bone not found, move to next
                data['current_bone_idx'] += 1
                data['current_frame'] = data['start_frame']
                data['prev_pos'] = None
                continue
            
            if data['current_frame'] == data['start_frame']:
                data['prev_pos'] = get_bone_world_position_fast(obj, bone.name, data['current_frame'])
                data['current_frame'] += data['frame_step']
                chunk_operations += 1
                continue
            
            # Check if we're within animation bounds
            if data['current_frame'] <= data['end_frame']:
                current_pos = get_bone_world_position_fast(obj, bone.name, data['current_frame'])
                
                if current_pos is not None and data['prev_pos'] is not None:
                    distance = (current_pos - data['prev_pos']).length * data['frame_step']
                    
                    if distance > data['max_speed']:
                        problem = {
                            'type': 'bone',
                            'armature': obj.name,
                            'name': bone.name,
                            'frame': data['current_frame'],
                            'distance': distance,
                            'speed': distance / data['frame_step'],
                            'excess': distance - data['max_speed']
                        }
                        
                        # FIXED: When rechecking bone, add problems to temporary list
                        if 'target_bone' in data:
                            if 'recheck_problems' not in data:
                                data['recheck_problems'] = []
                            data['recheck_problems'].append(problem)
                            data['problems_found_during_check'] += 1
                        else:
                            motion_problems.append(problem)
                
                data['prev_pos'] = current_pos
                data['current_frame'] += data['frame_step']
                data['current_operation'] += 1
                check_progress = data['current_operation'] / data['total_operations']
                chunk_operations += 1
            else:
                # Move to next bone
                data['current_bone_idx'] += 1
                data['current_frame'] = data['start_frame']
                data['prev_pos'] = None
                
                # FIXED: When rechecking specific bone, finish after checking it
                if 'target_bone' in data:
                    data['finished'] = True
                    return None
        else:
            # Skip object
            data['current_obj_idx'] += 1
            data['current_frame'] = data['start_frame']
            data['prev_pos'] = None
            data['bone_setup'] = False
    
    return 0.01  # Continue in 10ms

def get_bone_world_position_fast(armature, bone_name, frame):
    """Fast bone coordinate retrieval with optimization"""
    scene = bpy.context.scene
    if scene.frame_current != frame:
        scene.frame_set(frame)
        
    pose_bone = armature.pose.bones.get(bone_name)
    if pose_bone:
        return armature.matrix_world @ pose_bone.matrix @ Vector((0, 0, 0))
    return None

def get_important_bones(armature, check_roblox_only=True):
    """Get list of important bones to check"""
    if not check_roblox_only:
        return [bone.name for bone in armature.data.bones]
    
    # Filter only important bones
    important_bones = []
    for bone in armature.data.bones:
        if bone.name in ROBLOX_IMPORTANT_BONES:
            important_bones.append(bone.name)
    
    return important_bones

# Global dictionary for storing expansion states
expansion_states = {}

def get_expansion_state(key):
    """Get expansion state for key"""
    return expansion_states.get(key, False)

def set_expansion_state(key, state):
    """Set expansion state for key"""
    expansion_states[key] = state

class ROBLOX_OT_check_motion(Operator):
    bl_idname = "roblox.check_motion"
    bl_label = "Check Animation"
    bl_description = "Check motion speed in animation"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        global motion_problems, check_progress, check_status, check_timer, check_data
        
        # FIXED: Improved stop check logic
        if check_timer is not None:
            try:
                context.window_manager.event_timer_remove(check_timer)
            except:
                pass
            check_timer = None
            check_data = None  # Clear check data
            check_status = "Stopped"
            return {'FINISHED'}
        
        props = context.scene.roblox_motion_props
        motion_problems.clear()
        check_progress = 0.0
        check_status = "Initializing..."
        
        scene = context.scene
        # FIXED: Proper animation bounds retrieval
        start_frame = scene.frame_start
        end_frame = scene.frame_end
        frame_step = props.frame_step
        max_speed = props.max_speed
        
        # Get list of armatures to check
        objects_to_check = []
        if props.selected_only:
            objects_to_check = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        else:
            objects_to_check = [obj for obj in scene.objects if obj.type == 'ARMATURE']
        
        if not objects_to_check:
            self.report({'WARNING'}, "No armatures to check")
            check_status = "No armatures"
            return {'CANCELLED'}
        
        # Calculate total operations for bones
        total_operations = 0
        for obj in objects_to_check:
            if obj.type == 'ARMATURE':
                # Get number of important bones to check
                bones_to_check = get_important_bones(obj, props.check_roblox_bones_only)
                total_operations += len(bones_to_check) * (((end_frame - start_frame) // frame_step) + 1)
        
        if total_operations == 0:
            self.report({'WARNING'}, "No bones to check")
            check_status = "No bones"
            return {'CANCELLED'}
        
        # Save original state
        original_frame = scene.frame_current
        original_mode = context.mode
        original_active = context.view_layer.objects.active
        
        # Initialize data for async check
        check_data = {
            'objects_to_check': objects_to_check,
            'start_frame': start_frame,
            'end_frame': end_frame,
            'frame_step': frame_step,
            'max_speed': max_speed,
            'props': props,
            'total_operations': total_operations,
            'current_operation': 0,
            'current_obj_idx': 0,
            'current_frame': start_frame,
            'current_bone_idx': 0,
            'prev_pos': None,
            'bone_setup': False,
            'finished': False,
            'start_time': time.time(),
            'original_frame': original_frame,
            'original_mode': original_mode,
            'original_active': original_active
        }
        
        # Make sure we're in object mode
        try:
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        
        # Start timer for async processing
        check_timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        
        check_status = "Checking..."
        self.report({'INFO'}, "Check started")
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        global check_data, check_timer, check_status
        
        if event.type == 'TIMER':
            result = process_chunk()
            
            if result is None:  # Check completed
                # Restore original state
                try:
                    context.scene.frame_set(check_data['original_frame'])
                    if check_data['original_active']:
                        context.view_layer.objects.active = check_data['original_active']
                    if check_data['original_mode'] != context.mode:
                        if 'OBJECT' in check_data['original_mode']:
                            bpy.ops.object.mode_set(mode='OBJECT')
                        elif 'POSE' in check_data['original_mode'] and check_data['original_active'] and check_data['original_active'].type == 'ARMATURE':
                            bpy.ops.object.mode_set(mode='POSE')
                except:
                    pass
                
                # FIXED: Safe timer removal
                if check_timer is not None:
                    try:
                        context.window_manager.event_timer_remove(check_timer)
                    except:
                        pass
                    check_timer = None
                
                # Report result
                if motion_problems:
                    self.report({'WARNING'}, f"Found {len(motion_problems)} problems!")
                else:
                    self.report({'INFO'}, "Animation ready for Roblox!")
                
                return {'FINISHED'}
            
            # Update interface
            context.area.tag_redraw()
            
        elif event.type == 'ESC':
            # Cancel check
            if check_timer is not None:
                try:
                    context.window_manager.event_timer_remove(check_timer)
                except:
                    pass
                check_timer = None
            check_status = "Cancelled"
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}

class ROBLOX_OT_jump_to_problem(Operator):
    bl_idname = "roblox.jump_to_problem"
    bl_label = "Jump to Problem"
    bl_description = "Jump to frame with problem"
    
    problem_index: IntProperty()
    
    def execute(self, context):
        global motion_problems
        
        if 0 <= self.problem_index < len(motion_problems):
            problem = motion_problems[self.problem_index]
            
            # Jump to problem frame
            context.scene.frame_set(problem['frame'])
            
            # Make sure we're in correct mode
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Select object/bone
            if problem['type'] == 'object':
                obj = bpy.data.objects.get(problem['name'])
                if obj and obj.name in context.view_layer.objects:
                    # Clear selection safely
                    for o in context.selected_objects:
                        o.select_set(False)
                    
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    
            elif problem['type'] == 'bone':
                armature = bpy.data.objects.get(problem['armature'])
                if armature and armature.name in context.view_layer.objects:
                    # Clear selection safely
                    for o in context.selected_objects:
                        o.select_set(False)
                    
                    armature.select_set(True)
                    context.view_layer.objects.active = armature
                    
                    # Switch to pose mode
                    try:
                        if context.mode != 'POSE':
                            bpy.ops.object.mode_set(mode='POSE')
                        
                        # Clear bone selection
                        for bone in armature.pose.bones:
                            bone.bone.select = False
                        
                        # Select needed bone
                        pose_bone = armature.pose.bones.get(problem['name'])
                        if pose_bone:
                            pose_bone.bone.select = True
                            armature.data.bones.active = pose_bone.bone
                    except:
                        # If can't switch to pose mode, just select armature
                        pass
        
        return {'FINISHED'}

class ROBLOX_OT_clear_results(Operator):
    bl_idname = "roblox.clear_results"
    bl_label = "Clear Results"
    bl_description = "Clear check results"
    
    def execute(self, context):
        global motion_problems, check_progress, check_status
        motion_problems.clear()
        check_progress = 0.0
        check_status = "Ready"
        context.area.tag_redraw()
        return {'FINISHED'}

class ROBLOX_PT_motion_checker(bpy.types.Panel):
    bl_label = "Roblox Motion Checker"
    bl_idname = "ROBLOX_PT_motion_checker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Roblox Tools"
    
    def draw(self, context):
        global motion_problems, check_progress, check_status
        
        layout = self.layout
        props = context.scene.roblox_motion_props
        
        # Check settings
        box = layout.box()
        box.label(text="Check Settings:", icon='SETTINGS')
        
        row = box.row()
        row.prop(props, "max_speed")
        
        row = box.row(align=True)
        row.prop(props, "check_roblox_bones_only")
        
        row = box.row(align=True)
        row.prop(props, "frame_step")
        row.prop(props, "selected_only")

        row = box.row(align=True)
        row.prop(props, "selected_rig")
        
        # Check button
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        
        # Change button text based on state
        if check_timer is not None:  # FIXED: Check for None
            row.operator("roblox.check_motion", text="⏹ Stop Check", icon='PAUSE')
        else:
            row.operator("roblox.check_motion", text="▶ Check Animation", icon='PLAY')
        
        # Progress bar
        if 0 < check_progress < 1:
            layout.separator()
            row = layout.row()
            row.progress(factor=check_progress, text=f"Progress: {check_progress*100:.0f}%")
        
        # Status
        layout.separator()
        row = layout.row()
        row.label(text=f"Status: {check_status}")
        
        # Results
        if motion_problems:
             layout.separator()
             box = layout.box()
             
             # Results header
             row = box.row(align=True)
             row.label(text=f"Problems found: {len(motion_problems)}", icon='ERROR')
             
             # Control buttons
             row.operator("roblox.expand_all", text="", icon='DISCLOSURE_TRI_DOWN')
             row.operator("roblox.collapse_all", text="", icon='DISCLOSURE_TRI_RIGHT')
             row.operator("roblox.clear_results", text="", icon='X')
             
             # Group problems by bones
             grouped_problems = {}
             for i, problem in enumerate(motion_problems):
                 key = f"🦴 {problem['armature']}.{problem['name']}"
                 
                 if key not in grouped_problems:
                     grouped_problems[key] = []
                 grouped_problems[key].append((i, problem))
             
             # Show all groups
             for item_name, item_problems in grouped_problems.items():
                 
                 # Create unique key for expansion state
                 expand_key = f"expand_{item_name.replace(' ', '_').replace('.', '_')}"
                 
                 # Group header with expand button
                 row = box.row(align=True)
                 
                 # Expand/collapse button
                 expand_icon = 'DISCLOSURE_TRI_DOWN' if get_expansion_state(expand_key) else 'DISCLOSURE_TRI_RIGHT'
                 op = row.operator("roblox.toggle_expand", text="", icon=expand_icon)
                 op.expand_key = expand_key
                 
                 # Group name with problem count
                 problem_count = len(item_problems)
                 severity_icon = "🔴" if any(p[1]['excess'] > 2.0 for p in item_problems) else "🟠" if any(p[1]['excess'] > 1.0 for p in item_problems) else "🟡"
                 row.label(text=f"{item_name} ({problem_count}) {severity_icon}")
                 
                 # Recheck button for bones
                 clean_name = item_name.lstrip('🦴 ').strip()
                 parts = clean_name.rsplit('.', 1)
                 if len(parts) == 2:
                     armature = parts[0].strip()
                     bone = parts[1].strip()
                     op = row.operator("roblox.recheck_bone", text="", icon='FILE_REFRESH')
                     op.armature_name = armature
                     op.bone_name = bone
                 
                 # Show problems if group is expanded
                 if get_expansion_state(expand_key):
                     for j, (problem_index, problem) in enumerate(item_problems):
                         # Indent for nesting
                         problem_row = box.row()
                         problem_row.alignment = 'LEFT'
                         
                         # Empty space for indent
                         problem_row.label(text="    ")
                         
                         # Jump to problem button
                         op = problem_row.operator("roblox.jump_to_problem", 
                                                 text=f"frame {problem['frame']}: {problem['speed']:.2f} st/f")
                         op.problem_index = problem_index
        
        elif check_status.startswith("No problems"):
            layout.separator()
            row = layout.row()
            row.label(text="✅ Animation ready for Roblox!", icon='CHECKMARK')




class ROBLOX_OT_toggle_expand(bpy.types.Operator):
    bl_idname = "roblox.toggle_expand"
    bl_label = "Expand/Collapse"
    bl_description = "Expand or collapse problem list"
    
    expand_key: bpy.props.StringProperty()
    
    def execute(self, context):
        current_state = get_expansion_state(self.expand_key)
        set_expansion_state(self.expand_key, not current_state)
        context.area.tag_redraw()
        return {'FINISHED'}

class ROBLOX_OT_expand_all(bpy.types.Operator):
    bl_idname = "roblox.expand_all"
    bl_label = "Expand All"
    bl_description = "Expand all problem groups"
    
    def execute(self, context):
        global motion_problems
        
        # Group problems by bones
        grouped_problems = {}
        for i, problem in enumerate(motion_problems):
            key = f"🦴 {problem['armature']}.{problem['name']}"
            
            if key not in grouped_problems:
                grouped_problems[key] = []
            grouped_problems[key].append((i, problem))
        
        # Expand all groups
        for item_name in grouped_problems.keys():
            expand_key = f"expand_{item_name.replace(' ', '_').replace('.', '_')}"
            set_expansion_state(expand_key, True)
        
        context.area.tag_redraw()
        return {'FINISHED'}

class ROBLOX_OT_collapse_all(bpy.types.Operator):
    bl_idname = "roblox.collapse_all"
    bl_label = "Collapse All"
    bl_description = "Collapse all problem groups"
    
    def execute(self, context):
        global motion_problems
        
        # Group problems by bones
        grouped_problems = {}
        for i, problem in enumerate(motion_problems):
            key = f"🦴 {problem['armature']}.{problem['name']}"
            
            if key not in grouped_problems:
                grouped_problems[key] = []
            grouped_problems[key].append((i, problem))
        
        # Collapse all groups
        for item_name in grouped_problems.keys():
            expand_key = f"expand_{item_name.replace(' ', '_').replace('.', '_')}"
            set_expansion_state(expand_key, False)
        
        context.area.tag_redraw()
        return {'FINISHED'}

class ROBLOX_OT_recheck_bone(bpy.types.Operator):
    bl_idname = "roblox.recheck_bone"
    bl_label = "Recheck Bone"
    bl_description = "Check motion only for this bone"
    
    armature_name: bpy.props.StringProperty()
    bone_name: bpy.props.StringProperty()
    
    def execute(self, context):
        global motion_problems, check_data, check_timer, check_progress, check_status
        
        # Stop current check if running
        if check_timer is not None:
            context.window_manager.event_timer_remove(check_timer)
            check_timer = None
        
        armature = bpy.data.objects.get(self.armature_name)
        if not armature or armature.type != 'ARMATURE':
            self.report({'ERROR'}, "Armature not found")
            return {'CANCELLED'}
        
        bone = armature.pose.bones.get(self.bone_name)
        if not bone:
            self.report({'ERROR'}, "Bone not found")
            return {'CANCELLED'}
        
        # FIXED: Completely remove old problems for this bone
        old_problem_count = len([p for p in motion_problems if p['type'] == 'bone' and p['armature'] == self.armature_name and p['name'] == self.bone_name])
        motion_problems[:] = [p for p in motion_problems if not (p['type'] == 'bone' and p['armature'] == self.armature_name and p['name'] == self.bone_name)]
        
        # Initialize data for checking only this bone
        props = context.scene.roblox_motion_props
        start_frame = context.scene.frame_start
        end_frame = context.scene.frame_end
        frame_step = props.frame_step
        max_speed = props.max_speed
        
        check_objects = [armature]  # Only this armature
        total_operations = ((end_frame - start_frame) // frame_step + 1) * 1  # Only one bone
        
        # Save original state
        original_frame = context.scene.frame_current
        original_mode = context.mode
        original_active = context.view_layer.objects.active
        
        # FIXED: Create new data for recheck without saving old problems
        check_data = {
             'objects_to_check': check_objects,
             'start_frame': start_frame,
             'end_frame': end_frame,
             'frame_step': frame_step,
             'max_speed': max_speed,
             'props': props,
             'total_operations': total_operations,
             'current_operation': 0,
             'current_obj_idx': 0,
             'current_frame': start_frame,
             'current_bone_idx': 0,
             'prev_pos': None,
             'bone_setup': False,
             'finished': False,
             'start_time': time.time(),
             'original_frame': original_frame,
             'original_mode': original_mode,
             'original_active': original_active,
             'target_bone': self.bone_name,  # Target bone for recheck
             'problems_found_during_check': 0,  # Counter for new problems
             'recheck_problems': []  # List of problems found during recheck
         }
        
        check_progress = 0.0
        check_status = f"Rechecking bone {self.bone_name}..."
        
        # Start timer for async check
        check_timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        global check_data, check_timer, check_status, motion_problems
        
        if event.type == 'TIMER':
            result = process_chunk()
            
            if result is None:  # Check completed
                # FIXED: Add found problems to main list
                if 'recheck_problems' in check_data:
                    motion_problems.extend(check_data['recheck_problems'])
                
                # Restore original state
                try:
                    context.scene.frame_set(check_data['original_frame'])
                    if check_data['original_active']:
                        context.view_layer.objects.active = check_data['original_active']
                    if check_data['original_mode'] != context.mode:
                        if 'OBJECT' in check_data['original_mode']:
                            bpy.ops.object.mode_set(mode='OBJECT')
                        elif 'POSE' in check_data['original_mode'] and check_data['original_active'] and check_data['original_active'].type == 'ARMATURE':
                            bpy.ops.object.mode_set(mode='POSE')
                except:
                    pass
                
                # Stop timer
                if check_timer is not None:
                    try:
                        context.window_manager.event_timer_remove(check_timer)
                    except:
                        pass
                    check_timer = None
                
                # Update status with results
                problems_found = check_data.get('problems_found_during_check', 0)
                if problems_found > 0:
                    self.report({'WARNING'}, f"Found {problems_found} problems in bone {self.bone_name}")
                else:
                    self.report({'INFO'}, f"Bone {self.bone_name} checked - no problems")
                
                context.area.tag_redraw()
                return {'FINISHED'}
            
            # Update interface
            context.area.tag_redraw()
            
        elif event.type == 'ESC':
            # Cancel check
            if check_timer is not None:
                try:
                    context.window_manager.event_timer_remove(check_timer)
                except:
                    pass
                check_timer = None
            check_status = "Cancelled"
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
                
# Register classes
classes = [
    RobloxMotionProperties,
    RobloxUIProperties,
    ROBLOX_OT_check_motion,
    ROBLOX_OT_jump_to_problem,
    ROBLOX_OT_clear_results,
    ROBLOX_PT_motion_checker,
    ROBLOX_OT_toggle_expand,
    ROBLOX_OT_expand_all,
    ROBLOX_OT_collapse_all,
    ROBLOX_OT_recheck_bone,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.roblox_motion_props = bpy.props.PointerProperty(type=RobloxMotionProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.roblox_motion_props

if __name__ == "__main__":
    register()
