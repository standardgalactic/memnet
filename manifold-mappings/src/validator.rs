// src/validator.rs
//
// MML semantic validator.
//
// Checks:
//   - All flow origin/target references resolve to known region names.
//   - All relation parent/child references resolve to known bubble names.
//   - All residual source references resolve to known region names.
//   - Numeric field values are in plausible ranges (entropy ∈ [0,1], etc.).
//   - Admissibility threshold is present and in range.
//   - Xylomorphic criterion flags (salience > entropy) are reported.
//   - Dangling references (flows with unknown targets) are flagged.
//   - Constraint thresholds are checked for consistency.

use crate::ast::*;
use std::collections::HashSet;

// ── Diagnostics ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum Severity { Error, Warning, Info }

impl std::fmt::Display for Severity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Severity::Error   => write!(f, "ERROR"),
            Severity::Warning => write!(f, "WARN "),
            Severity::Info    => write!(f, "INFO "),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Diagnostic {
    pub severity: Severity,
    pub path:     String,   // e.g. "manifold.region.flow"
    pub message:  String,
}

impl std::fmt::Display for Diagnostic {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[{}] {}: {}", self.severity, self.path, self.message)
    }
}

pub struct ValidationReport {
    pub diagnostics: Vec<Diagnostic>,
}

impl ValidationReport {
    fn new() -> Self { Self { diagnostics: Vec::new() } }

    fn push(&mut self, severity: Severity, path: impl Into<String>, message: impl Into<String>) {
        self.diagnostics.push(Diagnostic { severity, path: path.into(), message: message.into() });
    }

    pub fn errors(&self) -> Vec<&Diagnostic> {
        self.diagnostics.iter().filter(|d| d.severity == Severity::Error).collect()
    }

    pub fn warnings(&self) -> Vec<&Diagnostic> {
        self.diagnostics.iter().filter(|d| d.severity == Severity::Warning).collect()
    }

    pub fn is_valid(&self) -> bool { self.errors().is_empty() }

    pub fn summary(&self) -> String {
        format!(
            "ValidationReport: {} error(s), {} warning(s), {} info(s)",
            self.errors().len(),
            self.warnings().len(),
            self.diagnostics.iter().filter(|d| d.severity == Severity::Info).count(),
        )
    }
}

// ── Validator ─────────────────────────────────────────────────────────────────

pub struct Validator;

impl Validator {
    pub fn validate(doc: &Document) -> ValidationReport {
        let mut rep = ValidationReport::new();
        for m in &doc.manifolds {
            Self::validate_manifold(m, &mut rep);
        }
        rep
    }

    fn validate_manifold(m: &Manifold, rep: &mut ValidationReport) {
        let path = format!("manifold.{}", m.name);

        // Collect known region names (flat + nested)
        let region_names  = collect_region_names(&m.regions);
        // Collect known bubble names
        let bubble_names: HashSet<String> = m.bubbles.iter().map(|b| b.name.clone()).collect();

        // Admissibility threshold
        match m.admissibility_threshold() {
            None => rep.push(Severity::Warning, &path,
                "admissibility-threshold not set; defaulting to 0.5"),
            Some(t) if !(0.0..=1.0).contains(&t) => rep.push(Severity::Error, &path,
                format!("admissibility-threshold {t} is out of [0,1]")),
            _ => {}
        }

        // Dimension
        if let Some(d) = m.dimension() {
            if d < 1.0 { rep.push(Severity::Error, &path, "dimension must be ≥ 1"); }
            if d.fract() != 0.0 { rep.push(Severity::Warning, &path,
                format!("non-integer dimension {d} — intentional?")); }
        }

        // Validate regions
        for r in &m.regions {
            Self::validate_region(r, &region_names, &format!("{path}.region.{}", r.name), rep);
        }

        // Validate top-level flows
        for f in &m.flows {
            Self::validate_flow(f, &region_names, &format!("{path}.flow.{}", f.name), rep);
        }

        // Validate top-level constraints
        for c in &m.constraints {
            Self::validate_constraint(c, &format!("{path}.constraint.{}", c.name), rep);
        }

        // Validate mappings
        for mp in &m.mappings {
            Self::validate_mapping(mp, &format!("{path}.mapping.{}", mp.name), rep);
        }

        // Validate relations (parent/child must be known bubble names)
        for rel in &m.relations {
            let rpath = format!("{path}.relation.{}", rel.name);
            if let Some(ref p) = rel.parent {
                if !bubble_names.contains(p) && !region_names.contains(p) {
                    rep.push(Severity::Error, &rpath,
                        format!("parent '{p}' does not refer to a known bubble or region"));
                }
            }
            if let Some(ref c) = rel.child {
                if !bubble_names.contains(c) && !region_names.contains(c) {
                    rep.push(Severity::Error, &rpath,
                        format!("child '{c}' does not refer to a known bubble or region"));
                }
            }
        }

        // Validate residuals (source must be a known region)
        for res in &m.residuals {
            let rpath = format!("{path}.residual.{}", res.name);
            if let Some(ref src) = res.source {
                if !region_names.contains(src) {
                    rep.push(Severity::Warning, &rpath,
                        format!("source '{src}' does not refer to a known region"));
                }
            }
            if let Some(coh) = res.coherence() {
                if !(0.0..=1.0).contains(&coh) {
                    rep.push(Severity::Error, &rpath,
                        format!("coherence {coh} is out of [0,1]"));
                }
            }
        }
    }

    fn validate_region(r: &Region, known: &HashSet<String>, path: &str, rep: &mut ValidationReport) {
        // Range checks
        check_range(r.entropy(),   path, "entropy",   0.0, 1.0, rep);
        check_range(r.salience(),  path, "salience",  0.0, 1.0, rep);
        check_range(r.density(),   path, "density",   0.0, 1.0, rep);

        // Xylomorphic info
        if r.is_xylomorphic() {
            rep.push(Severity::Info, path,
                "region is xylomorphic (salience > entropy): stable admissibility basin");
        } else if r.entropy().is_some() && r.salience().is_some() {
            rep.push(Severity::Info, path,
                "region is non-xylomorphic (entropy ≥ salience): potential dissolution zone");
        }

        // Curvature (no strict range, but warn on large values)
        if let Some(k) = r.curvature() {
            if k.abs() > 1.0 {
                rep.push(Severity::Warning, path,
                    format!("curvature {k} is large (|k| > 1); may indicate geometric instability"));
            }
        }

        // Validate nested flows and constraints
        for f in &r.flows {
            Self::validate_flow(f, known, &format!("{path}.flow.{}", f.name), rep);
        }
        for c in &r.constraints {
            Self::validate_constraint(c, &format!("{path}.constraint.{}", c.name), rep);
        }
        for sub in &r.sub_regions {
            Self::validate_region(sub, known, &format!("{path}.region.{}", sub.name), rep);
        }
    }

    fn validate_flow(f: &Flow, known: &HashSet<String>, path: &str, rep: &mut ValidationReport) {
        if let Some(ref o) = f.origin {
            if !known.contains(o) {
                rep.push(Severity::Warning, path,
                    format!("flow origin '{o}' does not refer to a known region"));
            }
        } else {
            rep.push(Severity::Warning, path, "flow has no origin specified");
        }
        if let Some(ref t) = f.target {
            if !known.contains(t) {
                rep.push(Severity::Warning, path,
                    format!("flow target '{t}' does not refer to a known region"));
            }
        } else {
            rep.push(Severity::Warning, path, "flow has no target specified");
        }
        check_range(f.persistence(), path, "persistence", 0.0, 1.0, rep);
    }

    fn validate_constraint(c: &Constraint, path: &str, rep: &mut ValidationReport) {
        if let Some(t) = c.threshold() {
            if !(0.0..=1.0).contains(&t) {
                rep.push(Severity::Warning, path,
                    format!("constraint threshold {t} outside [0,1]"));
            }
        }
        if let Some(mt) = c.max_torsion() {
            if mt < 0.0 {
                rep.push(Severity::Error, path,
                    format!("max-torsion {mt} must be non-negative"));
            }
        }
    }

    fn validate_mapping(mp: &Mapping, path: &str, rep: &mut ValidationReport) {
        if mp.source_space.is_none() {
            rep.push(Severity::Warning, path, "mapping has no source-space");
        }
        if mp.target_space.is_none() {
            rep.push(Severity::Warning, path, "mapping has no target-space");
        }
        if mp.preserve.is_empty() && mp.discard.is_empty() {
            rep.push(Severity::Info, path,
                "mapping specifies neither preserve nor discard properties");
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn collect_region_names(regions: &[Region]) -> HashSet<String> {
    let mut names = HashSet::new();
    for r in regions {
        names.insert(r.name.clone());
        names.extend(collect_region_names(&r.sub_regions));
    }
    names
}

fn check_range(val: Option<f64>, path: &str, field: &str, lo: f64, hi: f64, rep: &mut ValidationReport) {
    if let Some(v) = val {
        if !(lo..=hi).contains(&v) {
            rep.push(Severity::Error, path,
                format!("{field} {v} is out of [{lo},{hi}]"));
        }
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{token::Lexer, parser::Parser};

    fn validate(src: &str) -> ValidationReport {
        let tokens = Lexer::new(src).tokenize().unwrap();
        let doc    = Parser::new(tokens).parse_document().unwrap();
        Validator::validate(&doc)
    }

    #[test]
    fn valid_minimal() {
        let rep = validate("@manifold m { admissibility-threshold: 0.5 }");
        assert!(rep.is_valid());
    }

    #[test]
    fn invalid_threshold() {
        let rep = validate("@manifold m { admissibility-threshold: 1.5 }");
        assert!(!rep.is_valid());
    }

    #[test]
    fn dangling_flow_origin_is_warning() {
        let src = "@manifold m { flow f { origin: unknown  target: also_unknown } }";
        let rep = validate(src);
        assert!(!rep.warnings().is_empty());
    }

    #[test]
    fn xylomorphic_info() {
        let src = "@manifold m { region r { salience: 0.9  entropy: 0.2 } }";
        let rep = validate(src);
        let infos: Vec<_> = rep.diagnostics.iter().filter(|d| d.severity == Severity::Info).collect();
        assert!(!infos.is_empty());
        assert!(infos[0].message.contains("xylomorphic"));
    }
}
