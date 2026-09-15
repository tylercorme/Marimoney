import marimo

__generated_with = "0.24.0"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from datetime import datetime, timedelta
    from importlib import reload
    from dataclasses import dataclass

    from database import Accounts, Transactions, Categories, BudgetItems
    from transaction_parsers import make_parser, get_institutions


    return (
        Accounts,
        Categories,
        Transactions,
        datetime,
        get_institutions,
        make_parser,
        mo,
        timedelta,
    )


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
def _(balances, header, mo, net_worth):
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
            *[mo.hstack([mo.md(f"**{account["name"]}**"), mo.md(f"${account["current_balance"]:_.2f}")]) for account in balances]
        ]).center(),
    )
    return


@app.cell
def _(mo):
    get_account_state, set_account_state = mo.state(None)
    return get_account_state, set_account_state


@app.cell
def _(Accounts, get_account_state, mo):
    get_account_state()


    account_name = mo.ui.text(label="Name", placeholder="Account Name")
    start_balance = mo.ui.number(start=0.0, value=0.0, label="Start Balance")
    on_budget = mo.ui.checkbox(label="On Budget", value=True)
    new_account_button = mo.ui.button(label="Add Account", value=False, on_click=lambda _: True)


    balances = Accounts.balances()
    net_worth = sum([account["current_balance"] for account in balances])
    account_name_to_id = {account["name"]: account["id"] for account in balances}

    account_name_fields = mo.ui.array([mo.ui.text(value=account["name"]) for account in balances])
    start_balance_fields = mo.ui.array([mo.ui.number(start=0.0, value=float(account["start_balance"])/100.0) for account in balances])
    on_budget_fields = mo.ui.array([mo.ui.checkbox(value=bool(account["on_budget"])) for account in balances])
    account_update_buttons = mo.ui.array([mo.ui.button(kind="success", value=0, on_click=lambda value: value + 1, label="Update") for account in balances])
    account_delete_buttons = mo.ui.array([mo.ui.button(kind="danger", value=0, on_click=lambda value: value + 1, label="Delete") for account in balances])
    return (
        account_delete_buttons,
        account_name,
        account_name_fields,
        account_name_to_id,
        account_update_buttons,
        balances,
        net_worth,
        new_account_button,
        on_budget,
        on_budget_fields,
        start_balance,
        start_balance_fields,
    )


@app.cell
def _(
    account_delete_buttons,
    account_name,
    account_name_fields,
    account_update_buttons,
    balances,
    mo,
    new_account_button,
    on_budget,
    on_budget_fields,
    start_balance,
    start_balance_fields,
):
    mo.vstack([
        mo.md("# Accounts"),
        mo.md("---"),
        *[
            mo.hstack([
                account_name_fields[i], 
                start_balance_fields[i], 
                on_budget_fields[i],
                account_update_buttons[i],
                account_delete_buttons[i],
            ]).left() for i, _ in enumerate(balances)
        ],
        mo.hstack([account_name, start_balance, on_budget, new_account_button]).left(),           
    ])
    return


@app.cell
def _(
    Accounts,
    account_delete_buttons,
    account_name,
    account_name_fields,
    account_update_buttons,
    balances,
    new_account_button,
    on_budget,
    on_budget_fields,
    set_account_state,
    start_balance,
    start_balance_fields,
):
    if new_account_button.value and account_name.value:
        Accounts.insert(
            account_name.value,
            int(start_balance.value*100),
            bool(on_budget.value)
        )
        set_account_state(lambda _: None)

    for _account, _name, _start_balance, _on_budget, _update in zip(
        balances,
        account_name_fields.value,
        start_balance_fields.value,
        on_budget_fields.value,
        account_update_buttons.value,
    ):
        if _update:
            Accounts.update(_account["id"], _name, int(_start_balance*100), _on_budget)
            set_account_state(lambda _: None)

    for _account, _delete in zip(
        balances,
        account_delete_buttons.value,
    ):
        if _delete:
            Accounts.delete(_account["id"])
            set_account_state(lambda _: None)
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
    return transaction_account_select, transactions_from, transactions_to


@app.cell
def _(
    Transactions,
    mo,
    transaction_account_select,
    transactions_from,
    transactions_to,
):
    _transactions = [dict(t) for t in Transactions.all(*transaction_account_select.value, start_date=transactions_from.value, end_date=transactions_to.value)]
    _hidden_columns = ["id","account_id","transfer_from_id","category_id","payee_id"]
    if not _transactions:
        _hidden_columns = []

    transaction_table = mo.ui.table(
        _transactions,
        hidden_columns = _hidden_columns,
        # visible_columns=["date", "account_name", "transfer_from_name", "payee_name", "notes", "category_name", "amount", "is_cleared"],
        pagination=False,
        header_tooltip=None,
        hover_template=None
    )

    mo.vstack(
        [
            mo.md("# Transactions").left(),
            mo.md("---"),
            mo.hstack([transactions_from, transactions_to, transaction_account_select]).left(),
            transaction_table,
        ]
    )
    return


@app.cell
def _(mo):
    get_import_state, set_import_state = mo.state(0)
    return (get_import_state,)


@app.cell
def _(account_name_to_id, get_import_state, get_institutions, mo):
    get_import_state()
    statement_files = mo.ui.file(
        filetypes=(".csv",),
        multiple=True, 
        label="Statements",
        kind="area",
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

    commit_transactions = mo.ui.button(kind="success", label="Commit", value=False, on_click=lambda _: True)
    return (
        commit_transactions,
        import_account_select,
        statement_files,
        statement_type,
    )


@app.cell
def _(
    account_name_to_id,
    category_name_to_id,
    import_account_select,
    make_parser,
    mo,
    statement_files,
    statement_type,
):

    raw_transactions = []
    if import_account_select.value and statement_type.value and statement_files.value:
        parser = make_parser(
            statement_type.value
        )

        for file in statement_files.value:
            print(file.contents.decode())
            raw_transactions.extend(parser.parse(file.contents.decode()))


    raw_transaction_date_fields = mo.ui.array([
        mo.ui.date(value=transaction["date_"], disabled=True) for transaction in raw_transactions
    ])

    raw_transaction_transfer_account_fields = mo.ui.array([
        mo.ui.dropdown(options=account_name_to_id) for _ in range(len(raw_transactions))
    ])

    raw_transaction_category_fields = mo.ui.array([
        mo.ui.dropdown(options=category_name_to_id) for _ in raw_transactions
    ])

    raw_transaction_amount_fields = mo.ui.array([
        mo.ui.number(disabled=True, value=transaction["amount"]) for transaction in raw_transactions
    ])

    raw_transaction_note_fields = mo.ui.array([
        mo.ui.text(value=transaction["notes"]) for transaction in raw_transactions
    ])
    return (
        raw_transaction_amount_fields,
        raw_transaction_category_fields,
        raw_transaction_date_fields,
        raw_transaction_note_fields,
        raw_transaction_transfer_account_fields,
        raw_transactions,
    )


@app.cell
def _(
    Transactions,
    commit_transactions,
    import_account_select,
    raw_transaction_category_fields,
    raw_transaction_note_fields,
    raw_transaction_transfer_account_fields,
    raw_transactions,
    set_account_state,
):
    if commit_transactions.value:
        for ( _transfer_account, 
             _category,  
             _notes, raw_transaction) in zip(raw_transaction_transfer_account_fields,
                            raw_transaction_category_fields,
                            raw_transaction_note_fields, 
                            raw_transactions
        ): 
            _account_id = import_account_select.value
            Transactions.insert(
                _account_id,
                _transfer_account.value,
                payee_id=None,
                category_id=_category.value,
                amount=raw_transaction["amount"],
                notes=_notes.value,
                is_cleared=False,
                date_=raw_transaction["date_"]
            )

            set_account_state(lambda _: None)
    return


@app.cell
def _(
    commit_transactions,
    import_account_select,
    mo,
    raw_transaction_amount_fields,
    raw_transaction_category_fields,
    raw_transaction_date_fields,
    raw_transaction_note_fields,
    raw_transaction_transfer_account_fields,
    raw_transactions,
    statement_files,
    statement_type,
):
    mo.vstack(
        [
            mo.md("# Transaction Importer"),
            mo.md("---"),
            mo.hstack([statement_type, import_account_select]).left(),
            statement_files,
            *[
                mo.hstack([
                    raw_transaction_date_fields[i], 
                    raw_transaction_transfer_account_fields[i],
                    raw_transaction_note_fields[i],
                    raw_transaction_category_fields[i],
                    raw_transaction_amount_fields[i]
                ]) for i in range(len(raw_transactions))
            ],
            commit_transactions if raw_transactions else "",
        ]
    )
    return


@app.cell
def _(mo):
    get_category_state, set_category_state = mo.state(0)
    return get_category_state, set_category_state


@app.cell
def _(Categories, get_category_state, mo):
    get_category_state()
    new_category_name = mo.ui.text(value="", placeholder="New Category")
    add_category_button = mo.ui.button(label="Add Category", value=0, on_click=lambda value: value + 1)
    categories = Categories.all()
    category_name_to_id = {category["name"]:category["id"] for category in categories}
    return (
        add_category_button,
        categories,
        category_name_to_id,
        new_category_name,
    )


@app.cell
def _(categories, mo):
    category_name_fields = mo.ui.array([mo.ui.text(category["name"]) for category in categories])
    remove_category_buttons = mo.ui.array([mo.ui.button(label="Delete", kind="danger", value=0, on_click=lambda value: value + 1) for category in categories])
    update_category_buttons = mo.ui.array([mo.ui.button(label="Update", kind="success", value=0, on_click=lambda value: value + 1) for category in categories])
    return (
        category_name_fields,
        remove_category_buttons,
        update_category_buttons,
    )


@app.cell
def _(
    add_category_button,
    categories,
    category_name_fields,
    mo,
    new_category_name,
    remove_category_buttons,
    update_category_buttons,
):
    # category_names
    mo.vstack([
        mo.md("# Categories"),
        mo.md("---"),
        *[mo.hstack([category_name_fields[i], remove_category_buttons[i], update_category_buttons[i]]).left() for i, _ in enumerate(categories)],
        mo.hstack([new_category_name, add_category_button]).left()
    ])
    return


@app.cell
def _(
    Categories,
    add_category_button,
    categories,
    category_name_fields,
    new_category_name,
    remove_category_buttons,
    set_category_state,
    update_category_buttons,
):
    for category, value in zip(categories, remove_category_buttons.value):
        if value:
            id_ = category["id"]
            Categories.delete(id_)
            set_category_state(lambda val: val + 1)


    for category, name, value in zip(categories, category_name_fields.value, update_category_buttons.value):
        if value:
            id_ = category["id"]
            Categories.update(id_, name)
            set_category_state(lambda val: val + 1)


    if add_category_button.value and new_category_name.value:
        Categories.insert(new_category_name.value)
        set_category_state(lambda val: val + 1)
    return


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


app._unparsable_cell(
    r"""
    budget_items = []
    if budget_month.value and budget_year.value:
        budget_items = BudgetItems.all(budget_month.value, budget_year.value)

    for _item in categories:
        if _item["month"] is None 
        and _item["year"] is None 
        and _item["budgeted_amount"] is None:
            BudgetItems.insert_or_replace(month=budget_month.value, 
                                      year=budget_year.value,
                                      category_id=_category["id"],
                                      budgeted_amount=0,
                                     )
    """,
    name="_"
)


@app.cell
def _(budget_items, budget_month, budget_year, categories, mo):
    _category = mo.ui.array([
        mo.ui.text(_category["name"]) for _category in categories
     ])

    _budgeted = mo.ui.array([
        mo.ui.number(float(_item["budgeted_amount"])/100.0) for _item in budget_items
    ])

    _spent    = mo.ui.array([
     mo.ui.number(disabled=True, value=float(_item["total_spent"])/100.0) for _items in budget_items   
    ])

    _balance  = mo.ui.array([
        mo.ui.number(disabled=True, value=float(_item["budgeted_amount"]-_item["total_spent"])/100.0) for _items in budget_items
    ])

    mo.vstack(
        [
            mo.md("# Budget"),
            mo.hstack([budget_month, budget_year]).left(),
            mo.md("---"),
            mo.hstack([
                mo.md("Category"),
                mo.md("Budgeted"),
                mo.md("Spent"),
                mo.md("Balance")
            ]),
            *[mo.hstack([

            ]) for i in range(len(categories))],
            mo.md("# Report"),
            mo.md("---"),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
