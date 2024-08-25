import threading
from tkinter import Button, Canvas, Tk, Toplevel, Label, Frame
from utils.anki import add_vocabulary_to_anki, build_vocab_entry_from_VocabCard
import json

class VocabCanvas(Canvas):
    def __init__(self, root: Tk):
        super().__init__(root)
        self.config(bg='white', bd=0, highlightthickness=0)
        self.pack(fill='both', expand=True)
        self.root = root
        self.vocab_cards: list[VocabCard] = []
    
    def add_vocab_card(self, vocab: str, bbox: list[int], dictionary_entry):
        card = VocabCard(self, vocab, bbox, dictionary_entry)
        self.vocab_cards.append(card)
    
    def shift_focus(self, new_focus):
        for card in self.vocab_cards:
            if card == new_focus:
                card.construct_GUI()
            else:
                card.remove_GUI()
    
    def destroy(self):
        for card in self.vocab_cards:
            card.destroy()
        super().destroy()

class VocabCard:
    def __init__(self, parent: VocabCanvas, vocab: str, bbox: list[int], dictionary_entry):
        self.parent = parent
        self.simplified = vocab

        traditional_list = [entry[0] for entry in dictionary_entry]
        pinyin_list = [entry[1] for entry in dictionary_entry]
        english_list = [entry[2] for entry in dictionary_entry]

        def format_entries(pinyin_list, english_list):
            entries = {}
            for traditional, pinyin, english in zip(traditional_list, pinyin_list, english_list):
                if traditional in entries:
                    if pinyin in entries[traditional]:
                        entries[traditional][pinyin].append(english)
                    else:
                        entries[traditional][pinyin] = [english]
                else:
                    entries[traditional] = {pinyin: [english]}
                    
            return entries
        
        self.entries = format_entries(pinyin_list, english_list) # {traditional: {pinyin: [english]}}
        self.is_single_entry = len(traditional_list) == 1 and len(pinyin_list) == 1 and len(english_list) == 1

        self.bbox = bbox
        self.card = None
        self.hoverbox = None
        self.initiate_hoverbox()
        self.added_to_anki = False
        
    def initiate_hoverbox(self):
        self.hoverbox = Toplevel(self.parent)
        self.hoverbox.attributes('-alpha', 0.01)
        self.hoverbox.wm_attributes("-topmost", True)
        self.hoverbox.overrideredirect(True)

        self.hoverbox.update_idletasks()
        self.hoverbox.geometry(f"{self.bbox[2] - self.bbox[0]}x{self.bbox[3] - self.bbox[1]}+{self.bbox[0]}+{self.bbox[1]}")

        self.hoverbox.bind('<Enter>', self.update_card_visibility)
        self.hoverbox.bind('<Leave>', self.update_card_visibility)
    
    def update_card_visibility(self, event):
        x, y = event.x_root, event.y_root
        mouse_on_hoverbox = self.bbox[0] <= x <= self.bbox[2] and self.bbox[1] <= y <= self.bbox[3]
        mouse_on_card = self.card and \
            self.card.winfo_rootx() <= x <= (self.card.winfo_rootx() + self.card.winfo_width()) and \
                self.card.winfo_rooty() <= y <= (self.card.winfo_rooty() + self.card.winfo_height())
        is_focused = mouse_on_hoverbox or mouse_on_card

        if is_focused:
            self.parent.shift_focus(self)
        else:
            self.remove_GUI()

    def construct_GUI(self):
        if self.card:
            return # already constructed
        
        try:
            self.card = Toplevel(self.parent)
            self.card.attributes('-alpha', 1)
            self.card.config(bg='#ffffd7')
            self.card.overrideredirect(True)
            self.card.wm_attributes("-topmost", True)

            for i, traditional in enumerate(self.entries):
                title = Label(self.card, text=f"{self.simplified} | {traditional}", bg='#ffffd7', font=('Arial', 16), justify='left', anchor='w', padx=8)
                title.pack(fill='both', expand=True)

                pinyin_list = self.entries[traditional]
                for j, pinyin in enumerate(pinyin_list):
                    english_list = pinyin_list[pinyin]
                    if len(english_list) > 1:
                        # enumerate english
                        english = '\n'.join([f"{i}. {e}" for i, e in enumerate(english_list, 1)])
                    else:
                        english = english_list[0]
                    # label = Label(self.card, text=f"{english}\n\n{pinyin}", bg='#ffffd7', font=('Arial', 14), justify='left', anchor='w', padx=8, wraplength=500)
                    english_label = Label(self.card, text=f"{english}", bg='#ffffd7', font=('Arial', 14), justify='left', anchor='w', padx=8, wraplength=500)
                    english_label.pack(fill='both', expand=True)

                    pinyin_label = Label(self.card, text=f"{pinyin}", bg='#ffffd7', fg='red', font=('Arial', 14), justify='left', anchor='w', padx=8)
                    pinyin_label.pack(fill='both', expand=True)

                    if not self.is_single_entry:
                        english_label.config(font=('Arial', 12))
                        pinyin_label.config(font=('Arial', 12))

                    if j < len(pinyin_list) - 1:
                        # Add a dividing line
                        line = Frame(self.card, height=1, bg='black')
                        line.pack(fill='x', padx=5, pady=5)

                    english_label.pack(fill='both', expand=True)
                    pinyin_label.pack(fill='both', expand=True)
                
                if i < len(self.entries) - 1:
                    # Add a divider between traditionals
                    divider = Frame(self.card, height=2, bg='black')
                    divider.pack(fill='x', padx=5, pady=5)  
            
            self.card.update_idletasks()

            padding = 25
            width = self.card.winfo_reqwidth() + padding
            height = self.card.winfo_reqheight()
            self.card.geometry(f"{width}x{height}+{self.bbox[0]}+{self.bbox[1] - height}")

            # Create and pack the button at the bottom right
            self.add_to_anki_button = Button(self.card, cursor='hand2', text="+", bg='gray', fg='black', font=('Arial', 10), width=2, height=1, command=self.add_to_anki)
            if self.added_to_anki:
                self.add_to_anki_button.config(text='✓', bg='#90EE90', fg='white', cursor='arrow', state='disabled')
            self.add_to_anki_button.place(relx=1, rely=1, x=-5, y=-5, anchor='se')

            self.card.bind('<Enter>', self.update_card_visibility)
            self.card.bind('<Leave>', self.update_card_visibility)

        except Exception as e:
            print(f"Error constructing GUI: {e}")
            self.remove_GUI()
    
    def add_to_anki(self):
        self.add_to_anki_button.config(text='✓', bg='#90EE90', fg='white', cursor='arrow', state='disabled')
        self.added_to_anki = True

        def add_to_anki_thread():
            vocab_entry = build_vocab_entry_from_VocabCard(self)
            with open('./config.json', 'r') as f:
                CONFIG = json.load(f)
            add_vocabulary_to_anki(CONFIG['anki'], vocab_entry)
    
        threading.Thread(target=add_to_anki_thread).start()

    def remove_GUI(self):
        if self.card:
            self.card.destroy()
            self.card = None
    
    def destroy(self):
        self.remove_GUI()
        self.hoverbox.destroy()

    def __str__(self):
        formatted_entries = '\n'.join([f"{k}: {v}" for k, v in self.entries.items()])
        return f"{self.simplified}\n{formatted_entries}\n{self.bbox}"
    
    def __repr__(self):
        return f"VocabCard({self.simplified}, {self.bbox})"