from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

try:
    import pandas as pd
except ImportError:  # pragma: no cover - notebook environment concern
    pd = None

try:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.lines import Line2D
except ImportError:  # pragma: no cover - notebook environment concern
    plt = None
    FuncAnimation = None
    PillowWriter = None
    Line2D = None


PARTNER_TYPES = [
    "cooperative",
    "assertive",
    "hesitant",
    "opportunistic",
    "deceptive_switching",
]

OUTCOME_ORDER = ["success", "collision", "deadlock", "timeout"]
ACTION_ORDER = ["wait", "yield", "probe_gently", "proceed", "assert"]

OUTCOME_COLORS = {
    "success": "#4c78a8",
    "collision": "#e45756",
    "deadlock": "#f2cf5b",
    "timeout": "#8f8f8f",
}

SEED_MARKERS = {
    7: "o",
    11: "s",
}

PDF_STYLE = {
    "arrow": "#2f5aa8",
    "grid": "#d9d9d9",
    "edge": "#111111",
    "text": "#111111",
}


def require_plot_stack() -> None:
    missing: list[str] = []
    if pd is None:
        missing.append("pandas")
    if plt is None:
        missing.append("matplotlib")
    if missing:
        raise RuntimeError(f"Install plotting deps in the notebook image first: {', '.join(missing)}")


def load_json(path: Path) -> dict:
    return __import__("json").loads(path.read_text(encoding="utf-8"))


def _legend_handles() -> tuple[list[Line2D], list[Line2D]]:
    if Line2D is None:
        raise RuntimeError("matplotlib legend helpers unavailable")

    outcome_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label=label,
            markerfacecolor=color,
            markeredgecolor="black",
            markersize=9,
        )
        for label, color in OUTCOME_COLORS.items()
    ]
    seed_handles = [
        Line2D(
            [0],
            [0],
            marker=SEED_MARKERS[seed],
            color="black",
            linestyle="",
            label=f"seed {seed}",
            markersize=9,
        )
        for seed in sorted(SEED_MARKERS)
    ]
    return outcome_handles, seed_handles


def style_3d_axes_pdf(ax, title: str) -> None:
    ax.set_title(title, fontsize=13, pad=18, color=PDF_STYLE["text"])
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor("#d0d0d0")
    ax.yaxis.pane.set_edgecolor("#d0d0d0")
    ax.zaxis.pane.set_edgecolor("#d0d0d0")
    ax.grid(True, alpha=0.18)
    ax.tick_params(labelsize=9, pad=2)


def scatter_by_seed_outcome_pdf(ax, df, x: str, y: str, z: str) -> None:
    for seed in sorted(df["seed"].unique()):
        for outcome in OUTCOME_ORDER:
            subset = df[(df["seed"] == seed) & (df["outcome"] == outcome)]
            if subset.empty:
                continue
            ax.scatter(
                subset[x],
                subset[y],
                subset[z],
                s=42,
                alpha=0.85,
                c=OUTCOME_COLORS[outcome],
                marker=SEED_MARKERS.get(seed, "o"),
                edgecolors=PDF_STYLE["edge"],
                linewidths=0.35,
                depthshade=False,
            )


def set_equal_3d_limits(ax, xs, ys, zs) -> None:
    max_range = np.array(
        [
            np.max(xs) - np.min(xs),
            np.max(ys) - np.min(ys),
            np.max(zs) - np.min(zs),
        ]
    ).max() / 2.0

    mid_x = (np.max(xs) + np.min(xs)) * 0.5
    mid_y = (np.max(ys) + np.min(ys)) * 0.5
    mid_z = (np.max(zs) + np.min(zs)) * 0.5

    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)


def draw_polished_heatmap(ax, df, title: str, cmap: str = "viridis", fmt: str = "{:.2f}") -> None:
    values = df.values.astype(float)
    im = ax.imshow(values, cmap=cmap, aspect="auto")
    ax.set_title(title, fontsize=13, color=PDF_STYLE["text"], pad=12)
    ax.set_xticks(np.arange(df.shape[1]))
    ax.set_xticklabels(df.columns, rotation=35, ha="right", fontsize=9, color=PDF_STYLE["text"])
    ax.set_yticks(np.arange(df.shape[0]))
    ax.set_yticklabels(df.index, fontsize=9, color=PDF_STYLE["text"])

    for spine in ax.spines.values():
        spine.set_color("#d0d0d0")

    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            value = values[i, j]
            text_color = "white" if value > values.max() * 0.55 else PDF_STYLE["text"]
            ax.text(j, i, fmt.format(value), ha="center", va="center", fontsize=8.5, color=text_color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.outline.set_edgecolor("#d0d0d0")
    cbar.ax.tick_params(labelsize=8, colors=PDF_STYLE["text"])


def _load_variant2_frames(root: Path, seeds: tuple[int, ...]):
    scenario_rows: list[dict] = []
    context_action_rows: list[dict] = []
    partner_action_rows: list[dict] = []

    missing_paths: list[str] = []
    analysis_by_seed: dict[int, dict] = {}
    for seed in seeds:
        path = root / "logs" / f"local-run-v2-modal-seed{seed}" / "candidate_metrics" / "choice_analysis.json"
        if not path.exists():
            missing_paths.append(str(path))
            continue
        analysis_by_seed[seed] = load_json(path)

    if missing_paths:
        raise FileNotFoundError("Missing Variant 2 analysis files:\n" + "\n".join(missing_paths))

    for seed, analysis in analysis_by_seed.items():
        for row in analysis.get("scenario_summaries", []):
            ctx = row.get("context_tag_set") or {}
            scenario_rows.append(
                {
                    "seed": seed,
                    "scenario_family": row.get("scenario_family"),
                    "partner_style": row.get("partner_style"),
                    "urgency": ctx.get("urgency"),
                    "norm": ctx.get("norm"),
                    "margin": ctx.get("margin"),
                    "timeout_pressure": ctx.get("timeout_pressure"),
                    "belief_turning_point": row.get("belief_turning_point"),
                    "action_switch_point": row.get("action_switch_point"),
                    "switch_delay_after_evidence": row.get("switch_delay_after_evidence"),
                    "context_sensitive_action_regret": row.get("context_sensitive_action_regret"),
                    "belief_confidence_peak": row.get("belief_confidence_peak"),
                    "outcome": row.get("outcome"),
                    "context_tag": row.get("context_tag"),
                }
            )

        for key, value in (analysis.get("choice_context_rates") or {}).items():
            context, action = key.split("|", 1)
            context_action_rows.append(
                {
                    "seed": seed,
                    "context": context,
                    "action": action,
                    "rate": float(value),
                }
            )

        for partner_key, rates in (analysis.get("partner_style_rates") or {}).items():
            partner_index = int(partner_key.removeprefix("partner_type_"))
            partner_style = PARTNER_TYPES[partner_index]
            for rate_key, value in rates.items():
                if rate_key.endswith("_rate"):
                    partner_action_rows.append(
                        {
                            "seed": seed,
                            "partner_style": partner_style,
                            "action": rate_key.removesuffix("_rate"),
                            "rate": float(value),
                        }
                    )

    scenario_df = pd.DataFrame(scenario_rows)
    context_action_df = pd.DataFrame(context_action_rows)
    partner_action_df = pd.DataFrame(partner_action_rows)
    return scenario_df, context_action_df, partner_action_df


def _build_pca_data(scenario_df):
    plot_df = scenario_df.copy()

    fill_value = 20.0
    for col in ("belief_turning_point", "action_switch_point", "switch_delay_after_evidence"):
        plot_df[col] = plot_df[col].fillna(fill_value)

    numeric_cols = [
        "belief_turning_point",
        "action_switch_point",
        "switch_delay_after_evidence",
        "context_sensitive_action_regret",
        "belief_confidence_peak",
    ]
    categorical_cols = [
        "scenario_family",
        "partner_style",
        "urgency",
        "norm",
        "margin",
        "timeout_pressure",
    ]

    feature_df = pd.concat(
        [
            plot_df[numeric_cols].astype(float),
            pd.get_dummies(plot_df[categorical_cols], drop_first=False).astype(float),
        ],
        axis=1,
    )

    feature_std = (feature_df - feature_df.mean()) / feature_df.std(ddof=0).replace(0.0, 1.0)
    feature_values = feature_std.to_numpy(dtype=float)
    _, singular_values, vt = np.linalg.svd(feature_values, full_matrices=False)
    scores3 = feature_values @ vt.T[:, :3]
    loadings3 = vt.T[:, :3]

    explained = (singular_values**2) / max(1, (len(feature_std) - 1))
    explained_ratio = explained / explained.sum()

    plot_df["PC1"] = scores3[:, 0]
    plot_df["PC2"] = scores3[:, 1]
    plot_df["PC3"] = scores3[:, 2]

    return plot_df, feature_df, loadings3, explained_ratio


def load_variant2_bundle(root: str | Path, seeds: tuple[int, ...] = (7, 11)) -> dict:
    require_plot_stack()

    root = Path(root)
    export_dir = root / "modal" / "reports"
    export_dir.mkdir(parents=True, exist_ok=True)

    scenario_df, context_action_df, partner_action_df = _load_variant2_frames(root, seeds)
    plot_df, feature_df, loadings3, explained_ratio = _build_pca_data(scenario_df)
    outcome_handles, seed_handles = _legend_handles()

    return {
        "root": root,
        "export_dir": export_dir,
        "scenario_df": scenario_df,
        "context_action_df": context_action_df,
        "partner_action_df": partner_action_df,
        "plot_df": plot_df,
        "feature_df": feature_df,
        "loadings3": loadings3,
        "explained_ratio": explained_ratio,
        "outcome_handles": outcome_handles,
        "seed_handles": seed_handles,
        "seeds": tuple(seeds),
    }


def _draw_top_loadings(ax, bundle: dict, top_n: int, scale: float, annotate: bool = True) -> None:
    loadings3 = bundle["loadings3"]
    feature_columns = bundle["feature_df"].columns
    top_idx = np.argsort(np.linalg.norm(loadings3, axis=1))[-top_n:]
    for idx in top_idx:
        x, y, z = loadings3[idx] * scale
        ax.quiver(
            0,
            0,
            0,
            x,
            y,
            z,
            color=PDF_STYLE["arrow"],
            linewidth=1.8,
            alpha=0.82,
            arrow_length_ratio=0.08,
        )
        if annotate:
            ax.text(x * 1.08, y * 1.08, z * 1.08, feature_columns[idx], fontsize=8.3, color=PDF_STYLE["arrow"])


def build_3d_pca_figure(bundle: dict):
    fig = plt.figure(figsize=(11, 8.5), facecolor="white")
    ax = fig.add_subplot(111, projection="3d")

    scatter_by_seed_outcome_pdf(ax, bundle["plot_df"], "PC1", "PC2", "PC3")
    _draw_top_loadings(ax, bundle=bundle, top_n=9, scale=2.8, annotate=True)

    explained_ratio = bundle["explained_ratio"]
    plot_df = bundle["plot_df"]
    ax.set_xlabel("PC1", labelpad=8)
    ax.set_ylabel("PC2", labelpad=8)
    ax.set_zlabel("PC3", labelpad=8)
    style_3d_axes_pdf(
        ax,
        "Principal Component Analysis\n"
        f"PC1 {explained_ratio[0]:.1%}, PC2 {explained_ratio[1]:.1%}, PC3 {explained_ratio[2]:.1%}",
    )
    ax.view_init(elev=18, azim=-125)
    set_equal_3d_limits(ax, plot_df["PC1"], plot_df["PC2"], plot_df["PC3"])

    leg1 = ax.legend(
        handles=bundle["outcome_handles"],
        title="Outcome",
        loc="upper left",
        bbox_to_anchor=(0.02, 0.98),
        frameon=False,
    )
    ax.add_artist(leg1)
    ax.legend(
        handles=bundle["seed_handles"],
        title="Seed",
        loc="upper left",
        bbox_to_anchor=(0.02, 0.74),
        frameon=False,
    )
    fig.tight_layout()
    return fig


def build_side_by_side_figure(bundle: dict):
    plot_df = bundle["plot_df"]
    orig_df = plot_df.copy()
    orig_df["orig_x"] = orig_df["belief_turning_point"].fillna(20)
    orig_df["orig_y"] = orig_df["action_switch_point"].fillna(20)
    orig_df["orig_z"] = orig_df["context_sensitive_action_regret"]

    fig = plt.figure(figsize=(15, 7), facecolor="white")
    ax0 = fig.add_subplot(121, projection="3d")
    ax1 = fig.add_subplot(122, projection="3d")

    scatter_by_seed_outcome_pdf(ax0, orig_df, "orig_x", "orig_y", "orig_z")
    ax0.set_xlabel("Belief Turning Point", labelpad=8)
    ax0.set_ylabel("Action Switch Point", labelpad=8)
    ax0.set_zlabel("Context Regret", labelpad=8)
    style_3d_axes_pdf(ax0, "Original Feature Space")
    ax0.view_init(elev=18, azim=-125)
    set_equal_3d_limits(ax0, orig_df["orig_x"], orig_df["orig_y"], orig_df["orig_z"])

    scatter_by_seed_outcome_pdf(ax1, plot_df, "PC1", "PC2", "PC3")
    _draw_top_loadings(ax1, bundle=bundle, top_n=8, scale=2.6, annotate=True)
    explained_ratio = bundle["explained_ratio"]
    ax1.set_xlabel("PC1", labelpad=8)
    ax1.set_ylabel("PC2", labelpad=8)
    ax1.set_zlabel("PC3", labelpad=8)
    style_3d_axes_pdf(
        ax1,
        f"PCA Space\nPC1 {explained_ratio[0]:.1%}, PC2 {explained_ratio[1]:.1%}, PC3 {explained_ratio[2]:.1%}",
    )
    ax1.view_init(elev=18, azim=-125)
    set_equal_3d_limits(ax1, plot_df["PC1"], plot_df["PC2"], plot_df["PC3"])

    leg1 = ax1.legend(
        handles=bundle["outcome_handles"],
        title="Outcome",
        loc="upper left",
        bbox_to_anchor=(0.02, 0.98),
        frameon=False,
    )
    ax1.add_artist(leg1)
    ax1.legend(
        handles=bundle["seed_handles"],
        title="Seed",
        loc="upper left",
        bbox_to_anchor=(0.02, 0.74),
        frameon=False,
    )
    fig.tight_layout()
    return fig


def build_heatmap_panel(bundle: dict):
    scenario_df = bundle["scenario_df"]
    context_action_df = bundle["context_action_df"]
    partner_action_df = bundle["partner_action_df"]

    family_outcome = (
        scenario_df.pivot_table(index="scenario_family", columns="outcome", values="seed", aggfunc="count", fill_value=0)
        .reindex(columns=OUTCOME_ORDER, fill_value=0)
    )

    context_action = (
        context_action_df.groupby(["context", "action"])["rate"]
        .mean()
        .unstack(fill_value=0.0)
        .reindex(columns=ACTION_ORDER, fill_value=0.0)
    )

    partner_action = (
        partner_action_df.groupby(["partner_style", "action"])["rate"]
        .mean()
        .unstack(fill_value=0.0)
        .reindex(columns=ACTION_ORDER, fill_value=0.0)
    )

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8), facecolor="white")
    draw_polished_heatmap(axes[0], family_outcome, "Scenario Family x Outcome Count", cmap="Blues", fmt="{:.0f}")
    draw_polished_heatmap(axes[1], context_action, "Context x Action Rate", cmap="magma", fmt="{:.2f}")
    draw_polished_heatmap(axes[2], partner_action, "Partner Style x Action Rate", cmap="cividis", fmt="{:.2f}")
    fig.tight_layout()
    return fig


def build_regret_heatmap(bundle: dict):
    scenario_df = bundle["scenario_df"]
    regret_heatmap = scenario_df.pivot_table(
        index="scenario_family",
        columns="partner_style",
        values="context_sensitive_action_regret",
        aggfunc="mean",
        fill_value=0.0,
    )

    fig, ax = plt.subplots(figsize=(10.5, 5.8), facecolor="white")
    draw_polished_heatmap(ax, regret_heatmap, "Mean Context-Sensitive Action Regret", cmap="YlOrRd", fmt="{:.2f}")
    fig.tight_layout()
    return fig


def export_variant2_static(bundle: dict, include_rotation: bool = False) -> dict[str, str]:
    export_dir = bundle["export_dir"]
    outputs: dict[str, str] = {}

    figure_builders = {
        "variant2_pca_3d_polished": build_3d_pca_figure,
        "variant2_original_vs_pca_3d": build_side_by_side_figure,
        "variant2_heatmaps_panel": build_heatmap_panel,
        "variant2_regret_heatmap": build_regret_heatmap,
    }

    for stem, builder in figure_builders.items():
        fig = builder(bundle)
        pdf_path = export_dir / f"{stem}.pdf"
        svg_path = export_dir / f"{stem}.svg"
        fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
        fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        outputs[f"{stem}_pdf"] = str(pdf_path)
        outputs[f"{stem}_svg"] = str(svg_path)

    if include_rotation and FuncAnimation is not None and PillowWriter is not None:
        fig = build_3d_pca_figure(bundle)
        ax = fig.axes[0]

        def _update(frame):
            ax.view_init(elev=18, azim=frame)
            return fig,

        animation = FuncAnimation(fig, _update, frames=np.arange(-125, 235, 3), interval=80, blit=False)
        gif_path = export_dir / "variant2_pca_rotation.gif"
        animation.save(gif_path, writer=PillowWriter(fps=16))
        outputs["variant2_pca_rotation_gif"] = str(gif_path)

        if shutil.which("ffmpeg"):
            mp4_path = export_dir / "variant2_pca_rotation.mp4"
            animation.save(mp4_path, writer="ffmpeg", fps=16, dpi=160)
            outputs["variant2_pca_rotation_mp4"] = str(mp4_path)

        plt.close(fig)

    return outputs
