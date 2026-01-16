# Agent Onboarding Instructions

**Last Updated**: 2026-01-16 (Morning)
**Project**: Blooper4 → Blooper5 Migration
**Workflow**: Independent git branches with pull requests

---

## Your Role

You are one of 3 backend software engineers working in parallel on the Blooper5 migration. You will:
- Work independently on your assigned files
- Make commits to your feature branch
- Create a pull request when done
- Coordinate through `.agent-coordination/` files (read-only awareness)

**Project Manager**: The user (Nick) will review and merge your PRs

---

## Agent Assignments

### Agent 1: Core Layer Engineer (YOU if assigned "core")
**Branch**: `feature/core-migration`
**Status File**: `.agent-coordination/status/agent-core.md`
**Your Files**:
- `core/models.py` - Data classes (Note, Track, Song, AppState)
- `core/persistence.py` - Save/load .bloom5 files
- `core/commands.py` - Command pattern for undo/redo
- `core/constants.py` - MIDI constants and utilities

**Source Material**:
- `../Blooper4/models.py` (204 lines)
- `../Blooper4/constants.py` (84 lines)
- `../Blooper4/utils/project_manager.py` (51 lines)

**Key Deliverables**:
1. Port Note, Track, Song as frozen dataclasses
2. Implement .bloom5 format using MessagePack
3. Implement CommandHistory with undo/redo
4. All NotImplementedError replaced with working code

---

### Agent 2: Audio Engine Engineer (YOU if assigned "audio")
**Branch**: `feature/audio-migration`
**Status File**: `.agent-coordination/status/agent-audio.md`
**Your Files**:
- `audio/engine.py` - Audio playback engine
- `audio/mixer.py` - 17-channel mixer
- `audio/dsp.py` - DSP utilities (filters, envelopes)
- `midi/handler.py` - MIDI input handling

**Source Material**:
- `../Blooper4/audio_engine/manager.py` (156 lines)
- `../Blooper4/audio_engine/bridge.py` (105 lines)
- `../Blooper4/audio_engine/midi_handler.py` (155 lines)

**Key Deliverables**:
1. Multiprocess audio engine (not threading)
2. 17-channel mixer (16 tracks + master)
3. Port DSP utilities
4. Use python-rtmidi for MIDI (not Blooper4's custom handler)

**Dependency**: Wait for agent-core to define Note interface (check their status file)

---

### Agent 3: Plugin System Engineer (YOU if assigned "plugins")
**Branch**: `feature/plugin-migration`
**Status File**: `.agent-coordination/status/agent-plugins.md`
**Your Files**:
- `plugins/base.py` - AudioProcessor base class
- `plugins/registry.py` - Plugin discovery/loading
- `plugins/sources/*.py` - 6 synth plugins
- `plugins/effects/*.py` - 5 effect plugins

**Source Material**:
- `../Blooper4/audio_engine/base_processor.py` (43 lines)
- `../Blooper4/audio_engine/plugin_factory.py` (94 lines)
- `../Blooper4/components/builder_plugins/*.py` (12 plugins)

**Key Deliverables**:
1. Port BaseProcessor → AudioProcessor
2. Port plugin_factory → PluginRegistry
3. Migrate all 12 plugins (strip Pygame UI code, keep audio logic)
4. Add PluginMetadata for auto-UI generation

**Migration order**: base.py → registry.py → eq.py (simplest) → others

---

## Workflow

### 1. Initial Setup (Do once)
```bash
# Switch to your assigned branch
git checkout feature/core-migration        # If you're agent-core
git checkout feature/audio-migration       # If you're agent-audio
git checkout feature/plugin-migration      # If you're agent-plugins

# Verify you're on the right branch
git branch

# Read your assignment
cat .agent-coordination/status/agent-core.md       # Or agent-audio.md or agent-plugins.md
cat .agent-coordination/assignments.json
cat .agent-coordination/interfaces.md
```

### 2. Development Loop
```bash
# Work on your files (only modify files you own!)
# See "Your Files" section above

# Update your status file as you progress
# Mark tasks as: TODO → IN_PROGRESS → DONE

# Commit frequently
git add core/models.py                     # Example: add your changes
git commit -m "Implement Note dataclass"

# Update status after each major milestone
# Edit .agent-coordination/status/agent-core.md
# Update timestamps, mark tasks complete
```

### 3. Coordination Rules

**DO**:
- ✅ Only modify files assigned to you
- ✅ Update your status file after completing tasks
- ✅ Read other agents' status files to check dependencies
- ✅ Follow interfaces defined in `interfaces.md`
- ✅ Commit frequently with clear messages
- ✅ Test your code in isolation

**DON'T**:
- ❌ Modify files owned by other agents
- ❌ Change shared interfaces without documenting in `interfaces.md`
- ❌ Push to main (only push to your feature branch)
- ❌ Merge other branches into yours
- ❌ Break existing tests

### 4. When You're Done

```bash
# Final status update
# Edit your status file, mark all tasks DONE, add completion timestamp

# Final commit
git add -A
git commit -m "Complete [your agent name] migration

- All tasks from status file completed
- All NotImplementedError replaced
- Tests passing
- Ready for review

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push your branch
git push -u origin feature/core-migration     # Use your branch name

# Create pull request (use gh CLI if available)
gh pr create --title "Core Layer Migration" --body "$(cat <<'EOF'
## Summary
- ✅ Migrated Note, Track, Song dataclasses
- ✅ Implemented .bloom5 persistence (MessagePack)
- ✅ Implemented CommandHistory for undo/redo
- ✅ All constants ported from Blooper4

## Testing
- [x] Unit tests pass
- [x] Integration tests pass
- [x] Manual testing complete

## Files Changed
- core/models.py (328 lines)
- core/persistence.py (83 lines)
- core/commands.py (130 lines)
- core/constants.py (142 lines)

Ready for review and merge.

🤖 Generated by Agent-Core
EOF
)"
```

---

## Communication Protocol

### Status File Updates
Update your status file (`agent-core.md`, `agent-audio.md`, or `agent-plugins.md`) with:
```markdown
**Last Updated**: 2026-01-16 10:30 AM

### 1. core/models.py
- [x] Port Note class from Blooper4
- [x] Port Track class from Blooper4
- [ ] Port Song class from Blooper4
- **Status**: IN_PROGRESS
- **Started**: 2026-01-16 09:00 AM
- **Completed**: Not yet
```

### Checking Dependencies
```bash
# If you depend on another agent's work, check their status
cat .agent-coordination/status/agent-core.md

# Look for their completion status
# If blocked, document in your status file:
## Blockers
*Waiting for core/models.py Note class from agent-core (checked 10:30 AM, still TODO)*
```

### Interface Changes
If you need to change a shared interface:
1. Document in `.agent-coordination/interfaces.md`
2. Add a breaking change notice
3. Update your status file with "🚨 INTERFACE CHANGE" marker
4. Wait for other agents to acknowledge (check their status files)

---

## Testing Guidelines

### Unit Tests
```python
# Test your code in isolation
# Example for agent-core:
def test_note_creation():
    note = Note(note=60, start=0.0, duration=1.0, velocity=100, selected=False)
    assert note.note == 60
    assert note.start == 0.0
```

### Integration Tests (After all agents complete)
The project manager will run full integration tests after merging all PRs.

---

## Tips for Success

1. **Read before you code**: Review Blooper4 source files thoroughly
2. **Small commits**: Commit after each completed task
3. **Status updates**: Keep your status file current (helps other agents)
4. **Test as you go**: Don't wait until the end
5. **Check dependencies**: Read other agents' status files if you depend on them
6. **Ask questions**: Document blockers in your status file if stuck

---

## Example Session

```bash
# Agent-Core example workflow

# 1. Checkout branch
git checkout feature/core-migration

# 2. Read assignment
cat .agent-coordination/status/agent-core.md

# 3. Work on first task (models.py)
# ... implement Note class ...

# 4. Test
python -m pytest tests/core/test_models.py

# 5. Commit
git add core/models.py tests/core/test_models.py
git commit -m "Implement Note dataclass with validation"

# 6. Update status
# Edit .agent-coordination/status/agent-core.md
# Mark "Port Note class" as DONE

# 7. Repeat for next task
# ... implement Track class ...

# 8. When all done, create PR
git push -u origin feature/core-migration
gh pr create --title "Core Layer Migration" --body "..."
```

---

## Questions?

- **Technical questions**: Document in your status file under "Notes" section
- **Blockers**: Document in "Blockers" section with timestamp
- **Interface issues**: Update `interfaces.md` with proposed changes

The project manager (user) will review status files and provide guidance.

---

**Remember**: You're working independently with meta-awareness through coordination files. Trust the system, update your status file, and create clean commits. Good luck! 🚀
