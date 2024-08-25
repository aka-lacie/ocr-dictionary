import requests

def anki_connect(action, params={}):
    return {'action': action, 'version': 6, 'params': params}

def invoke(action, params={}):
    request_json = anki_connect(action, params)
    response = requests.post('http://localhost:8765', json=request_json)
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
    result = response.json()
    if 'error' in result and result['error'] is not None:
        print(f"Error from AnkiConnect: {result['error']}")
    return result['result']

def add_vocabulary_to_anki(anki_config, vocab_entry):
    deck_name = anki_config['deck_name']
    model_name = anki_config['model']
    front = anki_config['front']
    back = anki_config['back']

    invoke('createDeck', {'deck': deck_name})

    note = {
        'deckName': deck_name,
        'modelName': model_name, # "问答题"
        'fields': {
            front: vocab_entry['front'], # '正面'
            back: vocab_entry['back'] # '背面'
        },
        'options': {
            'allowDuplicate': False
        },
    }

    invoke('addNote', {'note': note})
    invoke('sync')

def build_vocab_entry_from_VocabCard(vocab_card):
    front = f"<h1>{vocab_card.simplified}</h1>"
    back = ""

    for traditional, pinyin_dict in vocab_card.entries.items():
        back += f"<h3>tr: {traditional}</h3>"
        for pinyin, english_list in pinyin_dict.items():
            english_string = '<br>- '.join(english_list)
            back += f"<code>{pinyin}</code><br>- {english_string}"
            back += "<br><br>"
    back = back[:-8] # strip trailing <br>s

    return {'front': front, 'back': back}
