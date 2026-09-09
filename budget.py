import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    from datetime import datetime, timedelta

    return datetime, mo, timedelta


@app.cell(disabled=True)
def _(datetime, mo, refresh):
    refresh
    now = datetime.now().strftime('%B %d, %Y, %I:%M:%S %p')
    header = mo.md(
        f"""
        # Tyler's Budget
        ### {now}
        """
    )
    return (header,)


@app.cell(hide_code=True)
def _(header, mo, refresh):
    refresh
    mo.sidebar(
        mo.vstack(
            [
                header,
                mo.md("# Accounts").center(),
            *[_ for account in []],
             mo.ui.button(label="Add Account", on_click=add_account).center()
            ]
        )
    )
    return


@app.cell
def _(datetime, mo, timedelta):
    _from = mo.ui.date(
                label = "From: ",
                start = (datetime.now() - timedelta(days=30)).date(),
    )

    _to = mo.ui.date(
        label = " To: ",
        start = (datetime.now().date())
    )

    transactions = mo.ui.table([1,2,3], 
                               header_tooltip=None,
                               hover_template=None
    )

    mo.vstack(
        [
            mo.md(
                """
                # Transactions
                """
            ).left(),
            mo.hstack([_from, _to]).left(),
            transactions,
        ]
    )
    return (transactions,)


@app.cell
def _(mo, transactions):
    transactions.value

    mo.vstack(
        [
            mo.md("# Transaction Editor"),
            mo.ui.form(
            
            )
        ]
    )
    return


@app.cell
def _(mo):
    def cell_hover(row_id: str, column_name: str, value) -> str:
        return f"{row_id}:{column_name}={value}"

    hover_table = mo.ui.table(
        [{"a": i, "b": i * i} for i in range(8)],
        hover_template=cell_hover,
    )
    hover_table
    return


@app.cell
def _(mo):
    # Demonstrate a long table with a sticky header and a custom max height
    long_rows = [{"row": i, "first_name": f"First {i}", "last_name": f"Last {i}"} for i in range(200)]
    long_table = mo.ui.table(
        long_rows,
        pagination=False,
        max_height=300,
    )
    long_table
    return


@app.cell(hide_code=True)
def _(mo):
    refresh = mo.ui.refresh(default_interval=1)
    refresh
    return (refresh,)


@app.function
def add_account():
    ...


if __name__ == "__main__":
    app.run()
