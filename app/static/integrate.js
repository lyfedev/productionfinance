// The middle pane assembles as the fields are filled, so the request body is
// visible before it is sent rather than only after. The page keeps working
// with JavaScript off — the form still submits and the server renders the
// same JSON — so this reveals the payload earlier, it does not gate access
// to it.
(function () {
  "use strict";
  var form = document.getElementById("pf-int-form");
  var pane = document.getElementById("pf-int-request");
  if (!form || !pane) return;

  function payload() {
    return {
      jurisdiction_id: form.elements.jurisdiction_id.value,
      qualified_spend: form.elements.qualified_spend.value,
      spend_confidence: form.elements.spend_confidence.value
    };
  }

  function render() {
    pane.textContent = JSON.stringify(payload(), null, 2);
  }

  form.addEventListener("input", render);
  form.addEventListener("change", render);

  // Presets fill the fields and update the request pane. They do not submit:
  // the point is to see the request assemble, then send it deliberately.
  Array.prototype.forEach.call(
    document.querySelectorAll("[data-preset]"),
    function (button) {
      button.addEventListener("click", function () {
        var preset = JSON.parse(button.getAttribute("data-preset"));
        form.elements.jurisdiction_id.value = preset.jurisdiction_id;
        form.elements.qualified_spend.value = preset.qualified_spend;
        form.elements.spend_confidence.value = preset.spend_confidence || "validated";
        render();
        form.elements.qualified_spend.focus();
      });
    }
  );

  render();
})();
