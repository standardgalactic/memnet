// Pure view logic for the spatial client. No DOM access: the same file runs in the
// browser page and under Node, so the audit can check exactly what the page draws.
// Everything drawn comes from the display list built here.
var CNView = (function () {
  var SUPPORT_MARK = { unassessed: "·", supported: "+", contested: "±", defeated: "×" };
  var CHANNEL_STYLE = { relevance: "thin-line", support: "arrow", admissibility: "chevron" };
  var STATUS_DASH = { established: "solid", provisional: "dashed", unverified: "dotted" };
  var ASSERTION_GLYPH = { established: "disc", provisional: "ring", unverified: "dotted-ring", none: "cross" };

  function centroid(scene) {
    var n = scene.nodes.length || 1, c = [0, 0, 0];
    scene.nodes.forEach(function (nd) { for (var i = 0; i < 3; i++) c[i] += nd.pos[i] / n; });
    return c;
  }

  function radius(scene, c) {
    var r = 1e-6;
    scene.nodes.forEach(function (nd) {
      var d = Math.hypot(nd.pos[0] - c[0], nd.pos[1] - c[1], nd.pos[2] - c[2]);
      if (d > r) r = d;
    });
    return r;
  }

  function project(pos, c, r, cam) {
    var x = (pos[0] - c[0]) / r, y = (pos[1] - c[1]) / r, z = (pos[2] - c[2]) / r;
    var cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
    var x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
    var y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    var persp = 1 / (1 + 0.35 * z2);
    return { x: x1 * persp * cam.zoom, y: y1 * persp * cam.zoom, depth: z2, scale: persp };
  }

  function edgeStyle(e, opts) {
    var shape = opts.mergeChannels ? "arrow" : CHANNEL_STYLE[e.channel];
    var dash = opts.markStatus ? STATUS_DASH[e.status] : "solid";
    return { shape: shape, dash: dash };
  }

  function buildDisplayList(scene, options) {
    var o = options || {};
    var opts = {
      showProvisional: !!o.showProvisional,
      mergeChannels: !!scene.options.merge_channels,
      markStatus: scene.options.mark_status !== false
    };
    var cam = o.camera || { yaw: 0.6, pitch: 0.35, zoom: 1 };
    var c = centroid(scene), r = radius(scene, c), at = {}, items = [];
    scene.nodes.forEach(function (nd) {
      var p = project(nd.pos, c, r, cam);
      at[nd.id] = p;
      items.push({
        kind: "node", id: nd.id, key: "node:" + nd.id, x: p.x, y: p.y, depth: p.depth, scale: p.scale,
        glyph: opts.markStatus ? ASSERTION_GLYPH[nd.assertion] : "disc",
        assertion: nd.assertion, support: nd.support, mark: SUPPORT_MARK[nd.support],
        door: nd.door, doorGlyph: nd.door === "open" ? "arch-open" : nd.door === "dimmed" ? "arch-dim" : null,
        review: (nd.review || []).length > 0
      });
    });
    scene.edges.forEach(function (e) {
      if (e.status !== "established" && !opts.showProvisional) return;
      if (!at[e.from] || !at[e.to]) return;
      var st = edgeStyle(e, opts);
      items.push({
        kind: "edge", event: e.event, key: "event:" + e.event, from: e.from, to: e.to,
        rel_type: e.rel_type, channel: e.channel, status: e.status, shape: st.shape, dash: st.dash,
        x1: at[e.from].x, y1: at[e.from].y, x2: at[e.to].x, y2: at[e.to].y
      });
    });
    (o.trail || []).forEach(function (id, i, a) {
      if (i > 0 && at[id] && at[a[i - 1]]) {
        items.push({ kind: "trail", from: a[i - 1], to: id, order: i,
                     x1: at[a[i - 1]].x, y1: at[a[i - 1]].y, x2: at[id].x, y2: at[id].y });
      }
    });
    return items;
  }

  function inspect(scene, key) {
    if (scene.options.explain_on_scan === false) return "";
    var t = scene.explanations[key];
    return t === undefined ? "No explanation is recorded for " + key : t;
  }

  function movement(scene, id) {
    return scene.movement && scene.movement[id] ? scene.movement[id] : null;
  }

  function dist2seg(px, py, x1, y1, x2, y2) {
    var dx = x2 - x1, dy = y2 - y1, l = dx * dx + dy * dy;
    var t = l ? Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / l)) : 0;
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  }

  // Nodes win over edges; the nearest within the radius is chosen.
  function pick(items, x, y, radiusNode, radiusEdge) {
    var best = null, bd = radiusNode;
    items.forEach(function (it) {
      if (it.kind !== "node") return;
      var d = Math.hypot(it.x - x, it.y - y);
      if (d < bd) { bd = d; best = it; }
    });
    if (best) return best;
    bd = radiusEdge;
    items.forEach(function (it) {
      if (it.kind !== "edge") return;
      var d = dist2seg(x, y, it.x1, it.y1, it.x2, it.y2);
      if (d < bd) { bd = d; best = it; }
    });
    return best;
  }

  return { buildDisplayList: buildDisplayList, inspect: inspect, movement: movement, pick: pick,
           SUPPORT_MARK: SUPPORT_MARK };
})();
if (typeof module !== "undefined") module.exports = CNView;
