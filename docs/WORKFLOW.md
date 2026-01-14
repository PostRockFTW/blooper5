# Blooper5 Development Workflow

## TDD Workflow (Red-Green-Refactor)

### 1. RED - Write Failing Test
```bash
# Create test file first
touch tests/unit/test_new_feature.py

# Write test that fails
def test_new_feature():
    result = new_feature()
    assert result == expected_value
```

Run test to confirm failure:
```bash
pytest tests/unit/test_new_feature.py
# Expected: FAILED (function doesn't exist yet)
```

### 2. GREEN - Minimal Implementation
```python
# blooper5/core/new_feature.py
def new_feature():
    return expected_value  # Just enough to pass
```

Run test to confirm pass:
```bash
pytest tests/unit/test_new_feature.py
# Expected: PASSED
```

### 3. REFACTOR - Improve Code
```python
# blooper5/core/new_feature.py
def new_feature():
    # Add proper implementation
    # Clean up code
    # Add error handling
    return computed_result
```

Run test to confirm still passes:
```bash
pytest tests/unit/test_new_feature.py
# Expected: PASSED
```

---

## Git Branching Strategy

### Branch Structure
```
main          (stable releases only)
  ↑
dev           (integration branch)
  ↑
feature/*     (individual features)
bugfix/*      (bug fixes)
refactor/*    (code restructuring)
```

### Feature Development Flow
```bash
# 1. Create feature branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/widget-test-page

# 2. Develop with frequent commits
git add blooper5/ui/widgets/button.py
git commit -m "feat(ui): add Button widget with accent theme

Implements clickable buttons with optional accent color.
Supports enabled/disabled states.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 3. Push regularly (every 30 minutes or major milestone)
git push origin feature/widget-test-page

# 4. Create PR when feature complete
gh pr create --base dev --title "Add widget test page" --body "$(cat <<'EOF'
## Summary
- Created Button, Slider, Knob widgets
- Built widget showcase test page
- Added screenshot MCP integration

## Test Plan
- [ ] All widgets render correctly
- [ ] Interactions work (click, drag)
- [ ] Screenshot MCP shows expected layout
- [ ] No console errors

🤖 Generated with Claude Code
EOF
)"

# 5. Merge after review
gh pr merge --squash
```

---

## Multi-Bot Coordination

### When to Use Multiple Bots
- **Parallel features**: MIDI Editor + Sound Designer simultaneously
- **Large refactors**: Core models + Audio engine + UI updates
- **Independent sub-systems**: Plugin system + File I/O

### Coordination File
Create `.claude/sessions.json`:
```json
{
  "active_sessions": [
    {
      "id": "bot-1",
      "branch": "feature/midi-editor",
      "focus": "Piano roll UI and note editing logic",
      "files": ["blooper5/ui/views/midi_editor.py", "tests/ui/test_midi_editor.py"],
      "status": "active",
      "last_update": "2026-01-14T15:30:00Z"
    },
    {
      "id": "bot-2",
      "branch": "feature/sound-designer",
      "focus": "Plugin parameter UI and automation lanes",
      "files": ["blooper5/ui/views/sound_designer.py", "blooper5/ui/widgets/automation_lane.py"],
      "status": "active",
      "last_update": "2026-01-14T15:28:00Z"
    }
  ]
}
```

### Avoiding Merge Conflicts
1. **File ownership**: Each bot works on different files
2. **Sync regularly**: Pull from dev before pushing
3. **Communication**: Update sessions.json with current status
4. **Integration tests**: Run full test suite before merging to dev

---

## Screenshot MCP Workflow

### Setup
Install screenshot MCP server:
```bash
# Add to claude_desktop_config.json
{
  "mcpServers": {
    "screenshot": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-screenshot"]
    }
  }
}
```

### Testing UI with Screenshots
1. Run widget test page:
```bash
python blooper5/tests/ui/widget_test_page.py
```

2. Request screenshot via MCP:
```
Claude: "Take a screenshot of the widget test page"
```

3. Review visual output:
   - Check widget alignment
   - Verify colors match theme
   - Test different window sizes
   - Compare to DAW reference (Ableton, Pro Tools)

4. Iterate on design:
```python
# Adjust widget spacing
with dpg.group(horizontal=True, spacing=10):  # Changed from 5
    dpg.add_button(label="Play")
    dpg.add_button(label="Stop")
```

5. Capture updated screenshot and compare

---

## Task Breakdown Guidelines

### Small Tasks (1-2 hours)
- Single widget implementation (button.py)
- Single plugin conversion (dual_osc.py)
- Isolated bug fix

**Example:**
```markdown
Task: Implement Slider widget
- [ ] Create ui/widgets/slider.py
- [ ] Add vertical/horizontal modes
- [ ] Support linear/logarithmic scaling
- [ ] Write tests/ui/test_slider.py
- [ ] Add to widget test page
- [ ] Capture screenshot
```

### Medium Tasks (4-8 hours)
- View implementation (landing_page.py)
- Plugin system setup
- Audio engine core loop

**Example:**
```markdown
Task: Build Landing Page
- [ ] Design layout (hamburger menu, recent projects, new project)
- [ ] Create ui/views/landing_page.py
- [ ] Implement menu items (New, Open, Settings, Exit)
- [ ] Add keyboard shortcuts (Ctrl+N, Ctrl+O)
- [ ] Style to match DAW conventions
- [ ] Test with screenshot MCP
```

### Large Tasks (16+ hours, split across multiple bots)
- MIDI Editor complete implementation
- Sound Designer with automation lanes
- Full plugin migration from Blooper4

**Example:**
```markdown
Task: MIDI Editor (split into 3 bots)

Bot 1: Piano Roll Canvas
- [ ] Grid rendering (tick marks, beat lines)
- [ ] Note rendering (colored rectangles)
- [ ] Viewport scrolling/zooming
- [ ] File: blooper5/ui/views/piano_roll_canvas.py

Bot 2: Note Editing Logic
- [ ] Click to add notes
- [ ] Drag to move notes
- [ ] Resize note duration
- [ ] Velocity editing
- [ ] File: blooper5/ui/views/piano_roll_editor.py

Bot 3: Commands and Integration
- [ ] AddNoteCommand, DeleteNoteCommand, MoveNoteCommand
- [ ] Undo/redo stack integration
- [ ] Keyboard shortcuts (Ctrl+D, Delete, Ctrl+Z)
- [ ] File: blooper5/core/state.py, blooper5/ui/commands/note_commands.py
```

---

## Code Review Process

### Before Creating PR
```bash
# Run full test suite
pytest tests/ --cov=blooper5

# Check code quality
pylint blooper5/

# Verify file lengths
find blooper5 -name "*.py" -exec wc -l {} \; | sort -rn | head -10

# Format code
black blooper5/ tests/
```

### PR Template
```markdown
## Summary
Brief description of changes

## Changes
- File 1: What changed
- File 2: What changed

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed (describe)
- [ ] Screenshots attached (for UI changes)

## Checklist
- [ ] All files under 1000 lines
- [ ] Type hints added
- [ ] Docstrings updated
- [ ] No commented-out code
- [ ] Tests added/updated

🤖 Generated with Claude Code
```

### Review Criteria
1. **Correctness**: Does it work as intended?
2. **Tests**: Are there tests? Do they pass?
3. **Readability**: Is the code clear and well-documented?
4. **Performance**: Any bottlenecks introduced?
5. **Architecture**: Follows Blooper5 patterns?
6. **File length**: Under 300 lines (or justified if larger)?

---

## Troubleshooting Common Issues

### Issue: Tests Failing After Merge
```bash
# 1. Pull latest dev
git checkout dev
git pull origin dev

# 2. Rebase your branch
git checkout feature/my-branch
git rebase dev

# 3. Fix conflicts if any
git add .
git rebase --continue

# 4. Re-run tests
pytest tests/
```

### Issue: File Exceeds 300 Lines
```bash
# 1. Identify refactor opportunities
# Split into multiple classes/files
# Extract helper functions to utils/

# 2. Example: Split large plugin
# Before: dual_osc.py (350 lines)
# After:
#   - dual_osc.py (150 lines) - Main plugin
#   - oscillator_utils.py (100 lines) - Shared waveform generators
#   - filter_utils.py (100 lines) - Shared filters
```

### Issue: UI Doesn't Match Screenshot
```bash
# 1. Check DearPyGui theme settings
# 2. Verify spacing/padding values
# 3. Test on different screen resolutions
# 4. Compare with DAW reference image
# 5. Iterate and re-screenshot until match
```

---

## Resources
- **DearPyGui Docs**: https://dearpygui.readthedocs.io
- **pytest Docs**: https://docs.pytest.org
- **NumPy Docs**: https://numpy.org/doc
- **Blooper4 Source**: ../Blooper4/ (reference for algorithms)
