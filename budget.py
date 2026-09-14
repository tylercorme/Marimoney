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
    from transaction_parsers import make_parser

    return Accounts, Categories, Transactions, datetime, mo, timedelta


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
    def validate_account(value) -> str:
        if not value['name']:
            return "Name required"

    create_account_form = mo.md(
        """
        {name} {start_balance} {on_budget}
        """
    ).batch(
        name=mo.ui.text(label="Name", placeholder="Account Name"),
        start_balance=mo.ui.number(start=0.0, label="Start Balance"),
        on_budget=mo.ui.checkbox(label="On Budget", value=True),
    ).form(submit_button_label="Add Account", validate=validate_account, clear_on_submit=True)

    mo.vstack([
        mo.md("# Accounts"),
        mo.md("---"),
        create_account_form,           
    ])
    return (create_account_form,)


@app.cell
def _(Accounts, create_account_form):
    balances = Accounts.balances()
    net_worth = 0.0
    if create_account_form.value:
        new_account = create_account_form.value
        Accounts.insert(
            new_account["name"],
            int(new_account["start_balance"]*100),
            bool(new_account["on_budget"])
        )
        balances = Accounts.balances()
        net_worth = sum([account["current_balance"] for account in balances])
    return balances, net_worth


@app.cell
def _(balances):
    account_name_to_id = {account["name"]: account["id"] for account in balances}
    return (account_name_to_id,)


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
    transactions = Transactions.all(*transaction_account_select.value, start_date=transactions_from.value, end_date=transactions_to.value)
    _hidden_columns = ["id_","account_id","transfer_from_id","category_id","payee_id"]
    if not transactions:
        _hidden_columns = []

    transaction_table = mo.ui.table(
        transactions,
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
def _(account_name_to_id, mo):
    statement_files = mo.ui.file(
        multiple=True, 
        label="Statements",
        kind="area",
    )

    supported_statements = ["Chase", "Capital One"]
    statement_type = mo.ui.dropdown(
        options=supported_statements,
        label="Institution: "
    )
    account_select = mo.ui.dropdown(
        options=account_name_to_id,
        label="Account: "
    )
    return account_select, statement_files, statement_type


@app.cell
def _(account_select, mo, statement_files, statement_type):
    mo.vstack(
        [
            mo.md("# Transaction Importer"),
            mo.md("---"),
            mo.hstack([statement_type, account_select]).left(),
            statement_files,
            # make_parser(statement_type.value).parse(statement_files.value)

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
    return add_category_button, categories, new_category_name


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
def _(budget_month, budget_year, categories, mo):
    num_categories = len(categories)
    _category = mo.vstack([
        mo.md("Category"),    
    ])
    _budgeted = mo.vstack([
        mo.md("Budgeted"),
    ])
    _spent = mo.vstack([
        mo.md("Spent"),
    ])
    _balance = mo.vstack([
        mo.md("Balance"),
    ])

    mo.vstack(
        [
            mo.md("# Budget"),
            mo.hstack([budget_month,budget_year]).left(),
            mo.md("---"),
            mo.hstack([_category, _budgeted, _spent, _balance]),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
