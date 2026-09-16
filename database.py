import sqlite3
from pathlib import Path




database_path = Path(__file__).parent / 'database.db'
_connection = sqlite3.connect(database_path)


        _connection.execute("""
        create table if not exists accounts (
            id integer primary key,
            name text unique not null,
            start_balance integer default 0,
            on_budget integer not null,
            created_at datetime default current_timestamp
        );
        """)

    @staticmethod
    def insert(name: str, start_balance: int, on_budget: bool) -> int:
            result = _connection.execute(
                'insert into accounts (name, start_balance, on_budget) values (?, ?, ?) returning id',
                (name, start_balance, on_budget)
            ).fetchone()
            _connection.commit()
            return result["id"]

    @staticmethod
    def update(id_: int, name: str, start_balance: int, on_budget: bool):
        _connection.execute(
            'update accounts set name = ?, start_balance = ?, on_budget = ? where id = ?',
            (name, start_balance, on_budget, id_)
        )
        _connection.commit()

    @staticmethod
    def all() -> list[dict]:
        return _connection.execute('select * from accounts').fetchall() or []

    @staticmethod
    def delete(id_: int) -> None:
        _connection.execute('delete from accounts where id = ?', (id_,))
        _connection.commit()

    @staticmethod
    def balances() -> list[dict]:
        rows = _connection.execute('''
            select 
                a.id,
                a.name,
                a.start_balance,
                a.on_budget,
                a.start_balance / 100.0 + coalesce(sum(t.amount), 0) / 100.0 as current_balance
            from accounts a
            left join transactions t on a.id = t.account_id
            group by a.id, a.name, a.start_balance, a.on_budget
            order by a.name
        ''').fetchall()
        return rows or []


class BudgetItems:

    @staticmethod
    def create_table():
        _connection.execute("""
            create table if not exists budget_items (
                month integer,
                year integer,
                category_id integer references categories(id) on delete cascade,
                budgeted_amount integer,
                primary key(month, year, category_id),
                check (month between 1 and 12)
            );
        """)

    @staticmethod
    def insert_or_replace(month: int, year: int, category_id: int, budgeted_amount: int) -> None:
        _connection.execute(
            '''
            insert or replace into budget_items (month, year, category_id, budgeted_amount)
            values (?, ?, ?, ?)
            ''',
            (month, year, category_id, budgeted_amount)
        )
        _connection.commit()

    @staticmethod
    def all(month: int, year: int) -> list[dict]:
        return _connection.execute("""
        select 
            c.id,
            c.name,
            b.month,
            b.year,
            b.category_id,
            b.budgeted_amount,
            coalesce(sum(t.amount), 0) as total_spent
        from categories c
        left join budget_items b on c.id = b.category_id 
            and b.month = ? and b.year = ?
        left join transactions t on c.id = t.category_id 
            and strftime('%m', t.date) = ? 
            and strftime('%Y', t.date) = ?
        group by c.id, c.name, b.month, b.year, b.category_id, b.budgeted_amount
        order by c.name
        """,
        (month, year, f'{month:02d}', f'{year:04d}')).fetchall() or []

    @staticmethod
    def delete(month: int, year: int, category_id: int) -> None:
        _connection.execute(
            'delete from budget_items where month = ? and year = ? and category_id = ?',
            (month, year, category_id)
        )
        _connection.commit()


class Categories:

    @staticmethod
    def create_table() -> None:
        _connection.execute("""
            create table if not exists categories (
                id integer primary key,
                name text unique not null
            );
        """)

    @staticmethod
    def insert(name: str) -> int:
            result = _connection.execute(
                """
                insert into categories (name) values (?)
                returning id
                """,
                (name,)
            ).fetchone()
            _connection.commit()
            return result["id"]

    @staticmethod
    def update(id_: int, name: str) -> None:
        _connection.execute(
            'update categories set name = ? where id = ?',
            (name, id_)
        )
        _connection.commit()

    @staticmethod
    def all() -> list[dict]:
        return _connection.execute('select * from categories').fetchall() or []

    @staticmethod
    def delete(id_: int) -> None:
        _connection.execute('delete from categories where id = ?', (id_,))
        _connection.commit()


class Transactions:

    @staticmethod
    def create_table():
        _connection.execute("""
            create table if not exists transactions (
                id integer primary key,
                account_id integer not null references accounts(id) on delete cascade,
                transfer_from_id integer references accounts(id),
                category_id integer references categories(id) on delete set null,
                amount integer not null,
                notes text,
                date datetime not null,
                status integer not null default 0,
            );
        """)

    @staticmethod
    def insert(
            account_id: int,
            transfer_from_id: int,
            category_id: int,
            amount: int,
            notes: str,
            date_: datetime
    ) -> int:
        result = _connection.execute(
            '''insert into transactions 
               (account_id, transfer_from_id, category_id, amount, notes, date)
               values (?, ?, ?, ?, ?, ?, ?, ?) returning id''',
            (
                account_id,
                transfer_from_id,
                category_id,
                amount,
                notes,
                datetime.combine(date_, datetime.min.time()).isoformat())
        ).fetchone()
        return result["id"]

    @staticmethod
    def update(
            id_: int,
            account_id: int,
            transfer_from_id: int,
            category_id: int,
            amount: int,
            notes: str,
            date_: datetime,
            status: int,
    ) -> None:
        _connection.execute("""
            update transactions set 
            account_id = ?, 
            transfer_from_id = ?, 
            category_id = ?, 
            amount = ?, 
            notes = ?, 
            date = ?,
            status = ? where id = ?
            """,
            (account_id,
             transfer_from_id,
             category_id,
             amount,
             notes,
             datetime.combine(date_, datetime.min.time()).isoformat(),
             status,
             id_)
        )

    @staticmethod
    def delete(id_: int) -> None:
        _connection.execute('delete from transactions where id = ?', (id_,))
        _connection.commit()

    @staticmethod
    def all(
        *account_ids: int,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> list[Transactions]:
        if not account_ids:
            return []

        placeholders = ','.join('?' * len(account_ids))
        params = []
        params.extend(account_ids)

        date_clause = ""
        if start_date:
            date_clause += " and t.date >= ?"
            params.append(datetime.combine(start_date, datetime.min.time()).isoformat())
        if end_date:
            date_clause += " and t.date <= ?"
            params.append(datetime.combine(end_date, datetime.max.time()).isoformat())

        rows = _connection.execute(f'''
            select 
                t.id,
                t.account_id,
                t.transfer_from_id,
                t.payee_id,
                t.category_id,
                t.amount,
                t.notes,
                t.is_cleared,
                t.date,
                a_transfer.name as transfer_from_name,
                p.name as payee_name,
                c.name as category_name
            from transactions t
            left join accounts a_transfer on a_transfer.id = t.transfer_from_id
            left join payees p on p.id = t.payee_id
            left join categories c on c.id = t.category_id
            where t.account_id in ({placeholders})
            {date_clause}
            order by t.date desc
        ''', params).fetchall()

        return rows or []


def main() -> None:
    _connection.execute("""
    create table if not exists accounts (
        id integer primary key,
        name text unique not null,
        start_balance integer default 0,
        on_budget integer not null,
        created_at datetime default current_timestamp
    );
    """)



if __name__ == '__main__':
    main()

