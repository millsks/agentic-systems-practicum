from practicum.exercises import extract_exercises

HTML = """
<div class="exercise" data-id="m01-e1" data-stdin="Ada\\n3">
  <div class="exercise-prompt"><p>Do it &amp; win</p></div>
  <textarea class="starter">def f():\n    ...</textarea>
  <script type="text/x-python" class="tests">
    def test_f():
        assert f() == 1 &lt; 2
  </script>
  <details class="hint"><summary>Hint</summary><p><code>not this</code></p></details>
  <details class="solution"><summary>Show</summary>
<pre><code class="language-python">def f():
    return 1 &lt; 2</code></pre>
  </details>
</div>
<div class="exercise" data-id="m01-e2"><script class="tests">def test_x(): pass</script></div>
"""


def test_extract_exercises_reads_solution_tests_and_stdin() -> None:
    first, second = extract_exercises(HTML)
    assert first.id == "m01-e1"
    assert first.stdin == "Ada\n3"
    assert first.solution == "def f():\n    return 1 < 2\n"
    assert first.tests == "def test_f():\n    assert f() == 1 &lt; 2\n"
    assert second.id == "m01-e2"
    assert second.solution == "\n"
