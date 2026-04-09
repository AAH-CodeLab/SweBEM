import pandas as pd
import plotly.graph_objects as go

def plot_hourly(hourly):
    data = pd.DataFrame(hourly)
    fig = go.Figure()
    for key, values in data.items():
        fig.add_trace(go.Scatter(y=values, name=key, mode="lines"))
    
    fig.update_layout(
        title="Hourly Results",
        xaxis_title="Hour",
        yaxis_title="kW",
        hovermode="x unified"
    )
    
    fig.show()

def plot_hourly_all(results: dict):
    """
    hourly_all: {period: {column: [values]}}
    """
    hourly_all = {period: data["hourly"] for period, data in results.items()}
    fig = go.Figure()

    periods = list(hourly_all.keys())

    # Add all traces, only first period visible
    for period, hourly in hourly_all.items():
        df = pd.DataFrame(hourly)
        visible = (period == periods[0])
        for col, values in df.items():
            fig.add_trace(go.Scatter(
                y=values,
                name=col,
                mode="lines",
                visible=visible,
                legendgroup=period,
            ))

    # Build dropdown buttons
    traces_per_period = [len(pd.DataFrame(h).columns) for h in hourly_all.values()]

    buttons = []
    for i, period in enumerate(periods):
        visibility = []
        for j, _ in enumerate(periods):
            visible = (i == j)
            visibility.extend([visible] * traces_per_period[j])
        buttons.append(dict(
            label=period,
            method="update",
            args=[{"visible": visibility}],
        ))

    fig.update_layout(
        title="Hourly Results",
        xaxis_title="Hour",
        yaxis_title="kW",
        hovermode="x unified",
        updatemenus=[dict(
            buttons=buttons,
            direction="down",
            x=1.0,
            y=1.15,
        )]
    )

    fig.show()