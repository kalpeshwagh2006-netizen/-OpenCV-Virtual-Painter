# Virtual Painter GUI Enhancement Plan

## Task Requirements:
1. Remove color tabs from screen
2. Add a colors panel beside the screen in the GUI
3. Add a save screen button in the GUI

## Current Implementation Analysis:
- Color buttons are currently on the right side of the screen (x=1210)
- Buttons are created in `setup_color_panel()` method
- Buttons are drawn in `draw_buttons()` method
- Button clicks are handled in `check_button_click()` method

## Proposed Changes:

### 1. Remove Color Tabs from Screen
- Remove the current button drawing logic from the main screen
- Keep the button data structure for color selection logic

### 2. Add Colors Panel Beside Screen
- Create a separate window for the color palette
- Position it beside the main application window
- Implement color selection from the panel

### 3. Add Save Screen Button
- Add a button to save the current canvas as an image file
- Implement save functionality using OpenCV's imwrite

## Implementation Steps:
1. Modify `setup_color_panel()` to prepare for external panel
2. Update `draw_buttons()` to not draw on main screen
3. Create separate color panel window
4. Implement color selection from external panel
5. Add save button and functionality
6. Update UI instructions

## Technical Considerations:
- Need to manage multiple OpenCV windows
- Coordinate color selection between windows
- Handle window positioning and sizing
- Implement file saving with proper naming
