from IPython.display import HTML, display


def toggle_code() -> None:
    """Render a button that toggles code-cell inputs in classic Jupyter and JupyterLab."""
    html = """
<script>
(function() {
  function toggleCodeCells() {
    const selectors = [
      '.jp-CodeCell .jp-InputArea',
      'div.cell.code_cell div.input'
    ];

    selectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((el) => {
        const current = window.getComputedStyle(el).display;
        el.style.display = current === 'none' ? '' : 'none';
      });
    });
  }

  window.code_toggle = toggleCodeCells;
})();
</script>
<form action="javascript:code_toggle()">
  <input type="submit" id="toggleButton" value="Toggle Code" />
</form>
"""
    display(HTML(html))
