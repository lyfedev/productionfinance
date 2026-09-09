// The example links fill the form rather than submitting it, so a visitor
// sees what changed before asking for an answer. Without JavaScript the
// form still works; only the shortcut is unavailable.
(function () {
  "use strict";
  var form = document.getElementById("calc");
  if (!form) return;
  Array.prototype.forEach.call(document.querySelectorAll("[data-fill]"), function (b) {
    b.addEventListener("click", function () {
      var v = JSON.parse(b.getAttribute("data-fill"));
      form.elements.jurisdiction_id.value = v.jurisdiction_id;
      form.elements.qualified_spend.value = v.qualified_spend;
      form.elements.qualified_spend.focus();
    });
  });
})();
