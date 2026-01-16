# Agent Coordination Protocol

**Last Updated**: 2026-01-15 08:30 AM
**Version**: 1.0

## Purpose
This directory coordinates 3 parallel agents migrating Blooper4 code into Blooper5.

## Agents

### Agent 1: Core Layer (agent-core)
**Responsibility**: Data models, persistence, commands
**Files owned**:
- core/models.py
- core/persistence.py
- core/commands.py
- core/constants.py

**Source files from Blooper4**:
- models.py
- constants.py
- utils/project_manager.py

### Agent 2: Audio Engine (agent-audio)
**Responsibility**: Audio processing, mixing, MIDI
**Files owned**:
- audio/engine.py
- audio/mixer.py
- audio/dsp.py
- midi/handler.py

**Source files from Blooper4**:
- audio_engine/manager.py
- audio_engine/bridge.py
- audio_engine/midi_handler.py

### Agent 3: Plugin System (agent-plugins)
**Responsibility**: Plugin base classes, registry, all 12 plugins
**Files owned**:
- plugins/base.py
- plugins/registry.py
- plugins/sources/*.py (6 synths)
- plugins/effects/*.py (5 effects)

**Source files from Blooper4**:
- audio_engine/base_processor.py
- audio_engine/plugin_factory.py
- components/builder_plugins/*.py (all 12 plugins)

## Rules

### 1. File Ownership
- Each agent ONLY modifies files listed in their assignment
- Never modify another agent's files
- To change shared interfaces, update interfaces.md first

### 2. Interface Contracts
- All shared interfaces defined in interfaces.md
- Must follow existing signatures in placeholder files
- Breaking changes require updating interfaces.md + notifying other agents

### 3. Progress Tracking
- Update your status file after each completed task
- Mark files as: TODO, IN_PROGRESS, DONE, BLOCKED
- If blocked, document reason and dependencies

### 4. Testing
- Each agent must test their own code in isolation
- Integration testing happens after all agents complete
- No agent should break existing tests

### 5. Conflict Resolution
- If two agents need the same Blooper4 file:
  - Document in your status file which parts you need
  - Coordinate in interfaces.md
  - One agent extracts and places in shared location

## Communication
- Use status files for async updates
- Update progress.md when completing major milestones
- Flag issues in your status file with "🚨 BLOCKED" marker
