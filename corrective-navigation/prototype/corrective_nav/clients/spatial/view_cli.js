// Runs the view logic under Node for the audit: reads {scene, options, inspect} on stdin,
// prints {items, inspections}.
const CNView = require("./view.js");
let buf = "";
process.stdin.on("data", (d) => (buf += d));
process.stdin.on("end", () => {
  const req = JSON.parse(buf);
  const items = CNView.buildDisplayList(req.scene, req.options || {});
  const inspections = {};
  (req.inspect || []).forEach((k) => (inspections[k] = CNView.inspect(req.scene, k)));
  process.stdout.write(JSON.stringify({ items, inspections }));
});
