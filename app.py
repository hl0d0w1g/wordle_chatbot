from collections import Counter
from datetime import datetime
from flask import Flask, request
from sqlalchemy import ForeignKey, and_
from twilio.twiml.messaging_response import MessagingResponse
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

USER = 'postgres'
PASSWORD = 'postgres'

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{USER}:{PASSWORD}@localhost:5432/wordle'
db = SQLAlchemy(app)

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


class Words(db.Model):
    __tablename__ = 'words'

    word_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String())
    word_date = db.Column(db.Date())

    def __init__(self, word, word_date):
        self.word = word
        self.word_date = word_date

    def __repr__(self):
        return f'<Word {self.word} for {self.word_date}>'

class Users(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    user_phone = db.Column(db.String())
    signup_on = db.Column(db.DateTime())
    last_login = db.Column(db.DateTime())
    sessions = db.relationship('Sessions')

    def __init__(self, user_phone, signup_on):
        self.user_phone = user_phone
        self.signup_on = signup_on
        self.last_login = signup_on

    def __repr__(self):
        return f'<User {self.user_phone}>'

class Sessions(db.Model):
    __tablename__ = 'sessions'

    session_id = db.Column(db.Integer, primary_key=True)
    session_date = db.Column(db.Date())
    completed = db.Column(db.Boolean())
    n_tries = db.Column(db.Integer())
    user_id = db.Column(db.Integer(), ForeignKey('users.user_id'))
    results = db.relationship('Results')

    def __init__(self, session_date, completed, user_id):
        self.session_date = session_date
        self.completed = completed
        self.n_tries = 0
        self.user_id = user_id

    def __repr__(self):
        return f'<Session of user {self.user_id} from {self.session_date}>'

class Results(db.Model):
    __tablename__ = 'results'

    result_id = db.Column(db.Integer, primary_key=True)
    result_datetime = db.Column(db.DateTime())
    color_code = db.Column(db.String())
    tried_word = db.Column(db.String())
    session_id = db.Column(db.Integer(), ForeignKey('sessions.session_id'))

    def __init__(self, result_datetime, color_code, tried_word, session_id):
        self.result_datetime = result_datetime
        self.color_code = color_code
        self.tried_word = tried_word
        self.session_id = session_id

    def __repr__(self):
        return f'<Result {self.color_code} from {self.tried_word} on {self.result_datetime}>'


def get_day_word(date:str) -> str:
    '''
    Get the word of the day to game
    '''
    
    words = db.session.query(Words).filter(Words.word_date == date)
    word = words[0].word
    return word

def check_word(word:str) -> bool:
    '''
    Check if the word introduced by the user is valid
    '''
    valid_word = False

    if len(word) == 5:
        valid_word = True
    # TO-DO: Check if the word is in the dictionary

    return valid_word

def check_try(word:str, tried_word:str) -> list:
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

def parse_result(result:list) -> str:
    '''
    Parses the result in a human readable string
    '''
    emojis = {'W': '⬜', 'Y': '🟨', 'G': '🟩'}
    
    word_parsed = ''.join([w.upper() + '   ' for w, r in result])
    result_parsed = ''.join([emojis[r] for w, r in result])

    result_str = f'{word_parsed}\n{result_parsed}'

    return result_str

def parse_global_results(n_tries:list, victories_pct=int) -> str:
    '''
    Parses the global results in a human readable string
    '''
    result_str = ''
    tries_dst = Counter(n_tries)
    for i in range(MAX_TRIES):
        n = tries_dst.get(i + 1, 0)
        pct = round((n / len(n_tries)) * 100)
        emoji_bar = ''.join(['⬛' for _ in range(round(pct / 10))])
        result_str += f'{i + 1}:' + emoji_bar + f'({pct}%)\n'
    return result_str

def twilio_message(messages:list, cost_optimizer:bool=True) -> str:
    '''
    Creates Twilio message from a list of strings
    '''
    tl_response = MessagingResponse()

    if cost_optimizer:
        messages = ['\n\n'.join(messages)]

    for message in messages:
        tl_response.message(message)

    return str(tl_response)


@app.route('/new-message', methods=['POST'])
def game():
    global BRIEFING, MAX_TRIES

    current_datetime = datetime.now()
    user_phone = request.form['From'].replace('whatsapp:', '')
    message = request.form['Body'].lower()
    # print(message)
    # print(user_phone, current_datetime.strftime('%Y-%m-%d'))
    
    user = db.session.query(Users).filter(Users.user_phone == user_phone).first()
    if user:
        user.last_login = current_datetime
        db.session.add(user)
        db.session.commit()
    else:
        user = Users(user_phone=user_phone, signup_on=current_datetime)
        db.session.add(user)
        db.session.commit()

    response_messages = []
    if message == 'instrucciones':
        response_messages.append(BRIEFING)

    elif message == 'resultados':
        sessions = db.session.query(Sessions).filter(Sessions.user_id == user.user_id).all()
        n_sessions = len(sessions)
        victories = [s for s in sessions if s.completed]
        n_victories = len(victories)
        victories_pct = round((n_victories / n_sessions) * 100)
        n_tries = [s.n_tries for s in sessions]

        response_messages.append('Tus resultados:')
        response_messages.append(f'Partidas jugadas: {n_sessions}\nVictorias: {victories_pct}%')
        response_messages.append(parse_global_results(n_tries, victories_pct))

    elif not check_word(message):
        response_messages.append('La palabra que has introducido no es válida.')
        response_messages.append('Recueda que debe ser una palabra del diccionario de 5 letras.')

    else:
        today_results = []
        session = db.session.query(Sessions).filter(and_(Sessions.user_id == user.user_id, Sessions.session_date == current_datetime.strftime('%Y-%m-%d'))).first()
        if session:
            session_results = db.session.query(Results).filter(Results.session_id == session.session_id).all()
            if session_results:
                today_results = [parse_result([(l, r) for l, r in zip(r.tried_word, r.color_code)]) for r in session_results]
                today_results = [tr.split('\n')[-1] for tr in today_results]
        else:
            session = Sessions(session_date=current_datetime.strftime('%Y-%m-%d'), completed=False, user_id=user.user_id)
            db.session.add(session)
            db.session.commit()

        n_tries = len(today_results)
        if n_tries >= MAX_TRIES or session.completed:
            response_messages.append('Has alcanzado el número máximo de intentos para la palabra de hoy.\Vuelve de nuevo mañana!')
            response_messages.append('Tus estadisticas de hoy:\n' + '\n'.join(today_results))

        else:
            day_word = get_day_word(current_datetime.strftime('%Y-%m-%d'))
            # print(day_word, message)
            n_tries += 1
            result = check_try(day_word, message)
            parsed_results = parse_result(result)
            response_messages.append(f'Intento {n_tries}/{MAX_TRIES}\n' + parsed_results)
            today_results.append(parsed_results.split('\n')[-1])

            correct_word = all([True if r == 'G' else False for l, r in result])
            
            result = Results(result_datetime=current_datetime, color_code=''.join([r for l, r in result]), tried_word=message, session_id=session.session_id)
            db.session.add(result)
            db.session.commit()

            session.n_tries = n_tries
            if correct_word:
                response_messages.append(f'!ENHORABUENA¡ Has adivinado la palabra en {n_tries} intentos.\nVuelve mañana para una nueva palabra!')
                response_messages.append('Tus estadisticas de hoy:\n' + '\n'.join(today_results))

                session.completed = True

            else:
                if n_tries >= MAX_TRIES:
                    response_messages.append('Has alcanzado el número máximo de intentos para la palabra de hoy.\nIntentalo de nuevo mañana!')
                    response_messages.append('Tus estadisticas de hoy:\n' + '\n'.join(today_results))
                
            db.session.add(session)
            db.session.commit()

    response = twilio_message(response_messages)
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


