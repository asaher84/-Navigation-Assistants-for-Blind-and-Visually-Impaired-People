import cv2
import threading
import speech_recognition as sr
from Base.detect import run_detection, speech_queue, audio_status, audio_lock
from Base.detect_track import run_detection_tracking
import time
import screeninfo  # For detecting screen resolution

# Global variables to manage the mode and threading
current_mode = "normal"  # Start in "normal" mode (detect.py)
mode_lock = threading.Lock()
running = True
listening_active = True  # To control the background listening loop

def get_screen_resolution():
    """Get the primary monitor's resolution."""
    try:
        monitor = screeninfo.get_monitors()[0]  # Get primary monitor
        return monitor.width, monitor.height
    except Exception as e:
        print(f"Error getting screen resolution: {e}. Defaulting to 1920x1080.")
        return 1920, 1080  # Fallback resolution

def resize_with_aspect_ratio(frame, target_width, target_height):
    """Resize frame to fit target dimensions while preserving aspect ratio."""
    h, w = frame.shape[:2]
    aspect_ratio = w / h
    target_aspect = target_width / target_height

    if aspect_ratio > target_aspect:
        # Fit to width, adjust height
        new_width = target_width
        new_height = int(target_width / aspect_ratio)
    else:
        # Fit to height, adjust width
        new_height = target_height
        new_width = int(target_height * aspect_ratio)

    # Resize frame
    resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # Create a black background with target dimensions
    result = cv2.copyMakeBorder(
        resized_frame,
        top=(target_height - new_height) // 2,
        bottom=(target_height - new_height + 1) // 2,
        left=(target_width - new_width) // 2,
        right=(target_width - new_width + 1) // 2,
        borderType=cv2.BORDER_CONSTANT,
        value=(0, 0, 0)
    )
    return result

def clear_speech_queue():
    """Clears the speech queue to stop ongoing speech."""
    global speech_queue
    while not speech_queue.empty():
        try:
            speech_queue.get_nowait()
            speech_queue.task_done()
        except Queue.Empty:
            break
    # Add a delay to ensure the speech thread processes the clear operation
    time.sleep(0.2)

def handle_command(recognizer, audio):
    """
    Callback function to process recognized speech.
    """
    global current_mode, running, listening_active, audio_status
    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"Recognized command: {command}")

        # Check for "Hello system"
        if "hello system" in command:
            # Store current audio_status to restore later
            with audio_lock:
                prev_audio_status = audio_status
                print("Pausing speech for interaction...")
                audio_status = False  # Stop object name announcements temporarily
            with mode_lock:
                clear_speech_queue()
                # Speak the response
                speech_queue.put("Heyy, how can I help you?")
                print("System: Heyy, how can I help you?")

            # Wait to ensure the speech queue is processed
            time.sleep(0.5)

            # Temporarily stop background listening to focus on sub-command
            listening_active = False

            # Listen for mode-switching command with up to 3 attempts
            attempts = 0
            max_attempts = 3
            command_recognized = False
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                while attempts < max_attempts:
                    try:
                        # Increased timeout and phrase time limit for better user experience
                        audio = recognizer.listen(source, timeout=2, phrase_time_limit=7)
                        sub_command = recognizer.recognize_google(audio).lower()
                        print(f"Recognized sub-command: {sub_command}")

                        with mode_lock:
                            if "find mode on" in sub_command:
                                current_mode = "find"
                                speech_queue.put("Switching to Find mode")
                                print("System: Switching to Find mode")
                                command_recognized = True
                                break
                            elif "normal mode on" in sub_command:
                                current_mode = "normal"
                                speech_queue.put("Switching to Normal mode")
                                print("System: Switching to Normal mode")
                                command_recognized = True
                                break
                            else:
                                attempts += 1
                                if attempts < max_attempts:
                                    speech_queue.put("I didn't understand. Please try again.")
                                    print("System: I didn't understand. Please try again.")
                                    # Delay to ensure system message is spoken and user has time
                                    time.sleep(1.5)
                    except sr.WaitTimeoutError:
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't hear you. Please try again.")
                            print("System: I didn't hear you. Please try again.")
                            time.sleep(1.5)
                        continue
                    except sr.UnknownValueError:
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't understand. Please try again.")
                            print("System: I didn't understand. Please try again.")
                            time.sleep(1.5)
                        continue
                    except sr.RequestError as e:
                        print(f"Speech recognition error: {e}")
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't understand. Please try again.")
                            print("System: I didn't understand. Please try again.")
                            time.sleep(1.5)
                        continue
                    except Exception as e:
                        print(f"Unexpected error in speech recognition: {e}")
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't understand. Please try again.")
                            print("System: I didn't understand. Please try again.")
                            time.sleep(1.5)
                        continue

            # After attempts or successful command, restore audio_status and resume
            with mode_lock:
                with audio_lock:
                    if command_recognized:
                        # Restore audio_status for Find mode; set to True for Normal mode
                        audio_status = True if current_mode == "normal" else prev_audio_status
                        print(f"Interaction ended. Audio status set to {audio_status} (Mode: {current_mode})")
                    else:
                        # If no command recognized, resume current mode
                        speech_queue.put("Skipping switching due to unclear command. Continuing in current mode.")
                        print("System: Skipping switching due to unclear command. Continuing in current mode.")
                        audio_status = True if current_mode == "normal" else prev_audio_status
                        print(f"Interaction ended. Audio status set to {audio_status} (Mode: {current_mode})")

            # Resume background listening
            listening_active = True
        else:
            # Check for direct mode-switching commands
            with mode_lock:
                with audio_lock:
                    if "find mode on" in command:
                        current_mode = "find"
                        # Do not set audio_status; let detect_track.py manage it
                        print("Switched to Find mode (detect_track.py).")
                    elif "normal mode on" in command:
                        current_mode = "normal"
                        audio_status = True  # Resume object names in normal mode
                        print("Switched to Normal mode (detect.py).")

    except sr.UnknownValueError:
        print("Could not understand the command.")
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
    except Exception as e:
        print(f"Unexpected error in speech recognition: {e}")

def listen_for_commands():
    """
    Listens to the microphone in the background and processes voice commands.
    """
    global running, listening_active
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("Microphone listening started. Say 'Hello system' to interact, or 'Find mode on'/'Normal mode on' to switch modes.")

    # Start background listening
    stop_listening = recognizer.listen_in_background(mic, handle_command, phrase_time_limit=5)

    while running:
        if not listening_active:
            # Wait until listening is resumed
            time.sleep(0.1)
            continue
        time.sleep(0.1)  # Small sleep to prevent excessive CPU usage

    # Stop background listening when done
    stop_listening(wait_for_stop=False)

def main_ui():
    """
    Main UI function that streams video, switches between detect.py and detect_track.py based on mode.
    """
    global current_mode, running, audio_status

    # Video source
    video_source = 1

    # Set up window for full-screen display
    window_name = "Blind Navigation - Object Detection"
    cv2.namedWindow(window_name, cv2.WINDOW_FULLSCREEN)
    
    # Get screen resolution
    screen_width, screen_height = get_screen_resolution()
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Start the microphone listening thread
    listener_thread = threading.Thread(target=listen_for_commands, daemon=True)
    listener_thread.start()

    # Variables to manage the detection generators
    detect_gen = None
    detect_track_gen = None

    while running:
        with mode_lock:
            mode = current_mode

        # Initialize or switch the generator based on the mode
        if mode == "normal":
            if detect_gen is None:
                detect_gen = run_detection(source=video_source, audio_status_initial=audio_status)
            try:
                frame = next(detect_gen)
                # Resize frame to fit full-screen while preserving aspect ratio
                frame = resize_with_aspect_ratio(frame, screen_width, screen_height)
            except StopIteration:
                print("Video stream ended in Normal mode. Restarting...")
                detect_gen = None
                continue
            except Exception as e:
                print(f"Error in Normal mode: {e}")
                detect_gen = None
                continue
            # Reset detect_track_gen when switching to normal mode
            detect_track_gen = None
        else:  # mode == "find"
            if detect_track_gen is None:
                detect_track_gen = run_detection_tracking(source=video_source, class_name="person")
            try:
                frame = next(detect_track_gen)
                # Resize frame to fit full-screen while preserving aspect ratio
                frame = resize_with_aspect_ratio(frame, screen_width, screen_height)
            except StopIteration:
                print("Video stream ended in Find mode. Restarting...")
                detect_track_gen = None
                continue
            except Exception as e:
                print(f"Error in Find mode: {e}")
                detect_track_gen = None
                continue
            # Reset detect_gen when switching to find mode
            detect_gen = None

        # Display the frame
        cv2.imshow(window_name, frame)

        # Exit on 'q' key
        if cv2.waitKey(30) & 0xFF == ord('q'):
            running = False
            break

        # Small sleep to prevent excessive CPU usage
        time.sleep(0.05)  # Increased sleep to reduce CPU load

    # Signal the listener thread to stop
    clear_speech_queue()
    speech_queue.put(None)

    # Wait for the listener thread to finish
    listener_thread.join()

    # Cleanup
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main_ui()
    except KeyboardInterrupt:
        print("Program interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        running = False
        cv2.destroyAllWindows()