"""
Main audio engine using multiprocessing with plugin integration.

NOTE: This file is currently UNUSED. Audio playback is handled by DAWView._playback_worker.
This is legacy code that may be refactored/removed in the future.

Architecture:
- UI process: Main thread with DearPyGui
- Audio process: Separate process for low-latency audio
- Communication: Lock-free queues (commands + audio data)
- Plugin system: Source plugins generate audio, FX plugins process it
"""
import multiprocessing as mp
from multiprocessing import Process, Queue, Value, Event
from typing import Optional, Dict, Any, List
import sounddevice as sd
import numpy as np
import time

from plugins.registry import PluginRegistry
from plugins.base import ProcessContext, AudioProcessor
from core.models import Song, Track, Note


class AudioEngine:
    """
    Main audio engine coordinator.

    Manages:
    - Audio device I/O via separate process
    - Real-time audio processing
    - Communication with UI process via queues
    - Plugin instantiation and audio generation
    """

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512):
        """
        Initialize audio engine.

        Args:
            sample_rate: Audio sample rate (Hz)
            buffer_size: Audio buffer size (frames)
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # Multiprocessing communication
        self.command_queue = Queue()  # UI → Audio commands
        self.status_queue = Queue()   # Audio → UI status updates

        # Shared state (using multiprocessing.Value for atomic access)
        self.playback_active = Value('i', 0)  # 0 = stopped, 1 = playing
        self.playback_position = Value('d', 0.0)  # Position in beats
        self.current_bpm = Value('d', 120.0)  # Current tempo
        self.cpu_usage = Value('d', 0.0)  # CPU usage percentage

        # Process control
        self.audio_process: Optional[Process] = None
        self.shutdown_event = Event()

        # Current song (sent to audio process via queue)
        self._current_song: Optional[Song] = None

    def load_song(self, song: Song):
        """
        Load song into audio engine.

        Args:
            song: Song to load
        """
        self._current_song = song
        self.command_queue.put(('load_song', song))

    def start(self):
        """Start audio engine process."""
        if self.audio_process and self.audio_process.is_alive():
            return  # Already running

        # Reset shutdown event
        self.shutdown_event.clear()

        # Start audio process
        self.audio_process = Process(
            target=_audio_process_loop,
            args=(
                self.sample_rate,
                self.buffer_size,
                self.command_queue,
                self.status_queue,
                self.playback_active,
                self.playback_position,
                self.current_bpm,
                self.cpu_usage,
                self.shutdown_event
            )
        )
        self.audio_process.start()

    def stop(self):
        """Stop audio engine process."""
        if not self.audio_process:
            return

        # Signal shutdown
        self.shutdown_event.set()

        # Wait for process to terminate
        self.audio_process.join(timeout=2.0)

        # Force terminate if still alive
        if self.audio_process.is_alive():
            self.audio_process.terminate()
            self.audio_process.join()

        self.audio_process = None

    def play(self):
        """Start playback."""
        self.command_queue.put(('play', None))
        self.playback_active.value = 1

    def pause(self):
        """Pause playback."""
        self.command_queue.put(('pause', None))
        self.playback_active.value = 0

    def stop_playback(self):
        """Stop playback and reset position."""
        self.command_queue.put(('stop', None))
        self.playback_active.value = 0
        self.playback_position.value = 0.0

    def set_bpm(self, bpm: float):
        """
        Set tempo.

        Args:
            bpm: Tempo in beats per minute
        """
        self.current_bpm.value = bpm
        self.command_queue.put(('set_bpm', bpm))

    def get_playback_position(self) -> float:
        """
        Get current playback position in beats.

        Returns:
            Current position in beats
        """
        return self.playback_position.value

    def set_playback_position(self, position: float):
        """
        Set playback position.

        Args:
            position: Position in beats
        """
        self.playback_position.value = position
        self.command_queue.put(('seek', position))

    def is_playing(self) -> bool:
        """
        Check if playback is active.

        Returns:
            True if playing
        """
        return self.playback_active.value == 1

    def get_cpu_usage(self) -> float:
        """
        Get audio CPU usage percentage.

        Returns:
            CPU usage (0.0-100.0)
        """
        return self.cpu_usage.value

    def set_mixer_parameter(self, channel: int, param: str, value: Any):
        """
        Set mixer parameter (volume, pan, mute, solo).

        Args:
            channel: Channel index (0-16)
            param: Parameter name ('volume', 'pan', 'mute', 'solo')
            value: Parameter value
        """
        self.command_queue.put(('mixer', {'channel': channel, 'param': param, 'value': value}))

    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


def _audio_process_loop(
    sample_rate: int,
    buffer_size: int,
    command_queue: Queue,
    status_queue: Queue,
    playback_active: Value,
    playback_position: Value,
    current_bpm: Value,
    cpu_usage: Value,
    shutdown_event: Event
):
    """
    Audio processing loop (runs in separate process).

    Handles:
    - Plugin instantiation and management
    - Note scheduling and playback
    - FX chain processing
    - Mixing and output

    Args:
        sample_rate: Audio sample rate
        buffer_size: Audio buffer size
        command_queue: Queue for receiving commands from UI
        status_queue: Queue for sending status to UI
        playback_active: Shared playback state
        playback_position: Shared playback position
        current_bpm: Shared BPM value
        cpu_usage: Shared CPU usage value
        shutdown_event: Event to signal shutdown
    """
    # Initialize plugin registry
    plugin_registry = PluginRegistry()

    # Audio state
    is_playing = False
    position_beats = 0.0
    bpm = 120.0
    tpqn = 480  # Ticks per quarter note
    current_song: Optional[Song] = None

    # Plugin instances per track (track_idx -> {source, effects})
    track_plugins: Dict[int, Dict[str, Any]] = {}

    # Performance tracking
    process_time_sum = 0.0
    process_time_count = 0

    def load_track_plugins(track: Track, track_idx: int):
        """Load plugins for a track."""
        plugins = {
            'source': None,
            'effects': []
        }

        # Load source plugin
        try:
            if track.mode == "SYNTH":
                source_id = track.source_type
            else:
                # For sampler mode, we'll load plugins per-note
                source_id = "NOISE_DRUM"  # Default

            plugins['source'] = plugin_registry.create_instance(source_id)
        except Exception as e:
            status_queue.put(('error', f"Failed to load source plugin '{source_id}': {e}"))

        # Load effect plugins
        for fx in track.effects:
            if fx.get('active', False):
                try:
                    fx_plugin = plugin_registry.create_instance(fx['type'])
                    plugins['effects'].append((fx_plugin, fx))
                except Exception as e:
                    status_queue.put(('error', f"Failed to load FX plugin '{fx['type']}': {e}"))

        track_plugins[track_idx] = plugins

    def render_track_audio(track: Track, track_idx: int, num_frames: int, context: ProcessContext) -> np.ndarray:
        """
        Render audio for a single track.

        Args:
            track: Track to render
            track_idx: Track index
            num_frames: Number of frames to render
            context: Processing context

        Returns:
            Rendered audio buffer (mono)
        """
        # Get track plugins
        if track_idx not in track_plugins:
            load_track_plugins(track, track_idx)

        plugins = track_plugins[track_idx]
        if not plugins['source']:
            return np.zeros(num_frames, dtype=np.float32)

        # Initialize output buffer
        output = np.zeros(num_frames, dtype=np.float32)

        # Find notes that should be playing in this buffer
        current_tick = context.current_tick
        buffer_duration_beats = (num_frames / sample_rate) * (bpm / 60.0)
        buffer_duration_ticks = buffer_duration_beats * tpqn

        for note in track.notes:
            note_start_tick = note.start * tpqn
            note_duration_ticks = note.duration * tpqn
            note_end_tick = note_start_tick + note_duration_ticks

            # Check if note overlaps with current buffer
            if note_start_tick < current_tick + buffer_duration_ticks and note_end_tick > current_tick:
                # Calculate note buffer
                try:
                    # Get source plugin parameters
                    if track.mode == "SYNTH":
                        params = track.source_params.copy()
                    else:
                        # Sampler mode: get params for this note's pitch
                        pad_config = track.sampler_map.get(note.note, {})
                        params = pad_config.get('params', {})
                        # Load different source if needed
                        source_id = pad_config.get('engine', 'NOISE_DRUM')
                        if plugins['source'].get_metadata().id != source_id:
                            plugins['source'] = plugin_registry.create_instance(source_id)

                    # Generate audio from source plugin
                    note_buffer = plugins['source'].process(None, params, note, context)

                    # Calculate where in the output buffer this note goes
                    offset_from_start = max(0, current_tick - note_start_tick)
                    offset_samples = int((offset_from_start / tpqn) * (60 / bpm) * sample_rate)

                    # Mix into output
                    available_frames = min(len(note_buffer) - offset_samples, num_frames)
                    if available_frames > 0 and offset_samples < len(note_buffer):
                        output[:available_frames] += note_buffer[offset_samples:offset_samples + available_frames]

                except Exception as e:
                    status_queue.put(('error', f"Error rendering note on track {track_idx}: {e}"))

        # Process FX chain
        for fx_plugin, fx_config in plugins['effects']:
            try:
                fx_params = fx_config.get('params', {})
                output = fx_plugin.process(output, fx_params, None, context)
            except Exception as e:
                status_queue.put(('error', f"Error processing FX on track {track_idx}: {e}"))

        return output

    def audio_callback(outdata, frames, time_info, status):
        """Sounddevice callback for audio output."""
        nonlocal is_playing, position_beats, bpm, current_song
        nonlocal process_time_sum, process_time_count

        start_time = time.perf_counter()

        # Process commands from queue (non-blocking)
        while not command_queue.empty():
            try:
                cmd, data = command_queue.get_nowait()

                if cmd == 'play':
                    is_playing = True
                elif cmd == 'pause':
                    is_playing = False
                elif cmd == 'stop':
                    is_playing = False
                    position_beats = 0.0
                elif cmd == 'seek':
                    position_beats = data
                elif cmd == 'set_bpm':
                    bpm = data
                elif cmd == 'load_song':
                    current_song = data
                    # Reload all plugins
                    track_plugins.clear()
                    if current_song:
                        for idx, track in enumerate(current_song.tracks):
                            load_track_plugins(track, idx)
                elif cmd == 'mixer':
                    # Update mixer parameters
                    channel_idx = data['channel']
                    param = data['param']
                    value = data['value']
                    channel = mixer.get_channel(channel_idx)

                    if param == 'volume':
                        channel.set_volume(value)
                    elif param == 'pan':
                        channel.set_pan(value)
                    elif param == 'mute':
                        channel.set_mute(value)
                    elif param == 'solo':
                        mixer.set_solo(channel_idx, value)

            except:
                break  # Queue empty

        # Generate audio
        if is_playing and current_song:
            # Create processing context
            current_tick = int(position_beats * tpqn)
            context = ProcessContext(
                sample_rate=sample_rate,
                bpm=bpm,
                tpqn=tpqn,
                current_tick=current_tick
            )

            # Render each track
            track_buffers = []
            for idx, track in enumerate(current_song.tracks[:16]):
                buffer = render_track_audio(track, idx, frames, context)
                track_buffers.append(buffer)

            # Pad to 16 tracks if needed
            while len(track_buffers) < 16:
                track_buffers.append(np.zeros(frames, dtype=np.float32))

            # Mix tracks
            mixed = mixer.process(track_buffers)

            # Update playback position
            beats_per_second = bpm / 60.0
            beats_per_sample = beats_per_second / sample_rate
            position_beats += frames * beats_per_sample

            # Update shared state
            playback_position.value = position_beats
            current_bpm.value = bpm

            # Copy to output (handle buffer size mismatch)
            if len(mixed) >= frames:
                outdata[:] = mixed[:frames]
            else:
                outdata[:len(mixed)] = mixed
                outdata[len(mixed):] = 0

        else:
            # Silence when not playing
            outdata.fill(0)

        # Track CPU usage
        elapsed = time.perf_counter() - start_time
        process_time_sum += elapsed
        process_time_count += 1

        if process_time_count >= 100:  # Update every 100 callbacks
            avg_time = process_time_sum / process_time_count
            buffer_duration = frames / sample_rate
            cpu_pct = (avg_time / buffer_duration) * 100.0
            cpu_usage.value = cpu_pct

            process_time_sum = 0.0
            process_time_count = 0

    # Open audio stream
    try:
        with sd.OutputStream(
            samplerate=sample_rate,
            blocksize=buffer_size,
            channels=2,
            dtype='float32',
            callback=audio_callback
        ):
            # Keep process alive until shutdown
            while not shutdown_event.is_set():
                time.sleep(0.1)

    except Exception as e:
        status_queue.put(('error', str(e)))

    finally:
        # Cleanup
        track_plugins.clear()
