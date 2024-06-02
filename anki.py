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

def add_vocabulary_to_anki(deck_name, vocab_entry):
    invoke('createDeck', {'deck': deck_name})

    note = {
        'deckName': deck_name,
        'modelName': "问答题",
        'fields': {
            '正面': vocab_entry['front'],
            '背面': vocab_entry['back']
        },
        'options': {
            'allowDuplicate': False
        },
        # 'tags': vocab_entry.get('tags', [])
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
