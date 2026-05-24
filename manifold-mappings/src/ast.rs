// src/ast.rs
//
// MML Abstract Syntax Tree.
//
// Every structural concept in MML has a dedicated AST node.
// Numeric field values are stored as f64; string values as String;
// bool values as bool.  Unknown value types are stored as StringLit
// for forward compatibility.

use std::collections::HashMap;

// ── Value ───────────────────────────────────────────────────────────────────

/// A scalar value in an MML field.
#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Number(f64),
    Text(String),
    Bool(bool),
    /// A bare identifier used as an enum-like value (e.g. `compression: lossy`)
    Enum(String),
    /// An inline list of values (e.g. `preserve: [continuity, local-coherence]`)
    List(Vec<Value>),
}

impl Value {
    pub fn as_f64(&self) -> Option<f64> {
        if let Value::Number(n) = self { Some(*n) } else { None }
    }
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::Text(s) | Value::Enum(s) => Some(s),
            _ => None,
        }
    }
    pub fn as_bool(&self) -> Option<bool> {
        if let Value::Bool(b) = self { Some(*b) } else { None }
    }
    pub fn as_list(&self) -> Option<&[Value]> {
        if let Value::List(v) = self { Some(v) } else { None }
    }
}

impl std::fmt::Display for Value {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Value::Number(n)  => write!(f, "{n}"),
            Value::Text(s)    => write!(f, "\"{s}\""),
            Value::Bool(b)    => write!(f, "{b}"),
            Value::Enum(s)    => write!(f, "{s}"),
            Value::List(v)    => {
                write!(f, "[")?;
                for (i, e) in v.iter().enumerate() {
                    if i > 0 { write!(f, ", ")?; }
                    write!(f, "{e}")?;
                }
                write!(f, "]")
            }
        }
    }
}

// ── Field map ───────────────────────────────────────────────────────────────

/// Ordered key–value pairs for a block's scalar fields.
pub type Fields = HashMap<String, Value>;

// ── Flow ────────────────────────────────────────────────────────────────────

/// A directional semantic trajectory between two regions.
#[derive(Debug, Clone)]
pub struct Flow {
    pub name:   String,
    pub fields: Fields,
    /// Origin region / attractor name.
    pub origin: Option<String>,
    /// Target region / basin name.
    pub target: Option<String>,
}

impl Flow {
    pub fn persistence(&self) -> Option<f64> {
        self.fields.get("persistence").and_then(|v| v.as_f64())
    }
    pub fn compression(&self) -> Option<&str> {
        self.fields.get("compression").and_then(|v| v.as_str())
    }
    pub fn amplification(&self) -> Option<&str> {
        self.fields.get("amplification").and_then(|v| v.as_str())
    }
    pub fn phase_lock(&self) -> Option<&str> {
        self.fields.get("phase-lock").and_then(|v| v.as_str())
    }
}

// ── Constraint ───────────────────────────────────────────────────────────────

/// An admissibility constraint governing stability, collapse, and deformation.
#[derive(Debug, Clone)]
pub struct Constraint {
    pub name:   String,
    pub fields: Fields,
}

impl Constraint {
    pub fn threshold(&self) -> Option<f64> {
        self.fields.get("threshold").and_then(|v| v.as_f64())
    }
    pub fn max_torsion(&self) -> Option<f64> {
        self.fields.get("max-torsion").and_then(|v| v.as_f64())
    }
}

// ── Mapping ──────────────────────────────────────────────────────────────────

/// A projection between semantic spaces.
#[derive(Debug, Clone)]
pub struct Mapping {
    pub name:         String,
    pub source_space: Option<String>,
    pub target_space: Option<String>,
    /// Properties preserved under the projection.
    pub preserve:     Vec<String>,
    /// Properties discarded under the projection.
    pub discard:      Vec<String>,
    pub fields:       Fields,
}

// ── Region ───────────────────────────────────────────────────────────────────

/// A localised semantic basin within a manifold.
#[derive(Debug, Clone)]
pub struct Region {
    pub name:        String,
    pub fields:      Fields,
    pub flows:       Vec<Flow>,
    pub constraints: Vec<Constraint>,
    /// Nested sub-regions.
    pub sub_regions: Vec<Region>,
}

impl Region {
    pub fn entropy(&self)  -> Option<f64> { self.fields.get("entropy").and_then(|v| v.as_f64()) }
    pub fn salience(&self) -> Option<f64> { self.fields.get("salience").and_then(|v| v.as_f64()) }
    pub fn density(&self)  -> Option<f64> { self.fields.get("density").and_then(|v| v.as_f64()) }
    pub fn curvature(&self)-> Option<f64> { self.fields.get("curvature").and_then(|v| v.as_f64()) }

    /// True when xylomorphic: salience > entropy (Φ > S).
    pub fn is_xylomorphic(&self) -> bool {
        match (self.salience(), self.entropy()) {
            (Some(sal), Some(ent)) => sal > ent,
            _ => false,
        }
    }
}

// ── Bubble ───────────────────────────────────────────────────────────────────

/// A Spherepop bubble node.
#[derive(Debug, Clone)]
pub struct Bubble {
    pub name:   String,
    pub fields: Fields,
}

// ── Relation ─────────────────────────────────────────────────────────────────

/// A structural relation between two named entities (typically bubbles).
#[derive(Debug, Clone)]
pub struct Relation {
    pub name:    String,
    pub parent:  Option<String>,
    pub child:   Option<String>,
    pub fields:  Fields,
}

// ── Residual ─────────────────────────────────────────────────────────────────

/// A residual artifact that persists after compression.
#[derive(Debug, Clone)]
pub struct Residual {
    pub name:   String,
    pub source: Option<String>,
    pub fields: Fields,
}

impl Residual {
    pub fn persistence(&self) -> Option<&str> {
        self.fields.get("persistence").and_then(|v| v.as_str())
    }
    pub fn coherence(&self) -> Option<f64> {
        self.fields.get("coherence").and_then(|v| v.as_f64())
    }
}

// ── Manifold ─────────────────────────────────────────────────────────────────

/// The top-level MML document container.
#[derive(Debug, Clone)]
pub struct Manifold {
    pub name:        String,
    pub fields:      Fields,
    pub regions:     Vec<Region>,
    pub flows:       Vec<Flow>,
    pub constraints: Vec<Constraint>,
    pub mappings:    Vec<Mapping>,
    pub bubbles:     Vec<Bubble>,
    pub relations:   Vec<Relation>,
    pub residuals:   Vec<Residual>,
}

impl Manifold {
    pub fn dimension(&self) -> Option<f64> {
        self.fields.get("dimension").and_then(|v| v.as_f64())
    }
    pub fn topology(&self) -> Option<&str> {
        self.fields.get("topology").and_then(|v| v.as_str())
    }
    pub fn admissibility_threshold(&self) -> Option<f64> {
        self.fields.get("admissibility-threshold").and_then(|v| v.as_f64())
    }

    /// Collect all flows (top-level and nested inside regions).
    pub fn all_flows(&self) -> Vec<&Flow> {
        let mut out: Vec<&Flow> = self.flows.iter().collect();
        for r in &self.regions {
            collect_flows_region(r, &mut out);
        }
        out
    }

    /// Collect all constraints (top-level and nested).
    pub fn all_constraints(&self) -> Vec<&Constraint> {
        let mut out: Vec<&Constraint> = self.constraints.iter().collect();
        for r in &self.regions {
            collect_constraints_region(r, &mut out);
        }
        out
    }
}

fn collect_flows_region<'a>(r: &'a Region, out: &mut Vec<&'a Flow>) {
    out.extend(r.flows.iter());
    for sub in &r.sub_regions { collect_flows_region(sub, out); }
}

fn collect_constraints_region<'a>(r: &'a Region, out: &mut Vec<&'a Constraint>) {
    out.extend(r.constraints.iter());
    for sub in &r.sub_regions { collect_constraints_region(sub, out); }
}

/// A complete parsed MML document (may contain multiple manifolds).
#[derive(Debug, Clone)]
pub struct Document {
    pub manifolds: Vec<Manifold>,
}

impl Document {
    pub fn manifold(&self, name: &str) -> Option<&Manifold> {
        self.manifolds.iter().find(|m| m.name == name)
    }
}
