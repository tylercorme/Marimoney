import sqlite3
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        PRAGMA foreign_keys = ON;
    
        create table if not exists accounts (
            id integer primary key,
            name text unique not null,
            start_balance integer default 0,
            on_budget integer not null default 1,
            created_at datetime default current_timestamp
        );
        
        create table if not exists categories (
            id integer primary key,
            name text unique not null
        );
        
        create table if not exists budget_items (
            month integer,
            year integer,
            category_id integer references categories(id) on delete cascade,
            budgeted_amount integer,
            primary key(month, year, category_id),
            check (month between 1 and 12)
        );
        
        create table if not exists transactions (
            id integer primary key,
            account_id integer not null references accounts(id) on delete cascade,
            transfer_from_id integer references accounts(id) on delete set null,
            category_id integer references categories(id) on delete set null,
            amount integer not null default 0,
            notes text,
            date datetime not null,
            status integer not null default 0
        ); 
    """)
    conn.commit()
    return conn