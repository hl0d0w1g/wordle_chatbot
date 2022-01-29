import random
from flask import Flask, request, jsonify, json
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

with open('data/spanish_words.txt') as file:
    WORDS = file.readlines()

MAX_TRIES = 6
BRIEFING = '''
Adivina la palabra oculta en seis intentos.
Cada intento debe ser una palabra válida de *5 letras*.
Después de cada intento unos indicadores de color (⬜🟨🟩) debajo de cada letra cambia para mostrar qué tan cerca estás de acertar la palabra.

Ejemplos:
G   A   T   O   S
🟩⬜⬜⬜⬜
La letra G🟩 está en la palabra y en la posición correcta. El resto de letras no están en la palabra⬜.

V   O   C   A   L
⬜⬜🟨⬜⬜
La letra C🟨 está en la palabra pero en la posición incorrecta. El resto de letras no están en la palabra⬜.

Puede haber letras repetidas. Las pistas son independientes para cada letra.

¡Una palabra nueva cada día!'''


current_word = ''
n_tries = 0
global_results = []

def generate_new_word() -> str:
    '''
    Generate a new word to start the game
    '''
    global WORDS
    word_idx = random.randint(0, len(WORDS))
    word = WORDS[word_idx]
    return word

def check_word(word: str) -> bool:
    '''
    Check if the word introduced by the user is valid
    '''
    valid_word = False

    if len(word) == 5:
        valid_word = True
    # TO-DO: Check if the word is in the dictionary

    return valid_word

def check_try(word: str, tried_word: str) -> list:
    '''
    Check the if the word introduced by the user match the target word
    '''
    result_ls = []

    for idx, l_pred in enumerate(tried_word):
        if l_pred == word[idx]:
            result = 'G'
        elif l_pred in word:
            result = 'Y'
        elif l_pred not in word:
            result = 'W'

        result_ls.append((l_pred, result)) # W | Y | G

    return result_ls

def parse_result(result: list) -> str:
    '''
    Parses the result in a human readable string
    '''
    emojis = {'W': '⬜', 'Y': '🟨', 'G': '🟩'}
    
    word_parsed = ''.join([w.upper() + '   ' for w, r in result])
    result_parsed = ''.join([emojis[r] for w, r in result])

    result_str = f'{word_parsed}\n{result_parsed}'
    return result_str

def twilio_message(messages: list) -> str:
    '''
    Creates Twilio message from a list of strings
    '''
    tl_response = MessagingResponse()
    for message in messages:
        tl_response.message(message)

    return str(tl_response)


@app.route('/new-message', methods=['POST'])
def game():
    global current_word, n_tries, global_results
    global BRIEFING, MAX_TRIES

    message = request.form['Body'].lower()
    # print(message)

    response_messages = []
    if message == 'quiero jugar':
        current_word = generate_new_word()
        global_results = []
        n_tries = 0

        response_messages.append(BRIEFING)

    elif not check_word(message):
        response_messages.append('La palabra que has introducido no es válida.')
        response_messages.append('Recueda que debe ser una palabra del diccionario de 5 letras.')

    else:
        if n_tries >= MAX_TRIES:
            response_messages.append('Has alcanzado el número máximo de intentos para la palabra de hoy.\nIntentalo de nuevo mañana!')
            response_messages.append('Tus estadisticas de hoy:\n' + '\n'.join(global_results))

        else:
            # print(current_word, message)
            n_tries += 1
            result = check_try(current_word, message)
            parsed_results = parse_result(result)
            response_messages.append(f'Intento {n_tries}/{MAX_TRIES}\n' + parsed_results)
            global_results.append(parsed_results.split('\n')[-1])

            correct_word = all([True if r == 'G' else False for l, r in result])

            if correct_word:
                response_messages.append(f'!ENHORABUENA¡ Has adivinado la palabra en {n_tries} intentos.\nVuelve mañana para una nueva palabra!')
                response_messages.append('Tus estadisticas de hoy:\n' + '\n'.join(global_results))

            else:
                if n_tries >= MAX_TRIES:
                    response_messages.append('Has alcanzado el número máximo de intentos para la palabra de hoy.\nIntentalo de nuevo mañana!')
                    response_messages.append('Tus estadisticas de hoy:\n' + '\n'.join(global_results))


    response = twilio_message(response_messages)
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
