import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from datetime import datetime, timedelta, date
    from traceback import TracebackException
    from hashlib import sha256
    import sqlite3
    import json

    from importlib import reload
    reload(__import__("transaction_parsers"))
    from transaction_parsers import get_parser, get_institutions


    return (
        TracebackException,
        date,
        datetime,
        get_institutions,
        get_parser,
        json,
        mo,
        reload,
        sha256,
        sqlite3,
        timedelta,
    )


@app.cell
def _(reload):
    from setup import get_connection
    reload(__import__("setup"))
    conn = get_connection()
    return (conn,)


@app.function
def to_money_str(cents: int | None, signed: bool = False) -> str:
    v = (cents or 0) / 100
    sign = "-" if v < 0 else ("+" if signed else "")
    return f"{sign}${abs(v):_.2f}"


@app.cell(hide_code=True)
def _(mo):
    refresh = mo.ui.refresh(default_interval=1)
    refresh
    return (refresh,)


@app.cell
def _(datetime, mo, refresh):
    refresh
    now = datetime.now().strftime('%B %d, %Y, %I:%M:%S %p')
    header = mo.md(
         f"""
         # Tyler's Budget
         ---
         ### {now}
         """
    )
    return (header,)


@app.cell(hide_code=True)
def _(account_name_to_balance, header, mo, net_worth):
    mo.sidebar(
        mo.vstack([
            header,
            mo.md(
                """
                ## Acounts
                ---
                """),
            mo.hstack([mo.md("**All**"), mo.md(net_worth)]),
            mo.md("---"),
            *[mo.hstack([mo.md(f"**{_name}**"), mo.md(_balance)]) for _name, _balance in account_name_to_balance.items()]
        ]).center(),
    )
    return


@app.cell
def _(mo):
    get_account_error_message, set_account_error_message = mo.state(None)
    get_account_message, set_account_message = mo.state(None)
    get_accounts, update_accounts = mo.state(None)
    get_balances, update_balances = mo.state(None)
    return (
        get_account_error_message,
        get_account_message,
        get_accounts,
        get_balances,
        set_account_error_message,
        set_account_message,
        update_accounts,
        update_balances,
    )


@app.cell
def _(
    TracebackException,
    conn,
    get_accounts,
    mo,
    set_account_error_message,
    set_account_message,
    update_balances,
):
    get_accounts()

    _accounts = conn.execute("""
        select id, name, start_balance, on_budget from accounts order by name
    """).fetchall() or []
    account_name_to_id = {_name: _id for _id, _name, _, _ in _accounts}


    def _update_name(v, id_):
        try:
            if not v:
                return
            conn.execute(
                "update accounts set name = ? where id = ?",
                (
                    str(v),
                    id_
                )
            )
            conn.commit()
            set_account_message(f"Successfully updated.")
            set_account_error_message(None)
        except Exception as e:
            _trace = TracebackException.from_exception(e)
            _trace_message = ''.join(_trace.format())
            set_account_error_message(_trace_message)
            conn.rollback()
        finally:
            update_balances(None)

    def _update_start_budget(v, id_):
        try:
            if v is None:
                return
            conn.execute(
                "update accounts set start_balance = ? where id = ?",
                (
                    int(v*100),
                    id_
                )
            )
            conn.commit()
            set_account_message(f"Successfully updated.")
            set_account_error_message(None)
        except Exception as e:
            _trace = TracebackException.from_exception(e)
            _trace_message = ''.join(_trace.format())
            set_account_error_message(_trace_message)
            conn.rollback()
        finally:
            update_balances(None)

    def _update_on_budget(v, id_):
        try:
            conn.execute(
                "update accounts set on_budget = ? where id = ?",
                (
                    bool(v),
                    id_
                )
            )
            conn.commit()
            set_account_message(f"Successfully updated.")
            set_account_error_message(None)
        except Exception as e:
            _trace = TracebackException.from_exception(e)
            _trace_message = ''.join(_trace.format())
            set_account_error_message(_trace_message)
            conn.rollback()
        finally:
            update_balances(None)


    accounts_header = mo.hstack(
        [
            mo.md("**Name**"),
            mo.md("**Start Budget**"),
            mo.md("**On Budget**"),
            mo.md(""), # save room for delete button
        ],
        widths="equal",                   
    )

    account_delete_buttons = mo.ui.array([
        mo.ui.run_button(kind="danger", label="Delete")
        for _ in range(len(_accounts))
    ])

    account_ids = [_id for _id, *_ in _accounts]

    account_fields = [
        mo.hstack(
            [
                mo.ui.text(
                    value=_name, 
                    on_change=lambda v, __id=_id: _update_name(v, __id),
                ),
                mo.ui.number(
                    value=float(_start_balance)/100.0, 
                    on_change=lambda v, __id=_id: _update_start_budget(v, __id) 
                ),
                mo.ui.checkbox(
                    value=bool(_on_budget),
                    on_change=lambda v, __id=_id: _update_on_budget(v, __id)
                ),
                account_delete_buttons[i],
            ],
            widths="equal"         
        ) for i, (_id, _name, _start_balance, _on_budget) in enumerate(_accounts)
    ]

    new_account_name = mo.ui.text(placeholder="Account Name")
    new_start_balance = mo.ui.number(value=0.0)
    new_on_budget = mo.ui.checkbox(value=True)
    new_account_button = mo.ui.run_button(label="Add Account")
    add_new_account_form = mo.hstack(
        [
            new_account_name, 
            new_start_balance, 
            new_on_budget, 
            new_account_button,
        ],
        widths="equal"
    )
    return (
        account_delete_buttons,
        account_fields,
        account_ids,
        account_name_to_id,
        accounts_header,
        add_new_account_form,
        new_account_button,
        new_account_name,
        new_on_budget,
        new_start_balance,
    )


@app.cell
def _(conn, get_accounts, get_balances):
    get_balances()
    get_accounts()

    _balances = conn.execute("""
        select
        a.name,
        a.start_balance
          + coalesce((select sum(t.amount) from transactions t
                      where t.account_id = a.id), 0)
          - coalesce((select sum(t.amount) from transactions t
                      where t.transfer_account_id = a.id), 0) as current_balance
        from accounts a
        order by a.name
    """).fetchall() or []

    account_name_to_balance = {_name: to_money_str(_balance) for _name, _balance in _balances}
    net_worth = to_money_str(sum([_balance for _, _balance in _balances]))
    return account_name_to_balance, net_worth


@app.cell
def _(get_account_error_message, get_account_message, mo):
    account_flag: mo.Html
    if get_account_error_message():
        account_flag = mo.md(get_account_error_message()).callout("danger")
    elif get_account_message():
        account_flag = mo.md(get_account_message()).callout("success")
    else:
        account_flag = ""
    return (account_flag,)


@app.cell
def _(
    TracebackException,
    account_delete_buttons,
    account_fields,
    account_flag: "mo.Html",
    account_ids,
    accounts_header,
    add_new_account_form,
    conn,
    mo,
    new_account_button,
    new_account_name,
    new_on_budget,
    new_start_balance,
    set_account_error_message,
    set_account_message,
    update_accounts,
    update_balances,
):
    _accounts = mo.vstack([
        mo.md("# Accounts"),
        mo.md("---"),
        accounts_header,
        *account_fields,
        mo.md("---"),
        add_new_account_form,
        account_flag,

    ])

    for _id, _delete_button in zip(account_ids, account_delete_buttons):
        if _delete_button.value:
            try:
                conn.execute(
                    """
                    delete from accounts where id = ?
                    """,
                    (_id,)
                )
                conn.commit()
                set_account_message(f"Successfully deleted.")
                set_account_error_message(None)
            except Exception as e:
                _trace = TracebackException.from_exception(e)
                _trace_message = '\n'.join(_trace.format())
                set_account_error_message(_trace_message)
                conn.rollback()
            finally:
                update_accounts(None)
                update_balances(None)


    if new_account_button.value and new_account_name.value:
        try:
            conn.execute(
                """
                insert into accounts (name, start_balance, on_budget) values (?,?,?)
                """,
                (
                    new_account_name.value,
                    int(new_start_balance.value*100),
                    bool(new_on_budget.value),
                )
            )
            conn.commit()
            set_account_message("Successfully Created.")
            set_account_error_message(None)
        except Exception as e:
            _trace = TracebackException.from_exception(e)
            _trace_message = '\n'.join(_trace.format())
            set_account_error_message(_trace_message)
            conn.rollback()
        finally:
            update_accounts(None)
            update_balances(None)


    _accounts
    return


@app.cell
def _(account_name_to_id, datetime, mo, timedelta):
    account_name_to_id
    transactions_from = mo.ui.date(
                label = "From: ",
                value = (datetime.now() - timedelta(days=30)).date(),
    )

    transactions_to = mo.ui.date(
        label = " To: ",
        value = (datetime.now().date())
    )

    transaction_account_select = mo.ui.multiselect(
        label = "Accounts: ",
        options = account_name_to_id,
        value = account_name_to_id.keys(),
    )

    transaction_filters = mo.hstack([transactions_from, transactions_to, transaction_account_select])
    return (
        transaction_account_select,
        transaction_filters,
        transactions_from,
        transactions_to,
    )


@app.cell
def _(mo):
    get_unconfirmed_transactions, update_unconfirmed_transactions = mo.state(None)
    get_confirmed_transactions, update_confirmed_transactions = mo.state(None)
    get_import_error_message, set_import_error_message = mo.state(None)
    get_import_success_message, set_import_success_message = mo.state(None)
    return (
        get_confirmed_transactions,
        get_import_error_message,
        get_import_success_message,
        get_unconfirmed_transactions,
        set_import_error_message,
        set_import_success_message,
        update_confirmed_transactions,
        update_unconfirmed_transactions,
    )


@app.cell
def _(get_import_error_message, get_import_success_message, mo):
    import_flag: mo.md | None
    if get_import_error_message():
        import_flag = mo.md(get_import_error_message()).callout("danger")
    elif get_import_success_message():
        import_flag = mo.md(get_import_success_message()).callout("success")
    else:
        import_flag = None
    return (import_flag,)


@app.cell
def _(
    conn,
    datetime,
    get_confirmed_transactions,
    mo,
    transaction_account_select,
    transactions_from,
    transactions_to,
):
    get_confirmed_transactions()
    _account_ids = transaction_account_select.value
    _start_date=transactions_from.value
    _end_date=transactions_to.value

    placeholders = ','.join('?' * len(_account_ids))
    params = []
    params.extend(_account_ids)

    date_clause = ""
    if _start_date:
        date_clause += " and t.date >= ?"
        params.append(datetime.combine(_start_date, datetime.min.time()).isoformat())
    if _end_date:
        date_clause += " and t.date <= ?"
        params.append(datetime.combine(_end_date, datetime.max.time()).isoformat())

    _transactions = conn.execute(f'''
        select 
            t.id,
            t.date,
            a.name,
            ta.name,
            t.notes,
            c.name,
            t.amount
        from transactions t
        join accounts a on t.account_id = a.id
        left join accounts ta on ta.id = t.transfer_account_id
        left join categories c on c.id = t.category_id
        where t.account_id in ({placeholders})
        {date_clause} and t.status = 1
        order by t.date desc
    ''', params).fetchall()

    _transactions = [
        {
            "Id": _id,
            "Date": _date,
            "Account": _name,
            "To/From": _transfer,
            "Notes": _notes,
            "Category": _category,
            "Amount": float(_amount)/100.0
        } for _id, _date, _name, _transfer, _notes, _category, _amount in _transactions
    ]

    transaction_table = mo.ui.table(
        _transactions,
        hidden_columns=["Id"] if _transactions else [],
        pagination=False,
    )
    return (transaction_table,)


@app.cell
def _(mo, transaction_filters, transaction_table):
    unconfirm_button = mo.ui.run_button(label="Move to Review", kind="neutral")
    delete_transactions_button = mo.ui.run_button(label="Delete", kind="danger")

    confirmed_transaction_view = mo.vstack(
        [
            transaction_filters.left(),
            transaction_table,
            mo.hstack([unconfirm_button, delete_transactions_button]).left() if transaction_table.value else "",
        ]
    )
    return (
        confirmed_transaction_view,
        delete_transactions_button,
        unconfirm_button,
    )


@app.cell
def _(
    account_name_to_id,
    category_name_to_id,
    conn,
    date,
    get_unconfirmed_transactions,
    mo,
):
    get_unconfirmed_transactions()

    num_transactions_need_review = conn.execute(
        """
        select count(t.id) from transactions t where t.status = 0
        """
    ).fetchone()[0]
    _transactions = conn.execute("""
        select
            t.id,
            t.date,
            a.name,
            ta.name,
            t.notes,
            c.name,
            t.amount
        from transactions t
        left join accounts ta on t.transfer_account_id = ta.name
        left join categories c on c.id = t.category_id
        join accounts a on t.account_id = a.id
        where t.status = 0
        order by t.date desc
    """).fetchall()

    unconfirmed_transaction_ids = [_id for _id, *_ in _transactions]

    def _update_transfer_account(v, _id):
        conn.execute(
            "update transactions set transfer_account_id = ? where id = ?",
            (v,_id)
        )
        conn.commit()

    def _update_notes(v, _id):
        conn.execute(
            "update transactions set notes = ? where id = ?",
            (v, _id)
        )
        conn.commit()

    def _update_category(v, _id):
        conn.execute(
            "update transactions set category_id = ? where id = ?",
            (v, _id)
        )
        conn.commit()


    unconfirmed_transaction_header = mo.hstack(
        [
            mo.md("**Date**"),
            mo.md("**Account**"),
            mo.md("**To/From**"),
            mo.md("**Notes**"),
            mo.md("**Category**"),
            mo.md("**Amount**"),
        ],
        widths="equal"
    )


    bulk_edit_account_from          = mo.ui.dropdown(options=account_name_to_id)
    bulk_edit_notes                 = mo.ui.text()
    bulk_edit_category              = mo.ui.dropdown(options=category_name_to_id, searchable=True)

    bulk_edit_fields = mo.hstack(
        [
            mo.ui.date(disabled=True),
            mo.ui.dropdown(options=account_name_to_id, disabled=True),
            bulk_edit_account_from,
            bulk_edit_notes,
            bulk_edit_category,
            mo.ui.number(disabled=True),
        ],
        widths="equal"
    )

    unconfirmed_transaction_fields = [
        mo.hstack(
            [
            mo.ui.date(
                date.fromisoformat(_date), 
                disabled=True
            ),
            mo.ui.text(disabled=True, value=_account_name),
            mo.ui.dropdown(
                value=_transfer,
                options=account_name_to_id,
                on_change=lambda v, __id=_id: _update_transfer_account(v, __id)
            ),
            mo.ui.text(
                value=_notes,
                on_change=lambda v, __id=_id: _update_notes(v, __id)
            ),
            mo.ui.dropdown(
                value=_category,
                options=category_name_to_id,
                searchable=True,
                on_change=lambda v, __id=_id: _update_category(v, __id)
            ),
            mo.ui.number(
                disabled=True, 
                value=float(_amount/100.0),
            ),
            ],
            widths="equal",
        ) for _id, _date, _account_name, _transfer, _notes, _category, _amount in _transactions
    ]
    return (
        bulk_edit_account_from,
        bulk_edit_category,
        bulk_edit_fields,
        bulk_edit_notes,
        num_transactions_need_review,
        unconfirmed_transaction_fields,
        unconfirmed_transaction_header,
        unconfirmed_transaction_ids,
    )


@app.cell
def _(
    bulk_edit_fields,
    mo,
    unconfirmed_transaction_fields,
    unconfirmed_transaction_header,
):
    confirm_all_transactions_button = mo.ui.run_button(kind="success", label="Confirm All")
    CHUNK_SIZE = 20
    unconfirmed_transaction_view = mo.vstack(
        [

            unconfirmed_transaction_header, # tbd make sticky?
            bulk_edit_fields,
            confirm_all_transactions_button.left(),
            mo.md("---"),
            mo.accordion(
                {
                    f"**Transactions[{i}:{i+len(unconfirmed_transaction_fields[i:i + CHUNK_SIZE])}]**" :
                    mo.vstack(unconfirmed_transaction_fields[i:i + CHUNK_SIZE])
                    for i in range(0, len(unconfirmed_transaction_fields), CHUNK_SIZE)
                }
            ),
        ],
    )
    return confirm_all_transactions_button, unconfirmed_transaction_view


@app.cell
def _(account_name_to_id, get_institutions, mo):
    # import transactions
    statement_files = mo.ui.file(
        filetypes=(".csv",),
        multiple=True,
        label="Statements",
    )

    supported_statements = get_institutions()
    statement_type = mo.ui.dropdown(
        options=supported_statements,
        label="Institution: "
    )
    import_account_select = mo.ui.dropdown(
        options=account_name_to_id,
        label="Account: "
    )

    transaction_import = mo.hstack([
        statement_type, import_account_select, statement_files  
    ])
    return (
        import_account_select,
        statement_files,
        statement_type,
        transaction_import,
    )


@app.cell
def _(
    TracebackException,
    conn,
    get_parser,
    import_account_select,
    json,
    set_import_error_message,
    set_import_success_message,
    sha256,
    sqlite3,
    statement_files,
    statement_type,
    update_balances,
    update_confirmed_transactions,
):
    raw_transactions = []
    _hashes = set() # assume duplicate transaction statements can have valid transactions. If a hash is the same increment count.
    if import_account_select.value and statement_type.value and statement_files.value:
        _parse = get_parser(
            statement_type.value
        )

        for file in statement_files.value:
            raw_transactions.extend(_parse(file.contents.decode()))

        try:
            skip_count = 0
            for _amount, _notes, _date in raw_transactions:

                _count = 1
                _hash = sha256(f"{_amount}{_notes}{_date}{_count}".encode())
                while _hash in _hashes:
                    _count += 1
                    _hash = sha256(f"{_amount}{_notes}{_date}{_count}".encode())
                _hashes.add(_hash)
                try:
                    conn.execute(
                        "insert into transactions (account_id, notes, amount, date, count, status, original_json) values (?, ?, ?, ?, ?, 1, ?)",
                        (
                            int(import_account_select.value),
                            _notes,
                            int(round(_amount*100)),
                            _date.isoformat(),
                            _count,
                            json.dumps({
                                "amount":_amount,
                                "notes":_notes,
                                "date":_date.isoformat()
                            })
                        )
                    )
                except sqlite3.IntegrityError:
                    skip_count += 1
            conn.commit()
            set_import_success_message(f"Successfully imported {len(raw_transactions)-skip_count} transactions. Skipped {skip_count}.")
            set_import_error_message(None)
            update_confirmed_transactions(None)
            update_balances(None)

        except Exception as e:
            _trace = TracebackException.from_exception(e)
            _trace_message = ''.join(_trace.format())
            set_import_error_message(_trace_message)
            set_import_success_message(None)
            conn.rollback()
    return


@app.cell
def _(
    bulk_edit_account_from,
    bulk_edit_category,
    bulk_edit_notes,
    confirm_all_transactions_button,
    confirmed_transaction_view,
    conn,
    delete_transactions_button,
    import_flag: "mo.md | None",
    mo,
    num_transactions_need_review,
    transaction_import,
    transaction_table,
    unconfirm_button,
    unconfirmed_transaction_ids,
    unconfirmed_transaction_view,
    update_balances,
    update_budget_items,
    update_confirmed_transactions,
    update_unconfirmed_transactions,
):
    _transactions = mo.vstack(
        [
            mo.md("# Transactions"),
            mo.md("---"),
            mo.md(
                f"{num_transactions_need_review} transactions awaiting review."
            ).callout("warn") if num_transactions_need_review else "",
            mo.accordion({
                "Import Transactions": 
                mo.vstack([transaction_import.left(), import_flag if import_flag else ""])
            }),
            mo.ui.tabs(
                {
                    "Needs Review": unconfirmed_transaction_view,
                    "Confirmed": confirmed_transaction_view,
                },
                on_change=lambda v: update_confirmed_transactions(None)
            ) if num_transactions_need_review else confirmed_transaction_view,
            sum(t["Amount"] for t in transaction_table.value)
        ]
    )

    if confirm_all_transactions_button.value:
        _account_from = bulk_edit_account_from.value
        _notes = bulk_edit_notes.value
        _category = bulk_edit_category.value
        try:
            for _id in unconfirmed_transaction_ids:
                if _account_from:
                    conn.execute(
                        "update transactions set transfer_account_id = ? where id = ?",
                        (_account_from, _id,)
                    )
                if _notes:
                     conn.execute(
                        "update transactions set notes = ? where id = ?",
                        (_notes, _id,)
                    )               
                if _category:
                    conn.execute(
                        "update transactions set category_id = ? where id = ?",
                        (_category, _id,)
                    )

                conn.execute("update transactions set status = 1 where id = ?", (_id,))
            conn.commit()
        except Exception as  e:
            conn.rollback()
            print(e)
        finally:
            update_confirmed_transactions(None)
            update_budget_items(None)
            update_balances(None)

    if unconfirm_button.value:
        try:
            for t in transaction_table.value:
                conn.execute(
                    "update transactions set status = 0 where id = ?",
                    (t["Id"],)
                )
            conn.commit()
        except:
            conn.rollback()
        finally:
            update_confirmed_transactions(None)
            update_unconfirmed_transactions(None)
            update_budget_items(None) # only show for confirmed
            update_balances(None)

    if delete_transactions_button.value:
        try:
            for t in transaction_table.value:
                conn.execute(
                    "delete from transactions where id = ?",
                    (t["Id"],)
                )
            conn.commit()
        except:
            conn.rollback()
        finally:
            update_confirmed_transactions(None)
            update_budget_items(None)
            update_balances(None)


    _transactions
    return


@app.cell
def _(mo):
    get_budget_state, set_budget_state = mo.state(0)
    get_budget_error_state, set_budget_error_state = mo.state(0)
    get_budget_items, update_budget_items = mo.state(0)
    return (
        get_budget_error_state,
        get_budget_items,
        get_budget_state,
        set_budget_error_state,
        set_budget_state,
        update_budget_items,
    )


@app.cell
def _(conn, date, datetime, mo):
    budget_month = mo.ui.dropdown(
        options = {
            "January":1,
            "Feburary":2,
            "March":3,
            "April":4,
            "May":5,
            "June":6,
            "July":7,
            "August":8,
            "September":9,
            "October":10,
            "November":11,
            "December":12,
        },
        value = datetime.now().strftime("%B"),
    )
    budget_year = mo.ui.dropdown(
        options = [year for year in range(datetime.now().year-5,datetime.now().year+5)],
        value = datetime.now().year,
    )


    def _update_start_date(v: date | None):
        if v:
            conn.execute(
                "insert into settings (key, value) values ('budget_start', ?)",
                (v.isoformat(),)
            )
            conn.commit()

    budget_start = conn.execute(
        "select value from settings where key = 'budget_start'"
    ).fetchone()
    if budget_start is not None:
        budget_start = date.fromisoformat(budget_start[0])
    budget_start_date = mo.ui.date(label="Start Date: ",value=budget_start, on_change=lambda v:_update_start_date(v))
    budget_settings = mo.accordion({
                "Settings": budget_start_date.left()
    })
    return budget_month, budget_settings, budget_start_date, budget_year


@app.cell
def _(get_budget_error_state, get_budget_state, mo):
    get_budget_error_state()
    get_budget_state()
    budget_flag: mo.Html
    if get_budget_error_state():
        budget_flag = mo.md(get_budget_error_state()).callout("danger")
    elif get_budget_state():
        budget_flag = mo.md(get_budget_state()).callout("success")
    else:
        budget_flag = ""
    return


@app.cell
def _(
    budget_month,
    budget_start_date,
    budget_year,
    conn,
    date,
    get_budget_items,
    mo,
):
    get_budget_items()

    copy_previous_months_budget_button = mo.ui.run_button(
        label="Copy Previous Month's Budget"
    )


    _sql = """
           with cat as (
               select
                   c.id, c.name, c.is_income,
                   coalesce((select sum(b.budgeted_amount) from budget_items b
                             where b.category_id = c.id
                               and b.year * 12 + b.month < :year * 12 + :month), 0) as assigned_before,
                   coalesce((select sum(b.budgeted_amount) from budget_items b
                             where b.category_id = c.id
                               and b.month = :month and b.year = :year), 0) as budgeted,
                   coalesce((select sum(t.amount) from transactions t
                             where t.category_id = c.id and t.status = 1
                               and t.date >= :budget_start and t.date < :start), 0) as actual_before,
                   coalesce((select sum(t.amount) from transactions t
                             where t.category_id = c.id and t.status = 1
                               and t.date >= :start and t.date < :end), 0) as actual
               from categories c
           )
           select
               id, name, is_income,
               case when is_income then 0 else assigned_before + actual_before end as rollover,
               budgeted,
               actual,
               case when is_income then null
               else assigned_before + actual_before + budgeted + actual end as balance
           from cat
           order by is_income desc, name;
           """

    budget_items = []
    to_budget = 0
    if budget_month.value and budget_year.value:
        _month = budget_month.value
        _year = budget_year.value
        _budget_start = budget_start_date.value.isoformat()

        def month_bounds(month: int, year: int) -> tuple[str, str]:
            start = date(year, month, 1)
            end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
            return start.isoformat(), end.isoformat()

        _start, _end = month_bounds(_month, _year)
        budget_items = conn.execute(
            _sql,
            {"month": _month, "year": _year, "start": _start, "end": _end, "budget_start":_budget_start},
        ).fetchall()

        to_budget = conn.execute(
            """
            select
                coalesce((select sum(t.amount)
                          from transactions t
                          join categories c on c.id = t.category_id
                          where c.is_income = 1 and t.status = 1
                            and t.date < :end and t.date >= :budget_start), 0)
              - coalesce((select sum(b.budgeted_amount)
                          from budget_items b
                          join categories c on c.id = b.category_id
                          where c.is_income = 0
                            and b.year * 12 + b.month <= :year * 12 + :month), 0)
            """,
            {"month": _month, "year": _year, "end": _end, "budget_start": _budget_start},
        ).fetchone()[0]

    category_name_to_id = {_name: _id for _id, _name, *_ in budget_items}
    category_ids = [_id for _id, *_ in budget_items]
    return (
        budget_items,
        category_ids,
        category_name_to_id,
        copy_previous_months_budget_button,
        to_budget,
    )


@app.cell
def _(
    budget_items,
    budget_month,
    budget_settings,
    budget_year,
    conn,
    copy_previous_months_budget_button,
    mo,
    set_budget_error_state,
    set_budget_state,
    to_budget,
    update_budget_items,
):
    budget_items
    def _update_is_income(v, id_):
        try:
            conn.execute(
                """
                update categories
                set is_income = ?
                where id = ?
                """,
                (int(v), id_)
            )
            if v:
                conn.execute(
                    """
                    update budget_items
                    set budgeted_amount = 0
                    where category_id = ?
                    """,
                    (id_,)
                )
            conn.commit()
            set_budget_state(f"Successfully updated.")
            set_budget_error_state(None)
            update_budget_items(None)
        except Exception as e:
            conn.rollback()
            set_budget_error_state(repr(e))

    def _update_name(v, id_):
        try:
            conn.execute(
                """
                update categories
                set name = ?
                where id = ?
                """,
                (v, id_)
            )
            conn.commit()
            set_budget_state(f"Successfully updated.")
            set_budget_error_state(None)
            update_budget_items(None)
        except Exception as e:
            conn.rollback()
            set_budget_error_state(repr(e))

    def _update_budget(v, id_):
        try:
            if v is None:
                v = 0.0
            conn.execute(
                """
                insert into budget_items (month, year, category_id, budgeted_amount)
                values (?, ?, ?, ?)
                on conflict (month, year, category_id)
                do update set budgeted_amount = excluded.budgeted_amount
                """,
                (
                    budget_month.value,
                    budget_year.value,
                    id_,
                    round(v * 100)
                )
            )
            conn.commit()
            set_budget_state(f"Successfully updated.")
            set_budget_error_state(None)
            update_budget_items(None)
        except Exception as e:
            set_budget_error_state(repr(e))


    def _dollars(cents: int | None) -> float:
        return (cents or 0) / 100.0


    category_delete_buttons = mo.ui.array([
        mo.ui.run_button(label="Delete", kind="danger") 
        for _ in range(len(budget_items))
    ])


    _income_actual = 0
    _expense_actual = 0
    _expense_assigned = 0  # only used to derive the pool rollover
    _cum_balance = 0
    _budget_rows = []

    for i, (_id, _name, _is_income, _rollover, _budgeted, _actual, _balance) in enumerate(budget_items):
        if _is_income:
            _income_actual += _actual
            _budgeted = _actual
            _balance = None
        else:
            _expense_actual += _actual
            _expense_assigned += _budgeted

        if _balance is not None:
            _cum_balance += _balance

        _budget_rows.append(mo.hstack([
                mo.ui.checkbox(
                    value=bool(_is_income),
                    on_change=lambda v, __id=_id: _update_is_income(v, __id),
                ),
                mo.ui.text(
                    _name,
                    on_change=lambda v, __id=_id: _update_name(v, __id),
                ),
                mo.ui.number(
                    value=_dollars(_budgeted),
                    disabled=bool(_is_income),
                    on_change=lambda v, __id=_id: _update_budget(v, __id),
                ),
                mo.ui.number(disabled=True, value=_dollars(_actual)),
                (
                    mo.ui.number(disabled=True, value=_dollars(_balance))
                    if _balance is not None
                    else mo.md("")
                ),
                category_delete_buttons[i],
        ], widths="equal"))

    _net_actual = _income_actual + _expense_actual
    _pool_rollover = to_budget - _income_actual + _expense_assigned


    _to_budget_stat = mo.stat(
        # bordered=True,
        value=to_money_str(to_budget),
        label="To Budget:",
        direction="increase" if to_budget >= 0 else "decrease",
    )

    _rollover_stat = mo.stat(
        # bordered=True,
        value=to_money_str(_pool_rollover),
        label="Rollover",
        direction="increase" if _pool_rollover >= 0 else "decrease",
    )

    _net_stat = mo.stat(
        # bordered=True,
        value=to_money_str(_net_actual),
        label="Net Cash Flow",
        direction="increase" if _net_actual >= 0 else "decrease",
    )

    _stats = mo.hstack([_to_budget_stat, _rollover_stat, _net_stat])


    _budget_header = mo.hstack(
        [
            mo.md("**Income**"),
            mo.md("**Name**"),
            mo.md("**Budgeted**"),
            mo.md("**Actual**"),
            mo.md("**Balance**"),
            mo.md("")
        ], 
        widths="equal"
    )


    _budget_totals_row = mo.hstack(
        [
            mo.md(""),
            mo.md("**Total**"),
            mo.ui.number(disabled=True, value=_dollars(_income_actual - _expense_assigned)),
            mo.ui.number(disabled=True, value=_dollars(_net_actual)),
            mo.ui.number(disabled=True, value=_dollars(_cum_balance)),
            mo.md(""),
        ],
        widths="equal",
    )


    new_category_name = mo.ui.text(value="", placeholder="New Category")
    new_category_is_income = mo.ui.checkbox()
    add_category_button = mo.ui.run_button(label="Add Category")
    new_category_form = mo.hstack([new_category_is_income, new_category_name, add_category_button])


    mo.vstack(
        [
            mo.md("# Budget"),
            budget_settings,
            mo.hstack([budget_month, budget_year]).left(),
            copy_previous_months_budget_button.left(),
            mo.md("---"),
            _stats.center(),
            _budget_header,
            *_budget_rows,
            new_category_form.left(),
            # budget_flag,
            mo.md("---"),
            _budget_totals_row,
        ]
    )
    return (
        add_category_button,
        category_delete_buttons,
        new_category_is_income,
        new_category_name,
    )


@app.cell
def _(
    add_category_button,
    budget_month,
    budget_year,
    category_delete_buttons,
    category_ids,
    conn,
    copy_previous_months_budget_button,
    new_category_is_income,
    new_category_name,
    set_budget_error_state,
    set_budget_state,
    update_budget_items,
):
    if new_category_name.value and add_category_button.value:
        try:    
            conn.execute(
                """insert into categories (name, is_income) values (?,?)""",
                (new_category_name.value,new_category_is_income.value)
            )
            conn.commit()
            set_budget_state("Successfully added.")
            set_budget_error_state(None)
            update_budget_items(None)
        except Exception as e:
            set_budget_error_state(repr(e))


    for _id, _button in zip(category_ids, category_delete_buttons):
        if _button.value:
            try:
                conn.execute("delete from categories where id = ?", (_id,))
                conn.commit()
                set_budget_state(f"Successfully deleted.")
                set_budget_error_state(None)
                update_budget_items(None)
            except Exception as e:
                set_budget_error_state(repr(e))


    if copy_previous_months_budget_button.value:
        _month = budget_month.value
        _year = budget_year.value

        if _month == 1:
            _prev_month, _prev_year = 12, _year - 1
        else:
            _prev_month, _prev_year = _month - 1, _year

        try:
            conn.execute(
                """
                insert or ignore into budget_items
                    (month, year, category_id, budgeted_amount)
                select ?, ?, category_id, budgeted_amount
                from budget_items
                where month = ? and year = ?
                """,
                (_month, _year, _prev_month, _prev_year),
                )
            conn.commit()
            set_budget_state("Copied previous month's budget.")
            set_budget_error_state(None)
            update_budget_items(None)
        except Exception as e:
            set_budget_error_state(repr(e))
    return


if __name__ == "__main__":
    app.run()
