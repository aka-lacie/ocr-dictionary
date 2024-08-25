# Introduction

Use OCR to instantly do a dictionary lookup by hovering over unselectable text (e.g. in a game). One-click to add vocab to Anki.

![demo](https://github.com/user-attachments/assets/35faae18-bd4b-4354-b3f2-262f50c9be36)

Currently supports simplified Chinese -> English

# Installation

Use `poetry install` or check `pyproject.toml` for the dependencies and use your preferred package manager.

If you have a compatible NVIDIA GPU, CUDA (12.1) is heavily recommended. Performance may significantly degrade without it.<br>
If torch gets downgraded for some reason, see how to manually install the correct version of torch+cuda [here](https://pytorch.org/get-started/locally/).

# Usage

This section will cover:
* How to startup
* Features and default control
* Config

## Run

Simply run
```
py script.py
```
Check console output on startup to see if it has initialized with CUDA as expected.

## Actions & Controls

You will primarily be pressing your scroll-wheel on your mouse to capture a snapshot. After a second or two, simply hover over a word and a dictionary card will appear.

| Action | Default mapping |
--- | ---
| Clear screen |  `mouse right click` |
| Capture fullscreen | `mouse middle click` or `F5` |
| Capture partial (manual) | `F6` |
| Colorpick text for `strict_mode`* | `F9` |
| Toggle verbose (debugging) | `F10` |
| Toggle `strict_mode`* | `F11` | 

### Strict mode

*In this mode, it will first pre-process the image to erase any pixels outside of the list of allowed colors (with some tolerance). Use if you encounter trouble with the recognition.

Use colorpicking to select a new color using the crosshairs + color preview. The default supported colors are white, beige-white, and two shades of gold-yellow. (Note the preview may *slightly* misrepresent the true color that gets recorded because tkinter applies a very light filter over the screen.)

## Anki

[AnkiConnect add-on](https://ankiweb.net/shared/info/2055492159) is required.

If you open Anki in the background, you can automatically add vocab cards to a deck of your choice by clicking on the `+` button on the bottom right of a card. This will automatically filter out duplicates.

## Config

Much of these controls and settings can be adjusted to your liking in `config.json`. For Anki, if your cards are set up in a different language, change the corresponding fields to the correct strings.

## Support

This project is developed on Windows with the intention of using on Chinese games with solid, horizontal text like Wuthering Waves or Genshin. It has not been tested outside of these environments.

Traditional Chinese and Japanese support will be added next.

## Acknowledgement

This project uses [EasyOCR](https://github.com/JaidedAI/EasyOCR) for character recognition, and CEDICT for dictionary entries.
