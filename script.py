
"""
This script performs optical character recognition (OCR) on Chinese text using EasyOCR library.
It captures a selected region of the screen, preprocesses the image, and performs OCR to extract Chinese text.
The extracted text is then matched with a Chinese-English dictionary to find the corresponding translations.
The script also provides functionality to manually configure the bounding box for capturing the screen region.
"""
import os
import sys
import threading
import uuid
import cv2
import easyocr
from PIL import Image
import numpy as np
import yaml
import pyautogui
import json
from tkinter import Tk, Canvas, TclError
from vocab import VocabCanvas
import keyboard
import mouse

with open('config.json', 'r') as file:
    CONFIG = json.load(file)

def update_config(*args):
    for key, value in args:
        if key in CONFIG: CONFIG[key] = value
    with open('config.json', 'w') as file:
        json.dump(CONFIG, file, indent=4)

# Create a reader for Chinese
reader = easyocr.Reader(['ch_sim'])
print("EasyOCR initiated using " + reader.device)

# Load the Chinese-English dictionary
with open('sim_cn_dictionary.json', 'r') as file:
    list_of_dicts = json.load(file)
    DICTIONARY = {}
    for entry in list_of_dicts:
        if entry['simplified'] in DICTIONARY:
            # If the simplified character is already in the dictionary, append the new entry to its list
            DICTIONARY[entry['simplified']].append((entry['traditional'], entry['pinyin'], entry['english']))
        else:
            # If the simplified character is not in the dictionary, add it with a list containing one pronunciation
            DICTIONARY[entry['simplified']] = [(entry['traditional'], entry['pinyin'], entry['english'])]

def clear_canvases(root: Tk):
    for widget in root.winfo_children():
        if isinstance(widget, Canvas):
            widget.destroy()

    root.attributes('-alpha', 0)

def draw_manual_bbox():
    clear_canvases(root)

    # Create a canvas for drawing the bounding box
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.2)
    root.focus_set()  # Set focus to the root window
    root.grab_set()  # Confine all input to this window

    canvas = Canvas(root, bg='white', cursor='crosshair', highlightthickness=0)
    canvas.pack(fill='both', expand=True)

    # Variables to store the bounding box coordinates
    start_x = start_y = end_x = end_y = 0

    def on_mouse_down(event):
        nonlocal start_x, start_y
        start_x = event.x
        start_y = event.y

    def on_mouse_move(event):
        nonlocal end_x, end_y
        end_x = event.x
        end_y = event.y
        canvas.delete('bbox')  # Delete the previous bounding box
        canvas.create_rectangle(start_x, start_y, end_x, end_y, outline='red', tags='bbox')  # Draw the new bounding box

    def on_mouse_up(event):
        nonlocal end_x, end_y
        end_x = event.x
        end_y = event.y
        canvas.delete('bbox')
        safe_destroy_canvas()  # Close the overlay window
    
    def on_escape(event):
        safe_destroy_canvas()
        return
    
    def safe_destroy_canvas():
        try:
            canvas.destroy()
        except TclError:
            pass  # Canvas is already destroyed, do nothing
        finally:
            root.attributes('-alpha', 0)  # Reset transparency
            root.unbind(escape)
            root.grab_release()  # Release input grab

    # Bind the mouse events to the handlers
    canvas.bind('<Button-1>', on_mouse_down)
    canvas.bind('<B1-Motion>', on_mouse_move)
    canvas.bind('<ButtonRelease-1>', on_mouse_up)
    escape = root.bind('<Escape>', on_escape)

    root.wait_window(canvas)

    # Calculate the region for the selected bounding box
    bbox = (start_x, start_y, end_x - start_x, end_y - start_y)
    return bbox

def configure_bbox():
    print("Select the dialog box region")
    dialog_bbox = draw_manual_bbox()
    print("Select the dialog responses region")
    responses_bbox = draw_manual_bbox()
    if not dialog_bbox or not responses_bbox:
        return
    update_config(('dialog_bbox', dialog_bbox), ('responses_bbox', responses_bbox))
    print("Configuration saved.")

def pick_text_color():
    x, y = pyautogui.position()
    color = pyautogui.pixel(x, y)
    print(f"Text color: {color}")

    current_list = CONFIG['text_colors']
    if list(color) not in current_list:
        current_list.append(color)
        update_config(('text_color', current_list))

def capture(bbox=None, fullscreen=False):
    """
    Capture a selected area of the game window.

    Args:
        bbox (tuple, optional): The bounding box coordinates (x, y, width, height) of the area to capture.
            If not provided, a manual bounding box will be prompted for user input.

    Returns:
        tuple: A tuple containing the processed image and the converted bounding box coordinates [x1, y1, x2, y2].

    """
    if fullscreen:
        bbox = [0, 0, pyautogui.size().width, pyautogui.size().height]
        # crop out bottom UID
        bbox[3] -= 40
    else:
        bbox = bbox or draw_manual_bbox() or [0, 0, pyautogui.size().width, pyautogui.size().height - 40]

    # Capture the selected area of the game window
    img = pyautogui.screenshot(region=bbox)

    bbox = [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]] # [x1, y1, x2, y2]
    return img, bbox

def strict_preprocess_image(img: Image.Image, tolerance=10) -> Image.Image:
    # Remove all pixels that are not text colors
    image = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
    
    lower_bounds = [np.array([max(0, c - tolerance) for c in color]) for color in CONFIG['text_colors']]
    upper_bounds = [np.array([min(255, c + tolerance) for c in color]) for color in CONFIG['text_colors']]

    masks = [cv2.inRange(image, lower, upper) for lower, upper in zip(lower_bounds, upper_bounds)]

    masks = [cv2.inRange(image, lower, upper) for lower, upper in zip(lower_bounds, upper_bounds)]
    mask = masks[0]
    for m in masks[1:]:
        mask = cv2.bitwise_or(mask, m)

    masked_image = cv2.bitwise_and(image, image, mask=mask)

    # Convert the processed image back to PIL format
    img = Image.fromarray(masked_image)
    if CONFIG["verbose"]: img.show()
    return img


def perform_ocr(img: Image.Image) -> list[tuple[list[int], str, float]]:
    """
    Perform OCR on the given image using EasyOCR.

    Args:
        img (PIL.Image.Image): The input image to perform OCR on.

    Returns:
        list[tuple[list[int], str, float]]: A list of tuples containing the bounding box coordinates,
        recognized text, and confidence score for each detected text region.

        bbox = [x1, y1, x2, y2]
    """
    # Perform OCR with EasyOCR
    easyocr_results = reader.readtext(np.array(img))
    easyocr_text = "\n".join([item[1] for item in easyocr_results])
    if CONFIG["verbose"]: print(easyocr_text)

    # Filter out text regions with low confidence
    # easyocr_results = [item for item in easyocr_results if item[2] > CONFIG['confidence_threshold']]
    
    # change bbox format to [x1, y1, x2, y2]
    for i, item in enumerate(easyocr_results):
        new_bbox = [item[0][0][0], item[0][0][1], item[0][2][0], item[0][2][1]]
        easyocr_results[i] = (new_bbox, item[1], item[2])
    
    return easyocr_results

def find_vocab_matches(text: str) -> list:
    matches = []
    # greedily match the longest possible string for each starting position i in len(text)
    for i in range(len(text)):
        current = text[i]
        for j in range(i + 1, len(text)):
            if current + text[j] in DICTIONARY:
                current += text[j]
            else:
                break

        if current in DICTIONARY:
            matches.append(current)
        else:
            matches.append(None)

    return matches # should be len(text) long

def save_ocr_data(image: Image.Image, ocr_results, save_dir=CONFIG['save_dir']):
    """
    Save img to saved_data/images and ocr results to saved_data/ocr_data.yaml
    """
     # Ensure the directory and subdirectory exist
    image_dir = os.path.join(save_dir, 'images')
    os.makedirs(image_dir, exist_ok=True)

    image_id = str(uuid.uuid4())
    image_path = os.path.join(image_dir, f"{image_id}.png")

    image.save(image_path)

    yaml_ocr_results = []
    for bbox, text, confidence in ocr_results:
        result = {
            'bbox': [int(x) for x in bbox],
            'text': text,
            'confidence': float(confidence)
        }
        yaml_ocr_results.append(result)

    ocr_data = {
        'image_id': image_id,
        'results': yaml_ocr_results
    }

    yaml_file_path = os.path.join(save_dir, 'ocr_data.yaml')
    with open(yaml_file_path, 'a', encoding='utf-8') as file:
        yaml.dump([ocr_data], file, allow_unicode=True)

def thread_save_ocr_data(image, ocr_results, save_dir=CONFIG['save_dir']):
    """
    Wrapper function to run save_ocr_data in a separate thread.
    """
    if not CONFIG['save_data']:
        return
    
    thread = threading.Thread(target=save_ocr_data, args=(image, ocr_results, save_dir))
    thread.start()
    return thread

def run(manual=False, fullscreen=False):
    clear_canvases(root)

    if manual:
        image, offset = capture()
        to_ocr, offsets = [image], [offset]
    elif fullscreen:
        image, offset = capture(fullscreen=True)
        to_ocr, offsets = [image], [offset]
    else:
        dialog_img, dialog_offset = capture(bbox=CONFIG['dialog_bbox'])
        responses_img, responses_offset = capture(bbox=CONFIG['responses_bbox'])
        to_ocr, offsets = [dialog_img, responses_img], [dialog_offset, responses_offset]
    
    vocab_canvas = VocabCanvas(root)

    for i, img in enumerate(to_ocr):
        img_to_ocr = strict_preprocess_image(img) if CONFIG['preprocess_image'] else img
        easyocr_results = perform_ocr(img_to_ocr)

        if not easyocr_results:
            print("No text detected.")
            continue

        thread_save_ocr_data(img, easyocr_results)

        for item in easyocr_results:
            bbox, text, confidence = item # bbox = [x1, y1, x2, y2]
            text = text.replace(':', '')
            matches = find_vocab_matches(text)
            if not matches: continue

            # apply offset to bbox
            offset = offsets[i]
            bbox = [bbox[0] + offset[0], bbox[1] + offset[1], bbox[2] + offset[0], bbox[3] + offset[1]]

            # segment bbox into len(matches) parts
            x1, y1, x2, y2 = bbox

            width = ( x2 - x1 ) / len(matches)

            for n, vocab in enumerate(matches):
                if not vocab: continue
                vocab_bbox = [int(x1 + n * width), int(y1), int(x1 + (n + 1) * width), int(y2)]
                vocab_canvas.add_vocab_card(vocab, vocab_bbox, DICTIONARY[vocab])

def gracefully_die(event=None):
    keyboard.unhook_all()
    root.quit()
    root.destroy()
    sys.exit(0)

def toggle_save():
    update_config(('save_data', not CONFIG['save_data']))
    print(f"Saving OCR data {'on' if CONFIG['save_data'] else 'off'}")

def toggle_verbose():
    update_config(('verbose', not CONFIG['verbose']))
    print(f"Verbose mode {'on' if CONFIG['verbose'] else 'off'}")

def toggle_strict_mode():
    update_config(('preprocess_image', not CONFIG['preprocess_image']))
    print(f"Strict mode {'on' if CONFIG['preprocess_image'] else 'off'}")

if __name__ == "__main__":
    # Bind the function to hotkey
    keyboard.add_hotkey(CONFIG['manual_capture_hotkey'], lambda: run(manual=True))
    keyboard.add_hotkey(CONFIG['configure_bbox_hotkey'], configure_bbox)
    keyboard.add_hotkey(CONFIG['fullscreen_capture_hotkey'], lambda: run(fullscreen=True))
    mouse.on_middle_click(lambda: run(fullscreen=True))
    keyboard.add_hotkey('f8', toggle_save)
    keyboard.add_hotkey('f9', pick_text_color)
    keyboard.add_hotkey('f10', toggle_verbose)
    keyboard.add_hotkey('f11', toggle_strict_mode)

    root = Tk()
    root.attributes('-fullscreen', True, '-topmost', True, '-alpha', 0)
    # root.overrideredirect(True)

    keyboard.add_hotkey('esc', lambda: clear_canvases(root))
    mouse.on_right_click(lambda: clear_canvases(root))

    print("Ready!")
    try:
        root.mainloop()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sys.exit(0)


# TODO:
# - Add a way to manually add custom vocab to the dictionary, categorize by game and only show if in that game
