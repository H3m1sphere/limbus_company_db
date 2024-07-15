from io import StringIO
import urllib.robotparser
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlalchemy
from sqlalchemy import Column, create_engine, Integer, String
from sqlalchemy.orm import sessionmaker,declarative_base
import sqlite3
import time
import my_module as mm







engine = create_engine('sqlite:///limbus_company.db')
Base = declarative_base()

class CharacterList(Base):
    __tablename__ = "character_list"

    id = Column("id", Integer, primary_key=True)
    scenario = Column("scenario", String)
    name = Column("name", String)
    cv = Column("cv", String)
    note = Column("note", String)
    link = Column("link", String)

    @property
    def source(self):
        return "https://wikiwiki.jp/lcbwiki/キャラクター"

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

for i,row in df.iterrows():
    character = CharacterList(
        scenario=row["シナリオ"],
        name=row["氏名"],
        cv=row["CV"],
        note=row["備考"],
        link=row["リンク"]
    )
    session.add(character)
session.commit()

characterlist = session.query(CharacterList).all()
for character in characterlist:
    print(character.id, character.scenario, character.name, character.cv, character.note, character.link)
mm.open_file(pd.read_sql("character_list", engine))