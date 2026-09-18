import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from datetime import datetime, timedelta, date
    from transaction_parsers import make_parser, get_institutions
    from importlib import reload
    reload(__import__("setup"))
    from setup import get_connection


    return (
        date,
        datetime,
        get_connection,
        get_institutions,
        make_parser,
        mo,
        timedelta,
    )


@app.cell
def _(get_connection):
    conn = get_connection()
    return (conn,)


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
            mo.hstack([mo.md("**All**"), mo.md(f"${net_worth:_.2f}")]),
            mo.md("---"),
            *[mo.hstack([mo.md(f"**{_name}**"), mo.md(f"${_balance:_.2f}")]) for _name, _balance in account_name_to_balance.items()]
        ]).center(),
    )
    return


@app.cell
def _(mo):
    get_account_error_message, set_account_error_message = mo.state(None)
    get_account_message, set_account_message = mo.state(None)
    get_accounts, fetch_accounts = mo.state(None)
    get_balances, update_balaces = mo.state(None)
    return (
        fetch_accounts,
        get_account_error_message,
        get_account_message,
        get_accounts,
        get_balances,
        set_account_error_message,
        set_account_message,
    )


@app.cell
def _(
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
            set_account_error_message(repr(e))
            conn.rollback()
        finally:
            update_balances()


    def _update_start_budget(v, id_):
        try:
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
            set_account_error_message(repr(e))
            conn.rollback()
        finally:
            update_balances()

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
            set_account_error_message(repr(e))
            conn.rollback()
        finally:
            update_balances()


    accounts_header = mo.hstack(
        [
            mo.md("Name"),
            mo.md("Start Budget"),
            mo.md("On Budget"),
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
    new_start_balance = mo.ui.number(start=0.0, value=0.0)
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
        a.start_balance / 100.0 + coalesce(sum(t.amount), 0) / 100.0 as current_balance
        from accounts a
        left join transactions t on a.id = t.account_id
        group by a.id, a.name, a.start_balance, a.on_budget
        order by a.name
    """).fetchall() or []

    account_name_to_balance = {_name: _balance for _name, _balance in _balances}
    net_worth = sum([_balance for _, _balance in _balances])
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
    account_delete_buttons,
    account_fields,
    account_flag: "mo.Html",
    account_ids,
    accounts_header,
    add_new_account_form,
    conn,
    fetch_account_state,
    fetch_accounts,
    mo,
    new_account_button,
    new_account_name,
    new_on_budget,
    new_start_balance,
    set_account_error_message,
    set_account_message,
):
    _accounts = mo.vstack([
        mo.md("# Accounts"),
        mo.md("---"),
        accounts_header,
        *account_fields,
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
                    (_id)
                )
                conn.commit()
                set_account_message(f"Successfully deleted.")
                set_account_error_message(None)
            except Exception as e:
                set_account_error_message(repr(e))
                conn.rollback()
            finally:
                fetch_account_state(None)


    if new_account_button.value and new_account_name.value:
        try:
            conn.execute(
                """
                insert into accounts (name, start_balance, on_budget) values (?,?,?)
                """,
                (
                    new_account_name.value,
                    int(new_start_balance.value*100),
                    bool(new_on_budget.value)
                )
            )
            conn.commit()
            set_account_message("Successfully Created.")
            set_account_error_message(None)
        except Exception as e:
            set_account_error_message(repr(e))
            conn.rollback()
        finally:
            fetch_accounts(None)
 

    _accounts
    return


@app.cell
def _(account_name_to_id, datetime, mo, timedelta):
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
    get_unconfirmed_transactions, fetch_unconfirmed_transactions = mo.state(None)
    get_confirmed_transactions, fetch_confirmed_transactions = mo.state(None)
    get_import_error_message, set_import_error_message = mo.state(None)
    get_import_success_message, set_import_success_message = mo.state(None)
    return (
        fetch_confirmed_transactions,
        fetch_unconfirmed_transactions,
        get_confirmed_transactions,
        get_import_error_message,
        get_import_success_message,
        get_unconfirmed_transactions,
        set_import_error_message,
        set_import_success_message,
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
            a_transfer.name,
            t.notes,
            c.name,
            t.amount
        from transactions t
        join accounts a on t.account_id = a.id
        left join accounts a_transfer on a_transfer.id = t.transfer_from_id
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
            "From": _transfer,
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
            t.transfer_from_id,
            t.notes,
            t.category_id,
            t.amount
        from transactions t
        join accounts a on t.account_id = a.id
        where t.status = 0
        order by t.date desc
    """).fetchall()

    unconfirmed_transaction_ids = [_id for _id, *_ in _transactions]

    def _update_transfer_from(v, _id):
        conn.execute(
            "update transactions set transfer_from_id = ? where id = ?",
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
            mo.md("Date"),
            mo.md("Account"),
            mo.md("From"),
            mo.md("Notes"),
            mo.md("Category"),
            mo.md("Amount"),
        ],
        widths="equal"
    )

    confirm_all_transactions_button = mo.ui.run_button(kind="success", label="Confirm All")
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
                options=account_name_to_id,
                on_change=lambda v, __id=_id: _update_transfer_from(v, __id)
            ),
            mo.ui.text(
                value=_notes,
                on_change=lambda v, __id=_id: _update_notes(v, __id)
            ),
            mo.ui.dropdown(
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
        ) for _id, _date, _account_name, _, _notes, _, _amount in _transactions
    ]

    CHUNK_SIZE = 20
    unconfirmed_transaction_view = mo.vstack(
        [
        
            unconfirmed_transaction_header, # tbd make sticky?
            bulk_edit_fields,
            confirm_all_transactions_button.left(),
            mo.md("---"),
            mo.accordion(
                {
                    f"Transactions {i} to {i+CHUNK_SIZE}" : 
                    mo.vstack(unconfirmed_transaction_fields[i:i + CHUNK_SIZE])
                    for i in range(0, len(unconfirmed_transaction_fields), CHUNK_SIZE)
                }
            ),
        ],
    )
    return (
        bulk_edit_account_from,
        bulk_edit_category,
        bulk_edit_notes,
        confirm_all_transactions_button,
        num_transactions_need_review,
        unconfirmed_transaction_ids,
        unconfirmed_transaction_view,
    )


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
    conn,
    fetch_unconfirmed_transactions,
    import_account_select,
    make_parser,
    set_import_error_message,
    set_import_success_message,
    statement_files,
    statement_type,
):
    raw_transactions = []
    if import_account_select.value and statement_type.value and statement_files.value:
        parser = make_parser(
            statement_type.value
        )

        for file in statement_files.value:
            raw_transactions.extend(parser.parse(file.contents.decode()))

        try:
            for _amount, _notes, _date in raw_transactions:
                conn.execute(
                    "insert into transactions (account_id, notes, amount, date, status) values (?, ?, ?, ?, 1)",
                    (
                        int(import_account_select.value),
                        _notes, 
                        int(_amount*100), 
                        _date.isoformat()
                    )
                )
            conn.commit()
            set_import_success_message(f"Successfully imported {len(raw_transactions)} transactions.")
            set_import_error_message(None)
            fetch_unconfirmed_transactions(None)
        except Exception as e:
            conn.rollback()
            set_import_success_message(None)
            set_import_error_message(repr(e))
    

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
    fetch_confirmed_transactions,
    fetch_unconfirmed_transactions,
    import_flag: "mo.md | None",
    mo,
    num_transactions_need_review,
    transaction_import,
    transaction_table,
    unconfirm_button,
    unconfirmed_transaction_ids,
    unconfirmed_transaction_view,
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
                on_change=lambda v: fetch_confirmed_transactions(None) if v=="Confirmed" else None
            ) if num_transactions_need_review else confirmed_transaction_view,
    
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
                        "update transactions set account_from_id = ? where id = ?",
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
            
        except:
            conn.rollback()
        finally:
            fetch_confirmed_transactions(None)


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
            fetch_confirmed_transactions(None)
            fetch_unconfirmed_transactions(None)

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
            fetch_confirmed_transactions(None)


    _transactions
    return


@app.cell
def _(mo):
    get_budget_state, set_budget_state = mo.state(0)
    get_budget_error_state, set_budget_error_state = mo.state(0)
    get_budget_items, fetch_budget_items = mo.state(0)
    return (
        fetch_budget_items,
        get_budget_error_state,
        get_budget_items,
        get_budget_state,
        set_budget_error_state,
        set_budget_state,
    )


@app.cell
def _(datetime, mo):
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
    return budget_month, budget_year


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
    budget_month,
    budget_year,
    conn,
    get_budget_items,
    mo,
    set_budget_error_state,
    set_budget_state,
):
    get_budget_items()
    _budget_items = []
    if budget_month.value and budget_year.value:
        _month = budget_month.value
        _year = budget_year.value
        _budget_items = conn.execute(
            """ 
            select 
                c.id,
                c.name,
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
            (_month, _year, f'{_month:02d}', f'{_year:04d}')).fetchall()
    category_name_to_id = {
        _name: _id for _id, _name, _, _ in _budget_items
    }


    def _clean(a: int | None, b: int | None = None) -> float:
        """Convert cents to dollars. Optionally subtract b from a."""
        if a is None:
            return 0.0
        if b is None:
            return a / 100.0
        return (a - b) / 100.0


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
        except Exception as e:
            conn.rollback()
            set_budget_error_state(repr(e))


    def _update_budget(v, id_):
        try:
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
                    int(v * 100)
                )
            )
            conn.commit()
            set_budget_state(f"Successfully updated.")
            set_budget_error_state(None)
        except Exception as e:
            conn.rollback()
            set_budget_error_state(repr(e))


    category_ids = [
        _id for _id, *_ in _budget_items
    ]

    category_delete_buttons = mo.ui.array([
        mo.ui.run_button(label="Delete", kind="danger") 
        for _ in range(len(_budget_items))
    ])

    budget_table_data = [
            mo.hstack([
            mo.ui.text(
                _name,
                on_change=lambda v, __id=_id: _update_name(v, __id)
            ),
            mo.ui.number(
                value=_clean(_budgeted),
                on_change=lambda v, __id=_id: _update_budget(v, __id)
            ),
            mo.ui.number(disabled=True, value=_clean(_spent)),
            mo.ui.number(disabled=True, value=_clean(_budgeted, _spent)),
            category_delete_buttons[i],
        ], widths="equal") for i, (_id, _name, _budgeted, _spent) in enumerate(_budget_items)
    ]

    budget_header = mo.hstack(
        [
            mo.md("**Name**"),
            mo.md("**Budgeted**"),
            mo.md("**Spent**"),
            mo.md("**Balance**"),
            mo.md("")
        ], 
        widths="equal"
    )

    new_category_name = mo.ui.text(value="", placeholder="New Category")
    add_category_button = mo.ui.run_button(label="Add Category")
    new_category_form = mo.hstack([new_category_name, add_category_button])
    return (
        add_category_button,
        budget_header,
        budget_table_data,
        category_delete_buttons,
        category_ids,
        category_name_to_id,
        new_category_form,
        new_category_name,
    )


@app.cell
def _(
    add_category_button,
    budget_flag: "mo.Html",
    budget_header,
    budget_month,
    budget_table_data,
    budget_year,
    category_delete_buttons,
    category_ids,
    conn,
    fetch_budget_items,
    mo,
    new_category_form,
    new_category_name,
    set_budget_error_state,
    set_budget_state,
):
    _display = mo.vstack(
        [
            mo.md("# Budget"),
            mo.hstack([budget_month, budget_year]).left(),
            mo.md("---"),
            budget_header,
            *budget_table_data,
            new_category_form.left(),
            budget_flag,
            mo.accordion(
                {
                    "Suggested Categories":
                    mo.md(
                        """
                        - Income
                        - Insurance
                        - Phone
                        - Dining Out
                        - Travel
                        - Gas
                        - Groceries
                        - Gifts
                        - Fun
                        - Groceries
                        - Savings
                        - To Budget
                        - Student Loans
                        - Investments
                        """
                    )
                }
            ),
            mo.md("# Report"),
            mo.md("---"),
        ]
    )

    if new_category_name.value and add_category_button.value:
        try:    
            conn.execute(
                """insert into categories (name) values (?)""",
                (new_category_name.value,)
            )
            conn.commit()
            set_budget_state("Successfully added.")
            set_budget_error_state(None)
        except Exception as e:
            conn.rollback()
            set_budget_error_state(repr(e))
        finally:
            fetch_budget_items(0)


    for _id, _button in zip(category_ids, category_delete_buttons):
        if _button.value:
            try:
                conn.execute("delete from categories where id = ?", (_id,))
                conn.commit()
                set_budget_state(f"Successfully deleted.")
                set_budget_error_state(None)
            except Exception as e:
                conn.rollback()
                set_budget_error_state(repr(e))
            finally:
                fetch_budget_items(0)

    _display
    return


if __name__ == "__main__":
    app.run()
