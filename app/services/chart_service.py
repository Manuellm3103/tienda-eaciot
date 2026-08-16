"""Chart generation for AI analytics (#15 on the innovation roadmap).

Renders simple bar/line/pie charts from query results using matplotlib.
matplotlib is an optional dependency declared in requirements-ai-innovations.txt.
"""
import io
from typing import Any


def _ensure_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is not installed") from exc


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


class ChartService:
    def render(
        self,
        chart_type: str,
        columns: list[str],
        data: list[list[Any]],
    ) -> bytes:
        """Render a chart image (PNG) from tabular data.

        chart_type: bar, line, pie, or number (number returns a simple PNG).
        columns: column names.
        data: rows of values.
        """
        plt = _ensure_matplotlib()

        if chart_type == "number":
            return self._render_number(plt, columns, data)

        if not data or len(columns) < 2:
            return self._render_empty(plt)

        labels = [str(row[0]) for row in data]
        values = [_to_number(row[1]) for row in data]

        fig, ax = plt.subplots(figsize=(8, 5))

        if chart_type == "pie":
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            ax.set_title(" ".join(columns))
        elif chart_type == "line":
            ax.plot(labels, values, marker="o")
            ax.set_xlabel(columns[0])
            ax.set_ylabel(columns[1])
            ax.set_title(f"{columns[1]} por {columns[0]}")
            plt.xticks(rotation=45, ha="right")
        else:  # bar (default)
            ax.bar(labels, values)
            ax.set_xlabel(columns[0])
            ax.set_ylabel(columns[1])
            ax.set_title(f"{columns[1]} por {columns[0]}")
            plt.xticks(rotation=45, ha="right")

        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    def _render_number(self, plt, columns: list[str], data: list[list[Any]]) -> bytes:
        value = _to_number(data[0][0]) if data and data[0] else 0.0
        label = columns[0] if columns else "Valor"

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(
            0.5,
            0.5,
            f"{value:,.2f}",
            fontsize=48,
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.text(
            0.5,
            0.2,
            label,
            fontsize=16,
            ha="center",
            va="center",
            transform=ax.transAxes,
            color="gray",
        )
        ax.axis("off")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    def _render_empty(self, plt) -> bytes:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "Sin datos", fontsize=20, ha="center", va="center")
        ax.axis("off")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()


chart_service = ChartService()
