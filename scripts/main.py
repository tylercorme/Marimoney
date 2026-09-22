# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "plotly==5.24.1",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from datetime import datetime, timedelta, date
    from traceback import TracebackException

    from importlib import reload
    import transactions
    import budget

    return (
        TracebackException,
        budget,
        date,
        datetime,
        mo,
        reload,
        timedelta,
        transactions,
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
          + coalesce((select sum(t.amount)
                      from transactions t
                      where t.account_id = a.id), 0)
          - coalesce((select sum(t.amount)
                      from transactions t
                      where t.transfer_account_id = a.id
                        and not exists (
                            select 1
                            from transactions m
                            where m.account_id = a.id
                              and m.amount = -t.amount
                              and abs(julianday(m.date) - julianday(t.date)) <= 7
                        )), 0)
          as current_balance
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
def _(account_name_to_id, category_name_to_id, datetime, mo, timedelta):
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

    transaction_category_select = mo.ui.multiselect(
        label = "Categories: ",
        options = category_name_to_id,
        value = list(category_name_to_id.keys()),
    )

    transaction_filters = mo.hstack([transactions_from, transactions_to, transaction_account_select, transaction_category_select])
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
            t.amount,
            t.created_at
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
            "Imported On": _created_at,
            "Id": _id,
            "Date": _date,
            "Account": _name,
            "To/From": _transfer,
            "Notes": _notes,
            "Category": _category,
            "Amount": float(_amount)/100.0
        } for _id, _date, _name, _transfer, _notes, _category, _amount, _created_at in _transactions
    ]

    transaction_table = mo.ui.table(
        _transactions,
        hidden_columns=["Id", "Imported On"] if _transactions else [],
        pagination=True,
        page_size=25,
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
        widths = [1, 1, 1, 2, 1, 1],
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
        widths=[1,1,1,2,1,1],
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
            widths=[1,1,1,2,1,1],
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
def _(account_name_to_id, mo, transactions):
    # import transactions
    statement_files = mo.ui.file(
        filetypes=(".csv",),
        multiple=True,
        label="Statements",
    )

    supported_statements = transactions.get_institutions()
    statement_type = mo.ui.dropdown(
        options=supported_statements,
        label="Institution: "
    )
    import_account_select = mo.ui.dropdown(
        options=account_name_to_id,
        label="Account: "
    )

    import_button = mo.ui.run_button(
        label = "Import",
    )

    transaction_import = mo.hstack([
        statement_type, import_account_select, statement_files, import_button,  
    ])
    return (
        import_account_select,
        import_button,
        statement_files,
        statement_type,
        transaction_import,
    )


@app.cell
def _(
    TracebackException,
    conn,
    import_account_select,
    import_button,
    mo,
    set_import_error_message,
    set_import_success_message,
    statement_files,
    statement_type,
    transactions,
    update_balances,
    update_confirmed_transactions,
):
    mo.stop(not import_button.value)
    mo.stop(
        not (import_account_select.value and statement_type.value and statement_files.value),
        mo.md("Select an institution, account, and at least one file."),
    )

    if import_button.value and import_account_select.value and statement_type.value and statement_files.value:
        _parse = transactions.get_parser(statement_type.value)

        try:
            _results: list[transactions.ImportResult] = []
            for file in statement_files.value:
                _results.append(
                    transactions.import_(
                        conn, 
                        import_account_select.value, 
                        _parse(file.contents.decode())
                    )
                )

            set_import_success_message(
                f"""
                Successfully imported {sum(_inserted for _inserted, _ in _results)} transactions.
                Skipped {sum(_skipped for _, _skipped in _results)}.
                """
            )
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
            f'Sum: {sum(t["Amount"] for t in transaction_table.value)}' if transaction_table.value else ""
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

    budget_period_select = mo.hstack([budget_month, budget_year])

    def _update_start_date(v: date | None):
        if v:
            conn.execute(
                """
                insert into settings (key, value) values ('budget_start', ?)
                on conflict (key)
                do update set value = excluded.value
                """,
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
    return (
        budget_month,
        budget_period_select,
        budget_settings,
        budget_start_date,
        budget_year,
    )


@app.cell
def _(
    budget,
    budget_month,
    budget_start_date,
    budget_year,
    conn,
    get_budget_items,
    mo,
):
    get_budget_items()

    copy_previous_months_budget_button = mo.ui.run_button(
        label="Copy Previous Month's Budget"
    )

    monthly_budget = budget.load_budget(
        conn, 
        budget_year.value, 
        budget_month.value, 
        budget_start_date.value
    )

    category_name_to_id = {e.name: e.id for e in monthly_budget.envelopes}
    category_ids = [e.id for e in monthly_budget.envelopes]
    return (
        category_ids,
        category_name_to_id,
        copy_previous_months_budget_button,
        monthly_budget,
    )


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
    return (budget_flag,)


@app.cell
def _(
    budget,
    budget_flag: "mo.Html",
    budget_month,
    budget_period_select,
    budget_settings,
    budget_year,
    conn,
    copy_previous_months_budget_button,
    mo,
    monthly_budget,
    set_budget_error_state,
    set_budget_state,
    update_budget_items,
):
    monthly_budget
    def _save(action):
        try:
            action()
            set_budget_state("Successfully updated.")
            set_budget_error_state(None)
            update_budget_items(None)
        except Exception as e:
            set_budget_error_state(repr(e))


    def _dollars(cents: int | None) -> float:
        return (cents or 0) / 100.0

    category_delete_buttons = mo.ui.array([
        mo.ui.run_button(label="Delete", kind="danger")
        for _ in monthly_budget.envelopes
    ])
    category_income_checks = mo.ui.array([
        mo.ui.checkbox(
            value=e.is_income,
            on_change=lambda v, id_=e.id: _save(lambda: budget.set_is_income(conn,id_,v)),
        )
        for e in monthly_budget.envelopes
    ])

    category_names = mo.ui.array([
        mo.ui.text(
            e.name,
            on_change=lambda v, id_=e.id: _save(lambda: budget.rename_category(conn,id_,v)),
        )
        for e in monthly_budget.envelopes
    ])

    category_budgets = mo.ui.array([
        mo.ui.number(
            value=_dollars(e.display_budgeted),
            disabled=e.is_income,
            on_change=lambda v, id_=e.id: 
            _save(
                lambda: 
                budget.set_budgeted(
                    conn,
                    budget_year.value,
                    budget_month.value,
                    id_, 
                    budget.dollars_to_cents(v)
                )
            ),
        )
        for e in monthly_budget.envelopes
    ])

    _rows = [
        mo.hstack([
            category_income_checks[i],
            category_names[i],
            category_budgets[i],
            mo.ui.number(disabled=True, value=_dollars(e.actual)),
            mo.ui.number(disabled=True, value=_dollars(e.balance))
            if e.balance is not None
            else mo.md(""),
            category_delete_buttons[i],
        ], widths="equal")
        for i, e in enumerate(monthly_budget.envelopes)
    ]
    def _stat(label, cents):
        return mo.stat(
            value=to_money_str(cents),
            label=label,
            direction="increase" if cents >= 0 else "decrease",
        )

    _stats = mo.hstack([
        mo.stat(
            label="To Budget:", 
            value=f"{to_money_str(monthly_budget.pool_rollover)} + {to_money_str(monthly_budget.income_actual - monthly_budget.expense_assigned)} = {to_money_str(monthly_budget.to_budget)}"
        ),
        _stat("Net Cash Flow", monthly_budget.net_actual),
    ])

    _header = mo.hstack(
        [
            mo.md(f"Income"), 
            mo.md("Name"),
            mo.md("Budgeted"),
            mo.md("Actual"),
            mo.md("Balance"),
            mo.md("")
        ],
        widths="equal",
    )

    _totals = mo.hstack([
        mo.md(""),
        mo.md("**Total**"),
        mo.ui.number(disabled=True, value=_dollars(monthly_budget.income_actual - monthly_budget.expense_assigned)),
        mo.ui.number(disabled=True, value=_dollars(monthly_budget.net_actual)),
        mo.ui.number(disabled=True, value=_dollars(monthly_budget.total_balance)),
        mo.md(""),
    ], widths="equal")


    new_category_name = mo.ui.text(value="", placeholder="New Category")
    new_category_is_income = mo.ui.checkbox()
    add_category_button = mo.ui.run_button(label="Add Category")
    new_category_form = mo.hstack([new_category_is_income, new_category_name, add_category_button])

    mo.vstack([
        mo.md("# Budget"),
        budget_settings,
        budget_period_select.left(),
        copy_previous_months_budget_button,
        mo.md("---"),
        _stats.center(),
        _header,
        *_rows,
        _totals,
        new_category_form.left(),
        budget_flag,
    ])
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


@app.cell
def _(budget_month, budget_year, mo, monthly_budget):
    import plotly.graph_objects as go
    from plotly.colors import qualitative
    _expense = [e for e in monthly_budget.envelopes if not e.is_income]
    _colors = {e.name: qualitative.Plotly[i % 10] for i, e in enumerate(_expense)}
    _TO_BUDGET = "To Budget"
    _colors["To Budget"] = "#9AA0A6"


    def _pie(items, center_top, center_bottom):
        if not items:
            return mo.md("Nothing to show for this month.").callout("warn")
        fig = go.Figure(go.Pie(
            labels=[n for n, _ in items],
            values=[c / 100 for _, c in items],
            hole=0.62,
            sort=False,
            direction="clockwise",
            textinfo="percent",
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
        ))
        fig.update_layout(
            height=400,
            margin=dict(t=50, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",   # keep only if you want it to blend with the page
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(x=1.02, y=0.5),
            annotations=[dict(
                text=f"<b style='font-size:22px'>{center_top}</b><br>{center_bottom}",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, align="center",
            )],
        )
        return fig


    # Budgeted pie: this month's assignments + the unassigned remainder of the pool
    _assigned = monthly_budget.expense_assigned
    _to_budget = monthly_budget.to_budget
    _budgeted_items = [(e.name, e.budgeted) for e in _expense if e.budgeted > 0]
    if _to_budget > 0:
        _budgeted_items.append((_TO_BUDGET, _to_budget))
    _pool = _assigned + _to_budget  # money available to assign this month

    # Spent pie: net spending per envelope
    _spent_items = [(e.name, -e.actual) for e in _expense if e.actual < 0]
    _total_spent = -monthly_budget.expense_actual

    _period = f"{budget_month.selected_key} {budget_year.value}"

    _stats = mo.hstack([
        mo.stat(
            value=to_money_str(_total_spent),
            label="Total Monthly Expenses",
        ),
        mo.stat(
            value=to_money_str(_assigned), 
            label="Total Budgeted", 
        ),
        mo.stat(
            value=to_money_str(_to_budget),
            label="To Budget",
            direction="increase" if _to_budget >= 0 else "decrease",
        ),
    ])

    _warning = (
        mo.md(f"Over-assigned by **{to_money_str(-_to_budget)}**").callout("warn")
        if _to_budget < 0 else mo.md("")
    )

    reports = mo.vstack([
        mo.md(f"# Report for {_period}"),
        mo.md("---"),
        _stats.left(),
        _warning,
        mo.md("## Budgeted"),
        _pie(
            _budgeted_items,
            to_money_str(_pool),
            "available"
        ),
        mo.md("## Expenses"),
        _pie(
            _spent_items,
            to_money_str(_total_spent), 
            "spent"
        ),
    ])
    reports
    return


if __name__ == "__main__":
    app.run()
