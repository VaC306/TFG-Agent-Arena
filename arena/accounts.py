"""Local accounts and revocable sessions. Provider credentials are deliberately separate."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from typing import Literal
from fastapi import HTTPException
from pydantic import Field, field_validator
from .contracts import Contract

COOKIE = 'arena_session'
SESSION_SECONDS = 7 * 24 * 60 * 60


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=3,
                          maxmem=64 * 1024 * 1024).hex()


class Credentials(Contract):
    username: str = Field(min_length=3, max_length=40, pattern=r'^[A-Za-z0-9_.-]+$')
    password: str = Field(min_length=1, max_length=128)

    @field_validator('username')
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Registration(Credentials):
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator('display_name')
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError('Escribe tu nombre')
        return value.strip()


class SavedPrompt(Contract):
    template: Literal['general', 'analyst', 'summary', 'extract', 'vision', 'custom'] = 'general'
    text: str = Field(default='', max_length=6000)


class Preferences(Contract):
    name: str = Field(default='Comparación personalizada', max_length=120)
    adapter: Literal['simulated', 'ollama'] = 'simulated'
    mode: Literal['same_model', 'different_models'] = 'same_model'
    source: Literal['manual', 'dataset'] = 'manual'
    repetitions: int = Field(default=1, ge=1, le=10)
    modelA: str = Field(default='simulated-a', max_length=120)
    modelB: str = Field(default='simulated-b', max_length=120)
    promptA: SavedPrompt = Field(default_factory=SavedPrompt)
    promptB: SavedPrompt = Field(default_factory=lambda: SavedPrompt(template='analyst'))


class ProfileUpdate(Contract):
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator('display_name')
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError('Escribe tu nombre')
        return value.strip()


class Accounts:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users(
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
                    salt TEXT NOT NULL, password_hash TEXT NOT NULL, preferences TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_attempts(client TEXT NOT NULL, at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS auth_attempts_client ON auth_attempts(client, at);
            ''')

    def limited(self, client):
        now = time.time()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM auth_attempts WHERE at < ?', (now - 60,))
            if db.execute('SELECT COUNT(*) FROM auth_attempts WHERE client=?', (client,)).fetchone()[0] >= 10:
                raise HTTPException(429, 'Demasiados intentos. Espera un minuto.')
            db.execute('INSERT INTO auth_attempts VALUES (?,?)', (client, now))

    @staticmethod
    def public(row):
        return {key: row[key] for key in ('id', 'username', 'display_name')} | {'preferences': json.loads(row['preferences'])}

    def register(self, data):
        return self.create_user(data.username, data.password, data.display_name)

    def create_user(self, username, password, display_name):
        salt = secrets.token_hex(16)
        hashed = password_hash(password, salt)
        user_id = str(uuid.uuid4())
        try:
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                first = db.execute('SELECT 1 FROM users LIMIT 1').fetchone() is None
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?)',
                           (user_id, username, display_name, salt, hashed, Preferences().model_dump_json()))
                if first:
                    db.execute('INSERT OR IGNORE INTO experiment_owners SELECT id,? FROM experiments', (user_id,))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Ese nombre de usuario ya existe')
        return user_id

    def create_test_user(self):
        """Explicit CLI-only development account; never run at application startup."""
        with self.store.connect() as db:
            existing = db.execute('SELECT id FROM users WHERE username=?', ('test',)).fetchone()
        if existing:
            # Do not replace an existing account's password or identity.
            self.login(Credentials(username='test', password='test'))
            return existing['id']
        return self.create_user('test', 'test', 'Test')

    def login(self, data):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (data.username,)).fetchone()
        salt = row['salt'] if row else '0' * 32
        hashed = password_hash(data.password, salt)
        if row is None or not hmac.compare_digest(hashed, row['password_hash']):
            raise HTTPException(401, 'Usuario o contraseña incorrectos')
        return row['id']

    def new_session(self, user_id):
        token = secrets.token_urlsafe(32)
        with self.store.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires_at < ?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time() + SESSION_SECONDS))
        return token

    def current(self, token):
        if not token or len(token) > 128:
            return None
        with self.store.connect() as db:
            row = db.execute('''SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id
                                WHERE s.token_hash=? AND s.expires_at>?''',
                             (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        return self.public(row) if row else None

    def logout(self, token):
        if token:
            with self.store.connect() as db:
                db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def has_users(self):
        with self.store.connect() as db:
            return db.execute('SELECT 1 FROM users LIMIT 1').fetchone() is not None

    def update(self, user_id, column, value):
        if column not in {'display_name', 'preferences'}:
            raise ValueError('Campo no permitido')
        with self.store.connect() as db:
            db.execute(f'UPDATE users SET {column}=? WHERE id=?', (value, user_id))
