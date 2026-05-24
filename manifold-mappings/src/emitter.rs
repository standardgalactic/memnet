// src/emitter.rs
//
// MML emitters:
//   - Pretty-printer: regenerates canonical MML source from an AST.
//   - JSON exporter: serialises the AST to a JSON-like string.
//   - Graph builder: extracts the flow graph as an adjacency list.
//   - Dot exporter: produces Graphviz DOT notation for visualisation.

use crate::ast::*;
use std::collections::HashMap;

// ── Pretty-printer ────────────────────────────────────────────────────────────

pub struct PrettyPrinter {
    indent: usize,
}

impl PrettyPrinter {
    pub fn new() -> Self { Self { indent: 0 } }

    fn ind(&self) -> String { "    ".repeat(self.indent) }

    pub fn print_document(&mut self, doc: &Document) -> String {
        doc.manifolds.iter().map(|m| self.print_manifold(m)).collect::<Vec<_>>().join("\n\n")
    }

    pub fn print_manifold(&mut self, m: &Manifold) -> String {
        let kind = m.fields.get("_kind")
            .and_then(|v| v.as_str()).unwrap_or("manifold");
        let mut out = format!("@{kind} {} {{\n", m.name);
        self.indent += 1;
        out += &self.print_fields(&m.fields, &["_kind"]);
        for r  in &m.regions    { out += &self.print_region(r); }
        for f  in &m.flows      { out += &self.print_flow(f); }
        for c  in &m.constraints{ out += &self.print_constraint(c); }
        for mp in &m.mappings   { out += &self.print_mapping(mp); }
        for b  in &m.bubbles    { out += &self.print_bubble(b); }
        for rel in &m.relations { out += &self.print_relation(rel); }
        for res in &m.residuals { out += &self.print_residual(res); }
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }

    fn print_fields(&self, fields: &Fields, skip: &[&str]) -> String {
        let mut out = String::new();
        // Sort for deterministic output, skip internal keys
        let mut keys: Vec<&String> = fields.keys()
            .filter(|k| !skip.contains(&k.as_str()))
            .collect();
        keys.sort();
        for k in keys {
            let v = &fields[k];
            out += &format!("{}{}: {}\n", self.ind(), k, v);
        }
        out
    }

    fn print_region(&mut self, r: &Region) -> String {
        let mut out = format!("{}region {} {{\n", self.ind(), r.name);
        self.indent += 1;
        out += &self.print_fields(&r.fields, &[]);
        for f in &r.flows      { out += &self.print_flow(f); }
        for c in &r.constraints{ out += &self.print_constraint(c); }
        for s in &r.sub_regions{ out += &self.print_region(s); }
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }

    fn print_flow(&mut self, f: &Flow) -> String {
        let mut out = format!("{}flow {} {{\n", self.ind(), f.name);
        self.indent += 1;
        out += &self.print_fields(&f.fields, &["origin", "target"]);
        if let Some(ref o) = f.origin { out += &format!("{}origin: {o}\n", self.ind()); }
        if let Some(ref t) = f.target { out += &format!("{}target: {t}\n", self.ind()); }
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }

    fn print_constraint(&mut self, c: &Constraint) -> String {
        let mut out = format!("{}constraint {} {{\n", self.ind(), c.name);
        self.indent += 1;
        out += &self.print_fields(&c.fields, &[]);
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }

    fn print_mapping(&mut self, mp: &Mapping) -> String {
        let mut out = format!("{}mapping {} {{\n", self.ind(), mp.name);
        self.indent += 1;
        out += &self.print_fields(&mp.fields, &["source-space","target-space","preserve","discard"]);
        if let Some(ref s) = mp.source_space { out += &format!("{}source-space: {s}\n", self.ind()); }
        if let Some(ref t) = mp.target_space { out += &format!("{}target-space: {t}\n", self.ind()); }
        if !mp.preserve.is_empty() {
            out += &format!("{}preserve: [{}]\n", self.ind(), mp.preserve.join(", "));
        }
        if !mp.discard.is_empty() {
            out += &format!("{}discard: [{}]\n", self.ind(), mp.discard.join(", "));
        }
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }

    fn print_bubble(&mut self, b: &Bubble) -> String {
        let mut out = format!("{}bubble {} {{\n", self.ind(), b.name);
        self.indent += 1;
        out += &self.print_fields(&b.fields, &[]);
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }

    fn print_relation(&mut self, rel: &Relation) -> String {
        let mut out = format!("{}relation {} {{\n", self.ind(), rel.name);
        self.indent += 1;
        out += &self.print_fields(&rel.fields, &["parent","child"]);
        if let Some(ref p) = rel.parent { out += &format!("{}parent: {p}\n", self.ind()); }
        if let Some(ref c) = rel.child  { out += &format!("{}child: {c}\n", self.ind()); }
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }

    fn print_residual(&mut self, res: &Residual) -> String {
        let mut out = format!("{}residual {} {{\n", self.ind(), res.name);
        self.indent += 1;
        out += &self.print_fields(&res.fields, &["source"]);
        if let Some(ref s) = res.source { out += &format!("{}source: {s}\n", self.ind()); }
        self.indent -= 1;
        out += &format!("{}}}\n", self.ind());
        out
    }
}

impl Default for PrettyPrinter { fn default() -> Self { Self::new() } }

// ── JSON exporter ─────────────────────────────────────────────────────────────

pub fn to_json(doc: &Document) -> String {
    let manifolds: Vec<String> = doc.manifolds.iter().map(manifold_to_json).collect();
    format!("{{\"manifolds\":[{}]}}", manifolds.join(","))
}

fn manifold_to_json(m: &Manifold) -> String {
    let mut parts = vec![
        format!("\"name\":\"{}\"", m.name),
        format!("\"fields\":{}", fields_to_json(&m.fields, &["_kind"])),
        format!("\"regions\":[{}]", m.regions.iter().map(region_to_json).collect::<Vec<_>>().join(",")),
        format!("\"flows\":[{}]", m.flows.iter().map(flow_to_json).collect::<Vec<_>>().join(",")),
        format!("\"mappings\":[{}]", m.mappings.iter().map(mapping_to_json).collect::<Vec<_>>().join(",")),
        format!("\"bubbles\":[{}]", m.bubbles.iter().map(bubble_to_json).collect::<Vec<_>>().join(",")),
        format!("\"relations\":[{}]", m.relations.iter().map(relation_to_json).collect::<Vec<_>>().join(",")),
        format!("\"residuals\":[{}]", m.residuals.iter().map(residual_to_json).collect::<Vec<_>>().join(",")),
    ];
    format!("{{{}}}", parts.join(","))
}

fn region_to_json(r: &Region) -> String {
    format!("{{\"name\":\"{}\",\"fields\":{},\"flows\":[{}],\"sub_regions\":[{}]}}",
        r.name,
        fields_to_json(&r.fields, &[]),
        r.flows.iter().map(flow_to_json).collect::<Vec<_>>().join(","),
        r.sub_regions.iter().map(region_to_json).collect::<Vec<_>>().join(","),
    )
}

fn flow_to_json(f: &Flow) -> String {
    format!("{{\"name\":\"{}\",\"origin\":{},\"target\":{},\"fields\":{}}}",
        f.name,
        f.origin.as_deref().map(|s| format!("\"{s}\"")).unwrap_or("null".into()),
        f.target.as_deref().map(|s| format!("\"{s}\"")).unwrap_or("null".into()),
        fields_to_json(&f.fields, &["origin","target"]),
    )
}

fn mapping_to_json(mp: &Mapping) -> String {
    format!("{{\"name\":\"{}\",\"source_space\":{},\"target_space\":{},\"preserve\":[{}],\"discard\":[{}]}}",
        mp.name,
        mp.source_space.as_deref().map(|s| format!("\"{s}\"")).unwrap_or("null".into()),
        mp.target_space.as_deref().map(|s| format!("\"{s}\"")).unwrap_or("null".into()),
        mp.preserve.iter().map(|s| format!("\"{s}\"")).collect::<Vec<_>>().join(","),
        mp.discard.iter().map(|s| format!("\"{s}\"")).collect::<Vec<_>>().join(","),
    )
}

fn bubble_to_json(b: &Bubble) -> String {
    format!("{{\"name\":\"{}\",\"fields\":{}}}", b.name, fields_to_json(&b.fields, &[]))
}

fn relation_to_json(rel: &Relation) -> String {
    format!("{{\"name\":\"{}\",\"parent\":{},\"child\":{},\"fields\":{}}}",
        rel.name,
        rel.parent.as_deref().map(|s| format!("\"{s}\"")).unwrap_or("null".into()),
        rel.child.as_deref().map(|s| format!("\"{s}\"")).unwrap_or("null".into()),
        fields_to_json(&rel.fields, &["parent","child"]),
    )
}

fn residual_to_json(res: &Residual) -> String {
    format!("{{\"name\":\"{}\",\"source\":{},\"fields\":{}}}",
        res.name,
        res.source.as_deref().map(|s| format!("\"{s}\"")).unwrap_or("null".into()),
        fields_to_json(&res.fields, &["source"]),
    )
}

fn fields_to_json(fields: &Fields, skip: &[&str]) -> String {
    let pairs: Vec<String> = fields.iter()
        .filter(|(k, _)| !skip.contains(&k.as_str()))
        .map(|(k, v)| format!("\"{}\":{}", k, value_to_json(v)))
        .collect();
    format!("{{{}}}", pairs.join(","))
}

fn value_to_json(v: &Value) -> String {
    match v {
        Value::Number(n)  => format!("{n}"),
        Value::Text(s)    => format!("\"{s}\""),
        Value::Bool(b)    => format!("{b}"),
        Value::Enum(s)    => format!("\"{s}\""),
        Value::List(items)=> format!("[{}]", items.iter().map(value_to_json).collect::<Vec<_>>().join(",")),
    }
}

// ── Flow graph ────────────────────────────────────────────────────────────────

/// Adjacency list: origin → [(target, persistence)]
pub type FlowGraph = HashMap<String, Vec<(String, f64)>>;

pub fn build_flow_graph(m: &Manifold) -> FlowGraph {
    let mut graph: FlowGraph = HashMap::new();
    for f in m.all_flows() {
        if let (Some(o), Some(t)) = (&f.origin, &f.target) {
            graph.entry(o.clone()).or_default().push((t.clone(), f.persistence().unwrap_or(1.0)));
        }
    }
    graph
}

// ── DOT exporter ──────────────────────────────────────────────────────────────

pub fn to_dot(m: &Manifold) -> String {
    let mut out = format!("digraph \"{}\" {{\n", m.name);
    out += "    rankdir=LR;\n";
    out += "    node [shape=ellipse, style=filled, fillcolor=lightblue];\n";

    // Nodes: regions and bubbles
    for r in &m.regions {
        let ent = r.entropy().map(|e| format!(" S={e:.2}")).unwrap_or_default();
        let sal = r.salience().map(|s| format!(" Φ={s:.2}")).unwrap_or_default();
        let fill = if r.is_xylomorphic() { "\"#b8f0b8\"" } else { "\"#f0c8c8\"" };
        out += &format!("    \"{}\" [label=\"{}{}{}\", fillcolor={}];\n",
            r.name, r.name, ent, sal, fill);
    }
    for b in &m.bubbles {
        out += &format!("    \"{}\" [shape=circle, fillcolor=\"#e8d8f8\"];\n", b.name);
    }

    // Edges: flows
    for f in m.all_flows() {
        if let (Some(o), Some(t)) = (&f.origin, &f.target) {
            let label = format!("{}{}", f.name,
                f.persistence().map(|p| format!(" p={p:.2}")).unwrap_or_default());
            out += &format!("    \"{}\" -> \"{}\" [label=\"{}\"];\n", o, t, label);
        }
    }

    // Edges: relations (bubbles)
    for rel in &m.relations {
        if let (Some(p), Some(c)) = (&rel.parent, &rel.child) {
            let coup = rel.fields.get("coupling").and_then(|v| v.as_str()).unwrap_or("nested");
            out += &format!("    \"{}\" -> \"{}\" [label=\"{} ({})\", style=dashed];\n",
                p, c, rel.name, coup);
        }
    }

    out += "}\n";
    out
}
