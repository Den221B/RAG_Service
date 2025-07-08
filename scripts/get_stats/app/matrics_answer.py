import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from extract import process_all_logs


def add_metrics(fig, metrics, row, col, grid_size):
    """Add a text box with summary statistics under a subplot."""
    if not metrics:
        return

    items = list(metrics.items())
    formatted_text = ""

    for i in range(0, len(items), 2):
        pair = items[i:i + 2]
        line = []
        for k, v in pair:
            value = "N/A" if v is None else f"{v:.1f}" if isinstance(v, (int, float)) else str(v)
            line.append(f"{k}: {value}")
        formatted_text += "&nbsp;&nbsp;".join(line) + "<br>"

    fig.add_annotation(
        x=0.83,
        y=-0.9,
        xref=f"x{grid_size * (row - 1) + col} domain",
        yref=f"y{grid_size * (row - 1) + col} domain",
        text=formatted_text.rstrip("<br>"),
        showarrow=False,
        align="center",
        font=dict(size=9)
    )


def get_metrics(values):
    """Compute basic statistics for a list of values."""
    filtered = [v for v in values if v is not None]
    if not filtered:
        return {
            "Mean": None,
            "Median": None,
            "Max": None,
            "Min": None,
        }
    array = np.array(filtered, dtype=np.float64)
    return {
        "Mean": np.mean(array),
        "Median": np.median(array),
        "Max": np.max(array),
        "Min": np.min(array),
    }


def generate_charts(result, date_str):
    """Generate HTML chart file with plots and IP stats."""
    ip_counts = Counter(result["ip"])
    top_ips = ip_counts.most_common(5)
    ip_labels = [ip for ip, _ in top_ips]
    ip_values = [count for _, count in top_ips]

    val = {}
    val_names = []

    for i, (key, values) in enumerate((k, v) for k, v in result["data"].items() if v):
        val[i + 2] = values
        val_names.append(key.split('.')[-1])

    num_subplots = len(val) + 1
    grid_size = int(num_subplots ** 0.5) + 1

    fig = make_subplots(
        rows=grid_size, cols=grid_size,
        vertical_spacing=0.11,
        subplot_titles=["Top IPs"] + val_names
    )

    fig.add_trace(
        go.Bar(x=ip_labels, y=ip_values, name="Top IPs"),
        row=1, col=1
    )

    positions = [
        (i, j)
        for i in range(1, grid_size + 1)
        for j in range(1, grid_size + 1)
        if (i, j) != (1, 1)
    ]

    for k, (i, j) in zip(range(2, num_subplots + 1), positions):
        fig.add_trace(
            go.Scatter(
                x=list(range(len(val[k]))),
                y=val[k],
                mode='lines+markers',
                name=val_names[k - 2]
            ),
            row=i, col=j
        )
        add_metrics(fig, get_metrics(val[k]), row=i, col=j, grid_size=grid_size)

    fig.update_layout(showlegend=False)

    metrics_dir = Path("metrics")
    metrics_dir.mkdir(exist_ok=True)
    fig.write_html(metrics_dir / f"metrics_{date_str}.html")


def export_answers_to_excel(data: dict, date_str: str):
    """Save question/answer pairs to Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Answer Data"

    ws.append(["Question", "Answer"])
    questions = data.get('texts.question.text', [])
    answers = data.get('texts.answer.text', [])

    for q, a in zip(questions, answers):
        ws.append([q, a])

    output_dir = Path("metrics")
    output_dir.mkdir(exist_ok=True)
    wb.save(output_dir / f"Answer_{date_str}.xlsx")


def main(flag_last: bool):
    result, data, date_str = process_all_logs(flag_last=flag_last)
    generate_charts(result, date_str)
    export_answers_to_excel(data, date_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--flag_last", action="store_true", help="Use only the most recent log file")
    args = parser.parse_args()

    main(args.flag_last)
