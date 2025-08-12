# Roblox Motion Checker

A Blender addon for checking animation motion speed to ensure compatibility with Roblox animation constraints.

## 📋 Overview

The Roblox Motion Checker addon helps animators ensure their bone animations meet Roblox's motion speed requirements. It analyzes bone movement throughout your animation timeline and identifies frames where bones move too quickly, which could cause issues when uploaded to Roblox.

## ✨ Features

- **Real-time Motion Analysis**: Checks bone movement speed across animation frames
- **Roblox-Specific Bone Detection**: Focuses on bones important for Roblox character rigs
- **Asynchronous Processing**: Non-blocking checks that don't freeze Blender
- **Interactive Problem Navigation**: Jump directly to problematic frames
- **Individual Bone Rechecking**: Recheck specific bones after making fixes
- **Expandable Results**: Organize problems by bone with collapsible groups
- **Progress Tracking**: Real-time progress bar and status updates

## 🎯 Supported Roblox Bones

The addon automatically detects and prioritizes these important Roblox bones:

- **Root/Core**: `Root`, `HumanoidRootPart`, `LowerTorso`, `UpperTorso`
- **Arms**: `RightUpperArm`, `RightLowerArm`, `RightHand`, `LeftUpperArm`, `LeftLowerArm`, `LeftHand`
- **Legs**: `RightUpperLeg`, `RightLowerLeg`, `RightFoot`, `LeftUpperLeg`, `LeftLowerLeg`, `LeftFoot`
- **Head**: `Head`

## 🚀 Installation

1. Download the `Roblox Motion Checker.py` file
2. Open Blender and go to `Edit > Preferences > Add-ons`
3. Click `Install...` and select the downloaded file
4. Enable the "Roblox Motion Checker" addon
5. The panel will appear in the 3D Viewport's N-Panel under "Roblox Tools"

## 🛠️ Usage

### Basic Workflow

1. **Open your animation** with rigged character
2. **Access the addon** in 3D Viewport > N-Panel > Roblox Tools
3. **Configure settings**:
   - **Max Speed**: Set maximum allowed speed (default: 1.0 studs/frame)
   - **Roblox Bones Only**: Check only important Roblox bones
   - **Frame Step**: Check every Nth frame (1 = all frames)
   - **Selected Only**: Limit check to selected armatures
4. **Click "Check Animation"** to start analysis
5. **Review results** in the expandable problem list

### Settings Explained

| Setting | Description | Default |
|---------|-------------|---------|
| **Max Speed** | Maximum allowed bone speed in studs per frame | 1.0 |
| **Roblox Bones Only** | Only check bones important for Roblox | ✅ Enabled |
| **Frame Step** | Check every N frames (higher = faster but less precise) | 1 |
| **Selected Only** | Only analyze selected armature objects | ❌ Disabled |

### Problem Resolution

When problems are found:

1. **Expand bone groups** to see individual problem frames
2. **Click on problem entries** to jump to that frame
3. **Use the refresh button** (🔄) next to bone names to recheck after fixes

## 🔧 Advanced Features

### Asynchronous Processing
- Checks run in background without freezing Blender
- Click "Stop Check" to cancel running analysis
- ESC key also cancels active checks

### Individual Bone Rechecking
- After fixing animation issues, use the refresh button next to bone names
- Rechecks only that specific bone instead of entire animation
- Maintains original problem organization

### Expandable Results
- Problems grouped by armature and bone
- Use expand/collapse buttons to manage visibility
- "Expand All" / "Collapse All" for bulk operations

## ⚡ Performance Tips

1. **Use Frame Step > 1** for quick initial checks
2. **Enable "Selected Only"** when working with multiple characters
3. **Focus on "Roblox Bones Only"** for faster processing
4. **Use individual bone rechecking** instead of full re-analysis

## 🎮 Roblox Compatibility

This addon helps ensure your animations work properly with Roblox's animation system by:

- **Preventing motion blur**: Keeps bone movement within acceptable speeds
- **Avoiding glitches**: Identifies potentially problematic rapid movements  
- **Optimizing performance**: Helps create smoother animations in-game
- **Meeting platform limits**: Ensures compatibility with Roblox's constraints

## 🐛 Troubleshooting

### Common Issues

**"No armatures to check"**
- Ensure you have armature objects in your scene
- Check that armatures are visible and not hidden

**"No bones to check"**  
- Verify your armature has bones with Roblox-standard names
- Disable "Roblox Bones Only" to check all bones

**Check gets stuck**
- Press ESC or click "Stop Check" to cancel
- Try increasing Frame Step for complex scenes
- Ensure animation has proper start/end frames set

**Recheck not working**
- Make sure the specific armature and bone still exist
- Verify you're not in the middle of another check operation

### Performance Issues

For large/complex animations:
- Increase **Frame Step** to 2 or 3
- Enable **Selected Only** mode
- Focus on problem areas with individual bone rechecking
- Consider checking animation in sections

## 📝 Technical Details

### Speed Calculation
- Bone world position is calculated per frame
- Distance between frames is measured in Blender units (studs)
- Speed = Distance × Frame Step (to account for skipped frames)

### Memory Usage
- Problems are stored in memory during Blender session
- Results are cleared when Blender closes
- Use "Clear Results" to free memory if needed

### Compatibility
- **Blender Version**: 3.0 or higher
- **Animation Types**: Keyframe animations on armature bones
- **Rig Types**: Any armature with standard Roblox bone names

## 🤝 Contributing

Found a bug or have a feature request? Please create an issue with:
- Blender version
- Addon version  
- Steps to reproduce
- Sample .blend file (if possible)

## 👤 Author

**Nultron**

---

*Happy animating! 🎬*
