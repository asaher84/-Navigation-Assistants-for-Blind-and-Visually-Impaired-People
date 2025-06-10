import cv2
import threading
import speech_recognition as sr
from Base.detect import run_detection, speech_queue, speech_paused
from Base.detect_track import run_detection_tracking
import time

# Global variables to manage the mode and threading
current_mode = "normal"  # Start in "normal" mode (detect.py)
mode_lock = threading.Lock()
running = True
listening_active = True  # To control the background listening loop

def clear_speech_queue():
    """Clears the speech queue to stop ongoing speech."""
    global speech_queue
    while not speech_queue.empty():
        try:
            speech_queue.get_nowait()
            speech_queue.task_done()
        except Queue.Empty:
            break
    # Add a small delay to ensure the speech thread processes the clear operation
    time.sleep(0.2)

def handle_command(recognizer, audio):
    """
    Callback function to process recognized speech.
    """
    global current_mode, running, speech_paused, listening_active
    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"Recognized command: {command}")

        # Check for "Hello system"
        if "hello system" in command:
            # Pause ongoing speech
            with mode_lock:
                print("Pausing speech for interaction...")
                speech_paused = True
                clear_speech_queue()
                # Speak the response
                speech_queue.put("Heyy, how can I help you?")
                print("System: Heyy, how can I help you?")

            # Wait briefly to ensure the speech queue is processed
            time.sleep(0.5)

            # Temporarily stop background listening to focus on sub-command
            listening_active = False

            # Listen for mode-switching command with up to 2 attempts
            attempts = 0
            max_attempts = 2
            command_recognized = False
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                while attempts < max_attempts:
                    try:
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
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
                                    # Small delay to ensure system message is spoken
                                    time.sleep(1)
                    except sr.WaitTimeoutError:
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't hear you. Please try again.")
                            print("System: I didn't hear you. Please try again.")
                            time.sleep(1)
                        continue
                    except sr.UnknownValueError:
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't understand. Please try again.")
                            print("System: I didn't understand. Please try again.")
                            time.sleep(1)
                        continue
                    except sr.RequestError as e:
                        print(f"Speech recognition error: {e}")
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't understand. Please try again.")
                            print("System: I didn't understand. Please try again.")
                            time.sleep(1)
                        continue
                    except Exception as e:
                        print(f"Unexpected error in speech recognition: {e}")
                        attempts += 1
                        if attempts < max_attempts:
                            speech_queue.put("I didn't understand. Please try again.")
                            print("System: I didn't understand. Please try again.")
                            time.sleep(1)
                        continue

            # After attempts, if no command recognized, resume current mode
            if not command_recognized:
                with mode_lock:
                    speech_queue.put("Skipping switching due to unclear command. Continuing in current mode.")
                    print("System: Skipping switching due to unclear command. Continuing in current mode.")
                    speech_paused = False
                    print("Resuming speech after interaction...")
            else:
                # Resume speech after successful mode switch
                with mode_lock:
                    speech_paused = False
                    print("Resuming speech after interaction...")

            # Resume background listening
            listening_active = True
        else:
            # Check for direct mode-switching commands
            with mode_lock:
                if "find mode on" in command:
                    current_mode = "find"
                    print("Switched to Find mode (detect_track.py).")
                elif "normal mode on" in command:
                    current_mode = "normal"
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
    global current_mode, running, speech_paused

    # Video source
    video_source = r"Source\vid.mp4"
    target_class = "person"  # Default class for detect_track.py

    # Set up window for display
    window_name = "Blind Navigation - Object Detection"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

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
                detect_gen = run_detection(source=video_source)
            try:
                frame = next(detect_gen)
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
                detect_track_gen = run_detection_tracking(source=video_source, target_class_input=target_class)
            try:
                frame = next(detect_track_gen)
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