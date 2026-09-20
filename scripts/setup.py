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
            name text unique not null,
            is_income integer not null default 0
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
            transfer_account_id integer references accounts(id) on delete set null,
            category_id integer references categories(id) on delete set null,
            amount integer not null default 0,
            notes text,
            date date not null,
            count int not null default 1,
            imported_date date not null default current_timestamp,
            status integer not null default 0,
            created_at datetime default current_timestamp,
            original_json json not null,
            unique(original_json, count)
            check (transfer_account_id != account_id)
        ); 
        
        create table if not exists settings (
            key text primary key,
            value text not null
        );
    """)
    conn.commit()
    return conn
