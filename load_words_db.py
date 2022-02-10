from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, Column, Integer, String, Date
import datetime
from random import shuffle

USER = 'postgres'
PASSWORD = 'postgres'

Base = declarative_base()
engine = create_engine(f'postgresql://{USER}:{PASSWORD}@localhost:5432/wordle')
session = sessionmaker(bind=engine)()

TODAY = datetime.datetime.today()

class Words(Base):
    __tablename__ = 'words'

    word_id = Column(Integer, primary_key=True)
    word = Column(String())
    word_date = Column(Date())

    def __init__(self, word, word_date):
        self.word = word
        self.word_date = word_date

    def __repr__(self):
        return f'<Word {self.word} for {self.word_date}>'

with open('data/spanish_words.txt') as file:
    words = file.readlines()

shuffle(words)

for idx, word in enumerate(words):
    word = word.rstrip()
    word_date = (TODAY + datetime.timedelta(days=idx)).strftime('%Y-%m-%d')
    print(word, word_date)

    w = Words(word=word, word_date=word_date)
    session.add(w)
    session.commit()