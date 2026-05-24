// src/parser.rs
//
// MML recursive-descent parser.
// Consumes a SpannedToken stream from the Lexer and produces a Document AST.

use crate::token::{Span, SpannedToken, Token};
use crate::ast::*;

// ── Error ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct ParseError {
    pub msg:  String,
    pub span: Span,
}

impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ParseError at {}: {}", self.span, self.msg)
    }
}

type PResult<T> = Result<T, ParseError>;

// ── Parser ────────────────────────────────────────────────────────────────────

pub struct Parser {
    tokens: Vec<SpannedToken>,
    pos:    usize,
}

impl Parser {
    pub fn new(tokens: Vec<SpannedToken>) -> Self {
        Self { tokens, pos: 0 }
    }

    // ── Token navigation ───────────────────────────────────────────────────

    fn peek(&self) -> &Token {
        self.tokens.get(self.pos).map(|st| &st.token).unwrap_or(&Token::Eof)
    }

    fn span(&self) -> Span {
        self.tokens.get(self.pos).map(|st| st.span.clone())
            .unwrap_or(Span { line: 0, col: 0 })
    }

    fn advance(&mut self) -> &Token {
        let t = self.tokens.get(self.pos).map(|st| &st.token).unwrap_or(&Token::Eof);
        if self.pos < self.tokens.len() { self.pos += 1; }
        t
    }

    fn expect_lbrace(&mut self) -> PResult<()> {
        match self.peek() {
            Token::LBrace => { self.advance(); Ok(()) }
            t => Err(ParseError { msg: format!("expected '{{', got {t}"), span: self.span() })
        }
    }

    fn expect_colon(&mut self) -> PResult<()> {
        match self.peek() {
            Token::Colon => { self.advance(); Ok(()) }
            t => Err(ParseError { msg: format!("expected ':', got {t}"), span: self.span() })
        }
    }

    fn take_ident(&mut self) -> PResult<String> {
        match self.peek().clone() {
            Token::Ident(s)   => { let s = s.clone(); self.advance(); Ok(s) }
            Token::Keyword(s) => { let s = s.clone(); self.advance(); Ok(s) }
            t => Err(ParseError { msg: format!("expected identifier, got {t}"), span: self.span() })
        }
    }

    // ── Value parsing ──────────────────────────────────────────────────────

    fn parse_value(&mut self) -> PResult<Value> {
        match self.peek().clone() {
            Token::Number(n)     => { let n = n; self.advance(); Ok(Value::Number(n)) }
            Token::StringLit(s)  => { let s = s.clone(); self.advance(); Ok(Value::Text(s)) }
            Token::Bool(b)       => { let b = b; self.advance(); Ok(Value::Bool(b)) }
            Token::Ident(s)      => { let s = s.clone(); self.advance(); Ok(Value::Enum(s)) }
            Token::LBracket      => {
                self.advance(); // consume '['
                let mut items = Vec::new();
                while *self.peek() != Token::RBracket && *self.peek() != Token::Eof {
                    items.push(self.parse_value()?);
                }
                match self.peek() {
                    Token::RBracket => { self.advance(); }
                    t => return Err(ParseError {
                        msg: format!("expected ']', got {t}"), span: self.span()
                    }),
                }
                Ok(Value::List(items))
            }
            t => Err(ParseError { msg: format!("expected value, got {t}"), span: self.span() })
        }
    }

    // ── Generic field parser ───────────────────────────────────────────────
    // Reads key: value pairs until RBrace or a block keyword.

    fn parse_fields_until_rbrace(&mut self) -> PResult<Fields> {
        let mut fields = Fields::new();
        loop {
            match self.peek() {
                Token::RBrace | Token::Eof => break,
                // Stop when we see a nested block keyword
                Token::Keyword(_) | Token::At(_) => break,
                Token::Ident(_) => {
                    let key = self.take_ident()?;
                    self.expect_colon()?;
                    let val = self.parse_value()?;
                    fields.insert(key, val);
                }
                other => {
                    return Err(ParseError {
                        msg: format!("unexpected token in field list: {other}"),
                        span: self.span(),
                    });
                }
            }
        }
        Ok(fields)
    }

    // ── Block parsers ──────────────────────────────────────────────────────

    fn parse_flow(&mut self) -> PResult<Flow> {
        // flow <name> { ... }
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields = self.parse_fields_until_rbrace()?;
        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close flow '{name}', got {t}"),
                span: self.span(),
            }),
        }
        let origin = fields.get("origin").and_then(|v| v.as_str()).map(|s| s.to_string());
        let target = fields.get("target").and_then(|v| v.as_str()).map(|s| s.to_string());
        Ok(Flow { name, fields, origin, target })
    }

    fn parse_constraint(&mut self) -> PResult<Constraint> {
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields = self.parse_fields_until_rbrace()?;
        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close constraint '{name}', got {t}"),
                span: self.span(),
            }),
        }
        Ok(Constraint { name, fields })
    }

    fn parse_mapping(&mut self) -> PResult<Mapping> {
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields = self.parse_fields_until_rbrace()?;
        // preserve / discard are list values stored in fields
        let preserve = extract_str_list(&fields, "preserve");
        let discard  = extract_str_list(&fields, "discard");
        let source_space = fields.get("source-space").and_then(|v| v.as_str()).map(str::to_string);
        let target_space = fields.get("target-space").and_then(|v| v.as_str()).map(str::to_string);
        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close mapping '{name}', got {t}"),
                span: self.span(),
            }),
        }
        Ok(Mapping { name, source_space, target_space, preserve, discard, fields })
    }

    fn parse_bubble(&mut self) -> PResult<Bubble> {
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields = self.parse_fields_until_rbrace()?;
        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close bubble '{name}', got {t}"),
                span: self.span(),
            }),
        }
        Ok(Bubble { name, fields })
    }

    fn parse_relation(&mut self) -> PResult<Relation> {
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields = self.parse_fields_until_rbrace()?;
        let parent = fields.get("parent").and_then(|v| v.as_str()).map(str::to_string);
        let child  = fields.get("child").and_then(|v| v.as_str()).map(str::to_string);
        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close relation '{name}', got {t}"),
                span: self.span(),
            }),
        }
        Ok(Relation { name, parent, child, fields })
    }

    fn parse_residual(&mut self) -> PResult<Residual> {
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields = self.parse_fields_until_rbrace()?;
        let source = fields.get("source").and_then(|v| v.as_str()).map(str::to_string);
        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close residual '{name}', got {t}"),
                span: self.span(),
            }),
        }
        Ok(Residual { name, source, fields })
    }

    fn parse_region(&mut self) -> PResult<Region> {
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields       = self.parse_fields_until_rbrace()?;
        let mut flows    = Vec::new();
        let mut constraints = Vec::new();
        let mut sub_regions = Vec::new();

        loop {
            match self.peek().clone() {
                Token::RBrace | Token::Eof => { break; }
                Token::Keyword(ref k) if k == "flow" => {
                    self.advance();
                    flows.push(self.parse_flow()?);
                }
                Token::Keyword(ref k) if k == "constraint" => {
                    self.advance();
                    constraints.push(self.parse_constraint()?);
                }
                Token::Keyword(ref k) if k == "region" => {
                    self.advance();
                    sub_regions.push(self.parse_region()?);
                }
                // trajectories: [...] and constraints: [...] blocks
                Token::Ident(ref s) if s == "trajectories" || s == "constraints" => {
                    self.advance(); // key
                    self.expect_colon()?;
                    // consume '['
                    match self.peek() {
                        Token::LBracket => { self.advance(); }
                        _ => {}
                    }
                    // parse nested blocks until ']'
                    loop {
                        match self.peek() {
                            Token::RBracket | Token::Eof => { self.advance(); break; }
                            Token::Keyword(ref k) if k == "flow" => {
                                self.advance();
                                flows.push(self.parse_flow()?);
                            }
                            Token::Keyword(ref k) if k == "constraint" || k == "curvature-limit" || k == "entropy-pressure" => {
                                self.advance();
                                constraints.push(self.parse_constraint()?);
                            }
                            Token::Ident(_) => {
                                // bare ident acting as constraint name
                                let name = self.take_ident()?;
                                self.expect_lbrace()?;
                                let f = self.parse_fields_until_rbrace()?;
                                match self.peek() { Token::RBrace => { self.advance(); } _ => {} }
                                constraints.push(Constraint { name, fields: f });
                            }
                            t => {
                                return Err(ParseError {
                                    msg: format!("unexpected token in block list: {t}"),
                                    span: self.span(),
                                });
                            }
                        }
                    }
                }
                other => {
                    return Err(ParseError {
                        msg: format!("unexpected token in region '{name}': {other}"),
                        span: self.span(),
                    });
                }
            }
        }

        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close region '{name}', got {t}"),
                span: self.span(),
            }),
        }
        Ok(Region { name, fields, flows, constraints, sub_regions })
    }

    fn parse_manifold(&mut self, kind: String) -> PResult<Manifold> {
        let name = self.take_ident()?;
        self.expect_lbrace()?;
        let fields         = self.parse_fields_until_rbrace()?;
        let mut regions    = Vec::new();
        let mut flows      = Vec::new();
        let mut constraints = Vec::new();
        let mut mappings   = Vec::new();
        let mut bubbles    = Vec::new();
        let mut relations  = Vec::new();
        let mut residuals  = Vec::new();

        loop {
            match self.peek().clone() {
                Token::RBrace | Token::Eof => break,
                Token::Keyword(ref k) if k == "region"     => { self.advance(); regions.push(self.parse_region()?); }
                Token::Keyword(ref k) if k == "flow"       => { self.advance(); flows.push(self.parse_flow()?); }
                Token::Keyword(ref k) if k == "constraint" => { self.advance(); constraints.push(self.parse_constraint()?); }
                Token::Keyword(ref k) if k == "mapping"    => { self.advance(); mappings.push(self.parse_mapping()?); }
                Token::Keyword(ref k) if k == "bubble"     => { self.advance(); bubbles.push(self.parse_bubble()?); }
                Token::Keyword(ref k) if k == "relation"   => { self.advance(); relations.push(self.parse_relation()?); }
                Token::Keyword(ref k) if k == "residual"   => { self.advance(); residuals.push(self.parse_residual()?); }
                other => {
                    return Err(ParseError {
                        msg: format!("unexpected token in manifold '{name}': {other}"),
                        span: self.span(),
                    });
                }
            }
        }

        match self.peek() {
            Token::RBrace => { self.advance(); }
            t => return Err(ParseError {
                msg: format!("expected '}}' to close manifold '{name}', got {t}"),
                span: self.span(),
            }),
        }

        // Store the manifold kind (manifold / template) in fields for introspection
        let mut fields = fields;
        fields.entry("_kind".into()).or_insert(Value::Enum(kind));

        Ok(Manifold { name, fields, regions, flows, constraints, mappings, bubbles, relations, residuals })
    }

    // ── Top-level ──────────────────────────────────────────────────────────

    pub fn parse_document(&mut self) -> PResult<Document> {
        let mut manifolds = Vec::new();
        loop {
            match self.peek().clone() {
                Token::Eof => break,
                Token::At(ref kind) => {
                    let kind = kind.clone();
                    self.advance();
                    manifolds.push(self.parse_manifold(kind)?);
                }
                t => {
                    return Err(ParseError {
                        msg: format!("expected @keyword at top level, got {t}"),
                        span: self.span(),
                    });
                }
            }
        }
        Ok(Document { manifolds })
    }
}

// ── Helper ────────────────────────────────────────────────────────────────────

fn extract_str_list(fields: &Fields, key: &str) -> Vec<String> {
    fields.get(key)
        .and_then(|v| v.as_list())
        .map(|items| items.iter().filter_map(|v| v.as_str().map(str::to_string)).collect())
        .unwrap_or_default()
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::token::Lexer;

    fn parse(src: &str) -> Document {
        let tokens = Lexer::new(src).tokenize().expect("lex");
        Parser::new(tokens).parse_document().expect("parse")
    }

    #[test]
    fn parse_minimal_manifold() {
        let doc = parse("@manifold test { dimension: 3 }");
        assert_eq!(doc.manifolds.len(), 1);
        assert_eq!(doc.manifolds[0].name, "test");
        assert_eq!(doc.manifolds[0].dimension(), Some(3.0));
    }

    #[test]
    fn parse_region_with_flow() {
        let src = r#"
@manifold m {
    region r {
        entropy: 0.2
        flow f { origin: a  target: b  persistence: 0.9 }
    }
}
"#;
        let doc = parse(src);
        let r = &doc.manifolds[0].regions[0];
        assert_eq!(r.name, "r");
        assert_eq!(r.entropy(), Some(0.2));
        assert_eq!(r.flows[0].name, "f");
        assert_eq!(r.flows[0].persistence(), Some(0.9));
    }

    #[test]
    fn parse_mapping_preserve_discard() {
        let src = r#"
@manifold m {
    mapping proj {
        source-space: sensory
        target-space: symbolic
        preserve: [continuity, coherence]
        discard: [noise]
    }
}
"#;
        let doc = parse(src);
        let mp = &doc.manifolds[0].mappings[0];
        assert_eq!(mp.name, "proj");
        assert_eq!(mp.preserve, vec!["continuity", "coherence"]);
        assert_eq!(mp.discard, vec!["noise"]);
    }

    #[test]
    fn parse_bubble_and_relation() {
        let src = r#"
@manifold m {
    bubble a { density: 0.9 }
    bubble b { density: 0.7 }
    relation nest { parent: a  child: b  coupling: resonant }
}
"#;
        let doc = parse(src);
        assert_eq!(doc.manifolds[0].bubbles.len(), 2);
        assert_eq!(doc.manifolds[0].relations[0].parent, Some("a".into()));
    }

    #[test]
    fn parse_residual() {
        let src = r#"
@manifold m {
    region compressed { entropy: 0.4 }
    residual echo { source: compressed  persistence: fading  coherence: 0.28 }
}
"#;
        let doc = parse(src);
        let res = &doc.manifolds[0].residuals[0];
        assert_eq!(res.source, Some("compressed".into()));
        assert_eq!(res.coherence(), Some(0.28));
    }

    #[test]
    fn xylomorphic_criterion() {
        let src = "@manifold m { region stable { salience: 0.9  entropy: 0.2 } }";
        let doc  = parse(src);
        assert!(doc.manifolds[0].regions[0].is_xylomorphic());
    }
}
